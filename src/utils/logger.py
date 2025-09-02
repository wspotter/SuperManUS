"""
Logging utilities for SuperManUS
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
import json

def setup_logging(name: str = None) -> logging.Logger:
    """Setup structured logging"""
    
    logger = logging.getLogger(name or "SuperManUS")
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        
        formatter = StructuredFormatter()
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)
    
    return logger

class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter"""
    
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if hasattr(record, 'extra'):
            log_obj.update(record.extra)
        
        if record.exc_info:
            log_obj['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj)