#!/usr/bin/env python3
"""
Timestamp Verification Tool for MLX Backend

This tool helps verify timestamp accuracy issues identified in GitHub Issue #1.
It can be used to manually test and compare timestamp accuracy across backends.

Usage:
    python timestamp_verification_tool.py <audio_file> [--backend mlx|cpu|cuda]
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def get_audio_duration(audio_file: Path) -> Optional[float]:
    """Get the duration of an audio file."""
    try:
        if audio_file.suffix.lower() == '.wav':
            with wave.open(str(audio_file), 'rb') as wav:
                frames = wav.getnframes()
                rate = wav.getframerate()
                return frames / float(rate)
        else:
            # Use ffprobe for other formats
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', str(audio_file)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                return float(result.stdout.strip())
    except Exception as e:
        print(f"Warning: Could not determine audio duration: {e}")
    
    return None


def parse_srt_timestamp(timestamp_str: str) -> float:
    """Parse SRT timestamp string (HH:MM:SS,mmm) to seconds."""
    time_part, ms_part = timestamp_str.split(',')
    hours, minutes, seconds = map(int, time_part.split(':'))
    milliseconds = int(ms_part)
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0


def extract_srt_timestamps(srt_content: str) -> List[Tuple[float, float, str]]:
    """Extract timestamps and text from SRT content."""
    timestamps = []
    pattern = r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.+?)(?=\n\n|\n\d+\n|\Z)'
    
    for match in re.finditer(pattern, srt_content, re.DOTALL):
        start_str, end_str, text = match.groups()
        start_seconds = parse_srt_timestamp(start_str)
        end_seconds = parse_srt_timestamp(end_str)
        text_clean = text.strip().replace('\n', ' ')
        timestamps.append((start_seconds, end_seconds, text_clean))
    
    return timestamps


def analyze_timestamps(timestamps: List[Tuple[float, float, str]], audio_duration: Optional[float]) -> Dict:
    """Analyze timestamp data for potential issues."""
    analysis = {
        'total_segments': len(timestamps),
        'issues': [],
        'warnings': [],
        'stats': {}
    }
    
    if not timestamps:
        analysis['issues'].append("No timestamps found")
        return analysis
    
    # Basic statistics
    starts = [t[0] for t in timestamps]
    ends = [t[1] for t in timestamps]
    durations = [t[1] - t[0] for t in timestamps]
    
    analysis['stats'] = {
        'first_start': min(starts),
        'last_end': max(ends),
        'total_duration': max(ends) - min(starts),
        'avg_segment_duration': sum(durations) / len(durations),
        'min_segment_duration': min(durations),
        'max_segment_duration': max(durations)
    }
    
    # Check for issues
    for i, (start, end, text) in enumerate(timestamps):
        if start < 0:
            analysis['issues'].append(f"Segment {i}: Negative start time ({start})")
        
        if end <= start:
            analysis['issues'].append(f"Segment {i}: End time not after start time ({start} -> {end})")
        
        if end - start > 30:
            analysis['warnings'].append(f"Segment {i}: Very long segment ({end - start:.1f}s)")
        
        if end - start < 0.1:
            analysis['warnings'].append(f"Segment {i}: Very short segment ({end - start:.3f}s)")
    
    # Check progression
    for i in range(len(timestamps) - 1):
        current_end = timestamps[i][1]
        next_start = timestamps[i + 1][0]
        
        if current_end > next_start + 1.0:  # Allow 1s overlap
            analysis['issues'].append(f"Segments {i}-{i+1}: Overlap issue ({current_end} > {next_start})")
    
    # Check against audio duration
    if audio_duration:
        last_end = analysis['stats']['last_end']
        ratio = last_end / audio_duration
        
        analysis['stats']['duration_ratio'] = ratio
        
        if ratio < 0.1:
            analysis['issues'].append(
                f"Timestamps much shorter than audio duration. "
                f"Last timestamp: {last_end:.2f}s, Audio: {audio_duration:.2f}s, "
                f"Ratio: {ratio:.3f}. This suggests incorrect conversion factor (0.02 issue)."
            )
        elif ratio > 2.0:
            analysis['warnings'].append(
                f"Timestamps much longer than audio duration. "
                f"Last timestamp: {last_end:.2f}s, Audio: {audio_duration:.2f}s"
            )
    
    return analysis


def run_transcription(audio_file: Path, backend: str = "mlx") -> Path:
    """Run transcription using transcribe-anything."""
    output_dir = Path(tempfile.mkdtemp())
    
    cmd = ["transcribe-anything", str(audio_file), "--device", backend]
    
    try:
        result = subprocess.run(cmd, cwd=output_dir, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Transcription failed: {result.stderr}")
            sys.exit(1)
        
        return output_dir
    except FileNotFoundError:
        print("Error: transcribe-anything command not found. Please install the package.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Verify timestamp accuracy for transcribe-anything")
    parser.add_argument("audio_file", help="Path to audio file")
    parser.add_argument("--backend", choices=["mlx", "cpu", "cuda"], default="mlx",
                       help="Backend to use for transcription")
    parser.add_argument("--output-dir", help="Output directory (default: temporary)")
    parser.add_argument("--keep-files", action="store_true", help="Keep output files")
    
    args = parser.parse_args()
    
    audio_file = Path(args.audio_file)
    if not audio_file.exists():
        print(f"Error: Audio file not found: {audio_file}")
        sys.exit(1)
    
    print(f"Analyzing timestamp accuracy for: {audio_file}")
    print(f"Backend: {args.backend}")
    print("-" * 50)
    
    # Get audio duration
    audio_duration = get_audio_duration(audio_file)
    if audio_duration:
        print(f"Audio duration: {audio_duration:.2f} seconds")
    else:
        print("Audio duration: Unknown")
    
    # Run transcription
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        # Run transcribe-anything manually in specified directory
        print(f"\nPlease run: transcribe-anything {audio_file} --device {args.backend}")
        print(f"In directory: {output_dir}")
        print("Then press Enter to continue...")
        input()
    else:
        print("\nRunning transcription...")
        output_dir = run_transcription(audio_file, args.backend)
    
    # Analyze results
    srt_file = output_dir / "out.srt"
    json_file = output_dir / "out.json"
    
    if not srt_file.exists():
        print(f"Error: SRT file not found at {srt_file}")
        sys.exit(1)
    
    print(f"\nAnalyzing: {srt_file}")
    
    # Load and analyze SRT
    srt_content = srt_file.read_text(encoding="utf-8")
    timestamps = extract_srt_timestamps(srt_content)
    analysis = analyze_timestamps(timestamps, audio_duration)
    
    # Print results
    print(f"\nTimestamp Analysis Results:")
    print(f"Total segments: {analysis['total_segments']}")
    
    if analysis['stats']:
        stats = analysis['stats']
        print(f"First timestamp: {stats['first_start']:.3f}s")
        print(f"Last timestamp: {stats['last_end']:.3f}s")
        print(f"Total duration: {stats['total_duration']:.3f}s")
        print(f"Average segment: {stats['avg_segment_duration']:.3f}s")
        
        if 'duration_ratio' in stats:
            print(f"Duration ratio: {stats['duration_ratio']:.3f}")
    
    # Print issues
    if analysis['issues']:
        print(f"\n🚨 ISSUES FOUND ({len(analysis['issues'])}):")
        for issue in analysis['issues']:
            print(f"  - {issue}")
    
    if analysis['warnings']:
        print(f"\n⚠️  WARNINGS ({len(analysis['warnings'])}):")
        for warning in analysis['warnings']:
            print(f"  - {warning}")
    
    if not analysis['issues'] and not analysis['warnings']:
        print("\n✅ No timestamp issues detected!")
    
    # Show first few timestamps
    if timestamps:
        print(f"\nFirst 3 timestamps:")
        for i, (start, end, text) in enumerate(timestamps[:3]):
            print(f"  {i+1}: {start:.3f}s - {end:.3f}s | {text[:50]}...")
    
    # Analyze JSON if available
    if json_file.exists():
        print(f"\nAnalyzing JSON format...")
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        if "segments" in json_data:
            segments = json_data["segments"]
            list_format_count = sum(1 for s in segments if isinstance(s, list))
            dict_format_count = sum(1 for s in segments if isinstance(s, dict))
            
            print(f"JSON segments: {len(segments)} total")
            print(f"  - List format (uses 0.02 conversion): {list_format_count}")
            print(f"  - Dict format (direct timestamps): {dict_format_count}")
            
            if list_format_count > 0:
                print("⚠️  List format detected - this uses the 0.02 conversion factor!")
    
    # Cleanup
    if not args.keep_files and not args.output_dir:
        import shutil
        shutil.rmtree(output_dir)
        print(f"\nTemporary files cleaned up.")
    else:
        print(f"\nOutput files saved in: {output_dir}")


if __name__ == "__main__":
    main()
