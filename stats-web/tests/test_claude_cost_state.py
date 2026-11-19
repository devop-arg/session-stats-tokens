"""Tests del parseo de cost-state de Claude Code (colisión [1m], cs inválido).

Ejecutar: python3 -m pytest stats-web/tests/test_claude_cost_state.py -q
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

import stats_common


def _write_jsonl(tmpdir, name, events):
    path = Path(tmpdir) / name
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    return path


def _session(files, session_id="test-sess"):
    return {
        "session_id": session_id,
        "files": files,
        "mtime": 0,
        "subagent_files": set(),
    }


class ClaudeCostStateTests(unittest.TestCase):
    def test_bracket_variant_cost_and_tokens_are_summed(self):
        # Caso real de claude_2e4fa758: opus[1m] y opus son facturaciones
        # separadas; con last-wins se perdía 10.8602 y ~18M de tokens.
        with tempfile.TemporaryDirectory() as tmp:
            f = _write_jsonl(tmp, "a.jsonl", [
                {"type": "assistant", "timestamp": "2026-11-01T00:00:00Z",
                 "message": {"id": "m1", "model": "claude-opus-5-5",
                             "usage": {"input_tokens": 10673, "output_tokens": 138276,
                                       "cache_read_input_tokens": 27897537,
                                       "cache_creation_input_tokens": 557923}}},
                {"type": "cost-state", "totalCostUSD": 23.7091034,
                 "modelUsage": {
                     "claude-opus-5-5[1m]": {"inputTokens": 10673, "outputTokens": 138276,
                                             "cacheReadInputTokens": 27897537,
                                             "cacheCreationInputTokens": 557923,
                                             "costUSD": 12.8437654},
                     "claude-haiku-5-5": {"inputTokens": 26588, "outputTokens": 5004,
                                          "cacheReadInputTokens": 0,
                                          "cacheCreationInputTokens": 0,
                                          "costUSD": 0.0051608},
                     "claude-opus-5-5": {"inputTokens": 6658, "outputTokens": 97142,
                                         "cacheReadInputTokens": 18576016,
                                         "cacheCreationInputTokens": 647174,
                                         "costUSD": 10.8601772},
                 }},
            ])
            stats = stats_common.get_claude_session_stats(_session([f]))
        opus = stats["by_model"]["claude-opus-5-5"]
        self.assertAlmostEqual(opus["cost"], 12.8437654 + 10.8601772, places=4)
        self.assertEqual(opus["input"], 10673 + 6658)
        self.assertEqual(opus["output"], 138276 + 97142)
        self.assertEqual(opus["cache_read"], 27897537 + 18576016)
        self.assertEqual(opus["cache_write"], 557923 + 647174)
        self.assertAlmostEqual(stats["cost"], 23.7091034, places=4)
        self.assertTrue(stats["has_real_cost"])

    def test_invalid_cost_state_does_not_wipe_tokens_or_cost(self):
        # Un cs final con totalCostUSD=0 no debe pisar el tramo facturado previo.
        with tempfile.TemporaryDirectory() as tmp:
            f = _write_jsonl(tmp, "a.jsonl", [
                {"type": "cost-state", "totalCostUSD": 10.0,
                 "modelUsage": {"claude-sonnet-4.5": {"inputTokens": 100,
                                                      "outputTokens": 50,
                                                      "cacheReadInputTokens": 1000,
                                                      "cacheCreationInputTokens": 10,
                                                      "costUSD": 10.0}}},
                {"type": "cost-state", "totalCostUSD": 0,
                 "modelUsage": {"claude-sonnet-4.5": {"inputTokens": 1,
                                                      "outputTokens": 1,
                                                      "cacheReadInputTokens": 0,
                                                      "cacheCreationInputTokens": 0,
                                                      "costUSD": 99.0}}},
            ])
            stats = stats_common.get_claude_session_stats(_session([f]))
        m = stats["by_model"]["claude-sonnet-4.5"]
        self.assertAlmostEqual(stats["cost"], 10.0, places=4)
        self.assertAlmostEqual(m["cost"], 10.0, places=4)
        self.assertEqual(m["input"], 100)
        self.assertEqual(m["cache_read"], 1000)

    def test_multiple_valid_cost_states_last_one_wins(self):
        # Los cs son acumulativos: el último válido reemplaza, no suma.
        with tempfile.TemporaryDirectory() as tmp:
            f = _write_jsonl(tmp, "a.jsonl", [
                {"type": "cost-state", "totalCostUSD": 10.0,
                 "modelUsage": {"claude-sonnet-4.5": {"inputTokens": 100,
                                                      "outputTokens": 50,
                                                      "cacheReadInputTokens": 1000,
                                                      "cacheCreationInputTokens": 10,
                                                      "costUSD": 10.0}}},
                {"type": "cost-state", "totalCostUSD": 20.0,
                 "modelUsage": {"claude-sonnet-4.5": {"inputTokens": 200,
                                                      "outputTokens": 100,
                                                      "cacheReadInputTokens": 2000,
                                                      "cacheCreationInputTokens": 20,
                                                      "costUSD": 20.0}}},
            ])
            stats = stats_common.get_claude_session_stats(_session([f]))
        m = stats["by_model"]["claude-sonnet-4.5"]
        self.assertAlmostEqual(stats["cost"], 20.0, places=4)
        self.assertEqual(m["input"], 200)
        self.assertEqual(m["cache_read"], 2000)
        self.assertAlmostEqual(m["cost"], 20.0, places=4)

    def test_no_cost_state_is_estimated(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = _write_jsonl(tmp, "a.jsonl", [
                {"type": "assistant", "timestamp": "2026-11-01T00:00:00Z",
                 "message": {"id": "m1", "model": "claude-sonnet-4.5",
                             "usage": {"input_tokens": 1000, "output_tokens": 100,
                                       "cache_read_input_tokens": 0,
                                       "cache_creation_input_tokens": 0}}},
            ])
            stats = stats_common.get_claude_session_stats(_session([f]))
        self.assertFalse(stats["has_real_cost"])
        self.assertGreater(stats["cost"], 0)

    def test_valid_cost_state_without_model_usage_keeps_previous(self):
        # Hardening B1: un cs válido sin modelUsage no debe borrar el
        # acumulado del cs anterior (el código pre-fix lo preservaba).
        with tempfile.TemporaryDirectory() as tmp:
            f = _write_jsonl(tmp, "a.jsonl", [
                {"type": "cost-state", "totalCostUSD": 10.0,
                 "modelUsage": {"claude-sonnet-4.5": {"inputTokens": 100,
                                                      "outputTokens": 50,
                                                      "cacheReadInputTokens": 1000,
                                                      "cacheCreationInputTokens": 10,
                                                      "costUSD": 10.0}}},
                {"type": "cost-state", "totalCostUSD": 20.0},
            ])
            stats = stats_common.get_claude_session_stats(_session([f]))
        m = stats["by_model"]["claude-sonnet-4.5"]
        self.assertAlmostEqual(stats["cost"], 20.0, places=4)  # real_cost sí avanza
        self.assertEqual(m["input"], 100)  # tokens conservados del cs anterior
        self.assertEqual(m["cache_read"], 1000)
        self.assertAlmostEqual(m["cost"], 10.0, places=4)


if __name__ == "__main__":
    unittest.main()
