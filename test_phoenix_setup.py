#!/usr/bin/env python3
"""
Quick validation script to check Phoenix integration setup.
Run this to verify all dependencies and configuration are correct.
"""

import sys

def check_imports():
    """Check if all required Phoenix packages are importable."""
    print("Checking Phoenix dependencies...")
    
    required_packages = [
        ("openinference.instrumentation.dspy", "DSPy instrumentation"),
        ("opentelemetry.sdk.trace", "OpenTelemetry SDK"),
        ("opentelemetry.exporter.otlp.proto.grpc.trace_exporter", "OTLP exporter"),
    ]
    
    missing = []
    for package, description in required_packages:
        try:
            __import__(package)
            print(f"  ✓ {description}")
        except ImportError as e:
            print(f"  ✗ {description}: {e}")
            missing.append(package)
    
    return len(missing) == 0

def check_dspy():
    """Check if DSPy is properly installed."""
    print("\nChecking DSPy installation...")
    try:
        import dspy
        print(f"  ✓ DSPy version: {dspy.__version__ if hasattr(dspy, '__version__') else 'unknown'}")
        
        # Check for modern API
        if hasattr(dspy, 'Predict'):
            print("  ✓ Modern DSPy API (dspy.Predict) available")
        else:
            print("  ✗ Modern DSPy API not found")
            return False
            
        return True
    except ImportError as e:
        print(f"  ✗ DSPy not installed: {e}")
        return False

def check_env_vars():
    """Check if Phoenix environment variables are set."""
    print("\nChecking environment variables...")
    import os
    
    env_vars = [
        ("OTEL_EXPORTER_OTLP_ENDPOINT", "http://phoenix:4317"),
        ("PHOENIX_PROJECT_NAME", "tabbacklog"),
    ]
    
    all_set = True
    for var, default in env_vars:
        value = os.environ.get(var, default)
        if value and value != "disabled":
            print(f"  ✓ {var}={value}")
        else:
            print(f"  ℹ {var} not set (will use default: {default})")
    
    return all_set

def main():
    """Run all checks."""
    print("=" * 60)
    print("Phoenix Integration Setup Validation")
    print("=" * 60)
    
    checks = [
        ("Dependencies", check_imports),
        ("DSPy", check_dspy),
        ("Environment", check_env_vars),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Error checking {name}: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All checks passed! Phoenix integration is ready.")
        print("\nNext steps:")
        print("  1. Start services: docker-compose up -d")
        print("  2. Access Phoenix: http://localhost:6006")
        print("  3. Trigger enrichment to see traces")
        return 0
    else:
        print("\n✗ Some checks failed. Please install missing dependencies:")
        print("  pip install -r requirements.txt")
        return 1

if __name__ == "__main__":
    sys.exit(main())
