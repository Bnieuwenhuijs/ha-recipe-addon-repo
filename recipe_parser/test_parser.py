"""
Lokale tests voor extract_ingredients(), gebaseerd op HTML-fixtures die
1-op-1 zijn overgenomen uit live voedingscentrum.nl-receptpagina's
(zie fixtures/*.html). Draai met:

    python -m unittest test_parser.py -v

Zo kan de extractielogica getest worden zonder de add-on in Home
Assistant te hoeven herbouwen en zonder live netwerktoegang.
"""

import pathlib
import unittest

from recipe_parser import extract_ingredients

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


class ExtractIngredientsTests(unittest.TestCase):
    def test_tagliatelle_two_columns(self):
        html = load_fixture("tagliatelle.html")
        ingredients = extract_ingredients(html)
        self.assertEqual(
            ingredients,
            [
                "200 gram volkoren tagliatelle",
                "100 gram prei",
                "300 gram spinazie",
                "250 gram champignons",
                "1 teentje knoflook",
                "150 gram tempé",
                "peper",
                "1 eetlepel olie",
                "20 gram hüttenkäse",
                "20 gram oude kaas 30+ (geraspt)",
            ],
        )

    def test_chinese_kool_uneven_columns(self):
        html = load_fixture("chinese_kool.html")
        ingredients = extract_ingredients(html)
        self.assertEqual(len(ingredients), 7)
        self.assertEqual(ingredients[0], "200 gram gedroogde linzen")
        self.assertEqual(ingredients[-1], "2 eetlepels ongezouten pinda's")

    def test_lasagnesoep_many_ingredients(self):
        html = load_fixture("lasagnesoep.html")
        ingredients = extract_ingredients(html)
        self.assertEqual(len(ingredients), 17)
        self.assertIn("1 ui", ingredients)
        self.assertIn("20 gram jonge kaas 30+ (geraspt)", ingredients)

    def test_does_not_include_bereiding_steps(self):
        html = load_fixture("tagliatelle.html")
        ingredients = extract_ingredients(html)
        joined = " ".join(ingredients)
        self.assertNotIn("verpakking", joined)

    def test_no_match_returns_empty_list(self):
        self.assertEqual(extract_ingredients("<html><body>geen recept</body></html>"), [])


class JsonLdSourcesTests(unittest.TestCase):
    """
    Leukerecepten.nl en ah.nl zetten hun recept niet in de HTML maar in een
    schema.org JSON-LD-blok.
    """

    def test_leukerecepten(self):
        ingredients = extract_ingredients(
            load_fixture("leukerecepten_couscoussalade.html")
        )
        self.assertEqual(len(ingredients), 10)
        self.assertIn("300 gr couscous", ingredients)
        self.assertIn("1 bosje verse munt", ingredients)

    def test_albert_heijn(self):
        ingredients = extract_ingredients(load_fixture("ah_orzosalade.html"))
        self.assertEqual(len(ingredients), 9)
        self.assertIn("250 g burrata", ingredients)
        self.assertIn("0.5 el honing", ingredients)

    def test_json_ld_inside_a_graph_is_found(self):
        html = """
        <html><head><script type="application/ld+json">
        {"@context":"https://schema.org","@graph":[
          {"@type":"WebPage"},
          {"@type":"Recipe","recipeIngredient":["2 uien","500 g gehakt"]}
        ]}
        </script></head><body></body></html>
        """
        self.assertEqual(extract_ingredients(html), ["2 uien", "500 g gehakt"])

    def test_broken_json_ld_does_not_crash(self):
        html = """
        <html><head>
        <script type="application/ld+json">{ dit is geen json ]</script>
        <script type="application/ld+json">
        {"@type":"Recipe","recipeIngredient":["1 komkommer"]}
        </script>
        </head><body></body></html>
        """
        self.assertEqual(extract_ingredients(html), ["1 komkommer"])

    def test_kitchen_equipment_is_not_a_shopping_item(self):
        html = """
        <html><head><script type="application/ld+json">
        {"@type":"Recipe","recipeIngredient":["400 gr pompoen","Staafmixer"]}
        </script></head><body></body></html>
        """
        self.assertEqual(extract_ingredients(html), ["400 gr pompoen"])


if __name__ == "__main__":
    unittest.main()
