"""
Tests voor split_ingredient(): het splitsen van een ingrediëntregel in een
Bring-artikelnaam (titel) en de hoeveelheid/toelichting (omschrijving).
Draai met:

    python -m unittest test_split.py -v
"""

import unittest

from recipe_parser import split_ingredient


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

    def test_long_description_keeps_all_detail(self):
        title, description = split_ingredient(
            "150 gram rauwkost, zoals rodekool, witte kool en wortel (julienne of geraspt)"
        )
        self.assertEqual(title, "Rauwkost")
        self.assertIn("150 gram", description)
        self.assertIn("rodekool", description)

    def test_unknown_product_keeps_its_own_name(self):
        self.assertSplit("150 gram tempé", "Tempé", "150 gram")
        self.assertSplit("150 gram edamame (vers of diepvries, gekookt)",
                         "Edamame", "150 gram (vers of diepvries, gekookt)")


if __name__ == "__main__":
    unittest.main()
