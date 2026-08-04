"""
Tests voor de / (formulier) route, met gemockte requests.get/requests.post
zodat er geen netwerktoegang (naar het recept of naar Home Assistant) nodig
is. Draai met:

    python -m unittest test_app.py -v
"""

import pathlib
import unittest
from unittest.mock import patch

import recipe_parser as rp

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


class FakeResponse:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise rp.requests.HTTPError(f"status {self.status_code}")


class IndexRouteTests(unittest.TestCase):
    def setUp(self):
        rp.app.config["TESTING"] = True
        self.client = rp.app.test_client()

    def test_get_shows_form_with_default_entity(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"todo.thuis", resp.data)

    @patch.object(rp, "SUPERVISOR_TOKEN", None)
    @patch("recipe_parser.requests.get")
    def test_post_without_supervisor_token_shows_warning(self, mock_get):
        mock_get.return_value = FakeResponse(text=load_fixture("tagliatelle.html"))
        resp = self.client.post(
            "/", data={"url": "https://example.com/recept", "entity_id": "todo.thuis"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("geen SUPERVISOR_TOKEN".encode(), resp.data)
        self.assertIn("200 gram volkoren tagliatelle".encode(), resp.data)

    @patch.object(rp, "SUPERVISOR_TOKEN", "test-token")
    @patch("recipe_parser.requests.post")
    @patch("recipe_parser.requests.get")
    def test_post_with_supervisor_token_adds_items(self, mock_get, mock_post):
        mock_get.return_value = FakeResponse(text=load_fixture("chinese_kool.html"))
        mock_post.return_value = FakeResponse(status_code=200)
        resp = self.client.post(
            "/", data={"url": "https://example.com/recept", "entity_id": "todo.thuis"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_post.call_count, 7)
        self.assertIn("Alle 7 ingrediënten toegevoegd".encode(), resp.data)

    @patch.object(rp, "SUPERVISOR_TOKEN", None)
    def test_post_without_url_shows_error(self):
        resp = self.client.post("/", data={"url": "", "entity_id": "todo.thuis"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Vul een recept-URL in".encode(), resp.data)


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
