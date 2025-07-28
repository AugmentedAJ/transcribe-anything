"""
Test timestamp accuracy across all transcription backends.

This test suite specifically addresses GitHub Issue #1:
MLX Mode Timestamp Accuracy Issue - Incorrect 0.02 Conversion Factor
"""

import json
import os
import re
import shutil
import tempfile
import unittest
import wave
from pathlib import Path
from typing import List, Tuple

from transcribe_anything.util import is_mac_arm
from transcribe_anything.whisper_mac import run_whisper_mac_mlx


HERE = Path(os.path.abspath(os.path.dirname(__file__)))
LOCALFILE_DIR = HERE / "localfile"
TEST_WAV = LOCALFILE_DIR / "video.wav"

CAN_RUN_MLX_TEST = is_mac_arm()


class TimestampAccuracyTester(unittest.TestCase):
    """Test timestamp accuracy across different backends."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        """Clean up test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def _parse_srt_timestamp(self, timestamp_str: str) -> float:
        """Parse SRT timestamp string (HH:MM:SS,mmm) to seconds."""
        time_part, ms_part = timestamp_str.split(',')
        hours, minutes, seconds = map(int, time_part.split(':'))
        milliseconds = int(ms_part)
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0

    def _extract_srt_timestamps(self, srt_content: str) -> List[Tuple[float, float]]:
        """Extract all timestamps from SRT content."""
        timestamps = []
        pattern = r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})'
        
        for match in re.finditer(pattern, srt_content):
            start_str, end_str = match.groups()
            start_seconds = self._parse_srt_timestamp(start_str)
            end_seconds = self._parse_srt_timestamp(end_str)
            timestamps.append((start_seconds, end_seconds))
        
        return timestamps

    def _get_audio_duration(self, wav_file: Path) -> float:
        """Get the duration of a WAV file in seconds."""
        try:
            with wave.open(str(wav_file), 'rb') as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                return frames / float(rate)
        except Exception:
            # Fallback - assume a reasonable duration for test audio
            return 10.0  # 10 seconds

    @unittest.skipUnless(CAN_RUN_MLX_TEST, "MLX tests require macOS with Apple Silicon")
    def test_mlx_timestamp_sanity_check(self) -> None:
        """Test that MLX timestamps are within reasonable bounds."""
        output_dir = self.test_dir / "mlx_sanity"
        output_dir.mkdir(parents=True)
        
        # Get actual audio duration
        audio_duration = self._get_audio_duration(TEST_WAV)
        
        run_whisper_mac_mlx(
            input_wav=TEST_WAV,
            model="small",
            output_dir=output_dir,
            language="en",
            task="transcribe"
        )
        
        # Check SRT file
        srt_file = output_dir / "out.srt"
        self.assertTrue(srt_file.exists(), "SRT file should be created")
        
        srt_content = srt_file.read_text(encoding="utf-8")
        timestamps = self._extract_srt_timestamps(srt_content)
        
        self.assertGreater(len(timestamps), 0, "Should have at least one timestamp")
        
        # Check timestamp sanity
        for i, (start, end) in enumerate(timestamps):
            with self.subTest(segment=i):
                self.assertGreaterEqual(start, 0, f"Start time should be non-negative: {start}")
                self.assertGreater(end, start, f"End time should be after start: {start} -> {end}")
                
                # Check if timestamps are suspiciously small (indicating 0.02 conversion issue)
                if audio_duration > 5:  # If audio is longer than 5 seconds
                    max_expected_end = timestamps[-1][1]  # Last segment end time
                    
                    # If the last timestamp is much smaller than audio duration, conversion is likely wrong
                    ratio = max_expected_end / audio_duration
                    if ratio < 0.1:  # Less than 10% of actual duration
                        self.fail(f"Timestamps appear too small. Last timestamp: {max_expected_end}s, "
                                f"Audio duration: {audio_duration}s, Ratio: {ratio:.3f}. "
                                f"This suggests the 0.02 conversion factor is incorrect.")

    @unittest.skipUnless(CAN_RUN_MLX_TEST, "MLX tests require macOS with Apple Silicon")
    def test_mlx_conversion_factor_detection(self) -> None:
        """Test to detect the 0.02 conversion factor issue from GitHub Issue #1."""
        output_dir = self.test_dir / "mlx_conversion"
        output_dir.mkdir(parents=True)
        
        run_whisper_mac_mlx(
            input_wav=TEST_WAV,
            model="small",
            output_dir=output_dir,
            language="en",
            task="transcribe"
        )
        
        # Load JSON to examine raw segment data
        json_file = output_dir / "out.json"
        self.assertTrue(json_file.exists(), "JSON file should be created")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        if "segments" not in json_data:
            self.skipTest("No segments found in JSON output")
        
        segments = json_data["segments"]
        conversion_factor_issues = []
        
        for i, segment in enumerate(segments):
            if isinstance(segment, list) and len(segment) >= 3:
                raw_start = segment[0]
                raw_end = segment[1]
                
                # Check if raw values suggest they're already in seconds
                # If so, the 0.02 conversion is wrong
                if raw_start > 0 and raw_end > raw_start:
                    # Calculate what the converted values would be
                    converted_start = raw_start * 0.02
                    converted_end = raw_end * 0.02
                    
                    # If raw values are reasonable timestamps (0-3600 seconds)
                    # but converted values are tiny, the conversion is likely wrong
                    if (0 <= raw_start <= 3600 and 0 <= raw_end <= 3600 and 
                        converted_end < 1.0 and raw_end > 50):
                        conversion_factor_issues.append({
                            'segment': i,
                            'raw_start': raw_start,
                            'raw_end': raw_end,
                            'converted_start': converted_start,
                            'converted_end': converted_end
                        })
        
        if conversion_factor_issues:
            issue_details = "\n".join([
                f"Segment {issue['segment']}: raw({issue['raw_start']:.2f}-{issue['raw_end']:.2f}) "
                f"-> converted({issue['converted_start']:.2f}-{issue['converted_end']:.2f})"
                for issue in conversion_factor_issues[:3]  # Show first 3 issues
            ])
            
            self.fail(f"Detected potential 0.02 conversion factor issue in {len(conversion_factor_issues)} segments:\n"
                     f"{issue_details}\n"
                     f"This confirms GitHub Issue #1: MLX timestamps may be using incorrect conversion factor.")

    @unittest.skipUnless(CAN_RUN_MLX_TEST, "MLX tests require macOS with Apple Silicon")
    def test_mlx_timestamp_progression(self) -> None:
        """Test that MLX timestamps progress logically."""
        output_dir = self.test_dir / "mlx_progression"
        output_dir.mkdir(parents=True)
        
        run_whisper_mac_mlx(
            input_wav=TEST_WAV,
            model="small",
            output_dir=output_dir,
            language="en",
            task="transcribe"
        )
        
        srt_file = output_dir / "out.srt"
        srt_content = srt_file.read_text(encoding="utf-8")
        timestamps = self._extract_srt_timestamps(srt_content)
        
        if len(timestamps) < 2:
            self.skipTest("Need at least 2 segments to test progression")
        
        # Check that timestamps progress forward
        for i in range(len(timestamps) - 1):
            current_start, current_end = timestamps[i]
            next_start, next_end = timestamps[i + 1]
            
            with self.subTest(segment_pair=f"{i}-{i+1}"):
                self.assertLessEqual(current_end, next_start + 2.0,  # Allow 2s overlap
                                   f"Segment {i} ends after segment {i+1} starts: "
                                   f"{current_end} > {next_start}")
                
                self.assertLess(current_start, next_end,
                              f"Segments {i} and {i+1} have no temporal relationship")

    def test_timestamp_format_validation(self) -> None:
        """Test timestamp format validation functions."""
        # Test valid SRT timestamp formats
        valid_timestamps = [
            "00:00:00,000",
            "00:01:30,500",
            "01:23:45,999"
        ]
        
        for ts in valid_timestamps:
            with self.subTest(timestamp=ts):
                seconds = self._parse_srt_timestamp(ts)
                self.assertGreaterEqual(seconds, 0)
        
        # Test specific conversions
        self.assertEqual(self._parse_srt_timestamp("00:00:01,500"), 1.5)
        self.assertEqual(self._parse_srt_timestamp("00:01:00,000"), 60.0)
        self.assertEqual(self._parse_srt_timestamp("01:00:00,000"), 3600.0)


if __name__ == "__main__":
    unittest.main()
