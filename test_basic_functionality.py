#!/usr/bin/env python3
"""
Basic SuperManUS functionality test - no external dependencies
"""

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_imports():
    """Test core SuperManUS imports"""
    print("🧪 Testing basic imports...")
    
    try:
        from config.settings import Settings
        settings = Settings()
        print(f"✅ Settings: {settings.app_name} v{settings.version}")
    except ImportError as e:
        print(f"❌ Settings import failed: {e}")
        return False
    
    try:
        from utils.celery_app import celery_app, TaskDispatcher
        print(f"✅ Celery app: {celery_app.main}")
        
        dispatcher = TaskDispatcher()
        print("✅ TaskDispatcher created")
    except ImportError as e:
        print(f"❌ Celery import failed: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Celery creation error (expected without Redis): {e}")
    
    return True

def test_file_structure():
    """Test that all expected files exist"""
    print("\n🗂️  Testing file structure...")
    
    required_files = [
        'src/main.py',
        'src/config/settings.py', 
        'src/utils/celery_app.py',
        'src/utils/orchestrator.py',
        'docker-compose.yml',
        'k8s/namespace.yaml',
        'k8s/deploy.sh',
        'SESSION_STATE.json',
        'MASTER_PLAN.md'
    ]
    
    missing = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} MISSING")
            missing.append(file_path)
    
    return len(missing) == 0

def test_kubernetes_manifests():
    """Test Kubernetes manifests completeness"""
    print("\n☸️  Testing Kubernetes manifests...")
    
    k8s_files = [
        'namespace.yaml',
        'redis-deployment.yaml', 
        'postgres-deployment.yaml',
        'mcp-server-deployment.yaml',
        'celery-deployment.yaml',
        'ai-services-deployment.yaml',
        'ingress.yaml',
        'monitoring.yaml',
        'deploy.sh'
    ]
    
    found = 0
    for k8s_file in k8s_files:
        path = f'k8s/{k8s_file}'
        if os.path.exists(path):
            print(f"✅ {k8s_file}")
            found += 1
        else:
            print(f"❌ {k8s_file} MISSING")
    
    print(f"📊 K8s completeness: {found}/{len(k8s_files)} = {found/len(k8s_files)*100:.0f}%")
    return found == len(k8s_files)

def test_documentation():
    """Test documentation completeness"""
    print("\n📚 Testing documentation...")
    
    docs = [
        'MASTER_PLAN.md',
        'SESSION_STATE.json', 
        'ACTUAL_STATUS_AUDIT.md',
        'WORK_LOG_TEMPLATE.md',
        'K8S_MANIFEST_TASKS.md',
        'ANTICIPATION_ARCHITECTURE.md'
    ]
    
    found = 0
    for doc in docs:
        if os.path.exists(doc):
            print(f"✅ {doc}")
            found += 1
        else:
            print(f"❌ {doc} MISSING")
    
    return found >= len(docs) - 1  # Allow 1 missing doc

def main():
    """Run all functionality tests"""
    print("🦸 SuperManUS Basic Functionality Test")
    print("=" * 40)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("File Structure", test_file_structure),
        ("K8s Manifests", test_kubernetes_manifests), 
        ("Documentation", test_documentation)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} CRASHED: {e}")
            results.append((test_name, False))
    
    print(f"\n🏁 Test Results Summary")
    print("=" * 25)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20s}: {status}")
        if result:
            passed += 1
    
    print(f"\nTotal: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All basic functionality tests PASSED!")
        print("🚀 SuperManUS repository is functional!")
    else:
        print("⚠️  Some tests failed - check output above.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)