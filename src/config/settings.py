"""
Configuration settings for SuperManUS
"""

import os
from dataclasses import dataclass
from typing import Optional
import json
from pathlib import Path

@dataclass
class Settings:
    """Application settings"""
    
    app_name: str = "SuperManUS"
    version: str = "0.1.0"
    
    redis_host: str = os.getenv("REDIS_HOST", "redis")
    redis_port: int = int(os.getenv("REDIS_PORT", 6379))
    
    postgres_host: str = os.getenv("POSTGRES_HOST", "postgres")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", 5432))
    postgres_db: str = os.getenv("POSTGRES_DB", "supermanus")
    postgres_user: str = os.getenv("POSTGRES_USER", "supermanus")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "supermanus_secure_password")
    
    mcp_server_url: str = os.getenv("MCP_SERVER_URL", "http://mcp-server:3000")
    
    voice_service_url: str = os.getenv("VOICE_SERVICE_URL", "http://voice:8001")
    image_service_url: str = os.getenv("IMAGE_SERVICE_URL", "http://image:8002")
    code_service_url: str = os.getenv("CODE_SERVICE_URL", "http://code:8003")
    search_service_url: str = os.getenv("SEARCH_SERVICE_URL", "http://search:8004")
    
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    anticipation_threshold: float = float(os.getenv("ANTICIPATION_THRESHOLD", 0.75))
    
    session_timeout: int = int(os.getenv("SESSION_TIMEOUT", 3600))
    
    gpu_enabled: bool = os.getenv("GPU_ENABLED", "true").lower() == "true"
    rocm_path: str = os.getenv("ROCM_PATH", "/opt/rocm")
    
    @classmethod
    def from_file(cls, path: Path) -> "Settings":
        """Load settings from JSON file"""
        if path.exists():
            with open(path, 'r') as f:
                data = json.load(f)
                return cls(**data)
        return cls()
    
    def to_dict(self) -> dict:
        """Convert settings to dictionary"""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }