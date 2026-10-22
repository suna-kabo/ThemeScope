from __future__ import annotations

import unittest
from unittest.mock import patch

from src.themescope.collect import _fetch_many


class SequentialFetchTests(unittest.TestCase):
    @patch("src.themescope.collect.time.sleep")
    def test_single_worker_spaces_requests_and_preserves_per_symbol_errors(self, sleep_mock) -> None:
        calls: list[str] = []

        def fetch(symbol: str) -> str:
            calls.append(symbol)
            if symbol == "B":
                raise ValueError("temporarily unavailable")
            return symbol.lower()

        values, errors = _fetch_many(
            {"C", "B", "A"}, fetch, workers=1, request_interval_seconds=1.5
        )

        self.assertEqual(calls, ["A", "B", "C"])
        self.assertEqual(values, {"A": "a", "C": "c"})
        self.assertEqual(errors, {"B": "ValueError: temporarily unavailable"})
        self.assertEqual(sleep_mock.call_count, 2)
        sleep_mock.assert_called_with(1.5)


if __name__ == "__main__":
    unittest.main()
