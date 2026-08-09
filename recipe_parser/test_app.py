"""
Tests voor het formulier: stap 1 zoekt recepten in geplakte tekst, stap 2 zet
de aangevinkte recepten op de lijst. Alle HTTP-verkeer is gemockt, dus er is
geen netwerk of Home Assistant nodig. Draai met:

    python -m unittest test_app.py -v
"""

import pathlib
import unittest
from unittest.mock import patch

import recipe_parser as rp

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"

VOEDINGSCENTRUM = "https://www.voedingscentrum.nl/recepten/gezond-recept/x.aspx"
LEUKERECEPTEN = "https://www.leukerecepten.nl/recepten/couscous-salade-met-feta/"


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, text="", status_code=200, url=""):
        self.text = text
        self.status_code = status_code
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            raise rp.requests.HTTPError(f"status {self.status_code}")


def fake_pages(mapping, default=None):
    """Geef per URL een andere pagina terug."""
    def _get(url, **kwargs):
        if url in mapping:
            return FakeResponse(text=load_fixture(mapping[url]))
        if default is not None:
            return FakeResponse(text=load_fixture(default))
        return FakeResponse(status_code=404)
    return _get


class IndexRouteTests(unittest.TestCase):
    def setUp(self):
        rp.app.config["TESTING"] = True
        self.client = rp.app.test_client()

    def test_get_shows_form_with_default_entity(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"todo.thuis", resp.data)

    def test_post_without_text_shows_error(self):
        resp = self.client.post("/", data={"text": "", "entity_id": "todo.thuis"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Plak eerst".encode(), resp.data)

    def test_post_with_text_but_no_recipe_shows_error(self):
        resp = self.client.post("/", data={"text": "wat eten we vandaag?"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Geen recepten gevonden".encode(), resp.data)

    @patch("recipe_parser.requests.get")
    def test_scan_lists_every_recipe_it_found(self, mock_get):
        mock_get.side_effect = fake_pages({
            VOEDINGSCENTRUM: "tagliatelle.html",
            LEUKERECEPTEN: "leukerecepten_couscoussalade.html",
        })
        pasted = (
            f"[05/07, 13:55] Bart: Ik kook vandaag dit!\n{VOEDINGSCENTRUM}\n"
            f"[05/07, 14:18] Lieke: {LEUKERECEPTEN}\n"
        )
        resp = self.client.post("/", data={"text": pasted})
        self.assertEqual(resp.status_code, 200)
        # Beide recepten staan aanvinkbaar in het overzicht.
        self.assertIn(VOEDINGSCENTRUM.encode(), resp.data)
        self.assertIn(LEUKERECEPTEN.encode(), resp.data)
        self.assertIn(b"05/07", resp.data)
        # En de samengevoegde lijst is alvast te zien.
        self.assertIn("Boodschappenlijst".encode(), resp.data)

    @patch("recipe_parser.requests.get")
    def test_scan_reports_a_link_it_could_not_fetch(self, mock_get):
        mock_get.side_effect = fake_pages({VOEDINGSCENTRUM: "tagliatelle.html"})
        pasted = f"{VOEDINGSCENTRUM}\nhttps://www.ah.nl/r/1196876\n"
        resp = self.client.post("/", data={"text": pasted})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"1196876", resp.data)
        self.assertIn("kon pagina niet ophalen".encode(), resp.data)
        # De rest gaat gewoon door: de ingrediënten van het andere recept
        # staan er wel.
        self.assertIn(b"Prei", resp.data)
        self.assertIn("Champignons".encode(), resp.data)

    @patch("recipe_parser.requests.get")
    def test_a_removed_recipe_says_so(self, mock_get):
        # Voedingscentrum stuurt verwijderde recepten naar /nl/404.aspx door,
        # maar met HTTP 200.
        removed = FakeResponse(
            text="<html><head><title>Pagina helaas niet gevonden</title></head>"
                 "<body></body></html>"
        )
        removed.url = "https://www.voedingscentrum.nl/nl/404.aspx"
        mock_get.return_value = removed

        resp = self.client.post("/", data={"text": VOEDINGSCENTRUM})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("bestaat niet meer".encode(), resp.data)

    def test_add_without_a_selected_recipe_shows_error(self):
        resp = self.client.post("/", data={"action": "add"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("minstens één recept".encode(), resp.data)

    @patch.object(rp, "SUPERVISOR_TOKEN", None)
    @patch("recipe_parser.requests.get")
    def test_add_without_supervisor_token_shows_warning(self, mock_get):
        mock_get.side_effect = fake_pages({VOEDINGSCENTRUM: "tagliatelle.html"})
        resp = self.client.post(
            "/", data={"action": "add", "recipe": VOEDINGSCENTRUM}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("geen SUPERVISOR_TOKEN".encode(), resp.data)

    @patch.object(rp, "SUPERVISOR_TOKEN", "test-token")
    @patch("recipe_parser._session")
    @patch("recipe_parser.requests.get")
    def test_add_puts_the_merged_list_on_the_todo_list(self, mock_get, mock_session):
        mock_get.side_effect = fake_pages({
            VOEDINGSCENTRUM: "tagliatelle.html",
            LEUKERECEPTEN: "leukerecepten_couscoussalade.html",
        })
        mock_post = mock_session.return_value.post
        mock_post.return_value = FakeResponse(status_code=200)

        resp = self.client.post("/", data={
            "action": "add",
            "recipe": [VOEDINGSCENTRUM, LEUKERECEPTEN],
            "entity_id": "todo.thuis",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("toegevoegd aan todo.thuis".encode(), resp.data)

        payloads = [call.kwargs["json"] for call in mock_post.call_args_list]
        titles = [p["item"] for p in payloads]
        # 10 + 10 ingredienten, maar Walnoten zit in beide recepten.
        self.assertEqual(len(titles), len(set(titles)), "geen dubbele artikelen")
        self.assertIn("Prei", titles)
        self.assertIn("Couscous", titles)

    @patch("recipe_parser.requests.get")
    def test_scan_puts_staples_in_their_own_group(self, mock_get):
        mock_get.side_effect = fake_pages({VOEDINGSCENTRUM: "tagliatelle.html"})
        resp = self.client.post("/", data={"text": VOEDINGSCENTRUM})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Waarschijnlijk in huis".encode(), resp.data)
        # Olie en peper hoeven niet mee, prei en spinazie wel.
        self.assertIn(b'name="pantry" value="Olie"', resp.data)
        self.assertNotIn(b'name="pantry" value="Prei"', resp.data)

    @patch.object(rp, "SUPERVISOR_TOKEN", "test-token")
    @patch("recipe_parser._session")
    @patch("recipe_parser.requests.get")
    def test_staples_are_skipped_unless_ticked(self, mock_get, mock_session):
        mock_get.side_effect = fake_pages({VOEDINGSCENTRUM: "tagliatelle.html"})
        mock_post = mock_session.return_value.post
        mock_post.return_value = FakeResponse(status_code=200)

        resp = self.client.post(
            "/", data={"action": "add", "recipe": VOEDINGSCENTRUM}
        )
        self.assertEqual(resp.status_code, 200)
        titles = [c.kwargs["json"]["item"] for c in mock_post.call_args_list]
        self.assertIn("Prei", titles)
        self.assertNotIn("Olie", titles)
        self.assertNotIn("Peper", titles)

    @patch.object(rp, "SUPERVISOR_TOKEN", "test-token")
    @patch("recipe_parser._session")
    @patch("recipe_parser.requests.get")
    def test_a_ticked_staple_is_added_after_all(self, mock_get, mock_session):
        mock_get.side_effect = fake_pages({VOEDINGSCENTRUM: "tagliatelle.html"})
        mock_post = mock_session.return_value.post
        mock_post.return_value = FakeResponse(status_code=200)

        resp = self.client.post("/", data={
            "action": "add",
            "recipe": VOEDINGSCENTRUM,
            "pantry": "Olie",
        })
        self.assertEqual(resp.status_code, 200)
        titles = [c.kwargs["json"]["item"] for c in mock_post.call_args_list]
        self.assertIn("Olie", titles)
        self.assertNotIn("Peper", titles)

    @patch.object(rp, "SUPERVISOR_TOKEN", "test-token")
    @patch("recipe_parser._session")
    @patch("recipe_parser.requests.get")
    def test_only_the_selected_recipes_are_added(self, mock_get, mock_session):
        mock_get.side_effect = fake_pages({
            VOEDINGSCENTRUM: "tagliatelle.html",
            LEUKERECEPTEN: "leukerecepten_couscoussalade.html",
        })
        mock_post = mock_session.return_value.post
        mock_post.return_value = FakeResponse(status_code=200)

        resp = self.client.post(
            "/", data={"action": "add", "recipe": LEUKERECEPTEN}
        )
        self.assertEqual(resp.status_code, 200)
        titles = [c.kwargs["json"]["item"] for c in mock_post.call_args_list]
        self.assertIn("Couscous", titles)
        self.assertNotIn("Prei", titles)


class DebugRouteTests(unittest.TestCase):
    def setUp(self):
        rp.app.config["TESTING"] = True
        self.client = rp.app.test_client()

    @patch.object(rp, "SUPERVISOR_TOKEN", None)
    def test_debug_without_token(self):
        resp = self.client.get("/debug")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data["supervisor_token_present"])
        self.assertIn("env_var_names", data)

    @patch.object(rp, "SUPERVISOR_TOKEN", "test-token")
    @patch("recipe_parser.requests.get")
    def test_debug_with_token_reachable(self, mock_get):
        mock_get.return_value = FakeResponse(text='{"message": "API running."}')
        resp = self.client.get("/debug")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["supervisor_token_present"])
        self.assertTrue(data["ha_api_reachable"])
        self.assertEqual(data["ha_api_status_code"], 200)

    @patch.object(rp, "SUPERVISOR_TOKEN", "test-token")
    @patch("recipe_parser.requests.get")
    def test_debug_with_token_unreachable(self, mock_get):
        mock_get.side_effect = rp.requests.ConnectionError("no route to host")
        resp = self.client.get("/debug")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["supervisor_token_present"])
        self.assertFalse(data["ha_api_reachable"])
        self.assertIn("no route to host", data["ha_api_error"])


if __name__ == "__main__":
    unittest.main()
