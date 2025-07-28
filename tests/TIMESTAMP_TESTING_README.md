# Timestamp Accuracy Testing Suite

This test suite addresses **GitHub Issue #1: MLX Mode Timestamp Accuracy Issue - Incorrect 0.02 Conversion Factor**.

## Overview

The MLX backend in transcribe-anything has a critical timestamp accuracy issue where the 0.02 conversion factor produces incorrect timestamps in all output formats (SRT, VTT, JSON). This test suite provides comprehensive testing to:

1. **Detect the timestamp issue** in MLX mode
2. **Verify timestamp accuracy** across all backends
3. **Prevent regression** of timestamp fixes
4. **Provide debugging tools** for timestamp analysis

## Test Files

### Core Test Modules

1. **`test_timestamp_accuracy.py`** - Comprehensive timestamp accuracy tests
   - Tests MLX timestamp sanity checks
   - Detects 0.02 conversion factor issues
   - Validates timestamp progression and format
   - Cross-backend timestamp comparison

2. **`test_insanely_fast_whisper_mlx.py`** - Enhanced MLX-specific tests
   - Original MLX functionality tests
   - Added timestamp accuracy validation
   - Format consistency checks
   - Direct function testing

### Testing Tools

3. **`timestamp_verification_tool.py`** - Manual verification tool
   - Analyzes timestamp accuracy for any audio file
   - Compares backends (MLX vs CPU vs CUDA)
   - Provides detailed timestamp analysis
   - Detects conversion factor issues

4. **`run_timestamp_tests.py`** - Comprehensive test runner
   - Runs all timestamp-related tests
   - Generates detailed test reports
   - Provides summary of timestamp issues
   - Suitable for CI/CD integration

## Prerequisites

Before running the tests, ensure:

1. **Install transcribe-anything** in development mode:
   ```bash
   pip install -e .
   ```

2. **Install test dependencies**:
   ```bash
   pip install -r requirements.testing.txt
   ```

3. **For MLX tests**: Requires macOS with Apple Silicon and MLX backend enabled

## Usage

### Running All Timestamp Tests

```bash
# Run all timestamp tests
python tests/run_timestamp_tests.py

# Verbose output
python tests/run_timestamp_tests.py --verbose

# Generate test report
python tests/run_timestamp_tests.py --create-report

# MLX-only tests (requires Apple Silicon)
python tests/run_timestamp_tests.py --mlx-only
```

### Running Individual Test Modules

```bash
# Run timestamp accuracy tests
python -m unittest tests.test_timestamp_accuracy

# Run MLX-specific tests
python -m unittest tests.test_insanely_fast_whisper_mlx

# Verbose output
python -m unittest tests.test_timestamp_accuracy -v
```

### Manual Timestamp Verification

```bash
# Analyze MLX backend timestamps
python tests/timestamp_verification_tool.py audio.wav --backend mlx

# Compare with CPU backend
python tests/timestamp_verification_tool.py audio.wav --backend cpu

# Keep output files for inspection
python tests/timestamp_verification_tool.py audio.wav --keep-files
```

## Test Categories

### 1. Timestamp Sanity Checks
- Verify timestamps are non-negative
- Check that end times are after start times
- Validate timestamp progression
- Detect unreasonably short/long segments

### 2. Conversion Factor Detection
- Identify the 0.02 conversion factor issue
- Compare raw vs converted timestamp values
- Detect when timestamps are suspiciously small
- Flag potential conversion errors

### 3. Format Validation
- Test SRT timestamp format (HH:MM:SS,mmm)
- Validate JSON segment formats
- Check consistency between output formats
- Verify timestamp parsing functions

### 4. Cross-Backend Comparison
- Compare MLX vs CPU timestamp accuracy
- Identify backend-specific issues
- Validate timestamp consistency
- Detect regression across updates

## Expected Test Results

### When Issue #1 is Present (Current State)
- ❌ `test_mlx_timestamp_sanity_check` - May fail if timestamps are too small
- ❌ `test_mlx_conversion_factor_detection` - Should detect 0.02 conversion issue
- ⚠️ `test_mlx_timestamp_progression` - May show timing inconsistencies
- ✅ Format validation tests should pass

### When Issue #1 is Fixed
- ✅ All timestamp sanity checks should pass
- ✅ No conversion factor issues detected
- ✅ Timestamps should match audio duration
- ✅ Cross-backend consistency achieved

## Platform Requirements

### MLX Tests
- **Platform**: macOS with Apple Silicon (M1/M2/M3)
- **Backend**: MLX backend enabled
- **Dependencies**: lightning-whisper-mlx

### CPU/CUDA Tests
- **Platform**: Any platform with transcribe-anything installed
- **Backend**: CPU or CUDA backend
- **Dependencies**: Standard whisper dependencies

### Skipped Tests
Tests will be automatically skipped if:
- Running on non-Apple Silicon hardware (MLX tests)
- Required backends are not available
- Test audio files are missing

## Test Data

The tests use audio files from `tests/localfile/`:
- `video.wav` - Primary test audio file
- Other test files as available

For comprehensive testing, ensure test audio files have:
- Known duration (for validation)
- Clear speech content
- Reasonable length (5-60 seconds)

## Debugging Failed Tests

### MLX Conversion Factor Issues
If tests detect the 0.02 conversion factor issue:

1. **Check the error message** for specific segment details
2. **Examine raw vs converted values** in test output
3. **Compare with CPU backend** results
4. **Review `src/transcribe_anything/whisper_mac.py` lines 85-86**

### Timestamp Format Issues
If timestamp format tests fail:

1. **Check SRT file format** manually
2. **Validate JSON segment structure**
3. **Test timestamp parsing functions** individually
4. **Compare with expected format examples**

### Platform-Specific Issues
If tests are skipped unexpectedly:

1. **Verify platform detection** (`is_mac_arm()`)
2. **Check MLX backend availability**
3. **Ensure test dependencies** are installed
4. **Review test skip conditions**

## Contributing

When adding new timestamp tests:

1. **Follow existing patterns** in test modules
2. **Add appropriate skip decorators** for platform requirements
3. **Include descriptive test names** and docstrings
4. **Test both success and failure cases**
5. **Update this README** with new test descriptions

## Integration with CI/CD

The test runner (`run_timestamp_tests.py`) is designed for CI/CD integration:

```bash
# In CI pipeline
python tests/run_timestamp_tests.py --create-report --report-file ci_timestamp_report.md

# Check exit code
if [ $? -ne 0 ]; then
    echo "Timestamp tests failed - MLX backend has issues"
    exit 1
fi
```

## Related Issues

- **GitHub Issue #1**: MLX Mode Timestamp Accuracy Issue - Incorrect 0.02 Conversion Factor
- **Files**: `src/transcribe_anything/whisper_mac.py` (lines 85-86)
- **Backend**: MLX (lightning-whisper-mlx)
- **Platform**: macOS with Apple Silicon

---

This test suite ensures the timestamp accuracy issue is properly detected, tracked, and prevented from regression once fixed.
