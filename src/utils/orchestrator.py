"""
Service orchestration for SuperManUS
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List
import logging
from dataclasses import dataclass
import json

from config.settings import Settings

@dataclass
class ServiceEndpoint:
    """Service endpoint definition"""
    name: str
    url: str
    health_check: str = "/health"
    timeout: int = 30

class ServiceOrchestrator:
    """Orchestrates communication between services"""
    
    def __init__(self):
        self.settings = Settings()
        self.logger = logging.getLogger(__name__)
        self.session: Optional[aiohttp.ClientSession] = None
        self.services = self._init_services()
        self.service_status = {}
        
    def _init_services(self) -> Dict[str, ServiceEndpoint]:
        """Initialize service endpoints"""
        return {
            "mcp": ServiceEndpoint(
                name="MCP Server",
                url=self.settings.mcp_server_url
            ),
            "voice": ServiceEndpoint(
                name="Voice Service",
                url=self.settings.voice_service_url
            ),
            "image": ServiceEndpoint(
                name="Image Service",
                url=self.settings.image_service_url
            ),
            "code": ServiceEndpoint(
                name="Code Service",
                url=self.settings.code_service_url
            ),
            "search": ServiceEndpoint(
                name="Search Service",
                url=self.settings.search_service_url
            )
        }
    
    async def connect_services(self):
        """Connect to all services"""
        self.session = aiohttp.ClientSession()
        
        for service_id, service in self.services.items():
            try:
                async with self.session.get(
                    f"{service.url}{service.health_check}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        self.service_status[service_id] = "healthy"
                        self.logger.info(f"{service.name} is healthy")
                    else:
                        self.service_status[service_id] = "unhealthy"
                        self.logger.warning(f"{service.name} returned {response.status}")
            except Exception as e:
                self.service_status[service_id] = "unavailable"
                self.logger.warning(f"{service.name} is unavailable: {e}")
    
    async def execute_task(self, task: Dict[str, Any], anticipated_needs: List[str]) -> Dict[str, Any]:
        """Execute a task across services"""
        
        task_type = task.get("type", "general")
        result = {"status": "pending", "outputs": {}}
        
        if anticipated_needs:
            self.logger.info(f"Pre-loading for anticipated needs: {anticipated_needs}")
            await self._preload_resources(anticipated_needs)
        
        try:
            if task_type == "voice":
                result["outputs"]["voice"] = await self._call_service("voice", "/process", task)
            elif task_type == "image":
                result["outputs"]["image"] = await self._call_service("image", "/generate", task)
            elif task_type == "code":
                result["outputs"]["code"] = await self._call_service("code", "/analyze", task)
            elif task_type == "search":
                result["outputs"]["search"] = await self._call_service("search", "/query", task)
            elif task_type == "composite":
                results = await asyncio.gather(
                    *[self._call_service(svc, "/process", task) 
                      for svc in task.get("services", [])]
                )
                result["outputs"] = dict(zip(task.get("services", []), results))
            
            result["status"] = "completed"
            
        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
        
        return result
    
    async def _call_service(self, service_id: str, endpoint: str, data: Dict[str, Any]) -> Any:
        """Call a specific service endpoint"""
        
        if service_id not in self.services:
            raise ValueError(f"Unknown service: {service_id}")
        
        service = self.services[service_id]
        
        try:
            async with self.session.post(
                f"{service.url}{endpoint}",
                json=data,
                timeout=aiohttp.ClientTimeout(total=service.timeout)
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise Exception(f"Service returned {response.status}")
                    
        except asyncio.TimeoutError:
            raise Exception(f"{service.name} timeout")
        except Exception as e:
            raise Exception(f"{service.name} error: {e}")
    
    async def _preload_resources(self, resources: List[str]):
        """Preload resources based on anticipated needs"""
        
        preload_tasks = []
        
        for resource in resources:
            if resource == "voice_models":
                preload_tasks.append(
                    self._call_service("voice", "/preload", {"models": ["whisper", "tts"]})
                )
            elif resource == "image_models":
                preload_tasks.append(
                    self._call_service("image", "/preload", {"models": ["sdxl"]})
                )
            elif resource == "code_models":
                preload_tasks.append(
                    self._call_service("code", "/preload", {"models": ["codellama"]})
                )
        
        if preload_tasks:
            await asyncio.gather(*preload_tasks, return_exceptions=True)
    
    async def disconnect_services(self):
        """Disconnect from all services"""
        if self.session:
            await self.session.close()