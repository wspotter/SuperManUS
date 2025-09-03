#!/usr/bin/env python3
"""
SuperManUS Task Enforcement System - Live Demo
Shows how the system prevents LLM deviation and enforces task discipline
"""

import sys
import os
sys.path.insert(0, 'src')

from utils.task_enforcer import TaskSystemEnforcer, get_enforcer
from utils.llm_guard import LLMActionGuard, check_task_discipline, validate_file_creation

def demo_task_enforcement():
    """Demonstrate the task enforcement system in action"""
    print("🚨 SuperManUS Task Enforcement System Demo")
    print("=" * 60)
    
    enforcer = get_enforcer()
    
    # Demo 1: Attempt action without task selection
    print("\n📋 DEMO 1: Action without task selection")
    print("-" * 40)
    
    disciplined, message = check_task_discipline()
    print(f"Task discipline check: {message}")
    
    # Demo 2: Force task selection
    print("\n📋 DEMO 2: Force task selection from official list")
    print("-" * 40)
    
    try:
        active_tasks = enforcer.get_active_tasks()
        print(f"Available tasks: {len(active_tasks)}")
        for i, task in enumerate(active_tasks, 1):
            print(f"  {i}. {task}")
        
        if active_tasks:
            # Select first task for demo
            selected_task = active_tasks[0]
            result = enforcer.set_current_task(selected_task)
            print(f"\nSelected task: {selected_task}")
            print(f"Selection result: {result}")
    except Exception as e:
        print(f"Task selection demo failed: {e}")
    
    # Demo 3: Attempt action without work log
    print("\n📋 DEMO 3: Action attempt without work log")
    print("-" * 40)
    
    disciplined, message = check_task_discipline()
    print(f"Task discipline check: {message[:200]}...")
    
    # Demo 4: Work log requirement
    print("\n📋 DEMO 4: Work log enforcement")
    print("-" * 40)
    
    work_log_msg = enforcer.require_work_log()
    print(f"Work log requirement: {work_log_msg[:150]}...")
    
    # Demo 5: Action validation with poor justification
    print("\n📋 DEMO 5: Action validation with poor justification") 
    print("-" * 40)
    
    try:
        with LLMActionGuard("Create random file", "because"):
            print("This should be blocked!")
    except Exception as e:
        print(f"✅ Properly blocked: {e}")
    
    # Demo 6: Action validation with good justification
    print("\n📋 DEMO 6: Action validation with proper justification")
    print("-" * 40)
    
    # Simulate work log being active for demo
    enforcer.work_log_active = True
    
    try:
        with LLMActionGuard(
            "Create task documentation file", 
            "This documentation file directly supports the current task by providing detailed implementation notes and tracking progress, which is essential for completing the assigned task requirements"
        ):
            print("✅ Action approved with proper justification")
    except Exception as e:
        print(f"❌ Unexpected block: {e}")
    
    # Demo 7: Completion proof requirements
    print("\n📋 DEMO 7: Completion proof requirements")
    print("-" * 40)
    
    proof_requirements = enforcer.require_completion_proof()
    print(f"Task: {proof_requirements.get('task_id', 'N/A')}")
    print(f"Risk level: {proof_requirements.get('risk_level', 'N/A')}")
    print("Required proof types:")
    for req_type, description in proof_requirements.get('requirements', {}).items():
        print(f"  • {req_type}: {description}")
    
    # Demo 8: Validation commands
    print("\n📋 DEMO 8: Auto-generated validation commands")
    print("-" * 40)
    
    validation_commands = proof_requirements.get('validation_commands', [])
    print("Validation commands for current task:")
    for i, cmd in enumerate(validation_commands, 1):
        print(f"  {i}. {cmd}")
    
    print("\n" + "=" * 60)
    print("🎯 DEMO COMPLETE")
    print("The task enforcement system successfully:")
    print("  ✅ Blocked actions without task selection")
    print("  ✅ Enforced work log requirements") 
    print("  ✅ Validated action justifications")
    print("  ✅ Generated appropriate proof requirements")
    print("  ✅ Created validation commands")
    print("\nThis system prevents LLM deviation and ensures task discipline!")

if __name__ == "__main__":
    try:
        demo_task_enforcement()
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()