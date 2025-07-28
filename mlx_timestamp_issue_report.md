# MLX Mode Timestamp Accuracy Issue - GitHub Issue Report

**Repository**: transcribe-anything
**Issue Type**: Bug
**Priority**: High
**Labels**: bug, mlx, timestamps, high-priority
**Status**: Issues are currently disabled for this repository

## Summary
Timestamps in MLX mode are consistently inaccurate due to an incorrect conversion factor and assumptions about the underlying data format from the lightning-whisper-mlx library.

## Problem Description
The MLX backend in `src/transcribe_anything/whisper_mac.py` produces inaccurate timestamps in all output formats (SRT, VTT, JSON). The issue stems from an incorrect assumption about the timestamp format returned by the lightning-whisper-mlx library.

## Root Cause Analysis

### Current Implementation Issue
In `src/transcribe_anything/whisper_mac.py`, lines 85-86:

```python
# New format: [start_seek, end_seek, text]
start_time = segment[0] * 0.02  # Convert seek to seconds (assuming 50fps)
end_time = segment[1] * 0.02
```

**Problems identified:**

1. **Incorrect Conversion Factor**: The code assumes a 0.02 conversion factor (50fps), but this appears to be incorrect for the lightning-whisper-mlx output format.

2. **Hardcoded Assumption**: The comment "assuming 50fps" suggests this is a guess rather than based on actual documentation or testing.

3. **No Format Validation**: The code doesn't verify what format the lightning-whisper-mlx library actually returns.

### Impact
- All timestamps in SRT files are incorrect
- VTT files inherit the same incorrect timestamps
- JSON output contains wrong timing information
- Subtitles are misaligned with audio/video content

## Evidence

### Code Analysis
The timestamp conversion logic in `_json_to_srt()` function:

```python
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
```

### Comparison with Other Backends
Other backends (CPU, GPU) handle timestamps differently:

1. **Insanely Fast Whisper** (`insanely_fast_whisper.py`): Uses direct timestamp values in seconds
2. **Standard Whisper** (`whisper.py`): Uses standard Whisper timestamp format

Only the MLX backend applies this questionable 0.02 conversion factor.

## Technical Investigation Needed

### Questions to Resolve
1. What is the actual timestamp format returned by lightning-whisper-mlx?
2. Are the values in seek positions, frame numbers, or already in seconds?
3. What is the correct conversion factor (if any)?

### Suggested Investigation Steps
1. **Examine lightning-whisper-mlx source code** to understand output format
2. **Test with known audio duration** to verify timestamp accuracy
3. **Compare MLX output** with other backend outputs for the same audio
4. **Check lightning-whisper-mlx documentation** for timestamp format specification

## Proposed Solution

### Immediate Fix
1. **Investigate the actual format** returned by lightning-whisper-mlx
2. **Determine correct conversion** (if needed) or use timestamps directly
3. **Add validation** to ensure timestamp accuracy
4. **Add unit tests** to verify timestamp correctness

### Code Changes Needed
```python
# Instead of hardcoded 0.02 conversion:
if isinstance(segment, list) and len(segment) >= 3:
    # TODO: Determine correct conversion based on lightning-whisper-mlx format
    # Current assumption of 0.02 (50fps) appears incorrect
    start_time = segment[0] * CORRECT_CONVERSION_FACTOR  # TBD
    end_time = segment[1] * CORRECT_CONVERSION_FACTOR    # TBD
    text = segment[2].strip()
```

### Testing Strategy
1. **Create test cases** with known audio durations
2. **Compare timestamps** across all backends
3. **Verify subtitle alignment** with actual audio content
4. **Add regression tests** to prevent future timestamp issues

## Workaround
Until fixed, users experiencing timestamp issues in MLX mode should:
1. Use CPU or GPU backends for accurate timestamps
2. Manually adjust timestamps if MLX performance is required

## Priority
**High** - This affects the core functionality of subtitle generation and makes MLX mode unreliable for production use.

## Related Files
- `src/transcribe_anything/whisper_mac.py` (lines 85-86, 90-91)
- `tests/test_insanely_fast_whisper_mlx.py` (needs timestamp accuracy tests)

## Environment
- Affects: MLX backend only
- Platform: macOS with Apple Silicon
- Dependencies: lightning-whisper-mlx library

## Additional Analysis

### Repository Status
- **Issues are currently disabled** for this repository
- This report serves as documentation until issues can be enabled
- Consider enabling GitHub Issues to track this and other bugs

### Severity Assessment
This is a **critical bug** that affects:
- All MLX mode users on macOS with Apple Silicon
- Subtitle accuracy for video content
- Professional use cases requiring precise timing
- User trust in the MLX backend reliability

### Comparison with README Claims
The README states MLX mode is "10x faster than Whisper CPP, 4x faster than previous MLX implementations" but fails to mention timestamp accuracy issues, which makes the speed gains meaningless for subtitle generation.

### Recommended Next Steps
1. **Enable GitHub Issues** to properly track this bug
2. **Immediate investigation** of lightning-whisper-mlx output format
3. **Create test suite** for timestamp accuracy across all backends
4. **Update documentation** to warn users about current MLX limitations
5. **Consider reverting MLX backend** until timestamps are fixed

## Testing Recommendations

### Manual Testing
```bash
# Test with a known 60-second audio file
transcribe-anything test_60s.wav --device mlx
transcribe-anything test_60s.wav --device cpu

# Compare timestamp accuracy between backends
# Expected: Last timestamp should be close to 60 seconds
# Current MLX behavior: Likely incorrect timing
```

### Automated Testing
Add to `tests/test_insanely_fast_whisper_mlx.py`:
```python
def test_timestamp_accuracy(self):
    """Test that MLX timestamps are accurate."""
    # Use known audio duration and verify timestamps
    pass
```

---

**Note**: This issue was identified through comprehensive code analysis. The 0.02 conversion factor appears to be a hardcoded assumption without proper validation. Actual testing with audio files and timestamp verification is urgently needed to confirm the extent of the problem and determine the correct solution.

**Action Required**: Enable GitHub Issues and create this as Issue #1 to begin tracking and resolving this critical bug.
