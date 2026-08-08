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

from recipe_parser import extract_ingredients, normalize_url

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


class HeadingFallbackTests(unittest.TestCase):
    """Voor pagina's zonder schema.org-gegevens."""

    def test_heading_may_be_any_level(self):
        html = """
        <html><body>
          <h4>Ingrediënten</h4>
          <ul><li>150 gram quinoa</li><li>1 teentje knoflook</li></ul>
        </body></html>
        """
        self.assertEqual(
            extract_ingredients(html), ["150 gram quinoa", "1 teentje knoflook"]
        )

    def test_a_subheading_before_the_list_does_not_end_it(self):
        # 24baby.nl zet "Voor 2 personen" tussen de kop en de lijst.
        html = """
        <html><body>
          <h4>Ingrediënten</h4>
          <h2>Voor 2 personen</h2>
          <ul><li>150 gram quinoa</li><li>2 avocado's</li></ul>
          <h2>Bereiding</h2>
          <ul><li>Kook de quinoa.</li></ul>
        </body></html>
        """
        self.assertEqual(
            extract_ingredients(html), ["150 gram quinoa", "2 avocado's"]
        )

    def test_the_next_real_heading_ends_the_list(self):
        html = """
        <html><body>
          <h2>Ingrediënten</h2>
          <ul><li>1 ui</li></ul>
          <h2>Bereiding</h2>
          <ul><li>Snipper de ui.</li></ul>
        </body></html>
        """
        self.assertEqual(extract_ingredients(html), ["1 ui"])

    def test_navigation_lists_are_skipped(self):
        html = """
        <html><body>
          <h2>Ingrediënten</h2>
          <nav><ul><li>Recepten</li><li>Inspiratie</li></ul></nav>
          <ul><li>1 ui</li></ul>
        </body></html>
        """
        self.assertEqual(extract_ingredients(html), ["1 ui"])

    def test_whole_paragraphs_are_not_ingredients(self):
        html = (
            "<html><body><h2>Ingrediënten</h2><ul>"
            "<li>1 ui</li><li>" + ("bereidingstekst " * 30) + "</li>"
            "</ul></body></html>"
        )
        self.assertEqual(extract_ingredients(html), ["1 ui"])


class NormalizeUrlTests(unittest.TestCase):
    def test_albert_heijn_share_link_is_rewritten(self):
        self.assertEqual(
            normalize_url("https://www.ah.nl/r/1196876"),
            "https://www.ah.nl/allerhande/recept/R-R1196876",
        )
        self.assertEqual(
            normalize_url("http://ah.nl/r/921580/"),
            "https://www.ah.nl/allerhande/recept/R-R921580",
        )

    def test_other_links_are_left_alone(self):
        for url in (
            "https://www.ah.nl/allerhande/recept/R-R1195514/romige-kip",
            "https://share.google/Hq97N61gRKZ0tiANx",
            "https://www.leukerecepten.nl/recepten/pompoensoep/",
        ):
            self.assertEqual(normalize_url(url), url)


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

    def test_json_ld_with_a_raw_newline_inside_a_string(self):
        # savorysweets.nl levert JSON met een letterlijke regelovergang in een
        # tekst. Strikt genomen ongeldig, maar de ingrediënten kloppen wel.
        html = (
            '<html><head><script type="application/ld+json">'
            '{"@type":"Recipe","name":"Stamppot",'
            '"description":"regel een\nregel twee",'
            '"recipeIngredient":["3 pastinaken","1 pompoen"]}'
            "</script></head><body></body></html>"
        )
        self.assertEqual(extract_ingredients(html), ["3 pastinaken", "1 pompoen"])

    def test_json_ld_with_a_charset_in_the_type_attribute(self):
        html = (
            '<html><head><script type="application/ld+json; charset=UTF-8">'
            '{"@type":"Recipe","recipeIngredient":["1 ui"]}'
            "</script></head><body></body></html>"
        )
        self.assertEqual(extract_ingredients(html), ["1 ui"])

    def test_legacy_schema_org_ingredients_key(self):
        # libelle-lekker.be gebruikt nog "ingredients" i.p.v. "recipeIngredient".
        html = (
            '<html><head><script type="application/ld+json">'
            '{"@type":"Recipe","name":"Penne","ingredients":["400g penne","1 sjalot"]}'
            "</script></head><body></body></html>"
        )
        self.assertEqual(extract_ingredients(html), ["400g penne", "1 sjalot"])

    def test_legacy_key_is_ignored_outside_a_recipe(self):
        # "ingredients" is een te algemeen woord om overal te vertrouwen.
        html = (
            '<html><head><script type="application/ld+json">'
            '{"@type":"Product","ingredients":["water","suiker"]}'
            "</script></head><body></body></html>"
        )
        self.assertEqual(extract_ingredients(html), [])

    def test_kitchen_equipment_is_not_a_shopping_item(self):
        html = """
        <html><head><script type="application/ld+json">
        {"@type":"Recipe","recipeIngredient":["400 gr pompoen","Staafmixer"]}
        </script></head><body></body></html>
        """
        self.assertEqual(extract_ingredients(html), ["400 gr pompoen"])


if __name__ == "__main__":
    unittest.main()
