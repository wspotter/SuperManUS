"""
Anticipation Engine for SuperManUS
Predicts user needs and preloads resources
"""

import asyncio
from typing import Dict, Any, List, Optional
import logging
import json
from datetime import datetime, timedelta
from collections import deque
import numpy as np

class AnticipationEngine:
    """Predicts and prepares for future user needs"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pattern_history = deque(maxlen=100)
        self.resource_predictions = {}
        self.confidence_threshold = 0.75
        self.patterns = self._load_patterns()
        
    def _load_patterns(self) -> Dict[str, Any]:
        """Load behavioral patterns"""
        return {
            "voice_after_text": {
                "trigger": ["text_input", "query"],
                "predict": ["voice_response"],
                "confidence": 0.85
            },
            "image_after_description": {
                "trigger": ["describe", "generate", "create"],
                "predict": ["image_generation"],
                "confidence": 0.80
            },
            "code_after_error": {
                "trigger": ["error", "bug", "fix"],
                "predict": ["code_analysis"],
                "confidence": 0.90
            },
            "search_after_question": {
                "trigger": ["what", "how", "why", "when"],
                "predict": ["web_search"],
                "confidence": 0.70
            },
            "multiple_services": {
                "trigger": ["complex", "multi", "all"],
                "predict": ["voice_response", "image_generation", "code_analysis"],
                "confidence": 0.65
            }
        }
    
    async def initialize(self):
        """Initialize anticipation engine"""
        self.logger.info("Anticipation Engine initialized")
        asyncio.create_task(self._pattern_analyzer())
    
    async def predict_needs(self, task: Dict[str, Any]) -> List[str]:
        """Predict what resources will be needed"""
        
        predictions = []
        task_text = json.dumps(task).lower()
        
        for pattern_name, pattern in self.patterns.items():
            if any(trigger in task_text for trigger in pattern["trigger"]):
                if pattern["confidence"] >= self.confidence_threshold:
                    predictions.extend(pattern["predict"])
                    self.logger.info(
                        f"Predicted {pattern['predict']} based on {pattern_name} "
                        f"(confidence: {pattern['confidence']})"
                    )
        
        self.pattern_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "task": task.get("name", "unknown"),
            "predictions": predictions
        })
        
        unique_predictions = list(set(predictions))
        
        resource_map = {
            "voice_response": "voice_models",
            "image_generation": "image_models",
            "code_analysis": "code_models",
            "web_search": "search_cache"
        }
        
        resources = [resource_map.get(p, p) for p in unique_predictions]
        
        return resources
    
    async def _pattern_analyzer(self):
        """Continuously analyze patterns and improve predictions"""
        
        while True:
            await asyncio.sleep(60)
            
            if len(self.pattern_history) >= 10:
                self._analyze_recent_patterns()
    
    def _analyze_recent_patterns(self):
        """Analyze recent patterns to improve predictions"""
        
        recent = list(self.pattern_history)[-20:]
        
        pattern_success = {}
        for entry in recent:
            for prediction in entry.get("predictions", []):
                if prediction not in pattern_success:
                    pattern_success[prediction] = {"correct": 0, "total": 0}
                pattern_success[prediction]["total"] += 1
        
        for pattern_name, pattern in self.patterns.items():
            for predicted in pattern["predict"]:
                if predicted in pattern_success:
                    stats = pattern_success[predicted]
                    if stats["total"] > 5:
                        new_confidence = stats["correct"] / stats["total"]
                        old_confidence = pattern["confidence"]
                        
                        pattern["confidence"] = (
                            0.7 * old_confidence + 0.3 * new_confidence
                        )
                        
                        self.logger.info(
                            f"Updated confidence for {pattern_name}: "
                            f"{old_confidence:.2f} -> {pattern['confidence']:.2f}"
                        )
    
    async def learn_from_outcome(self, task: Dict[str, Any], actual_needs: List[str]):
        """Learn from actual resource usage"""
        
        if self.pattern_history:
            last_entry = self.pattern_history[-1]
            if last_entry.get("task") == task.get("name"):
                predicted = set(last_entry.get("predictions", []))
                actual = set(actual_needs)
                
                correct = predicted & actual
                missed = actual - predicted
                extra = predicted - actual
                
                accuracy = len(correct) / max(len(predicted | actual), 1)
                
                self.logger.info(
                    f"Prediction accuracy: {accuracy:.2%} "
                    f"(correct: {correct}, missed: {missed}, extra: {extra})"
                )
                
                if missed:
                    await self._create_new_pattern(task, list(missed))
    
    async def _create_new_pattern(self, task: Dict[str, Any], missed_predictions: List[str]):
        """Create new pattern from missed predictions"""
        
        task_words = task.get("name", "").lower().split()
        
        new_pattern = {
            "trigger": task_words[:3],
            "predict": missed_predictions,
            "confidence": 0.50
        }
        
        pattern_id = f"learned_{len(self.patterns)}"
        self.patterns[pattern_id] = new_pattern
        
        self.logger.info(f"Created new pattern {pattern_id}: {new_pattern}")
    
    async def shutdown(self):
        """Shutdown anticipation engine"""
        
        with open("anticipation_patterns.json", 'w') as f:
            json.dump({
                "patterns": self.patterns,
                "history": list(self.pattern_history)[-50:]
            }, f, indent=2)
        
        self.logger.info("Anticipation Engine shutdown complete")