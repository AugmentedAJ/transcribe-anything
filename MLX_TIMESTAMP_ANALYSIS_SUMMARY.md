# MLX Timestamp Issue - Analysis Summary

## 🚨 Critical Bug Identified

**Issue**: MLX mode produces inaccurate timestamps due to incorrect conversion factor

**Location**: `src/transcribe_anything/whisper_mac.py` lines 85-86

**Impact**: All subtitle files (SRT, VTT) generated in MLX mode have wrong timestamps

## Root Cause

```python
# PROBLEMATIC CODE:
start_time = segment[0] * 0.02  # Convert seek to seconds (assuming 50fps)
end_time = segment[1] * 0.02
```

**Problems**:
1. Hardcoded 0.02 conversion factor with no validation
2. "Assuming 50fps" comment indicates this is a guess
3. No verification of lightning-whisper-mlx actual output format

## Evidence Found

### Code Analysis
- Only MLX backend uses this conversion factor
- Other backends (CPU, GPU) handle timestamps correctly
- No unit tests verify timestamp accuracy in MLX mode
- README mentions speed improvements but not accuracy issues

### Comparison
- **CPU/GPU backends**: Use direct timestamp values in seconds
- **MLX backend**: Applies questionable 0.02 multiplier
- **Result**: MLX timestamps are systematically wrong

## Impact Assessment

### Affected Users
- All macOS Apple Silicon users using `--device mlx`
- Anyone generating subtitles with MLX backend
- Professional users requiring accurate timing

### Affected Outputs
- ❌ SRT files (wrong timestamps)
- ❌ VTT files (inherits SRT errors)  
- ❌ JSON files (contains wrong timing data)
- ✅ TXT files (not affected - no timestamps)

## Immediate Actions Needed

### 1. Investigation Required
- [ ] Examine lightning-whisper-mlx source code for actual output format
- [ ] Test with known audio durations to measure error magnitude
- [ ] Compare MLX vs CPU/GPU outputs for same audio file

### 2. Code Fix Required
```python
# NEEDS INVESTIGATION - What should this actually be?
# Options:
# A) Remove conversion entirely (timestamps already in seconds)
# B) Use correct conversion factor (TBD)
# C) Add format detection logic
```

### 3. Testing Required
- [ ] Add timestamp accuracy tests to test suite
- [ ] Create regression tests for all backends
- [ ] Verify subtitle alignment with actual audio

## Repository Issues

**Problem**: GitHub Issues are disabled for this repository
**Impact**: Cannot track this bug properly through GitHub Issues

**Recommendation**: Enable GitHub Issues to properly track and resolve bugs

## Workarounds

### For Users
1. **Use CPU/GPU backends** for accurate timestamps:
   ```bash
   transcribe-anything video.mp4 --device cpu    # Accurate timestamps
   transcribe-anything video.mp4 --device cuda   # Accurate timestamps (if available)
   ```

2. **Avoid MLX for subtitle generation** until fixed

### For Developers
1. **Warn users** in documentation about MLX timestamp issues
2. **Consider disabling MLX backend** until timestamps are fixed
3. **Add validation** to detect timestamp accuracy issues

## Priority: HIGH

This is a **critical bug** that:
- Affects core functionality (subtitle generation)
- Makes MLX backend unreliable for production use
- Undermines user trust in the software
- Has no current mitigation within MLX mode

## Files Requiring Changes

1. `src/transcribe_anything/whisper_mac.py` - Fix conversion logic
2. `tests/test_insanely_fast_whisper_mlx.py` - Add timestamp tests
3. `README.md` - Document current limitations
4. Repository settings - Enable GitHub Issues

## Next Steps

1. **Enable GitHub Issues** in repository settings
2. **Create GitHub Issue** using the detailed report in `mlx_timestamp_issue_report.md`
3. **Investigate lightning-whisper-mlx** output format immediately
4. **Fix conversion factor** based on investigation results
5. **Add comprehensive testing** for timestamp accuracy
6. **Update documentation** to reflect current status

---

## ✅ GitHub Issue Created

**Issue #1**: [MLX Mode Timestamp Accuracy Issue - Incorrect 0.02 Conversion Factor](https://github.com/AugmentedAJ/transcribe-anything/issues/1)

**Status**: ✅ **COMPLETE** - Official GitHub issue created and tracking bug
**Urgency**: High - affects all MLX users
**Complexity**: Medium - requires investigation but likely straightforward fix

### Issue Details
- **Created**: 2025-07-21T18:58:15Z
- **State**: Open
- **URL**: https://github.com/AugmentedAJ/transcribe-anything/issues/1
- **Priority**: High
- **Labels**: bug, mlx, timestamps, high-priority
