"""
Automated Test Suite Runner
Discovers and executes all unit and integration tests
"""

import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_all_tests():
    print("\n" + "="*60)
    print("  RUNNING ORDERFLOW360 AUTOMATED TEST SUITE")
    print("="*60 + "\n")

    loader = unittest.TestLoader()
    suite = loader.discover(start_dir=str(PROJECT_ROOT / "tests"), pattern="test_*.py")
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*60)
    if result.wasSuccessful():
        print(f"  ALL {result.testsRun} TESTS PASSED SUCCESSFULLY! (100% SUCCESS)")
    else:
        print(f"  TEST FAILURES DETECTED: {len(result.failures)} Failures, {len(result.errors)} Errors")
    print("="*60 + "\n")
    
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
