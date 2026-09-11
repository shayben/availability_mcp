import datetime as dt
import unittest

from availability_mcp.activity import IdleReading, activity_snapshot


class ActivitySnapshotTests(unittest.TestCase):
    def test_reports_idle_state_and_timestamps(self):
        observed_at = dt.datetime(2026, 9, 11, 3, 49, tzinfo=dt.timezone.utc)

        result = activity_snapshot(
            300,
            reader=lambda: IdleReading(420.125, "test"),
            now=lambda: observed_at,
        )

        self.assertTrue(result["is_idle"])
        self.assertEqual(result["idle_seconds"], 420.125)
        self.assertEqual(result["source"], "test")
        self.assertEqual(result["last_activity_at"], "2026-09-11T03:41:59.875000+00:00")

    def test_rejects_negative_threshold(self):
        with self.assertRaisesRegex(ValueError, "non-negative"):
            activity_snapshot(-1, reader=lambda: IdleReading(0, "test"))


if __name__ == "__main__":
    unittest.main()
