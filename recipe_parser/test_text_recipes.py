"""
Tests voor recepten die als tekst geplakt worden in plaats van als link,
zoals de recepten die met Claude gemaakt zijn en in de WhatsApp-groep
belanden. Draai met:

    python -m unittest test_text_recipes.py -v
"""

import unittest

from recipe_parser import (
    collect_recipes,
    find_text_recipes,
    ingredients_to_items,
    split_ingredient,
)

CURRY = """[19/07, 16:44] Bart Nieuwenhuijs: Noord-Indiase bonen-groentecurry met hing (asafoetida)

Een stevige, authentieke Punjabi-stijl curry met kikkererwten en veel groente.

INGREDIENTS
• 44 1/3 ml zonnebloemolie
• 1 grote ui, fijngesneden
• 3 knoflookteentjes, fijngehakt
• 400 g kikkererwten uit blik, afgespoeld
• 200 g verse spinazie

STEPS
1. Verhit 44 1/3 ml zonnebloemolie in een grote pan of wok op middelhoog vuur.
2. Voeg 1 grote ui, fijngesneden toe en bak 5-6 minuten tot goudbruin.

NOTES
Hing is sterk - een kwart theelepel is genoeg voor dit recept.
"""

FASOLAKIA = """[19/07, 16:48] Bart Nieuwenhuijs: Fasolakia - Griekse sperziebonen in tomatensaus met feta

Griekse fasolakia: sperziebonen gestoofd in tomatensaus.

INGREDIENTS
• 600 g sperziebonen, schoongemaakt
• 1 ui, gesnipperd
• 100 g feta, verkruimeld

STEPS
1. Verhit de olijfolie in een brede pan.

NOTES
Klassiek Grieks zomergerecht.
"""


class FindTextRecipesTests(unittest.TestCase):
    def test_reads_a_recipe_that_was_pasted_as_text(self):
        recipes = find_text_recipes(CURRY)
        self.assertEqual(len(recipes), 1)
        recipe = recipes[0]
        self.assertEqual(
            recipe["title"],
            "Noord-Indiase bonen-groentecurry met hing (asafoetida)",
        )
        self.assertEqual(recipe["date"], "19/07")
        self.assertEqual(recipe["ingredients"], [
            "44 1/3 ml zonnebloemolie",
            "1 grote ui, fijngesneden",
            "3 knoflookteentjes, fijngehakt",
            "400 g kikkererwten uit blik, afgespoeld",
            "200 g verse spinazie",
        ])

    def test_the_steps_and_notes_are_not_ingredients(self):
        ingredients = find_text_recipes(CURRY)[0]["ingredients"]
        joined = " ".join(ingredients)
        self.assertNotIn("Verhit", joined)
        self.assertNotIn("Hing is sterk", joined)

    def test_several_recipes_in_the_american_export_format(self):
        # Deze export schrijft tijd vóór datum; zonder herkenning van dat
        # formaat plakten twee recepten aan elkaar en verdween de tweede.
        recipes = find_text_recipes(
            "[3:37 PM, 8/9/2026] Bart: Sumaghiyya\n\n"
            "INGREDIENTS\n* 5 tbsp sumak\n* 1 ui\n\nSTEPS\n1. Koken.\n"
            "[3:41 PM, 8/9/2026] Bart: Insalata di farro\n\n"
            "INGREDIENTS\n* 300 g farro\n* 1 komkommer\n\nSTEPS\n1. Koken.\n"
        )
        self.assertEqual(len(recipes), 2)
        self.assertEqual(recipes[0]["title"], "Sumaghiyya")
        self.assertEqual(recipes[1]["title"], "Insalata di farro")
        self.assertEqual(recipes[1]["date"], "8/9")

    def test_several_pasted_recipes_at_once(self):
        recipes = find_text_recipes(CURRY + FASOLAKIA)
        self.assertEqual(len(recipes), 2)
        self.assertTrue(recipes[1]["title"].startswith("Fasolakia"))
        self.assertEqual(len(recipes[1]["ingredients"]), 3)

    def test_a_recipe_without_whatsapp_header(self):
        plain = "\n".join(CURRY.splitlines()[0].split(": ", 1)[1:] + CURRY.splitlines()[1:])
        recipes = find_text_recipes(plain)
        self.assertEqual(len(recipes), 1)
        self.assertEqual(recipes[0]["date"], "")
        self.assertEqual(len(recipes[0]["ingredients"]), 5)

    def test_dutch_heading_and_dash_bullets(self):
        recipes = find_text_recipes(
            "Snelle soep\n\nIngrediënten\n- 1 ui\n- 500 ml bouillon\n\nBereiding\n1. Koken.\n"
        )
        self.assertEqual(recipes[0]["ingredients"], ["1 ui", "500 ml bouillon"])

    def test_a_group_inside_the_list_does_not_end_it(self):
        # Van een site geplakt: de lijst heeft tussenkopjes en lege regels.
        # Alles onder "Sausmix" hoort er gewoon bij.
        recipes = find_text_recipes(
            "Kippenvleugels\n\nIngrediënten\nOp basis van 4 personen\n"
            "20 kippenvleugels\n1 el olie\n\nSausmix\n\n"
            "1 el lichte sojasaus\n1½ el suiker\n\n"
            "Extra benodigdheden\n\nAirfryer\n\n"
            "Informatie\nPrak de tofu in een kom.\n"
        )
        self.assertEqual(recipes[0]["ingredients"], [
            "20 kippenvleugels",
            "1 el olie",
            "1 el lichte sojasaus",
            "1½ el suiker",
        ])

    def test_loose_text_after_the_list_still_ends_it(self):
        recipes = find_text_recipes(
            "Curry\n\nINGREDIENTS\n- 1 ui\n- 400 g kikkererwten\n\n"
            "Lekker met rijst erbij en een frisse salade\n"
        )
        self.assertEqual(recipes[0]["ingredients"], ["1 ui", "400 g kikkererwten"])

    def test_text_without_an_ingredients_heading_is_not_a_recipe(self):
        self.assertEqual(find_text_recipes("Zullen we vanavond pizza halen?"), [])

    def test_kitchen_equipment_is_left_out(self):
        recipes = find_text_recipes(
            "Soep\n\nINGREDIENTS\n• 400 gr pompoen\n• Staafmixer\n\nSTEPS\n1. Koken.\n"
        )
        self.assertEqual(recipes[0]["ingredients"], ["400 gr pompoen"])


class PastedRecipeIngredientTests(unittest.TestCase):
    """De hoeveelheden in deze recepten hebben een eigen schrijfwijze."""

    def test_mixed_fractions(self):
        self.assertEqual(
            split_ingredient("44 1/3 ml zonnebloemolie"),
            ("Olie", "44 1/3 ml zonnebloemolie"),
        )
        self.assertEqual(
            split_ingredient("1 1/4 ml asafoetida (hing)"),
            ("Asafoetida", "1 1/4 ml (hing)"),
        )

    def test_english_units(self):
        self.assertEqual(split_ingredient("3 tbsp olijfolie"), ("Olijfolie", "3 tbsp"))
        self.assertEqual(
            split_ingredient("250 g Griekse yoghurt"), ("Yoghurt", "250 g Griekse")
        )
        self.assertEqual(
            ingredients_to_items(["1 pinch vers gemalen zwarte peper en zout"]),
            [("Zwarte peper", "1 pinch vers gemalen"), ("Zout", "1 pinch")],
        )

    def test_portion_words_are_not_repeated(self):
        self.assertEqual(
            split_ingredient("3 knoflookteentjes, fijngehakt"),
            ("Knoflook", "3, fijngehakt"),
        )
        self.assertEqual(
            split_ingredient("200 g bloemkoolroosjes"), ("Bloemkool", "200 g")
        )

    def test_a_different_product_is_still_kept(self):
        # "sap" en "filet" zijn geen portiewoorden, dus die info blijft staan.
        self.assertEqual(
            split_ingredient("2 eetlepels citroensap"),
            ("Citroen", "2 eetlepels citroensap"),
        )
        self.assertEqual(
            split_ingredient("200 gram kipfilet"), ("Kip", "200 gram kipfilet")
        )


class CollectRecipesTests(unittest.TestCase):
    def test_a_paste_with_only_text_recipes_needs_no_network(self):
        recipes = collect_recipes(CURRY + FASOLAKIA)
        self.assertEqual(len(recipes), 2)
        self.assertTrue(all(r["value"].startswith("tekst:") for r in recipes))
        self.assertTrue(all(not r["error"] for r in recipes))
        titles = [title for title, _ in recipes[0]["items"]]
        self.assertIn("Knoflook", titles)
        self.assertIn("Spinazie", titles)


if __name__ == "__main__":
    unittest.main()
