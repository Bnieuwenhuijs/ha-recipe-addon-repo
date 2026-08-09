"""
Tests voor het verwerken van meerdere recepten in één keer: links uit geplakte
tekst vissen en artikelen die in meerdere recepten voorkomen samenvoegen.
Draai met:

    python -m unittest test_multi.py -v
"""

import unittest

from recipe_parser import find_recipe_links, merge_items

# Zoals het uit WhatsApp komt: tijdstempels, namen, tekst om de link heen,
# en links die op een eigen regel onder het bericht staan.
WHATSAPP = """[05/07, 13:43] Lieke 💕: Ik eet vandaag: Tortilla's met vissticks, salade en ananassalsa #AlbertHeijn https://www.ah.nl/r/1196876
[05/07, 13:55] Bart Nieuwenhuijs: Ik kook vandaag Aardappel-knolselderijgratin van het Voedingscentrum!
https://www.voedingscentrum.nl/recepten/gezond-recept/aardappel-knolselderijgratin.aspx
[05/07, 14:18] Bart Nieuwenhuijs: https://www.leukerecepten.nl/recepten/kikkererwten-curry/
[12/07, 12:40] Bart Nieuwenhuijs: Ik kook vandaag Bruine bonen in kruidige tomatensaus van het Voedingscentrum!
https://www.voedingscentrum.nl/recepten/gezond-recept/bruine-bonen-in-kruidige-tomatensaus.aspx
[31/07, 18:51] Lieke 💕: https://mobiel.voedingscentrum.nl/recepten/gezond-recept/spinazielasagne-met-hazelnoten.aspx
"""


class FindRecipeLinksTests(unittest.TestCase):
    def test_finds_every_link_in_a_whatsapp_export(self):
        links = find_recipe_links(WHATSAPP)
        self.assertEqual(len(links), 5)
        self.assertEqual(links[0]["url"], "https://www.ah.nl/r/1196876")
        self.assertTrue(links[4]["url"].startswith("https://mobiel.voedingscentrum.nl/"))

    def test_takes_the_date_from_the_message_the_link_belongs_to(self):
        links = find_recipe_links(WHATSAPP)
        dates = [link["date"] for link in links]
        self.assertEqual(dates, ["05/07", "05/07", "05/07", "12/07", "31/07"])

    def test_a_link_on_its_own_line_keeps_the_date_of_the_message_above_it(self):
        links = find_recipe_links(
            "[12/07, 12:40] Bart: Ik kook dit vandaag!\n"
            "https://www.voedingscentrum.nl/recepten/gezond-recept/x.aspx\n"
        )
        self.assertEqual(links[0]["date"], "12/07")

    def test_link_in_the_middle_of_a_sentence(self):
        links = find_recipe_links("kijk eens: https://site.nl/recept lekker toch?")
        self.assertEqual(links[0]["url"], "https://site.nl/recept")

    def test_trailing_punctuation_is_not_part_of_the_link(self):
        links = find_recipe_links("dit wordt het: https://site.nl/recept.")
        self.assertEqual(links[0]["url"], "https://site.nl/recept")

    def test_the_same_link_twice_becomes_one_recipe(self):
        links = find_recipe_links(
            "https://site.nl/recept\nen nog eens https://site.nl/recept\n"
        )
        self.assertEqual(len(links), 1)

    def test_a_plain_url_still_works(self):
        links = find_recipe_links("https://www.leukerecepten.nl/recepten/pompoensoep/")
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["date"], "")

    def test_text_without_links(self):
        self.assertEqual(find_recipe_links("wat eten we vandaag?"), [])

    def test_other_whatsapp_timestamp_formats(self):
        # Het formaat verschilt per telefoon en taalinstelling.
        varianten = {
            "[05/07, 13:43] Lieke: kijk": "05/07",
            "[3:23 PM, 8/9/2026] Bart: kijk": "8/9",
            "[8/9/2026, 3:23 PM] Bart: kijk": "8/9",
            "8-9-2026 15:23 - Bart: kijk": "8-9",
        }
        for regel, datum in varianten.items():
            links = find_recipe_links(f"{regel} https://site.nl/recept")
            self.assertEqual(links[0]["date"], datum, regel)


class MergeItemsTests(unittest.TestCase):
    def test_same_product_from_several_recipes_becomes_one_line(self):
        merged = merge_items([
            [("Knoflook", "2 tenen"), ("Uien", "1")],
            [("Knoflook", "1 teentje")],
            [("Knoflook", "2 teentjes"), ("Spinazie", "200 gr")],
        ])
        self.assertEqual(
            dict(merged),
            {
                "Knoflook": "2 tenen + 1 teentje + 2 teentjes",
                "Uien": "1",
                "Spinazie": "200 gr",
            },
        )

    def test_identical_amounts_are_kept_because_they_count(self):
        # Drie recepten die elk 1 ui willen, betekent drie uien kopen.
        merged = merge_items([[("Uien", "1")], [("Uien", "1")], [("Uien", "1")]])
        self.assertEqual(merged, [("Uien", "1 + 1 + 1")])

    def test_products_without_an_amount_stay_empty(self):
        merged = merge_items([[("Peper", "")], [("Peper", "")]])
        self.assertEqual(merged, [("Peper", "")])

    def test_order_follows_the_first_time_a_product_appears(self):
        merged = merge_items([
            [("Uien", "1"), ("Prei", "100 gram")],
            [("Kaas", "40 gram"), ("Uien", "2")],
        ])
        self.assertEqual([title for title, _ in merged], ["Uien", "Prei", "Kaas"])

    def test_nothing_to_merge(self):
        self.assertEqual(merge_items([]), [])


if __name__ == "__main__":
    unittest.main()
