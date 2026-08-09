"""
Tests voor de voorraadkast: artikelen die je vrijwel altijd in huis hebt gaan
niet vanzelf naar de boodschappenlijst. Draai met:

    python -m unittest test_pantry.py -v
"""

import unittest

from recipe_parser import is_pantry_item, split_ingredient, split_pantry


class PowderVersusFreshTests(unittest.TestCase):
    """
    Het poeder staat in de kast, het verse product ligt in de winkel. Die twee
    lijken in tekst sterk op elkaar, dus dit is waar het snel misgaat.
    """

    def assertPantry(self, line, title):
        got_title, description = split_ingredient(line)
        self.assertEqual(got_title, title, line)
        self.assertTrue(is_pantry_item(got_title, description), f"{line} → kast")

    def assertShopping(self, line, title):
        got_title, description = split_ingredient(line)
        self.assertEqual(got_title, title, line)
        self.assertFalse(is_pantry_item(got_title, description), f"{line} → kopen")

    def test_garlic(self):
        self.assertPantry("1 tsp knoflookpoeder", "Knoflookpoeder")
        self.assertShopping("2 teentjes knoflook", "Knoflook")

    def test_onion(self):
        self.assertPantry("1 el uienpoeder", "Uienpoeder")
        self.assertShopping("1 grote ui", "Uien")

    def test_ginger(self):
        self.assertPantry("1 tsp gemberpoeder", "Gemberpoeder")
        self.assertShopping("3 cm verse gember", "Gember")

    def test_fennel(self):
        self.assertPantry("2 tl venkelzaad", "Venkelzaad")
        self.assertShopping("1 venkel, in reepjes", "Venkel")

    def test_coriander(self):
        self.assertPantry("1 tsp korianderpoeder", "Korianderzaad")
        self.assertShopping("1 bosje verse koriander", "Koriander")


class PantryTests(unittest.TestCase):
    def test_staples_are_recognised(self):
        for title in ("Zout", "Peper en zout", "Kaneel", "Bloem", "Soja saus",
                      "Olie", "Olijfolie", "Garam masala", "Laos", "Kardemom",
                      "Chilipoeder", "Bouillon"):
            self.assertTrue(is_pantry_item(title), f"{title} hoort voorraad te zijn")

    def test_the_spice_rack_from_the_orders(self):
        # Kruiden die daadwerkelijk in de kast staan (De Kruidenbaron).
        for title in ("Kruidnagel", "Sumak", "Berbere", "Karwijzaad",
                      "Nootmuskaat", "Italiaanse kruiden", "Provençaalse kruiden",
                      "Kerrie", "Nasi kruiden", "Kokosrasp", "Sesamzaad",
                      "Venkelzaad", "Korianderzaad", "Uienpoeder",
                      "Knoflookpoeder", "Asafoetida", "Thee"):
            self.assertTrue(is_pantry_item(title), f"{title} hoort voorraad te zijn")

    def test_normal_groceries_are_not(self):
        for title in ("Uien", "Kikkererwten", "Feta", "Spinazie", "Kip",
                      "Tomaten", "Pasta", "Melk"):
            self.assertFalse(is_pantry_item(title), f"{title} moet je wel kopen")

    def test_fresh_beats_the_pantry(self):
        # Een bosje verse kruiden koop je, ook al staat het gedroogde potje
        # in de kast.
        self.assertFalse(is_pantry_item("Basilicum", "5 g verse"))
        self.assertFalse(is_pantry_item("Koriander", "3 takjes verse"))

    def test_dried_herbs_are_in_the_cupboard(self):
        self.assertTrue(is_pantry_item("Basilicum", "1 tsp gedroogde"))
        self.assertTrue(is_pantry_item("Oregano", "4.9 ml gedroogde"))
        self.assertTrue(is_pantry_item("Tijm", "1 tl"))
        self.assertTrue(is_pantry_item("Peterselie", "1 el"))

    def test_a_bunch_or_a_sprig_means_fresh(self):
        # Zonder het woord "verse" verraadt de maat ook dat het vers moet zijn.
        self.assertFalse(is_pantry_item("Basilicum", "1 bosje"))
        self.assertFalse(is_pantry_item("Munt", "3 takjes"))
        self.assertFalse(is_pantry_item("Peterselie", "een handje"))
        self.assertFalse(is_pantry_item("Koriander", "2 blaadjes"))

    def test_a_recipe_asking_for_it_fresh_wins_from_one_asking_dried(self):
        # Twee recepten samengevoegd: dan koop je het verse bosje.
        self.assertFalse(is_pantry_item("Basilicum", "5 g verse + 1 tsp gedroogde"))

    def test_freshly_ground_pepper_is_still_pantry(self):
        # "vers gemalen" gaat over de molen, niet over verse peper kopen.
        self.assertTrue(is_pantry_item("Peper en zout", "1 pinch vers gemalen zwarte"))
        self.assertTrue(is_pantry_item("Peper", "vers gemalen"))

    def test_split_keeps_both_groups_in_order(self):
        shopping, pantry = split_pantry([
            ("Uien", "1"),
            ("Zout", "1 tsp"),
            ("Kikkererwten", "400 g"),
            ("Olijfolie", "3 tbsp"),
        ])
        self.assertEqual(shopping, [("Uien", "1"), ("Kikkererwten", "400 g")])
        self.assertEqual(pantry, [("Zout", "1 tsp"), ("Olijfolie", "3 tbsp")])

    def test_nothing_to_split(self):
        self.assertEqual(split_pantry([]), ([], []))


if __name__ == "__main__":
    unittest.main()
