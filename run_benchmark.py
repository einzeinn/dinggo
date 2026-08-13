#!/usr/bin/env python3
"""
Dinggo Performance & Abstraction Benchmark Runner
Executes comprehensive performance and abstraction benchmarks across the 3-layer architecture.
"""

import sys
import unittest

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from tests.test_benchmark import TestPerformanceAndAbstractionBenchmark

def main():
    print("=" * 70)
    print("DINGGO CLI IDE - PERFORMANCE & ABSTRACTION BENCHMARK SUITE")
    print("=" * 70)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPerformanceAndAbstractionBenchmark)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print("✅ ALL BENCHMARK TESTS PASSED SUCCESSFULLY!")
    else:
        print("❌ BENCHMARK COMPLETED WITH FAILURES!")
    print("=" * 70)
    
    sys.exit(0 if result.wasSuccessful() else 1)

if __name__ == "__main__":
    main()
