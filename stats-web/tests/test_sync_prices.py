"""Tests de scripts/sync-prices.py (helpers puros, sin red)."""
import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

spec = importlib.util.spec_from_file_location(
    "sync_prices", SCRIPT_DIR / "scripts" / "sync-prices.py")
sp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sp)


API = {
    "opencode-go": {"models": {
        "glm-5.3": {"cost": {"input": 1.4, "output": 4.4, "cache_read": 0.26}},
        "step-5-preview": {"cost": {"input": 1, "output": 2.7, "cache_read": 0.1,
                                     "cache_write": 0.2}},
        "free-zero-model": {"cost": {"input": 0, "output": 0, "cache_read": 0}},
    }},
    "openai": {"models": {
        "gpt-5-nano": {"cost": {"input": 0.05, "output": 0.4, "cache_read": 0.005}},
    }},
    "anthropic": {"models": {
        "claude-fable-5-2": {"cost": {"input": 8, "output": 40, "cache_read": 0.2,
                                       "cache_write": 10}},
    }},
}


class PriceFromCostTests(unittest.TestCase):
    def test_basic_conversion(self):
        e = sp.price_from_cost({"input": 2, "output": 10, "cache_read": 0.2,
                                 "cache_write": 2.5})
        self.assertEqual(e, {"input": 2, "output": 10, "cache": 0.2, "cache_write": 2.5})

    def test_requires_input_output(self):
        self.assertIsNone(sp.price_from_cost({"input": 2, "cache_read": 0.2}))
        self.assertIsNone(sp.price_from_cost(None))


class BuildReportTests(unittest.TestCase):
    def setUp(self):
        self.costs = {
            # pendiente con uso -> fill desde opencode-go
            "glm-5.3": {"input": 0.0, "output": 0.0, "cache": 0.0},
            # precio-ado sin drift -> nada
            "gpt-5-nano": {"input": 0.05, "output": 0.4, "cache": 0.005},
            # precio-ado con drift -> reporte (no fill)
            "claude-fable-5-2": {"input": 4, "output": 40, "cache": 0.2},
            # pendiente cuyo match es gratis -> NO se llena
            "free-zero-model": {"input": 0.0, "output": 0.0, "cache": 0.0},
            # usado pero sin match
            "tencent/hy3": {"input": 0.14, "output": 0.58, "cache": 0.035},
        }
        self.used = {"glm-5.3", "step-5-preview", "gpt-5-nano",
                     "claude-fable-5-2", "free-zero-model", "tencent/hy3"}

    def test_classification(self):
        fills, drift, no_match = sp.build_report(self.costs, self.used, API)
        fill_models = {f["model"] for f in fills}
        self.assertEqual(fill_models, {"glm-5.3", "step-5-preview"})
        glm = [f for f in fills if f["model"] == "glm-5.3"][0]
        self.assertEqual(glm["provider"], "opencode-go")
        self.assertEqual(glm["price"]["input"], 1.4)
        # step-5-preview trae cache_write
        step = [f for f in fills if f["model"] == "step-5-preview"][0]
        self.assertEqual(step["price"]["cache_write"], 0.2)
        # drift solo para fable (ours 4/40 vs dev 8/40)
        self.assertEqual([d["model"] for d in drift], ["claude-fable-5-2"])
        self.assertEqual(no_match, ["tencent/hy3"])

    def test_free_pending_is_not_filled(self):
        fills, _, _ = sp.build_report(self.costs, self.used, API)
        self.assertNotIn("free-zero-model", {f["model"] for f in fills})

    def test_used_without_costs_entry_counts_as_pending(self):
        # canon usado sin entrada en costs -> se trata como pendiente y se llena
        fills, _, _ = sp.build_report(self.costs, {"step-5-preview"}, API)
        self.assertEqual([f["model"] for f in fills], ["step-5-preview"])


if __name__ == "__main__":
    unittest.main()
