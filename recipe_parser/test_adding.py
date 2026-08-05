"""
Tests voor add_ingredients_to_todo(): de ingrediënten gaan in kleine groepjes
tegelijk naar Home Assistant, omdat elke todo.add_item pas terugkomt als Bring
het item heeft opgeslagen. Draai met:

    python -m unittest test_adding.py -v
"""

import threading
import time
import unittest
from unittest.mock import patch

import recipe_parser as rp

ITEMS = [(f"Artikel {i}", f"{i} gram") for i in range(11)]


class AddIngredientsTests(unittest.TestCase):
    def test_empty_list_does_nothing(self):
        self.assertEqual(rp.add_ingredients_to_todo("todo.thuis", []), (0, []))

    def test_all_items_are_added(self):
        added_titles = []
        lock = threading.Lock()

        def fake_add(entity_id, title, description=""):
            with lock:
                added_titles.append(title)

        with patch.object(rp, "add_ingredient_to_todo", fake_add):
            added, failed = rp.add_ingredients_to_todo("todo.thuis", ITEMS)

        self.assertEqual(added, len(ITEMS))
        self.assertEqual(failed, [])
        self.assertCountEqual(added_titles, [title for title, _ in ITEMS])

    def test_failures_are_reported_in_recipe_order(self):
        def fake_add(entity_id, title, description=""):
            if title in ("Artikel 7", "Artikel 2"):
                raise rp.requests.ConnectionError("kon niet toevoegen")

        with patch.object(rp, "add_ingredient_to_todo", fake_add):
            added, failed = rp.add_ingredients_to_todo("todo.thuis", ITEMS)

        self.assertEqual(added, len(ITEMS) - 2)
        self.assertEqual(failed, ["Artikel 2", "Artikel 7"])

    def test_a_failure_does_not_stop_the_rest(self):
        seen = []
        lock = threading.Lock()

        def fake_add(entity_id, title, description=""):
            with lock:
                seen.append(title)
            if title == "Artikel 0":
                raise rp.requests.ConnectionError("kon niet toevoegen")

        with patch.object(rp, "add_ingredient_to_todo", fake_add):
            rp.add_ingredients_to_todo("todo.thuis", ITEMS)

        self.assertEqual(len(seen), len(ITEMS))

    def test_items_are_added_concurrently(self):
        """Elf trage items mogen niet elf keer de wachttijd kosten."""
        latency = 0.2

        def slow_add(entity_id, title, description=""):
            time.sleep(latency)

        with patch.object(rp, "add_ingredient_to_todo", slow_add):
            start = time.perf_counter()
            rp.add_ingredients_to_todo("todo.thuis", ITEMS)
            elapsed = time.perf_counter() - start

        sequential = len(ITEMS) * latency
        self.assertLess(elapsed, sequential / 2)

    def test_concurrency_stays_within_the_limit(self):
        """Bring niet overvragen: nooit meer dan MAX_PARALLEL_ADDS tegelijk."""
        lock = threading.Lock()
        active = 0
        peak = 0

        def counting_add(entity_id, title, description=""):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(0.05)
            with lock:
                active -= 1

        with patch.object(rp, "add_ingredient_to_todo", counting_add):
            rp.add_ingredients_to_todo("todo.thuis", ITEMS)

        self.assertLessEqual(peak, rp.MAX_PARALLEL_ADDS)


if __name__ == "__main__":
    unittest.main()
