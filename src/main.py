#!/usr/bin/env python3
"""
SuperManUS - Main Application Entry Point
Autonomous AI system with anticipatory capabilities
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import json
import os

from config.settings import Settings
from utils.logger import setup_logging
from utils.orchestrator import ServiceOrchestrator
from models.session import SessionManager
from models.anticipation import AnticipationEngine

class SuperManUS:
    """Main application class for SuperManUS autonomous AI system"""
    
    def __init__(self):
        self.settings = Settings()
        self.logger = setup_logging(__name__)
        self.orchestrator = ServiceOrchestrator()
        self.session_manager = SessionManager()
        self.anticipation_engine = AnticipationEngine()
        self.running = False
        
    async def initialize(self):
        """Initialize all services and connections"""
        self.logger.info("Initializing SuperManUS...")
        
        try:
            await self.orchestrator.connect_services()
            await self.session_manager.load_session()
            await self.anticipation_engine.initialize()
            
            self.logger.info("All services initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}")
            return False
    
    async def run(self):
        """Main run loop"""
        self.running = True
        self.logger.info("SuperManUS is running...")
        
        while self.running:
            try:
                task = await self.session_manager.get_next_task()
                
                if task:
                    self.logger.info(f"Processing task: {task.get('name', 'Unknown')}")
                    
                    anticipated_needs = await self.anticipation_engine.predict_needs(task)
                    
                    result = await self.orchestrator.execute_task(
                        task,
                        anticipated_needs
                    )
                    
                    await self.session_manager.update_task_status(
                        task['id'],
                        'completed',
                        result
                    )
                    
                await asyncio.sleep(1)
                
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal")
                break
            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)
    
    async def shutdown(self):
        """Graceful shutdown"""
        self.logger.info("Shutting down SuperManUS...")
        self.running = False
        
        await self.session_manager.save_session()
        await self.orchestrator.disconnect_services()
        await self.anticipation_engine.shutdown()
        
        self.logger.info("Shutdown complete")

async def main():
    """Main entry point"""
    app = SuperManUS()
    
    if not await app.initialize():
        sys.exit(1)
    
    try:
        await app.run()
    finally:
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())