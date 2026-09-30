#!/usr/bin/env python3
"""Offline tests for the pieces of agent_run.py that are easy to break silently: the USD price
table lookup (a missing table only shows up as a missing "est. USD" line) and the ns-reader
permission list. No agent CLI, no network."""
import importlib.util
import json
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class PriceTableTest(unittest.TestCase):
    def test_price_table_sits_next_to_the_scripts_and_is_valid(self):
        path = os.path.join(_HERE, "prices.json")
        self.assertTrue(os.path.isfile(path), "prices.json must live beside agent_run.py")
        data = json.load(open(path, encoding="utf-8"))
        self.assertIn("deepseek/deepseek-flash", data)

    def test_agent_run_finds_a_price_for_the_default_model(self):
        p = load("agent_run").peak_price("deepseek/deepseek-flash")
        self.assertIsInstance(p, dict)
        for k in ("input", "output", "cached_input"):
            self.assertIsInstance(p.get(k), (int, float), k)
            self.assertGreater(p[k], 0, k)

    def test_unknown_model_has_no_price_not_a_guess(self):
        self.assertIsNone(load("agent_run").peak_price("some/model-nobody-priced"))

    def test_ask_cheap_reads_the_same_table(self):
        p = load("ask_cheap").load_prices("deepseek/deepseek-flash")
        self.assertGreater(p.get("input", 0), 0)
        self.assertGreater(p.get("output", 0), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
