#!/usr/bin/env python3
"""
Test script to validate all imports work correctly
"""

import sys
import traceback

def test_import(module_name, description):
    """Test importing a module and report results"""
    try:
        __import__(module_name)
        print(f"✅ {description}: {module_name}")
        return True
    except Exception as e:
        print(f"❌ {description}: {module_name}")
        print(f"   Error: {e}")
        traceback.print_exc()
        return False

def main():
    """Run import tests"""
    print("Testing module imports...")
    print("=" * 50)
    
    modules_to_test = [
        ("config", "Configuration module"),
        ("database", "Database utilities"),
        ("authentication", "Authentication module"),
        ("security", "Security utilities"),
        ("routes.dashboard", "Dashboard routes"),
        ("routes.shopping", "Shopping routes"),
        ("routes.chores", "Chores routes"),
        ("routes.bills", "Bills routes"),
        ("routes.expiry", "Expiry routes"),
    ]
    
    success_count = 0
    total_count = len(modules_to_test)
    
    for module_name, description in modules_to_test:
        if test_import(module_name, description):
            success_count += 1
        print()
    
    print("=" * 50)
    print(f"Import Test Results: {success_count}/{total_count} successful")
    
    if success_count == total_count:
        print("🎉 All imports successful!")
        return 0
    else:
        print("⚠️  Some imports failed. Check errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())