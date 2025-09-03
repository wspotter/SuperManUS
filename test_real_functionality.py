#!/usr/bin/env python3
"""
Real functionality tests for SuperManUS
Tests that actually execute code, not just file existence
"""

import subprocess
import sys
import os
import json
import time
from pathlib import Path

def test_main_app_imports():
    """Test that main.py imports successfully without crashing"""
    print("Testing main app imports...")
    
    # Test import by running Python -c "import ..." 
    result = subprocess.run([
        sys.executable, "-c", 
        "import sys; sys.path.insert(0, 'src'); "
        "from main import SuperManUS; "
        "print('SUCCESS: Main app imports work')"
    ], capture_output=True, text=True, timeout=10)
    
    if result.returncode != 0:
        print(f"FAILED: Main app import failed: {result.stderr}")
        return False
    else:
        print("PASSED: Main app imports successfully")
        return True

def test_core_module_imports():
    """Test that all core modules can be imported individually"""
    print("Testing core module imports...")
    
    modules_to_test = [
        "config.settings",
        "utils.logger", 
        "utils.orchestrator",
        "models.session",
        "models.anticipation"
    ]
    
    all_passed = True
    for module in modules_to_test:
        result = subprocess.run([
            sys.executable, "-c",
            f"import sys; sys.path.insert(0, 'src'); "
            f"import {module}; "
            f"print('SUCCESS: {module} imports work')"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            print(f"FAILED: {module} import failed: {result.stderr}")
            all_passed = False
        else:
            print(f"PASSED: {module} imports successfully")
    
    return all_passed

def test_main_app_startup():
    """Test that main.py starts up (even if it can't connect to services)"""
    print("Testing main app startup...")
    
    # Run main.py with a timeout to see if it starts
    process = subprocess.Popen([
        sys.executable, "src/main.py"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    try:
        # Let it run for 3 seconds to see startup messages
        stdout, stderr = process.communicate(timeout=3)
        print(f"FAILED: Process exited unexpectedly: {stderr}")
        return False
    except subprocess.TimeoutExpired:
        # This is expected - the app should keep running
        process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
        
        # Check if we got expected startup messages or service unavailable messages (which means it started)
        if ("Initializing SuperManUS" in stderr or 
            "SuperManUS is running" in stderr or
            "MCP Server is unavailable" in stderr):  # This means it started but can't connect to services
            print("PASSED: Main app starts and attempts initialization")
            return True
        else:
            print(f"FAILED: Unexpected startup behavior: {stderr}")
            return False

def test_dependencies_installed():
    """Test that all required dependencies are properly installed"""
    print("Testing dependencies...")
    
    required_packages = [
        "redis", "aiohttp", "asyncpg", "numpy", 
        "pandas", "sklearn", "fastapi", "uvicorn"
    ]
    
    all_passed = True
    for package in required_packages:
        # Map package names that differ between pip and import
        import_name = package
        if package == "sklearn":
            import_name = "sklearn"
        
        result = subprocess.run([
            sys.executable, "-c",
            f"import {import_name}; print('SUCCESS: {package} available')"
        ], capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            print(f"FAILED: {package} not available: {result.stderr}")
            all_passed = False
        else:
            print(f"PASSED: {package} is available")
    
    return all_passed

def test_session_state_readable():
    """Test that SESSION_STATE.json is readable and valid"""
    print("Testing SESSION_STATE.json...")
    
    try:
        with open("SESSION_STATE.json", 'r') as f:
            data = json.load(f)
        
        required_keys = ["current_session_id", "project_name", "modules_status"]
        for key in required_keys:
            if key not in data:
                print(f"FAILED: Missing required key '{key}' in SESSION_STATE.json")
                return False
        
        print("PASSED: SESSION_STATE.json is valid and readable")
        return True
        
    except Exception as e:
        print(f"FAILED: Could not read SESSION_STATE.json: {e}")
        return False

def run_all_tests():
    """Run all functionality tests"""
    print("=" * 60)
    print("SUPERMANUS REAL FUNCTIONALITY TESTS")
    print("=" * 60)
    print()
    
    tests = [
        ("Dependencies Installation", test_dependencies_installed),
        ("Session State File", test_session_state_readable),
        ("Core Module Imports", test_core_module_imports),
        ("Main App Imports", test_main_app_imports),
        ("Main App Startup", test_main_app_startup),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        if test_func():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 ALL TESTS PASSED - SuperManUS core functionality is working!")
        return True
    else:
        print("❌ SOME TESTS FAILED - Core functionality issues remain")
        return False

if __name__ == "__main__":
    # Change to project directory
    os.chdir(Path(__file__).parent)
    
    success = run_all_tests()
    sys.exit(0 if success else 1)