"""Offline checks of provider parsing and honest capture failure behaviour."""

import contextlib
import csv
import io
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import fetch_basel_weather as fetch
from weather_csv import (
    UTC,
    check_temperature_unit,
    coverage,
    measurements,
    normalized_rows,
    numeric_value,
    parse_time,
    read_csv,
    select_location,
    select_run,
    selected_point_csv,
    snow_forecast_status,
)


class ForecastParsingTests(unittest.TestCase):
    def test_provider_capitalized_date_header(self):
        for parameter, value in (("tre200h0", "18.5"), ("jww003i0", "16")):
            raw = (f"point_type_id;point_id;Date;{parameter}\n2;123;202610030800;{value}\n").encode(
                "latin-1"
            )
            values = measurements(
                read_csv(raw), {"point_type_id": "2", "point_id": "123"}, parameter
            )
            self.assertEqual(values[parse_time("202610030800")][1], "available")

    def test_header_normalization_handles_spacing_and_rejects_collisions(self):
        raw = b"point_type_id;point_id; TIME ;tre200h0\n2;123; 202610030800 ;18.5\n"
        values = measurements(read_csv(raw), {"point_type_id": "2", "point_id": "123"}, "tre200h0")
        self.assertEqual(values[parse_time("202610030800")], (18.5, "available"))
        with self.assertRaisesRegex(ValueError, "duplicate column names"):
            read_csv(b"Date;date\n202610030800;202610030900\n")

    def test_missing_time_column_and_empty_timestamp_have_clear_errors(self):
        location = {"point_type_id": "2", "point_id": "123"}
        with self.assertRaisesRegex(ValueError, "no Date/time column"):
            measurements([{**location, "tre200h0": "18.5"}], location, "tre200h0")
        with self.assertRaisesRegex(ValueError, "empty timestamp"):
            measurements([{**location, "date": "", "tre200h0": "18.5"}], location, "tre200h0")

    def test_metadata_requires_unique_postcode_point(self):
        rows = [
            {"point_id": "4056", "point_type_id": "1", "postal_code": "4056"},
            {"point_id": "123", "point_type_id": "2", "postal_code": "4056"},
        ]
        self.assertEqual(select_location(rows, "4056")["point_id"], "123")
        with self.assertRaises(ValueError):
            select_location(rows + [rows[1]], "4056")

    def test_forecast_run_does_not_mix_cycles(self):
        assets = {
            "vnut12.lssw.202610030600.tre200h0.csv": {"href": "temperature-old"},
            "vnut12.lssw.202610030600.jww003i0.csv": {"href": "weather-old"},
            "vnut12.lssw.202610030700.tre200h0.csv": {"href": "temperature-new"},
        }
        issue, urls = select_run(assets)
        self.assertEqual(issue, datetime(2026, 10, 3, 6, tzinfo=UTC))
        self.assertEqual(urls["tre200h0"], "temperature-old")
        with self.assertRaises(ValueError):
            select_run({"vnut12.lssw.202610030700.tre200h0.csv": {"href": "only-one"}})

    def test_same_point_id_different_type_is_excluded(self):
        raw = (
            "point_type_id;point_id;time;tre200h0\n1;123;202610030800;99\n2;123;202610030800;18.5\n"
        ).encode("latin-1")
        values = measurements(read_csv(raw), {"point_type_id": "2", "point_id": "123"}, "tre200h0")
        self.assertEqual(values[parse_time("202610030800")], (18.5, "available"))
        saved = read_csv(selected_point_csv(raw, {"point_type_id": "2", "point_id": "123"}))
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["tre200h0"], "18.5")

    def test_temperature_unit_is_verified(self):
        content = "parameter_shortname;parameter_unit\ntre200h0;°C\n".encode("latin-1")
        check_temperature_unit(read_csv(content))
        with self.assertRaises(ValueError):
            check_temperature_unit([{"parameter_shortname": "tre200h0", "parameter_unit": "K"}])

    def test_invalid_and_missing_values_stay_unknown(self):
        cases = (("", "missing"), ("NaN", "invalid"), ("inf", "invalid"), ("oops", "invalid"))
        for value, status in cases:
            self.assertEqual(numeric_value(value, "tre200h0"), ("", status))
        self.assertEqual(numeric_value("3.5", "jww003i0"), ("", "invalid"))
        self.assertEqual(numeric_value("-1", "jww003i0"), ("", "invalid"))
        self.assertEqual(numeric_value("30.0", "tre200h0"), (30.0, "available"))

    def test_intervals_and_dst_offsets_are_preserved(self):
        first = parse_time("202610250000")
        second = parse_time("202610250100")
        values = {
            "tre200h0": {first: (30.0, "available"), second: (30.1, "available")},
            "jww003i0": {first: (16, "available")},
        }
        rows = normalized_rows(values, "synthetic")
        self.assertEqual(rows[0]["temperature_valid_start_utc"], "2026-10-24T23:00:00Z")
        self.assertEqual(rows[0]["weather_valid_start_utc"], "2026-10-24T21:00:00Z")
        self.assertEqual(rows[0]["valid_end_local"], "2026-10-25T02:00:00+02:00")
        self.assertEqual(rows[1]["valid_end_local"], "2026-10-25T02:00:00+01:00")
        self.assertEqual(rows[1]["weather_code_status"], "missing")
        self.assertEqual(rows[0]["snow_forecast_status"], "present")
        self.assertEqual(rows[1]["snow_forecast_status"], "unknown")

    def test_documented_snow_and_mixed_precipitation_day_and_night(self):
        # Explicit official examples, including the codes added on pages 2 and 4.
        for code in (8, 11, 16, 19, 22, 30, 34, 37, 39, 42):
            self.assertEqual(snow_forecast_status(code, "available"), "present")
            self.assertEqual(snow_forecast_status(code + 100, "available"), "present")
        for code in (7, 10, 15, 18, 21, 31):
            self.assertEqual(snow_forecast_status(code, "available"), "present")
            self.assertEqual(snow_forecast_status(code + 100, "available"), "present")

    def test_known_non_snow_code_does_not_claim_route_is_clear(self):
        for code in (1, 6, 14, 20, 33, 40, 41, 101, 114, 120, 140, 141):
            self.assertEqual(snow_forecast_status(code, "available"), "not_indicated")

    def test_missing_unfamiliar_and_inconsistent_codes_remain_unknown(self):
        for code in (0, 43, 100, 143, 999, 133):
            self.assertEqual(snow_forecast_status(code, "available"), "unknown")
        for status in ("missing", "invalid"):
            self.assertEqual(snow_forecast_status("", status), "unknown")
            self.assertEqual(snow_forecast_status(16, status), "unknown")

    def test_coverage_reports_missing_temperature_gap(self):
        values = {
            "tre200h0": {
                parse_time("202610030800"): (18.5, "available"),
                parse_time("202610030900"): ("", "missing"),
                parse_time("202610031000"): (30.1, "available"),
            }
        }
        summary = coverage(values)["tre200h0"]
        self.assertEqual(
            summary["gaps"],
            [
                {
                    "start_utc": "2026-10-03T08:00:00Z",
                    "end_utc": "2026-10-03T09:00:00Z",
                }
            ],
        )
        self.assertEqual(summary["available_records"], 2)

    def test_duplicate_and_malformed_timestamps_are_rejected(self):
        row = {"point_type_id": "2", "point_id": "123", "date": "202610030800", "tre200h0": "18"}
        with self.assertRaises(ValueError):
            measurements([row, row], row, "tre200h0")
        with self.assertRaises(ValueError):
            parse_time("20261003080")


class CaptureTests(unittest.TestCase):
    def test_capture_succeeds_with_capitalized_provider_date_headers(self):
        raw, location, issue, urls = fetch.example_inputs("4056")
        for parameter in ("tre200h0", "jww003i0"):
            name = f"{parameter}.csv"
            raw[name] = raw[name].replace(b";date;", b";Date;")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "example"
            self.assertEqual(
                fetch.save_capture(output, raw, location, issue, urls, synthetic=True), 4
            )
            with (output / "forecast.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(rows[0]["valid_end_utc"], "2026-10-03T08:00:00Z")
            self.assertEqual(rows[1]["snow_forecast_status"], "present")

    def test_offline_example_is_labelled_and_never_calls_network(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "example"
            with patch.object(fetch, "download", side_effect=AssertionError("Network forbidden")):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(fetch.main(["--example", "--output", str(output)]), 0)
            provenance = json.loads((output / "provenance.json").read_text())
            self.assertTrue(provenance["synthetic"])
            self.assertIsNone(provenance["retrieved_at_utc"])
            self.assertIsNone(provenance["provider"])
            self.assertIn("SYNTHETIC EXAMPLE", (output / "preview.html").read_text())
            with (output / "forecast.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 4)
            self.assertEqual(rows[-1]["temperature_status"], "missing")
            self.assertEqual(
                [row["snow_forecast_status"] for row in rows],
                ["not_indicated", "present", "present", "unknown"],
            )
            self.assertEqual({row["sample_kind"] for row in rows}, {"synthetic"})
            original = (output / "forecast.csv").read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(fetch.main(["--example", "--output", str(output)]), 1)
            self.assertEqual((output / "forecast.csv").read_bytes(), original)

    def test_network_failure_never_creates_fake_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "live"
            with patch.object(fetch, "download", side_effect=URLError("DNS unavailable")):
                with contextlib.redirect_stderr(io.StringIO()) as errors:
                    self.assertEqual(fetch.main(["--output", str(output)]), 1)
            self.assertFalse(output.exists())
            self.assertIn("No synthetic fallback", errors.getvalue())

    def test_missing_today_uses_yesterday_and_keeps_item_date(self):
        from urllib.error import HTTPError

        missing = HTTPError("url", 404, "absent", {}, None)
        with patch.object(fetch, "download", side_effect=[missing, b'{"assets": {}}']) as download:
            _, url = fetch.latest_item(datetime(2026, 10, 3, 23, tzinfo=UTC))
        self.assertTrue(download.call_args_list[0].args[0].endswith("20261004-ch"))
        self.assertTrue(url.endswith("20261003-ch"))


if __name__ == "__main__":
    unittest.main()
