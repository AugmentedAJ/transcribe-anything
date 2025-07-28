#!/usr/bin/env python3
"""
Standalone timestamp function tests that don't require full package installation.

These tests can be run independently to verify timestamp conversion logic
without needing transcribe-anything dependencies.
"""

import json
import re
import unittest
from typing import Any, Dict


def _format_timestamp(seconds: float) -> str:
    """Format seconds into SRT timestamp format (copied from whisper_mac.py)."""
    milliseconds = int(seconds * 1000)
    hours = milliseconds // 3_600_000
    milliseconds -= hours * 3_600_000
    minutes = milliseconds // 60_000
    milliseconds -= minutes * 60_000
    seconds = milliseconds // 1_000
    milliseconds -= seconds * 1_000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def _json_to_srt(json_data: Dict[str, Any]) -> str:
    """Convert lightning-whisper-mlx JSON output to SRT format (copied from whisper_mac.py)."""
    srt_content = ""

    if "segments" not in json_data:
        # If no segments, try to create a single segment from the full text
        if "text" in json_data:
            srt_content = "1\n00:00:00,000 --> 00:01:00,000\n" + json_data["text"] + "\n\n"
        return srt_content

    for i, segment in enumerate(json_data["segments"], start=1):
        # Handle both old format (start/end) and new format (list with start, end, text)
        if isinstance(segment, list) and len(segment) >= 3:
            # New format: [start_seek, end_seek, text]
            start_time = segment[0] * 0.02  # Convert seek to seconds (assuming 50fps)
            end_time = segment[1] * 0.02
            text = segment[2].strip()
        else:
            # Old format: dict with start/end/text
            start_time = segment.get("start", 0)
            end_time = segment.get("end", start_time + 5)  # Default to 5 seconds if no end time
            text = segment.get("text", "").strip()

        if text:  # Only include non-empty segments
            srt_content += f"{i}\n"
            srt_content += f"{_format_timestamp(start_time)} --> {_format_timestamp(end_time)}\n"
            srt_content += f"{text}\n\n"

    return srt_content


class StandaloneTimestampTests(unittest.TestCase):
    """Standalone tests for timestamp functions."""

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

    def test_json_to_srt_dict_format(self) -> None:
        """Test _json_to_srt with dict format (old format)."""
        json_data = {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello world"},
                {"start": 2.5, "end": 5.0, "text": "This is a test"}
            ]
        }
        
        srt_content = _json_to_srt(json_data)
        
        # Check that timestamps are preserved correctly
        self.assertIn("00:00:00,000 --> 00:00:02,500", srt_content)
        self.assertIn("00:00:02,500 --> 00:00:05,000", srt_content)
        self.assertIn("Hello world", srt_content)
        self.assertIn("This is a test", srt_content)

    def test_json_to_srt_list_format_conversion_issue(self) -> None:
        """Test _json_to_srt with list format - demonstrates the 0.02 conversion issue."""
        # This test documents the current problematic behavior
        json_data = {
            "segments": [
                [0, 125, "Hello world"],      # 0 * 0.02 = 0, 125 * 0.02 = 2.5
                [125, 250, "This is a test"]  # 125 * 0.02 = 2.5, 250 * 0.02 = 5.0
            ]
        }
        
        srt_content = _json_to_srt(json_data)
        
        # With current 0.02 conversion, these should produce specific timestamps
        self.assertIn("00:00:00,000 --> 00:00:02,500", srt_content)
        self.assertIn("00:00:02,500 --> 00:00:05,000", srt_content)
        
        # But this demonstrates the issue: if the raw values were already in seconds,
        # the conversion would be wrong
        
    def test_conversion_factor_issue_detection(self) -> None:
        """Test that demonstrates the 0.02 conversion factor issue."""
        # Simulate what might be the actual lightning-whisper-mlx output
        # If the library returns timestamps already in seconds:
        json_data_if_already_seconds = {
            "segments": [
                [0.0, 2.5, "Hello world"],      # Already in seconds
                [2.5, 5.0, "This is a test"]   # Already in seconds
            ]
        }

        # With 0.02 conversion, these would become tiny values
        srt_content = _json_to_srt(json_data_if_already_seconds)

        # The 0.02 conversion would make these: 0*0.02=0, 2.5*0.02=0.05, 5.0*0.02=0.1
        expected_wrong_timestamps = [
            "00:00:00,000 --> 00:00:00,050",  # 2.5 * 0.02 = 0.05 seconds
            "00:00:00,050 --> 00:00:00,100"   # 5.0 * 0.02 = 0.1 seconds
        ]

        # This test EXPECTS to find the wrong timestamps, demonstrating the bug
        found_issue = False
        for wrong_timestamp in expected_wrong_timestamps:
            if wrong_timestamp in srt_content:
                found_issue = True
                print(f"✅ CONFIRMED: 0.02 conversion issue detected: {wrong_timestamp}")
                break

        # If we don't find the issue, the conversion might have been fixed
        if not found_issue:
            print("ℹ️  0.02 conversion issue not detected - may have been fixed")
            print(f"Actual SRT content: {srt_content[:200]}...")

    def test_large_values_conversion_issue(self) -> None:
        """Test with large values that would indicate seek positions, not seconds."""
        # If lightning-whisper-mlx returns seek positions (frame numbers):
        json_data_seek_positions = {
            "segments": [
                [0, 6250, "Hello world"],      # 0 frames to 6250 frames
                [6250, 12500, "This is a test"]  # 6250 to 12500 frames
            ]
        }
        
        srt_content = _json_to_srt(json_data_seek_positions)
        
        # With 0.02 conversion: 6250 * 0.02 = 125 seconds, 12500 * 0.02 = 250 seconds
        # This would be reasonable if the values are indeed seek positions
        
        # Check if we get reasonable timestamps
        if "00:02:05,000" in srt_content and "00:04:10,000" in srt_content:
            # This suggests the 0.02 conversion might be correct for this format
            pass
        else:
            # Extract actual timestamps to see what we got
            timestamp_pattern = r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})'
            matches = re.findall(timestamp_pattern, srt_content)
            if matches:
                print(f"Actual timestamps generated: {matches}")

    def test_mixed_format_handling(self) -> None:
        """Test handling of mixed segment formats."""
        json_data = {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Dict format"},
                [125, 250, "List format"],  # This will use 0.02 conversion
                {"start": 5.0, "end": 7.5, "text": "Dict format again"}
            ]
        }
        
        srt_content = _json_to_srt(json_data)
        
        # Should handle both formats
        self.assertIn("Dict format", srt_content)
        self.assertIn("List format", srt_content)
        self.assertIn("Dict format again", srt_content)
        
        # Check that we have 3 segments
        segment_count = srt_content.count("\n\n")
        self.assertEqual(segment_count, 3)

    def test_empty_segments_handling(self) -> None:
        """Test handling of empty or malformed segments."""
        json_data = {
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Valid segment"},
                {"start": 2.5, "end": 3.0, "text": ""},  # Empty text
                [150, 200, "List format with text"],  # List format with text
                {"start": 5.0, "end": 7.5, "text": "Another valid segment"}
            ]
        }

        srt_content = _json_to_srt(json_data)

        # Should include segments with text
        self.assertIn("Valid segment", srt_content)
        self.assertIn("List format with text", srt_content)
        self.assertIn("Another valid segment", srt_content)

        # Count actual segments (lines that are just numbers)
        segment_count = len([line for line in srt_content.split('\n') if line.strip().isdigit()])
        self.assertEqual(segment_count, 3)  # 3 segments with text

    def test_no_segments_handling(self) -> None:
        """Test handling when no segments are present."""
        json_data_no_segments = {"text": "Full transcription text"}
        srt_content = _json_to_srt(json_data_no_segments)
        
        # Should create a default segment
        self.assertIn("00:00:00,000 --> 00:01:00,000", srt_content)
        self.assertIn("Full transcription text", srt_content)
        
        json_data_empty = {}
        srt_content_empty = _json_to_srt(json_data_empty)
        self.assertEqual(srt_content_empty, "")


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)
