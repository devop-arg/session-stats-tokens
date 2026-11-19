"""Tests de recalculate_model_usage_costs (reglas de skip, dry-run, invariante).

Ejecutar: python3 -m pytest stats-web/tests/test_recalc_costs.py -q
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

import stats_common
from stats_common import init_db, recalculate_model_usage_costs, save_session


def _mk_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    import os
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.close()
    init_db(path)
    return path


def _set_price(model, entry):
    stats_common.MODEL_COSTS[model] = dict(entry)


def _del_price(model):
    stats_common.MODEL_COSTS.pop(model, None)


class RecalcCostsTests(unittest.TestCase):
    def setUp(self):
        self.db = _mk_db()
        _set_price("test-paid", {"input": 2, "output": 10, "cache": 0.1})
        _set_price("test-zero", {"input": 0.0, "output": 0.0, "cache": 0.0})

    def tearDown(self):
        _del_price("test-paid")
        _del_price("test-zero")
        Path(self.db).unlink(missing_ok=True)

    def _rows(self, path):
        conn = sqlite3.connect(path)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(sessions)")]
        sel = "id, cost, cost_source" if "cost_source" in cols else "id, cost, NULL"
        sess = conn.execute(f"SELECT {sel} FROM sessions").fetchall()
        mu = conn.execute(
            "SELECT session_id, model, cost FROM model_usage ORDER BY session_id, model"
        ).fetchall()
        conn.close()
        return sess, mu

    def test_dry_run_does_not_write(self):
        save_session("ses_a", "codex", "2026-01-01", 1000, 1, 1_000_000, 100_000,
                     0, 0, 999.0, {"test-paid": {"input": 1_000_000, "output": 100_000,
                                                 "cache": 0, "cost": 999.0}},
                     db_path=self.db, cost_source="estimated")
        conn = sqlite3.connect(self.db)
        result = recalculate_model_usage_costs(conn, dry_run=True)
        conn.close()
        self.assertGreater(result["updated"], 0)
        sess, mu = self._rows(self.db)
        self.assertEqual(sess[0][1], 999.0)
        self.assertEqual(mu[0][2], 999.0)

    def test_reported_session_is_never_touched(self):
        save_session("claude_a", "claude", "2026-01-01", 1000, 1, 50_000, 10_000,
                     100_000, 0, 7.77,
                     {"claude-test-model": {"input": 50_000, "output": 10_000,
                                            "cache": 100_000, "cache_read": 100_000,
                                            "cache_write": 0, "cost": 7.77}},
                     db_path=self.db, cache_read_tokens=100_000,
                     cost_source="reported")
        _set_price("claude-test-model", {"input": 4, "output": 20, "cache": 0.2,
                                         "cache_write": 8})
        conn = sqlite3.connect(self.db)
        result = recalculate_model_usage_costs(conn, dry_run=False)
        conn.close()
        self.assertEqual(result["skipped_reported"], 1)
        self.assertEqual(result["updated"], 0)
        sess, mu = self._rows(self.db)
        self.assertEqual(sess[0][1], 7.77)
        self.assertEqual(mu[0][2], 7.77)
        self.assertEqual(sess[0][2], "reported")

    def test_estimated_claude_session_is_recalculated_and_aligned(self):
        save_session("claude_b", "claude", "2026-01-01", 1000, 1, 50_000, 10_000,
                     100_000, 0, 99.0,
                     {"claude-test-model": {"input": 50_000, "output": 10_000,
                                            "cache": 100_000, "cache_read": 100_000,
                                            "cache_write": 0, "cost": 99.0}},
                     db_path=self.db, cache_read_tokens=100_000,
                     cost_source="estimated")
        _set_price("claude-test-model", {"input": 4, "output": 20, "cache": 0.2,
                                         "cache_write": 8})
        expected = 50_000 / 1e6 * 4 + 10_000 / 1e6 * 20 + 100_000 / 1e6 * 0.2
        conn = sqlite3.connect(self.db)
        result = recalculate_model_usage_costs(conn, dry_run=False)
        conn.close()
        self.assertEqual(result["updated"], 1)
        sess, mu = self._rows(self.db)
        self.assertAlmostEqual(mu[0][2], expected, places=4)
        self.assertAlmostEqual(sess[0][1], expected, places=4)
        # Invariante por sesión
        self.assertAlmostEqual(sess[0][1], mu[0][2], places=6)

    def test_zero_price_model_is_skipped_and_reported(self):
        save_session("ses_c", "opencode", "2026-01-01", 1000, 1, 500_000, 5_000,
                     100_000, 0, 0.0,
                     {"test-zero": {"input": 500_000, "output": 5_000,
                                    "cache": 100_000, "cost": 0.0}},
                     db_path=self.db, cache_read_tokens=100_000,
                     cost_source="estimated")
        conn = sqlite3.connect(self.db)
        result = recalculate_model_usage_costs(conn, dry_run=True)
        conn.close()
        self.assertEqual(result["updated"], 0)
        self.assertIn("test-zero", result["skipped_zero_price"])
        sess, mu = self._rows(self.db)
        self.assertEqual(mu[0][2], 0.0)
        self.assertEqual(sess[0][1], 0.0)

    def test_codex_semantics_exclude_cache_from_input(self):
        # codex: input_tokens incluye cache reads; se cobra input no-cacheado
        # + cache a precio cache.
        save_session("codex_d", "codex", "2026-01-01", 1000, 1, 1_000_000, 100_000,
                     900_000, 0, 0.0,
                     {"test-paid": {"input": 1_000_000, "output": 100_000,
                                    "cache": 900_000, "cost": 0.0}},
                     db_path=self.db, cost_source="estimated")
        expected = (1_000_000 - 900_000) / 1e6 * 2 + 100_000 / 1e6 * 10 \
            + 900_000 / 1e6 * 0.1
        conn = sqlite3.connect(self.db)
        result = recalculate_model_usage_costs(conn, dry_run=False)
        conn.close()
        self.assertEqual(result["updated"], 1)
        _, mu = self._rows(self.db)
        self.assertAlmostEqual(mu[0][2], expected, places=4)

    def test_apply_keeps_global_invariant_and_skips_empty_sessions(self):
        save_session("ses_e", "hermes", "2026-01-01", 1000, 1, 200_000, 20_000,
                     0, 0, 0.0,
                     {"test-paid": {"input": 200_000, "output": 20_000,
                                    "cache": 0, "cost": 0.0}},
                     db_path=self.db, cost_source="estimated")
        # Sesión sin filas en model_usage: no debe quedar en 0 (guarda EXISTS).
        conn = sqlite3.connect(self.db)
        conn.execute(
            "INSERT INTO sessions (id, source, date, timestamp, requests,"
            " input_tokens, output_tokens, cache_tokens, cost, cost_source)"
            " VALUES ('ses_empty', 'opencode', '2026-01-02', 2000, 1, 10, 10, 0,"
            " 5.5, 'estimated')"
        )
        conn.commit()
        result = recalculate_model_usage_costs(conn, dry_run=False)
        conn.close()
        self.assertEqual(result["updated"], 1)
        sess, mu = self._rows(self.db)
        self.assertAlmostEqual(mu[0][2], 200_000 / 1e6 * 2 + 20_000 / 1e6 * 10,
                               places=4)
        self.assertAlmostEqual(sess[0][1], mu[0][2], places=6)
        empty = [s for s in sess if s[0] == "ses_empty"][0]
        self.assertEqual(empty[1], 5.5)
        # Invariante global: solo cuentan sesiones CON filas en model_usage
        # (la sesión vacía conserva su costo, por eso EXISTS es obligatorio).
        conn = sqlite3.connect(self.db)
        sess_sum = conn.execute(
            "SELECT ROUND(SUM(s.cost),4) FROM sessions s"
            " WHERE EXISTS (SELECT 1 FROM model_usage mu WHERE mu.session_id=s.id)"
        ).fetchone()[0]
        mu_sum = conn.execute("SELECT ROUND(SUM(cost),4) FROM model_usage").fetchone()[0]
        conn.close()
        self.assertAlmostEqual(sess_sum, mu_sum, places=3)

    def test_apply_aligns_drift_without_price_changes(self):
        # M2: sin cambios de precio pero con drift en sessions.cost, el apply
        # igual debe ejecutar la alineación que el preview reportó.
        computed = 200_000 / 1e6 * 2 + 20_000 / 1e6 * 10  # 0.6
        save_session("ses_h", "hermes", "2026-01-01", 1000, 1, 200_000, 20_000,
                     0, 0, computed,
                     {"test-paid": {"input": 200_000, "output": 20_000,
                                    "cache": 0, "cost": computed}},
                     db_path=self.db, cost_source="estimated")
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE sessions SET cost=99.0 WHERE id='ses_h'")
        conn.commit()
        result = recalculate_model_usage_costs(conn, dry_run=True)
        self.assertEqual(result["updated"], 0)
        self.assertEqual(len(result["session_changes"]), 1)
        self.assertAlmostEqual(result["session_changes"][0]["new"], computed, places=4)
        result = recalculate_model_usage_costs(conn, dry_run=False)
        conn.close()
        self.assertEqual(result["updated"], 0)
        sess, mu = self._rows(self.db)
        self.assertAlmostEqual(sess[0][1], computed, places=4)
        self.assertAlmostEqual(mu[0][2], computed, places=4)

    def test_missing_cost_source_column_degrades_to_estimated(self):
        # Compatibilidad: sin migración, el recálculo no debe fallar.
        save_session("ses_f", "hermes", "2026-01-01", 1000, 1, 200_000, 20_000,
                     0, 0, 0.0,
                     {"test-paid": {"input": 200_000, "output": 20_000,
                                    "cache": 0, "cost": 0.0}},
                     db_path=self.db, cost_source="estimated")
        conn = sqlite3.connect(self.db)
        conn.execute("ALTER TABLE sessions DROP COLUMN cost_source")
        conn.commit()
        result = recalculate_model_usage_costs(conn, dry_run=True)
        conn.close()
        self.assertFalse(result["has_cost_source"])
        self.assertEqual(result["skipped_reported"], 0)
        self.assertEqual(result["updated"], 1)

    def test_legacy_mode_treats_claude_as_reported(self):
        # Sin columna cost_source, Claude se salta igual que en modo migrado.
        save_session("claude_g", "claude", "2026-01-01", 1000, 1, 50_000, 10_000,
                     100_000, 0, 7.77,
                     {"claude-test-model": {"input": 50_000, "output": 10_000,
                                            "cache": 100_000, "cache_read": 100_000,
                                            "cache_write": 0, "cost": 7.77}},
                     db_path=self.db, cache_read_tokens=100_000,
                     cost_source="reported")
        _set_price("claude-test-model", {"input": 4, "output": 20, "cache": 0.2,
                                         "cache_write": 8})
        conn = sqlite3.connect(self.db)
        conn.execute("ALTER TABLE sessions DROP COLUMN cost_source")
        conn.commit()
        result = recalculate_model_usage_costs(conn, dry_run=False)
        conn.close()
        self.assertFalse(result["has_cost_source"])
        self.assertEqual(result["skipped_reported"], 1)
        self.assertEqual(result["updated"], 0)
        sess, mu = self._rows(self.db)
        self.assertEqual(sess[0][1], 7.77)
        self.assertEqual(mu[0][2], 7.77)


if __name__ == "__main__":
    unittest.main()
