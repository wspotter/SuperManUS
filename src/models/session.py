"""
Session management for SuperManUS
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import redis.asyncio as redis
import asyncpg

from config.settings import Settings

class SessionManager:
    """Manages user sessions and task queues"""
    
    def __init__(self):
        self.settings = Settings()
        self.logger = logging.getLogger(__name__)
        self.redis_client: Optional[redis.Redis] = None
        self.pg_conn: Optional[asyncpg.Connection] = None
        self.current_session: Dict[str, Any] = {}
        self.task_queue: List[Dict[str, Any]] = []
        
    async def load_session(self):
        """Load or create session"""
        try:
            self.redis_client = redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                decode_responses=True
            )
            
            self.pg_conn = await asyncpg.connect(
                host=self.settings.postgres_host,
                port=self.settings.postgres_port,
                user=self.settings.postgres_user,
                password=self.settings.postgres_password,
                database=self.settings.postgres_db
            )
            
            session_file = Path("SESSION_STATE.json")
            if session_file.exists():
                with open(session_file, 'r') as f:
                    self.current_session = json.load(f)
                    
            if "active_tasks" in self.current_session:
                for task_str in self.current_session["active_tasks"]:
                    self.task_queue.append({
                        "id": task_str,
                        "name": task_str,
                        "type": "general",
                        "status": "pending"
                    })
            
            self.logger.info(f"Session loaded with {len(self.task_queue)} tasks")
            
        except Exception as e:
            self.logger.error(f"Failed to load session: {e}")
    
    async def get_next_task(self) -> Optional[Dict[str, Any]]:
        """Get next task from queue"""
        
        if self.redis_client:
            task_data = await self.redis_client.lpop("task_queue")
            if task_data:
                return json.loads(task_data)
        
        if self.task_queue:
            return self.task_queue.pop(0)
        
        return None
    
    async def add_task(self, task: Dict[str, Any]):
        """Add task to queue"""
        
        if self.redis_client:
            await self.redis_client.rpush(
                "task_queue",
                json.dumps(task)
            )
        else:
            self.task_queue.append(task)
        
        self.logger.info(f"Added task: {task.get('name', 'Unknown')}")
    
    async def update_task_status(self, task_id: str, status: str, result: Any = None):
        """Update task status"""
        
        if self.pg_conn:
            await self.pg_conn.execute(
                """
                INSERT INTO task_history (task_id, status, result, completed_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (task_id) DO UPDATE
                SET status = $2, result = $3, completed_at = $4
                """,
                task_id,
                status,
                json.dumps(result) if result else None,
                datetime.utcnow()
            )
        
        self.logger.info(f"Task {task_id} updated to {status}")
    
    async def save_session(self):
        """Save current session state"""
        
        self.current_session["last_updated"] = datetime.utcnow().isoformat()
        self.current_session["pending_tasks"] = [
            task["id"] for task in self.task_queue
        ]
        
        with open("SESSION_STATE.json", 'w') as f:
            json.dump(self.current_session, f, indent=2)
        
        if self.redis_client:
            await self.redis_client.aclose()
        
        if self.pg_conn:
            await self.pg_conn.close()
        
        self.logger.info("Session saved")