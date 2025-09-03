"""
SuperManUS Distributed Task Queue with Celery
Handles async task distribution across the system
"""

import asyncio
from celery import Celery, Task
from celery.signals import worker_ready, worker_shutting_down
import redis
import logging
from typing import Dict, Any, Optional, List
import json
import aiohttp
import time

from config.settings import Settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize settings
settings = Settings()

# Create Celery app
celery_app = Celery(
    'supermanus',
    broker=f'redis://{settings.redis_host}:{settings.redis_port}/0',
    backend=f'redis://{settings.redis_host}:{settings.redis_port}/0',
    include=['utils.celery_app']
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        'utils.celery_app.process_voice_task': {'queue': 'voice'},
        'utils.celery_app.process_image_task': {'queue': 'image'},
        'utils.celery_app.process_code_task': {'queue': 'code'},
        'utils.celery_app.process_search_task': {'queue': 'search'},
        'utils.celery_app.process_composite_task': {'queue': 'orchestrator'},
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Task execution
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Result backend
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'retry_policy': {
            'timeout': 5.0
        }
    },
    
    # Queue configuration
    task_default_queue='default',
    task_default_exchange='default',
    task_default_exchange_type='direct',
    task_default_routing_key='default',
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

class AsyncTask(Task):
    """Base task class that supports async operations"""
    
    def run(self, *args, **kwargs):
        """Run the task in an event loop"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.async_run(*args, **kwargs))
        finally:
            loop.close()
    
    async def async_run(self, *args, **kwargs):
        """Override this method with async implementation"""
        raise NotImplementedError("Subclasses must implement async_run")

# Global HTTP session for service calls
_http_session: Optional[aiohttp.ClientSession] = None

async def get_http_session() -> aiohttp.ClientSession:
    """Get or create HTTP session for service calls"""
    global _http_session
    if _http_session is None or _http_session.closed:
        _http_session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
    return _http_session

async def call_service(service_url: str, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Call a microservice endpoint"""
    session = await get_http_session()
    
    try:
        async with session.post(
            f"{service_url}{endpoint}",
            json=data,
            headers={'Content-Type': 'application/json'}
        ) as response:
            if response.status == 200:
                return await response.json()
            else:
                error_text = await response.text()
                raise Exception(f"Service call failed: {response.status} - {error_text}")
    except aiohttp.ClientError as e:
        raise Exception(f"Service connection error: {str(e)}")
    except Exception as e:
        raise Exception(f"Service call error: {str(e)}")

# Task implementations

@celery_app.task(base=AsyncTask, bind=True, name='process_voice_task')
async def process_voice_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process voice-related tasks"""
    logger.info(f"Processing voice task: {task_data.get('type', 'unknown')}")
    
    start_time = time.time()
    
    try:
        # Call voice service
        result = await call_service(
            settings.voice_service_url,
            "/process",
            task_data
        )
        
        execution_time = time.time() - start_time
        
        return {
            "status": "completed",
            "task_type": "voice",
            "result": result,
            "execution_time": execution_time,
            "worker": self.request.hostname
        }
        
    except Exception as e:
        logger.error(f"Voice task failed: {str(e)}")
        return {
            "status": "failed",
            "task_type": "voice",
            "error": str(e),
            "execution_time": time.time() - start_time,
            "worker": self.request.hostname
        }

@celery_app.task(base=AsyncTask, bind=True, name='process_image_task')
async def process_image_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process image generation tasks"""
    logger.info(f"Processing image task: {task_data.get('type', 'unknown')}")
    
    start_time = time.time()
    
    try:
        # Call image service
        result = await call_service(
            settings.image_service_url,
            "/generate",
            task_data
        )
        
        execution_time = time.time() - start_time
        
        return {
            "status": "completed",
            "task_type": "image",
            "result": result,
            "execution_time": execution_time,
            "worker": self.request.hostname
        }
        
    except Exception as e:
        logger.error(f"Image task failed: {str(e)}")
        return {
            "status": "failed",
            "task_type": "image",
            "error": str(e),
            "execution_time": time.time() - start_time,
            "worker": self.request.hostname
        }

@celery_app.task(base=AsyncTask, bind=True, name='process_code_task')
async def process_code_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process code analysis/generation tasks"""
    logger.info(f"Processing code task: {task_data.get('type', 'unknown')}")
    
    start_time = time.time()
    
    try:
        # Call code service
        result = await call_service(
            settings.code_service_url,
            "/analyze",
            task_data
        )
        
        execution_time = time.time() - start_time
        
        return {
            "status": "completed",
            "task_type": "code",
            "result": result,
            "execution_time": execution_time,
            "worker": self.request.hostname
        }
        
    except Exception as e:
        logger.error(f"Code task failed: {str(e)}")
        return {
            "status": "failed",
            "task_type": "code",
            "error": str(e),
            "execution_time": time.time() - start_time,
            "worker": self.request.hostname
        }

@celery_app.task(base=AsyncTask, bind=True, name='process_search_task')
async def process_search_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process web search tasks"""
    logger.info(f"Processing search task: {task_data.get('type', 'unknown')}")
    
    start_time = time.time()
    
    try:
        # Call search service
        result = await call_service(
            settings.search_service_url,
            "/query",
            task_data
        )
        
        execution_time = time.time() - start_time
        
        return {
            "status": "completed",
            "task_type": "search",
            "result": result,
            "execution_time": execution_time,
            "worker": self.request.hostname
        }
        
    except Exception as e:
        logger.error(f"Search task failed: {str(e)}")
        return {
            "status": "failed",
            "task_type": "search",
            "error": str(e),
            "execution_time": time.time() - start_time,
            "worker": self.request.hostname
        }

@celery_app.task(base=AsyncTask, bind=True, name='process_composite_task')
async def process_composite_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process composite tasks that involve multiple services"""
    logger.info(f"Processing composite task: {task_data.get('type', 'unknown')}")
    
    start_time = time.time()
    
    try:
        services = task_data.get('services', [])
        results = {}
        
        # Process services in parallel if possible
        if task_data.get('parallel', True):
            # Create tasks for each service
            service_tasks = []
            for service_name in services:
                if service_name == 'voice':
                    service_tasks.append(call_service(settings.voice_service_url, "/process", task_data))
                elif service_name == 'image':
                    service_tasks.append(call_service(settings.image_service_url, "/generate", task_data))
                elif service_name == 'code':
                    service_tasks.append(call_service(settings.code_service_url, "/analyze", task_data))
                elif service_name == 'search':
                    service_tasks.append(call_service(settings.search_service_url, "/query", task_data))
            
            # Execute all tasks concurrently
            service_results = await asyncio.gather(*service_tasks, return_exceptions=True)
            
            # Combine results
            for i, service_name in enumerate(services):
                if isinstance(service_results[i], Exception):
                    results[service_name] = {"status": "failed", "error": str(service_results[i])}
                else:
                    results[service_name] = service_results[i]
        else:
            # Process services sequentially
            for service_name in services:
                try:
                    if service_name == 'voice':
                        results[service_name] = await call_service(settings.voice_service_url, "/process", task_data)
                    elif service_name == 'image':
                        results[service_name] = await call_service(settings.image_service_url, "/generate", task_data)
                    elif service_name == 'code':
                        results[service_name] = await call_service(settings.code_service_url, "/analyze", task_data)
                    elif service_name == 'search':
                        results[service_name] = await call_service(settings.search_service_url, "/query", task_data)
                except Exception as e:
                    results[service_name] = {"status": "failed", "error": str(e)}
        
        execution_time = time.time() - start_time
        
        return {
            "status": "completed",
            "task_type": "composite",
            "results": results,
            "execution_time": execution_time,
            "worker": self.request.hostname
        }
        
    except Exception as e:
        logger.error(f"Composite task failed: {str(e)}")
        return {
            "status": "failed",
            "task_type": "composite",
            "error": str(e),
            "execution_time": time.time() - start_time,
            "worker": self.request.hostname
        }

# High-level task dispatcher
class TaskDispatcher:
    """High-level interface for dispatching tasks to the queue"""
    
    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=1,  # Use different DB for task tracking
            decode_responses=True
        )
    
    def dispatch_task(self, task_type: str, task_data: Dict[str, Any], 
                     priority: str = 'normal', delay: int = 0) -> str:
        """Dispatch a task to the appropriate queue"""
        
        # Generate task ID
        task_id = f"{task_type}_{int(time.time()*1000)}"
        
        # Set task priority
        queue_options = {}
        if priority == 'high':
            queue_options['priority'] = 9
        elif priority == 'low':
            queue_options['priority'] = 1
        else:
            queue_options['priority'] = 5
        
        # Add delay if specified
        if delay > 0:
            queue_options['countdown'] = delay
        
        # Dispatch based on task type
        try:
            if task_type == 'voice':
                result = process_voice_task.apply_async(
                    args=[task_data], 
                    task_id=task_id,
                    **queue_options
                )
            elif task_type == 'image':
                result = process_image_task.apply_async(
                    args=[task_data], 
                    task_id=task_id,
                    **queue_options
                )
            elif task_type == 'code':
                result = process_code_task.apply_async(
                    args=[task_data], 
                    task_id=task_id,
                    **queue_options
                )
            elif task_type == 'search':
                result = process_search_task.apply_async(
                    args=[task_data], 
                    task_id=task_id,
                    **queue_options
                )
            elif task_type == 'composite':
                result = process_composite_task.apply_async(
                    args=[task_data], 
                    task_id=task_id,
                    **queue_options
                )
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            # Store task metadata in Redis
            task_metadata = {
                "task_id": task_id,
                "task_type": task_type,
                "status": "pending",
                "created_at": time.time(),
                "priority": priority,
                "delay": delay
            }
            
            self.redis_client.hset(
                f"task:{task_id}", 
                mapping=task_metadata
            )
            self.redis_client.expire(f"task:{task_id}", 3600)  # Expire after 1 hour
            
            logger.info(f"Dispatched {task_type} task with ID: {task_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to dispatch task: {str(e)}")
            raise
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a task"""
        
        # Get task metadata from Redis
        task_data = self.redis_client.hgetall(f"task:{task_id}")
        
        if not task_data:
            return {"status": "not_found", "task_id": task_id}
        
        # Get result from Celery if available
        result = celery_app.AsyncResult(task_id)
        
        return {
            "task_id": task_id,
            "status": result.state.lower(),
            "result": result.result if result.successful() else None,
            "error": str(result.result) if result.failed() else None,
            "created_at": float(task_data.get("created_at", 0)),
            "task_type": task_data.get("task_type"),
            "priority": task_data.get("priority")
        }
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        
        inspect = celery_app.control.inspect()
        
        try:
            active = inspect.active()
            scheduled = inspect.scheduled()
            reserved = inspect.reserved()
            
            stats = {
                "active_tasks": sum(len(tasks) for tasks in (active or {}).values()),
                "scheduled_tasks": sum(len(tasks) for tasks in (scheduled or {}).values()),
                "reserved_tasks": sum(len(tasks) for tasks in (reserved or {}).values()),
                "workers": list((active or {}).keys()),
                "queues": ["default", "voice", "image", "code", "search", "orchestrator"]
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {str(e)}")
            return {"error": str(e)}

# Signal handlers
@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handler for when worker starts"""
    logger.info(f"SuperManUS worker {sender} is ready")

@worker_shutting_down.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handler for when worker shuts down"""
    global _http_session
    if _http_session and not _http_session.closed:
        # Note: This is synchronous but Celery signal handlers can't be async
        logger.info(f"SuperManUS worker {sender} shutting down")

# Create dispatcher instance
task_dispatcher = TaskDispatcher()

if __name__ == "__main__":
    # Start Celery worker
    celery_app.start()