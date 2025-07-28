#!/usr/bin/env python3
"""
Comprehensive Timestamp Test Runner

This script runs all timestamp-related tests to verify the MLX backend
timestamp accuracy issue identified in GitHub Issue #1.

Usage:
    python run_timestamp_tests.py [--verbose] [--mlx-only] [--create-report]
"""

import argparse
import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict, List


def run_unittest_module(module_name: str, verbose: bool = False) -> Dict:
    """Run a unittest module and return results."""
    cmd = [sys.executable, "-m", "unittest", module_name]
    if verbose:
        cmd.append("-v")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent)
        return {
            'module': module_name,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }
    except Exception as e:
        return {
            'module': module_name,
            'returncode': -1,
            'stdout': '',
            'stderr': str(e),
            'success': False
        }


def parse_test_output(output: str) -> Dict:
    """Parse unittest output to extract test results."""
    lines = output.split('\n')
    
    results = {
        'tests_run': 0,
        'failures': 0,
        'errors': 0,
        'skipped': 0,
        'test_details': []
    }
    
    # Look for summary line like "Ran 5 tests in 0.123s"
    for line in lines:
        if line.startswith('Ran ') and ' tests in ' in line:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    results['tests_run'] = int(parts[1])
                except ValueError:
                    pass
        
        elif 'FAILED' in line and '(' in line:
            # Parse failures and errors
            if 'failures=' in line:
                try:
                    failures_part = line.split('failures=')[1].split(',')[0].split(')')[0]
                    results['failures'] = int(failures_part)
                except (ValueError, IndexError):
                    pass
            
            if 'errors=' in line:
                try:
                    errors_part = line.split('errors=')[1].split(',')[0].split(')')[0]
                    results['errors'] = int(errors_part)
                except (ValueError, IndexError):
                    pass
        
        elif 'skipped=' in line:
            try:
                skipped_part = line.split('skipped=')[1].split(',')[0].split(')')[0]
                results['skipped'] = int(skipped_part)
            except (ValueError, IndexError):
                pass
    
    return results


def generate_report(test_results: List[Dict], output_file: Path = None) -> str:
    """Generate a comprehensive test report."""
    report_lines = [
        "# Timestamp Accuracy Test Report",
        "",
        f"Generated for GitHub Issue #1: MLX Mode Timestamp Accuracy Issue",
        "",
        "## Test Summary",
        ""
    ]
    
    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    successful_modules = 0
    
    for result in test_results:
        parsed = parse_test_output(result['stdout'])
        total_tests += parsed['tests_run']
        total_failures += parsed['failures']
        total_errors += parsed['errors']
        total_skipped += parsed['skipped']
        
        if result['success']:
            successful_modules += 1
    
    report_lines.extend([
        f"- **Total Test Modules**: {len(test_results)}",
        f"- **Successful Modules**: {successful_modules}",
        f"- **Total Tests Run**: {total_tests}",
        f"- **Failures**: {total_failures}",
        f"- **Errors**: {total_errors}",
        f"- **Skipped**: {total_skipped}",
        "",
        "## Module Results",
        ""
    ])
    
    for result in test_results:
        module = result['module']
        success = "✅" if result['success'] else "❌"
        parsed = parse_test_output(result['stdout'])
        
        report_lines.extend([
            f"### {success} {module}",
            "",
            f"- Tests run: {parsed['tests_run']}",
            f"- Failures: {parsed['failures']}",
            f"- Errors: {parsed['errors']}",
            f"- Skipped: {parsed['skipped']}",
            ""
        ])
        
        if not result['success']:
            report_lines.extend([
                "**Error Output:**",
                "```",
                result['stderr'][:1000] + ("..." if len(result['stderr']) > 1000 else ""),
                "```",
                ""
            ])
        
        # Show any test output that might indicate timestamp issues
        if "conversion factor" in result['stdout'].lower() or "0.02" in result['stdout']:
            report_lines.extend([
                "**Timestamp Issue Detected:**",
                "```",
                result['stdout'][:1000] + ("..." if len(result['stdout']) > 1000 else ""),
                "```",
                ""
            ])
    
    # Add recommendations
    report_lines.extend([
        "## Recommendations",
        ""
    ])
    
    if total_failures > 0 or total_errors > 0:
        report_lines.extend([
            "🚨 **Critical Issues Found:**",
            "",
            "1. Timestamp accuracy tests are failing",
            "2. This confirms the MLX backend timestamp issue",
            "3. Immediate investigation of the 0.02 conversion factor is needed",
            "4. Consider disabling MLX backend until timestamps are fixed",
            ""
        ])
    else:
        report_lines.extend([
            "✅ **All Tests Passing:**",
            "",
            "1. No timestamp accuracy issues detected",
            "2. MLX backend appears to be working correctly",
            "3. Continue monitoring for regression",
            ""
        ])
    
    if total_skipped > 0:
        report_lines.extend([
            f"ℹ️ **{total_skipped} Tests Skipped:**",
            "",
            "- Some tests may require specific hardware (Apple Silicon for MLX)",
            "- Consider running on appropriate hardware for complete coverage",
            ""
        ])
    
    report_content = "\n".join(report_lines)
    
    if output_file:
        output_file.write_text(report_content, encoding='utf-8')
        print(f"Report saved to: {output_file}")
    
    return report_content


def main():
    parser = argparse.ArgumentParser(description="Run timestamp accuracy tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose test output")
    parser.add_argument("--mlx-only", action="store_true", help="Run only MLX-specific tests")
    parser.add_argument("--create-report", action="store_true", help="Generate test report")
    parser.add_argument("--report-file", help="Report output file", default="timestamp_test_report.md")
    
    args = parser.parse_args()
    
    # Define test modules to run
    test_modules = [
        "tests.test_timestamp_accuracy",
        "tests.test_insanely_fast_whisper_mlx"
    ]
    
    if args.mlx_only:
        test_modules = [m for m in test_modules if "mlx" in m]
    
    print("Running Timestamp Accuracy Tests")
    print("=" * 50)
    print(f"Test modules: {', '.join(test_modules)}")
    print()
    
    results = []
    
    for module in test_modules:
        print(f"Running {module}...")
        result = run_unittest_module(module, args.verbose)
        results.append(result)
        
        if result['success']:
            print(f"✅ {module} - PASSED")
        else:
            print(f"❌ {module} - FAILED")
            if args.verbose:
                print(f"Error: {result['stderr']}")
        print()
    
    # Summary
    successful = sum(1 for r in results if r['success'])
    total = len(results)
    
    print("=" * 50)
    print(f"Test Summary: {successful}/{total} modules passed")
    
    if successful == total:
        print("🎉 All timestamp tests passed!")
        exit_code = 0
    else:
        print("🚨 Some timestamp tests failed - MLX backend may have issues")
        exit_code = 1
    
    # Generate report if requested
    if args.create_report:
        print()
        report_file = Path(args.report_file)
        generate_report(results, report_file)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
