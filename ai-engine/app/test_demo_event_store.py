import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from app import demo_event_store as store
from app.api import detection_validated
from app.feature_extraction.run_reference_capture import PredictionWriter


class DemoEventStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_path = store.DB_PATH
        store.DB_PATH = Path(self.temp_dir.name) / "demo-events.sqlite3"
        store.initialize_store()

    def tearDown(self):
        store.DB_PATH = self.previous_path
        self.temp_dir.cleanup()

    @staticmethod
    def result():
        return {
            "model_version": "test-model",
            "detection": {
                "random_forest": {
                    "classification": "NORMAL",
                    "attack_probability": 0.12,
                    "threshold": 0.27,
                    "flagged": False,
                },
                "isolation_forest": {
                    "classification": "ANOMALOUS",
                    "anomaly_score": 0.61,
                    "threshold": 0.52,
                    "flagged": True,
                },
            },
            "risk_assessment": {"detector_agreement": "IF_ONLY"},
            "input_warnings": {},
        }

    def test_records_only_prediction_metadata(self):
        event = store.record_prediction("cicflowmeter-python-test", self.result(), "pcap")
        self.assertEqual(event["input_source"], "cicflowmeter-python-test")
        self.assertEqual(event["capture_mode"], "pcap")
        self.assertFalse(event["simulated"])
        self.assertEqual(event["if_classification"], "ANOMALOUS")
        self.assertNotIn("features", event)
        self.assertNotIn("source_ip", event)

        rows = store.recent_predictions(20)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], event["id"])
        self.assertEqual(rows[0]["capture_mode"], "pcap")
        self.assertIsInstance(rows[0]["rf_flagged"], bool)

    def test_prediction_writer_sends_capture_mode_without_flow_storage(self):
        for mode in ("pcap", "live"):
            with self.subTest(mode=mode), patch(
                "app.feature_extraction.run_reference_capture.requests.post"
            ) as post, patch("builtins.print"):
                response = MagicMock()
                response.json.return_value = {
                    "input_source": "adapter",
                    "capture_mode": mode,
                    "packet_level_reference_features": True,
                    "detection": {},
                    "input_warnings": {},
                    "caution": "research only",
                }
                post.return_value = response
                PredictionWriter("http://127.0.0.1/test", mode).write({"Flow Duration": 1})
                self.assertEqual(post.call_args.kwargs["json"]["_capture_mode"], mode)
                self.assertNotIn("src_ip", post.call_args.kwargs["json"])

    def test_migrates_existing_store_to_capture_mode(self):
        legacy_db = Path(self.temp_dir.name) / "legacy.sqlite3"
        with sqlite3.connect(legacy_db) as connection:
            connection.execute("""CREATE TABLE prediction_events (
                id TEXT PRIMARY KEY, recorded_at TEXT NOT NULL, input_source TEXT NOT NULL,
                model_version TEXT NOT NULL, rf_classification TEXT NOT NULL,
                rf_probability REAL NOT NULL, rf_threshold REAL NOT NULL, rf_flagged INTEGER NOT NULL,
                if_classification TEXT NOT NULL, if_score REAL NOT NULL,
                if_threshold REAL NOT NULL, if_flagged INTEGER NOT NULL, detector_agreement TEXT
            )""")
        store.DB_PATH = legacy_db
        store.initialize_store()
        with store._connect() as connection:
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(prediction_events)")}
        self.assertIn("capture_mode", columns)
        store.record_prediction("capture", self.result(), "live")
        self.assertEqual(store.recent_predictions(1)[0]["capture_mode"], "live")

    def test_invalid_capture_mode_is_stored_as_unspecified(self):
        event = store.record_prediction("capture", self.result(), {"mode": "pcap"})
        self.assertEqual(event["capture_mode"], "unspecified")
        self.assertEqual(store.recent_predictions(1)[0]["capture_mode"], "unspecified")

    def test_limit_is_bounded_and_empty_store_is_empty(self):
        self.assertEqual(store.recent_predictions(50), [])
        store.record_prediction("capture", self.result())
        self.assertEqual(len(store.recent_predictions(0)), 1)
        self.assertLessEqual(len(store.recent_predictions(9999)), 250)

    def test_capture_route_persists_prediction_without_flow_fields(self):
        store.initialize_store()
        with patch.object(
            detection_validated,
            "map_cicflowmeter_record",
            return_value=({}, []),
        ), patch.object(
            detection_validated,
            "detect_with_validated_models",
            return_value=self.result(),
        ):
            result = detection_validated.detect_cicflowmeter_python_record(
                {"src_ip": "192.0.2.10", "dst_ip": "198.51.100.20", "_capture_mode": "pcap"}
            )

        self.assertEqual(result["input_source"], "cicflowmeter-python-0.5.0")
        self.assertEqual(result["capture_mode"], "pcap")
        rows = store.recent_predictions(10)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["input_source"], "cicflowmeter-python-0.5.0")
        self.assertEqual(rows[0]["capture_mode"], "pcap")
        self.assertNotIn("src_ip", rows[0])
        self.assertNotIn("dst_ip", rows[0])


if __name__ == "__main__":
    unittest.main()
