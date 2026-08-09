"""
Tests voor de voorraadkast: artikelen die je vrijwel altijd in huis hebt gaan
niet vanzelf naar de boodschappenlijst. Draai met:

    python -m unittest test_pantry.py -v
"""

import unittest

from recipe_parser import is_pantry_item, split_pantry


class PantryTests(unittest.TestCase):
    def test_staples_are_recognised(self):
        for title in ("Zout", "Peper en zout", "Kaneel", "Bloem", "Soja saus",
                      "Olie", "Olijfolie", "Garam masala", "Laos", "Kardemom",
                      "Chilipoeder", "Bouillon"):
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

    def test_leafy_herbs_only_count_as_pantry_when_dried(self):
        self.assertTrue(is_pantry_item("Basilicum", "1 tsp gedroogde"))
        self.assertTrue(is_pantry_item("Oregano", "4.9 ml gedroogde"))
        # Zonder aanwijzing gaat een blaadjeskruid gewoon op de lijst.
        self.assertFalse(is_pantry_item("Basilicum", "1 bosje"))
        self.assertFalse(is_pantry_item("Munt", "3 takjes"))

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
