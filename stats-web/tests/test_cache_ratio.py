import datetime
import importlib.util
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_DIR))

import stats_common
from stats_common import calculate_session_cache_ratio


class SessionCacheRatioTests(unittest.TestCase):
    def test_short_session_is_eligible_even_with_zero_ratio(self):
        result = calculate_session_cache_ratio([
            {
                "session_id": "short",
                "session_requests": 4,
                "source": "hermes",
                "model": "m",
                "input_tokens": 1000,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
            },
        ])

        self.assertEqual(result["eligible_sessions"], 1)
        self.assertEqual(result["excluded_sessions"], 0)
        self.assertEqual(result["ratio"], 0.0)

    def test_below_five_percent_excludes_at_five_requests(self):
        result = calculate_session_cache_ratio([
            {
                "session_id": "low",
                "session_requests": 5,
                "source": "hermes",
                "model": "m",
                "input_tokens": 9500,
                "cache_read_tokens": 499,
                "cache_write_tokens": 0,
            },
        ])

        self.assertEqual(result["eligible_sessions"], 0)
        self.assertEqual(result["excluded_sessions"], 1)
        self.assertEqual(result["ratio"], 0.0)

    def test_exactly_five_percent_is_eligible_without_rounding(self):
        result = calculate_session_cache_ratio([
            {
                "session_id": "exact",
                "session_requests": 5,
                "source": "hermes",
                "model": "m",
                "input_tokens": 9500,
                "cache_read_tokens": 500,
                "cache_write_tokens": 0,
            },
        ])

        self.assertEqual(result["eligible_sessions"], 1)
        self.assertEqual(result["ratio"], 5.0)

    def test_zero_denominator_depends_on_request_guard(self):
        result = calculate_session_cache_ratio([
            {
                "session_id": "many",
                "session_requests": 5,
                "source": "hermes",
                "model": "m1",
                "input_tokens": 0,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
            },
            {
                "session_id": "few",
                "session_requests": 4,
                "source": "hermes",
                "model": "m2",
                "input_tokens": 0,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
            },
        ])

        self.assertEqual(result["eligible_sessions"], 1)
        self.assertEqual(result["excluded_sessions"], 1)

    def test_legacy_fallback_counts_but_cache_write_only_does_not(self):
        result = calculate_session_cache_ratio([
            {
                "session_id": "legacy",
                "session_requests": 5,
                "source": "hermes",
                "model": "legacy_model",
                "input_tokens": 1900,
                "cache_tokens": 100,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
            },
            {
                "session_id": "write-only",
                "session_requests": 5,
                "source": "hermes",
                "model": "write_model",
                "input_tokens": 100,
                "cache_tokens": 0,
                "cache_read_tokens": 0,
                "cache_write_tokens": 100,
            },
        ])

        self.assertEqual(result["eligible_sessions"], 1)
        self.assertEqual(result["excluded_sessions"], 1)
        self.assertEqual(result["by_model"]["legacy_model"]["cache_read_tokens"], 100)

    def test_multi_model_session_is_filtered_as_one_unit(self):
        result = calculate_session_cache_ratio([
            {
                "session_id": "mixed",
                "session_requests": 10,
                "source": "hermes",
                "model": "mixed_model_a",
                "input_tokens": 100,
                "cache_read_tokens": 900,
                "cache_write_tokens": 0,
            },
            {
                "session_id": "mixed",
                "session_requests": 10,
                "source": "hermes",
                "model": "mixed_model_b",
                "input_tokens": 200_000,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
            },
        ])

        self.assertEqual(result["eligible_sessions"], 0)
        self.assertEqual(result["excluded_sessions"], 1)
        self.assertEqual(result["by_model"], {})

    def test_eligible_session_keeps_hit_and_miss_in_model_denominator(self):
        result = calculate_session_cache_ratio([
            {
                "session_id": "hit-miss",
                "session_requests": 10,
                "source": "hermes",
                "model": "same_model",
                "input_tokens": 100,
                "cache_read_tokens": 900,
                "cache_write_tokens": 0,
            },
            {
                "session_id": "hit-miss",
                "session_requests": 10,
                "source": "hermes",
                "model": "same_model",
                "input_tokens": 9000,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
            },
        ])

        self.assertEqual(result["eligible_sessions"], 1)
        self.assertEqual(result["by_model"]["same_model"]["cache_read_tokens"], 900)
        self.assertEqual(result["by_model"]["same_model"]["ratio"], 9.0)

    def test_codex_keeps_input_including_cache_as_denominator(self):
        result = calculate_session_cache_ratio([
            {
                "session_id": "codex",
                "session_requests": 5,
                "source": "codex",
                "model": "gpt-5.6",
                "input_tokens": 1000,
                "cache_tokens": 900,
                "cache_read_tokens": 900,
                "cache_write_tokens": 0,
            },
        ])

        self.assertEqual(result["ratio"], 90.0)
        self.assertEqual(result["by_model"]["gpt-5.6"]["ratio_input_tokens"], 1000)

    def test_session_requests_are_canonical_not_model_request_sum(self):
        result = calculate_session_cache_ratio([
            {
                "session_id": "canonical-requests",
                "session_requests": 5,
                "requests": 1,
                "source": "hermes",
                "model": "m1",
                "input_tokens": 9500,
                "cache_read_tokens": 499,
            },
            {
                "session_id": "canonical-requests",
                "session_requests": 5,
                "requests": 1,
                "source": "hermes",
                "model": "m2",
                "input_tokens": 100,
                "cache_read_tokens": 0,
            },
        ])

        self.assertEqual(result["eligible_sessions"], 0)


class EndpointCacheRatioTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "fixture.db"
        stats_common.init_db(self.db_path)
        now = int(time.time()) - 600
        date = datetime.datetime.fromtimestamp(now).isoformat()
        sessions = [
            ("excluded", "hermes", date, now, 5, 9500, 10, 499, 0, 1.0, 499, 0),
            ("eligible", "hermes", date, now + 1, 5, 1_000_000, 10, 100_000, 0, 2.0, 100_000, 0),
            ("mixed", "hermes", date, now + 2, 10, 200_100, 10, 900, 0, 3.0, 900, 0),
        ]
        model_usage = [
            ("excluded", "excluded_model", 5, 9500, 10, 499, 0, 1.0, 499, 0),
            ("eligible", "eligible_model", 5, 900_000, 10, 100_000, 0, 1.5, 100_000, 0),
            ("eligible", "eligible_miss", 0, 100_000, 0, 0, 0, 0.5, 0, 0),
            ("mixed", "mixed_model_a", 5, 100, 10, 900, 0, 0.2, 900, 0),
            ("mixed", "mixed_model_b", 5, 200_000, 0, 0, 0, 0.3, 0, 0),
        ]
        conn = sqlite3.connect(self.db_path)
        conn.executemany(
            """INSERT INTO sessions
               (id, source, date, timestamp, requests, input_tokens, output_tokens,
                cache_tokens, reasoning_tokens, cost, cache_read_tokens, cache_write_tokens)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            sessions,
        )
        conn.executemany(
            """INSERT INTO model_usage
               (session_id, model, requests, input_tokens, output_tokens,
                cache_tokens, reasoning_tokens, cost, cache_read_tokens, cache_write_tokens)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            model_usage,
        )
        conn.commit()
        conn.close()

        self.previous_db_path = stats_common.DB_PATH
        self.previous_init_db = stats_common.init_db
        stats_common.DB_PATH = self.db_path
        stats_common.init_db = lambda *args, **kwargs: None
        module_path = SCRIPT_DIR / "stats-web" / "main.py"
        module_name = f"session_stats_test_main_{id(self)}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        assert spec is not None and spec.loader is not None
        self.main = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.main)
        setattr(self.main, "DB_PATH", self.db_path)

    def tearDown(self):
        stats_common.DB_PATH = self.previous_db_path
        stats_common.init_db = self.previous_init_db
        self.tempdir.cleanup()

    def test_endpoints_filter_ratios_but_keep_consumption(self):
        recalc_stub = {
            "total_sessions": 3,
            "total_requests": 20,
            "total_input": 1_209_600,
            "total_input_uncached": 1_208_700,
            "total_output": 30,
            "total_cache_read": 101_399,
            "total_tokens": 1_311_029,
            "total_cost": 6.0,
            "cache_ratio": 9.1,
            "models_totals": {},
        }
        with patch.object(self.main, "recalculate_historical_cost", return_value=recalc_stub):
            summary = self.main.api_summary()
        today = self.main.api_today_summary(range="today")
        top30 = self.main._build_top_models_payload(days=30, bucket="day", limit=20)
        top12 = self.main._build_top_models_payload(days=364, bucket="week", limit=20)
        cache = self.main.api_cache_ratio()

        self.assertEqual(summary["total_sessions"], 3)
        self.assertEqual(summary["total_requests"], 20)
        self.assertEqual(summary["total_input_tokens"], 1_209_600)
        self.assertEqual(summary["cache_ratio"], 9.1)
        self.assertEqual(today["total_sessions"], 3)
        self.assertEqual(today["total_requests"], 20)
        self.assertEqual(today["total_input_tokens"], 1_209_600)
        self.assertEqual(today["cache_ratio"], 9.1)

        today_models = {row["model"]: row for row in today["top_models"]}
        self.assertEqual(today_models["eligible_model"]["cache_ratio"], 10.0)
        self.assertEqual(today_models["excluded_model"]["cache_ratio"], 0.0)
        self.assertEqual(today_models["mixed_model_a"]["cache_ratio"], 0.0)

        for payload in (top30, top12):
            self.assertEqual(payload["cache_ratio"], 9.1)
            leaders = {row["model"]: row for row in payload["leaderboard"]}
            self.assertEqual(leaders["eligible_model"]["cache_ratio"], 10.0)
            self.assertEqual(leaders["excluded_model"]["cache_ratio"], 0.0)
            self.assertEqual(leaders["mixed_model_a"]["cache_ratio"], 0.0)

        self.assertEqual(cache["overall"], {
            "ratio": 9.1,
            "cached": 100_000,
            "uncached": 1_000_000,
        })
        cache_models = {row["model"]: row for row in cache["models"]}
        self.assertEqual(cache_models["eligible_model"]["input_tokens"], 1_000_000)
        self.assertEqual(cache_models["eligible_model"]["cache_tokens"], 100_000)
        self.assertEqual(cache_models["eligible_model"]["ratio"], 10.0)
        self.assertNotIn("excluded_model", cache_models)
        self.assertNotIn("mixed_model_a", cache_models)

    def test_cache_write_exposed_gated_by_billable_source(self):
        """El campo cache_write_tokens de leaderboard/today usa solo fuentes
        con write facturable aparte (claude/hermes); para otras fuentes el
        write guardado NO se expone (no entra al Total ni al ratio)."""
        conn = sqlite3.connect(self.db_path)
        date = datetime.datetime.now().isoformat()
        now = int(time.time()) - 300
        conn.execute(
            "INSERT INTO sessions (id, source, date, timestamp, requests, input_tokens,"
            " output_tokens, cache_tokens, reasoning_tokens, cost, cache_read_tokens,"
            " cache_write_tokens) VALUES (?, 'claude', ?, ?, 1, 100, 50, 0, 0, 1.0, 8000, 4000)",
            ("claude_sess", date, now),
        )
        conn.execute(
            "INSERT INTO model_usage (session_id, model, requests, input_tokens,"
            " output_tokens, cache_tokens, reasoning_tokens, cost, cache_read_tokens,"
            " cache_write_tokens) VALUES ('claude_sess', 'claude_model', 1, 100, 50, 0, 0, 1.0, 8000, 4000)",
        )
        # Fuente NO billable con write guardado: no debe exponerse.
        conn.execute(
            "INSERT INTO sessions (id, source, date, timestamp, requests, input_tokens,"
            " output_tokens, cache_tokens, reasoning_tokens, cost, cache_read_tokens,"
            " cache_write_tokens) VALUES (?, 'opencode', ?, ?, 1, 100, 50, 0, 0, 1.0, 0, 9999)",
            ("oc_sess", date, now + 1),
        )
        conn.execute(
            "INSERT INTO model_usage (session_id, model, requests, input_tokens,"
            " output_tokens, cache_tokens, reasoning_tokens, cost, cache_read_tokens,"
            " cache_write_tokens) VALUES ('oc_sess', 'oc_model', 1, 100, 50, 0, 0, 1.0, 0, 9999)",
        )
        conn.commit()
        conn.close()

        today = self.main.api_today_summary(range="today")
        today_models = {row["model"]: row for row in today["top_models"]}
        self.assertEqual(today_models["claude_model"]["cache_write_tokens"], 4000)

        top12 = self.main._build_top_models_payload(days=364, bucket="week", limit=20)
        leaders = {row["model"]: row for row in top12["leaderboard"]}
        self.assertEqual(leaders["claude_model"]["cache_write_tokens"], 4000)
        self.assertEqual(leaders["oc_model"]["cache_write_tokens"], 0)


class CacheWriteDenominatorTests(unittest.TestCase):
    """El cache write entra al denominador solo para fuentes billable-aparte.

    Decisión del dueño (2026-09-23): el cache write es cache miss facturado
    aparte; para claude/hermes suma al denominador del ratio. Para codex/zcode
    (input_includes_cache_read) el denominador no cambia.
    """

    def test_claude_write_enters_denominator(self):
        result = calculate_session_cache_ratio([
            {
                "session_id": "claude_sess",
                "session_requests": 10,
                "source": "claude",
                "model": "claude-opus-5-5",
                "input_tokens": 100,
                "cache_tokens": 0,
                "cache_read_tokens": 8000,
                "cache_write_tokens": 4000,
            },
        ])
        # denominador = 100 + 8000 + 4000 = 12100 → ratio = 8000/12100
        self.assertAlmostEqual(result["ratio"], round(8000 / 12100 * 100, 1), places=5)

    def test_hermes_write_enters_denominator(self):
        result = calculate_session_cache_ratio([
            {
                "session_id": "hermes_sess",
                "session_requests": 10,
                "source": "hermes",
                "model": "m",
                "input_tokens": 1000,
                "cache_tokens": 0,
                "cache_read_tokens": 1000,
                "cache_write_tokens": 1000,
            },
        ])
        # denominador = 1000 + 1000 + 1000 = 3000 → ratio = 1000/3000
        self.assertAlmostEqual(result["ratio"], round(1000 / 3000 * 100, 1), places=5)

    def test_codex_denominator_unchanged_with_write(self):
        result = calculate_session_cache_ratio([
            {
                "session_id": "codex_sess",
                "session_requests": 10,
                "source": "codex",
                "model": "gpt-5.6-luna",
                "input_tokens": 10000,
                "cache_tokens": 4000,
                "cache_read_tokens": 4000,
                "cache_write_tokens": 5000,
            },
        ])
        # codex: input ya incluye cache; el write NO entra al denominador.
        # cache read efectivo = 4000 → 4000/10000
        self.assertAlmostEqual(result["ratio"], 40.0, places=5)

    def test_zero_write_keeps_legacy_behavior(self):
        result = calculate_session_cache_ratio([
            {
                "session_id": "legacy",
                "session_requests": 10,
                "source": "hermes",
                "model": "m",
                "input_tokens": 9000,
                "cache_tokens": 1000,
                "cache_read_tokens": 1000,
                "cache_write_tokens": 0,
            },
        ])
        self.assertAlmostEqual(result["ratio"], 10.0, places=5)


if __name__ == "__main__":
    unittest.main()
