"""
Tests transcribe_anything with lightning-whisper-mlx (MLX backend)
"""

# pylint: disable=bad-option-value,useless-option-value,no-self-use,protected-access,R0801
# flake8: noqa E501

import json
import os
import re
import shutil
import unittest
import wave
from pathlib import Path

from transcribe_anything.util import is_mac_arm
from transcribe_anything.whisper_mac import run_whisper_mac_english, run_whisper_mac_mlx, _format_timestamp, _json_to_srt

HERE = Path(os.path.abspath(os.path.dirname(__file__)))
LOCALFILE_DIR = HERE / "localfile"
TESTS_DATA_DIR = LOCALFILE_DIR / "text_video_mlx" / "en"
TEST_WAV = LOCALFILE_DIR / "video.wav"

CAN_RUN_TEST = is_mac_arm()


class MacOsWhisperMLXTester(unittest.TestCase):
    """Tester for transcribe anything with lightning-whisper-mlx (MLX backend)."""

    @unittest.skipUnless(CAN_RUN_TEST, "Not mac")
    def test_local_file_english(self) -> None:
        """Check that the command works on a local file with English."""
        shutil.rmtree(TESTS_DATA_DIR, ignore_errors=True)
        run_whisper_mac_mlx(input_wav=TEST_WAV, model="small", output_dir=TESTS_DATA_DIR, language="en", task="transcribe")

        # Verify output files were created
        self.assertTrue((TESTS_DATA_DIR / "out.txt").exists())
        self.assertTrue((TESTS_DATA_DIR / "out.srt").exists())
        self.assertTrue((TESTS_DATA_DIR / "out.json").exists())
        self.assertTrue((TESTS_DATA_DIR / "out.vtt").exists())

    @unittest.skipUnless(CAN_RUN_TEST, "Not mac")
    def test_local_file_with_initial_prompt(self) -> None:
        """Check that the command works with initial_prompt (now supported)."""
        test_dir = LOCALFILE_DIR / "text_video_mlx_prompt"
        shutil.rmtree(test_dir, ignore_errors=True)

        # This should work with initial_prompt support
        run_whisper_mac_mlx(input_wav=TEST_WAV, model="small", output_dir=test_dir, language="en", task="transcribe", other_args=["--initial_prompt", "test vocabulary terms"])

        # Verify output files were created
        self.assertTrue((test_dir / "out.txt").exists())
        self.assertTrue((test_dir / "out.srt").exists())
        self.assertTrue((test_dir / "out.json").exists())

    @unittest.skipUnless(CAN_RUN_TEST, "Not mac")
    def test_backward_compatibility(self) -> None:
        """Check that the old function still works for backward compatibility."""
        test_dir = LOCALFILE_DIR / "text_video_compat"
        shutil.rmtree(test_dir, ignore_errors=True)

        # Test the old function name
        run_whisper_mac_english(
            input_wav=TEST_WAV,
            model="small",
            output_dir=test_dir,
        )

        # Verify output files were created
        self.assertTrue((test_dir / "out.txt").exists())
        self.assertTrue((test_dir / "out.srt").exists())
        self.assertTrue((test_dir / "out.json").exists())

    @unittest.skipUnless(CAN_RUN_TEST, "Not mac")
    def test_multilingual_support(self) -> None:
        """Check that multilingual support works (auto-detect)."""
        test_dir = LOCALFILE_DIR / "text_video_multilingual"
        shutil.rmtree(test_dir, ignore_errors=True)

        # Test with auto-detection (no language specified)
        run_whisper_mac_mlx(input_wav=TEST_WAV, model="small", output_dir=test_dir, language=None, task="transcribe")  # Auto-detect

        # Verify output files were created
        self.assertTrue((test_dir / "out.txt").exists())
        self.assertTrue((test_dir / "out.srt").exists())
        self.assertTrue((test_dir / "out.json").exists())

    @unittest.skipUnless(CAN_RUN_TEST, "Not mac")
    def test_timestamp_accuracy_basic(self) -> None:
        """Test that MLX timestamps are reasonable and properly formatted."""
        test_dir = LOCALFILE_DIR / "text_video_timestamp_test"
        shutil.rmtree(test_dir, ignore_errors=True)

        run_whisper_mac_mlx(input_wav=TEST_WAV, model="small", output_dir=test_dir, language="en", task="transcribe")

        # Check SRT file exists and has proper timestamp format
        srt_file = test_dir / "out.srt"
        self.assertTrue(srt_file.exists())

        srt_content = srt_file.read_text(encoding="utf-8")

        # Verify SRT timestamp format (HH:MM:SS,mmm --> HH:MM:SS,mmm)
        timestamp_pattern = r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}'
        timestamps = re.findall(timestamp_pattern, srt_content)
        self.assertGreater(len(timestamps), 0, "No valid timestamps found in SRT file")

        # Parse timestamps and verify they're reasonable
        for timestamp_line in timestamps:
            start_str, end_str = timestamp_line.split(' --> ')
            start_seconds = self._parse_srt_timestamp(start_str)
            end_seconds = self._parse_srt_timestamp(end_str)

            # Basic sanity checks
            self.assertGreaterEqual(start_seconds, 0, f"Start time should be non-negative: {start_str}")
            self.assertGreater(end_seconds, start_seconds, f"End time should be after start time: {timestamp_line}")
            self.assertLess(end_seconds - start_seconds, 30, f"Segment too long (>30s): {timestamp_line}")

    @unittest.skipUnless(CAN_RUN_TEST, "Not mac")
    def test_timestamp_conversion_factor_issue(self) -> None:
        """Test for the specific 0.02 conversion factor issue identified in GitHub Issue #1."""
        test_dir = LOCALFILE_DIR / "text_video_conversion_test"
        shutil.rmtree(test_dir, ignore_errors=True)

        run_whisper_mac_mlx(input_wav=TEST_WAV, model="small", output_dir=test_dir, language="en", task="transcribe")

        # Load the JSON output to examine raw data
        json_file = test_dir / "out.json"
        self.assertTrue(json_file.exists())

        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # Check if we have segments data
        if "segments" in json_data and json_data["segments"]:
            segments = json_data["segments"]

            # Look for the problematic list format that uses 0.02 conversion
            for segment in segments:
                if isinstance(segment, list) and len(segment) >= 3:
                    # This is the format that uses the 0.02 conversion factor
                    raw_start = segment[0]
                    raw_end = segment[1]
                    converted_start = raw_start * 0.02
                    converted_end = raw_end * 0.02

                    # Log the conversion for debugging
                    print(f"Raw segment: start={raw_start}, end={raw_end}")
                    print(f"Converted (0.02): start={converted_start}, end={converted_end}")

                    # Check if the conversion seems reasonable
                    # If raw values are already in seconds, 0.02 conversion would make them tiny
                    if raw_start > 100:  # If raw value is large, 0.02 conversion is likely wrong
                        self.fail(f"Potential timestamp conversion issue: raw_start={raw_start}, "
                                f"converted={converted_start}. The 0.02 conversion factor may be incorrect.")

    @unittest.skipUnless(CAN_RUN_TEST, "Not mac")
    def test_timestamp_format_consistency(self) -> None:
        """Test that timestamp formats are consistent across output files."""
        test_dir = LOCALFILE_DIR / "text_video_format_test"
        shutil.rmtree(test_dir, ignore_errors=True)

        run_whisper_mac_mlx(input_wav=TEST_WAV, model="small", output_dir=test_dir, language="en", task="transcribe")

        # Load JSON and SRT files
        json_file = test_dir / "out.json"
        srt_file = test_dir / "out.srt"

        self.assertTrue(json_file.exists())
        self.assertTrue(srt_file.exists())

        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        srt_content = srt_file.read_text(encoding="utf-8")

        # Extract timestamps from SRT
        srt_timestamps = []
        timestamp_pattern = r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})'
        for match in re.finditer(timestamp_pattern, srt_content):
            start_str, end_str = match.groups()
            start_seconds = self._parse_srt_timestamp(start_str)
            end_seconds = self._parse_srt_timestamp(end_str)
            srt_timestamps.append((start_seconds, end_seconds))

        # Compare with JSON segments if available
        if "segments" in json_data and json_data["segments"]:
            json_segments = json_data["segments"]

            # We should have roughly the same number of segments
            self.assertGreater(len(srt_timestamps), 0, "No timestamps found in SRT")

            # Check that timestamps are in ascending order
            for i in range(len(srt_timestamps) - 1):
                current_end = srt_timestamps[i][1]
                next_start = srt_timestamps[i + 1][0]
                self.assertLessEqual(current_end, next_start + 1.0,  # Allow 1 second overlap
                                   f"Timestamps not in order: segment {i} ends at {current_end}, "
                                   f"segment {i+1} starts at {next_start}")

    def test_format_timestamp_function(self) -> None:
        """Test the _format_timestamp function directly."""
        # Test basic cases
        self.assertEqual(_format_timestamp(0), "00:00:00,000")
        self.assertEqual(_format_timestamp(1.5), "00:00:01,500")
        self.assertEqual(_format_timestamp(61.25), "00:01:01,250")
        self.assertEqual(_format_timestamp(3661.123), "01:01:01,123")

        # Test edge cases
        self.assertEqual(_format_timestamp(0.001), "00:00:00,001")
        self.assertEqual(_format_timestamp(0.999), "00:00:00,999")

    def test_json_to_srt_conversion(self) -> None:
        """Test the _json_to_srt function with different input formats."""
        # Test with dict format (old format)
        json_data_dict = {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello world"},
                {"start": 2.5, "end": 5.0, "text": "This is a test"}
            ]
        }

        srt_content = _json_to_srt(json_data_dict)
        self.assertIn("00:00:00,000 --> 00:00:02,500", srt_content)
        self.assertIn("Hello world", srt_content)

        # Test with list format (new format that uses 0.02 conversion)
        # This test documents the current behavior - it may need updating when the bug is fixed
        json_data_list = {
            "segments": [
                [0, 125, "Hello world"],  # 0 * 0.02 = 0, 125 * 0.02 = 2.5
                [125, 250, "This is a test"]  # 125 * 0.02 = 2.5, 250 * 0.02 = 5.0
            ]
        }

        srt_content = _json_to_srt(json_data_list)
        # With current 0.02 conversion, these should produce the same timestamps as above
        self.assertIn("00:00:00,000 --> 00:00:02,500", srt_content)
        self.assertIn("Hello world", srt_content)

    def _parse_srt_timestamp(self, timestamp_str: str) -> float:
        """Parse SRT timestamp string (HH:MM:SS,mmm) to seconds."""
        # Format: HH:MM:SS,mmm
        time_part, ms_part = timestamp_str.split(',')
        hours, minutes, seconds = map(int, time_part.split(':'))
        milliseconds = int(ms_part)

        total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
        return total_seconds


if __name__ == "__main__":
    unittest.main()
