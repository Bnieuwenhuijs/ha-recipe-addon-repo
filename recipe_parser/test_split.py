"""
Tests voor split_ingredient(): het splitsen van een ingrediëntregel in een
Bring-artikelnaam (titel) en de hoeveelheid/toelichting (omschrijving).
Draai met:

    python -m unittest test_split.py -v
"""

import unittest

from recipe_parser import ingredients_to_items, split_ingredient


class SplitIngredientTests(unittest.TestCase):
    def assertSplit(self, text, title, description):
        self.assertEqual(split_ingredient(text), (title, description))

    def test_simple_amount_and_product(self):
        self.assertSplit("400 gram prei", "Prei", "400 gram")
        self.assertSplit("100 gram prei", "Prei", "100 gram")
        self.assertSplit("300 gram spinazie", "Spinazie", "300 gram")

    def test_unit_with_word_amount(self):
        self.assertSplit("1 teentje knoflook", "Knoflook", "1 teentje")
        self.assertSplit("2 eetlepels sesamolie", "Olie", "2 eetlepels sesamolie")

    def test_fraction_amount(self):
        self.assertSplit("½ courgette", "Courgette", "½")

    def test_product_without_amount_has_no_description(self):
        self.assertSplit("peper", "Peper", "")
        self.assertSplit("chilivlokken", "Chillipeper", "")

    def test_singular_recipe_word_maps_to_plural_bring_name(self):
        self.assertSplit("1 ui", "Uien", "1")
        self.assertSplit("1 tomaat", "Tomaten", "1")

    def test_synonym_maps_to_bring_name(self):
        self.assertSplit("20 gram hüttenkäse", "Huttenkaas", "20 gram")
        self.assertSplit("2 bosuien", "Bosui / Lente-ui", "2")
        self.assertSplit(
            "200 gram volkoren tagliatelle", "Pasta", "200 gram volkoren tagliatelle"
        )

    def test_qualifier_after_product_does_not_become_the_title(self):
        # "zout" mag hier niet als artikel gekozen worden - sojasaus staat voorop.
        self.assertSplit(
            "1 eetlepel sojasaus met minder zout",
            "Soja saus",
            "1 eetlepel met minder zout",
        )
        self.assertSplit(
            "200 gram tomatenblokjes zonder zout (blik)",
            "Tomatenblokjes",
            "200 gram zonder zout (blik)",
        )

    def test_description_does_not_repeat_the_title(self):
        self.assertSplit("200 gram groenten", "Groenten", "200 gram")
        self.assertSplit("100 gram radijs", "Radijzen", "100 gram")
        self.assertSplit("1 appel", "Appels", "1")
        self.assertSplit("20 gram ongezouten walnoten", "Walnoten", "20 gram ongezouten")

    def test_description_keeps_words_that_add_information(self):
        # "verse", "halfvolle" en "vloeibare" staan niet in de titel en zeggen
        # wel iets over wat je moet kopen.
        self.assertSplit("5 gram verse basilicum", "Basilicum", "5 gram verse")
        self.assertSplit("3 eetlepels halfvolle yoghurt", "Yoghurt", "3 eetlepels halfvolle")
        self.assertSplit(
            "1 eetlepel vloeibare margarine", "Margarine", "1 eetlepel vloeibare"
        )

    def test_more_specific_product_is_never_dropped(self):
        # De titel is algemener dan wat het recept vraagt, dus dat detail moet blijven.
        self.assertSplit("200 gram kipfilet", "Kip", "200 gram kipfilet")
        self.assertSplit(
            "250 gram zilvervliesrijst", "Rijst", "250 gram zilvervliesrijst"
        )

    def test_parenthesised_prefix_does_not_pick_the_wrong_product(self):
        self.assertSplit("2 eetlepels (olijf)olie", "Olijfolie", "2 eetlepels")
        title, _ = split_ingredient("½ (groente)bouillontablet met minder zout")
        self.assertEqual(title, "Bouillon")

    def test_a_bracket_inside_a_word_does_not_cut_off_the_name(self):
        # "(wijn)azijn" is één woord; "(geraspt)" is een opmerking.
        self.assertSplit("2 eetlepel witte (wijn)azijn", "Azijn",
                         "2 eetlepel witte (wijn)azijn")
        self.assertSplit("120 gram (winter)wortel", "Wortelen",
                         "120 gram (winter)wortel")
        title, description = split_ingredient("20 gram oude kaas 30+ (geraspt)")
        self.assertEqual(title, "Kaas")
        self.assertIn("(geraspt)", description)

    def test_a_colour_before_or_is_not_the_product(self):
        title, _ = split_ingredient("1 gele of rode paprika, in kleine blokjes")
        self.assertEqual(title, "Paprika")
        title, _ = split_ingredient("1 rode of gele ui")
        self.assertEqual(title, "Uien")

    def test_colours_that_belong_to_the_product_stay(self):
        self.assertSplit("1 blik witte bonen", "Witte bonen", "1 blik")
        self.assertSplit("1 rode biet", "Rode biet", "1")
        title, _ = split_ingredient("1 rode peper")
        self.assertEqual(title, "Chillipeper")

    def test_long_description_keeps_all_detail(self):
        title, description = split_ingredient(
            "150 gram rauwkost, zoals rodekool, witte kool en wortel (julienne of geraspt)"
        )
        self.assertEqual(title, "Rauwkost")
        self.assertIn("150 gram", description)
        self.assertIn("rodekool", description)

    def test_a_range_counts_as_one_amount(self):
        self.assertSplit("2-3 eetlepels misopasta", "Miso", "2-3 eetlepels")
        self.assertSplit("2 tot 3 teentjes knoflook", "Knoflook", "2 tot 3 teentjes")
        title, description = split_ingredient("2 à 3 blokjes tofu")
        self.assertEqual(title, "Tofu")
        self.assertEqual(description, "2 à 3 blokjes")

    def test_an_approximation_before_the_amount(self):
        self.assertSplit("Ongeveer 150 gram quinoa", "Quinoa", "Ongeveer 150 gram")
        self.assertSplit("ca. 200 g bloem", "Bloem", "ca. 200 g")
        self.assertSplit("ruim 500 ml water", "Water", "ruim 500 ml")

    def test_a_plain_amount_is_not_read_as_a_range(self):
        # De "a" van "appels" mag geen bereik beginnen.
        self.assertSplit("2 appels", "Appels", "2")
        self.assertSplit("3 tomaten", "Tomaten", "3")

    def test_brand_names_do_not_become_the_title(self):
        self.assertSplit("200 g Go-Tan whole wheat noodles", "Noedels",
                         "200 g Go-Tan whole wheat noodles")
        title, _ = split_ingredient("1 pak Go-Tan bami")
        self.assertEqual(title, "Noedels")

    def test_wine_vinegar_is_vinegar_not_wine(self):
        self.assertSplit("2 el witte wijn azijn", "Azijn", "2 el witte wijn")
        self.assertSplit("1 el witte wijnazijn", "Azijn", "1 el witte wijnazijn")
        # Wijn zelf blijft wijn.
        self.assertSplit("100 ml witte wijn", "Witte wijn", "100 ml")

    def test_units_used_by_leukerecepten_and_ah(self):
        # "gr", "g", "el", "tl", "blokje", "scheutje", "krop", "teen", "snuf"
        self.assertSplit("300 gr couscous", "Couscous", "300 gr")
        self.assertSplit("100 g rucola", "Rucola", "100 g")
        self.assertSplit("3 el balsamico", "Balsamico", "3 el")
        self.assertSplit("0.5 el honing", "Honing", "0.5 el")
        self.assertSplit("1 scheutje olijfolie", "Olijfolie", "1 scheutje")
        self.assertSplit("1 teen knoflook", "Knoflook", "1 teen")

    def test_pasta_shapes_map_to_pasta(self):
        self.assertSplit("300 gr fusilli pasta", "Pasta", "300 gr fusilli")
        title, _ = split_ingredient("300 g biologische volkorenorzo")
        self.assertEqual(title, "Pasta")

    def test_rice_noodles_are_noodles_not_rice(self):
        title, _ = split_ingredient("225 g rijstnoedels")
        self.assertEqual(title, "Noedels")

    def test_pepper_and_salt_become_two_items(self):
        # Twee producten, dus twee regels - allebei voorraad overigens.
        self.assertEqual(
            ingredients_to_items(["1 snuf peper en zout"]),
            [("Peper", "1 snuf"), ("Zout", "1 snuf")],
        )
        self.assertEqual(
            ingredients_to_items(["1 pinch zout en peper, naar smaak"]),
            [("Zout", "1 pinch, naar smaak"), ("Peper", "1 pinch, naar smaak")],
        )

    def test_an_en_that_is_not_two_products_is_left_alone(self):
        # Alleen splitsen als beide helften een bekend artikel zijn.
        self.assertEqual(len(ingredients_to_items(["1 blik mais en bonen mix"])), 1)
        title, description = split_ingredient(
            "150 gram rauwkost, zoals rodekool, witte kool en wortel"
        )
        self.assertEqual(title, "Rauwkost")

    def test_leading_qualifiers_are_moved_to_the_description(self):
        self.assertSplit("2 biologische limoenen", "Limoen", "2 biologische")
        self.assertSplit("2 el donkere basterdsuiker", "Basterdsuiker", "2 el donkere")

    def test_catalog_names_starting_with_a_qualifier_still_match(self):
        # "Zoete aardappelen" en "Witte bonen" mogen niet tot "Aardappelen"
        # en "Bonen" worden afgekapt.
        self.assertSplit("500 gram zoete aardappelen", "Zoete aardappelen", "500 gram")
        self.assertSplit("1 blik witte bonen", "Witte bonen", "1 blik")

    def test_unknown_product_keeps_its_own_name(self):
        self.assertSplit("150 gram tempé", "Tempé", "150 gram")
        self.assertSplit("150 gram edamame (vers of diepvries, gekookt)",
                         "Edamame", "150 gram (vers of diepvries, gekookt)")


if __name__ == "__main__":
    unittest.main()
