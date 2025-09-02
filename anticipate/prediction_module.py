from fastapi import FastAPI
from fastapi.websockets import WebSocket
from sklearn.ensemble import RandomForestClassifier
import asyncio
import json
import redis
import sqlite3
import numpy as np
from datetime import datetime
from pydantic import BaseModel
import logging

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Redis for caching predictions
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# SQLite for storing interaction logs
conn = sqlite3.connect('user_logs.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS interactions
                 (session_id TEXT, timestamp TEXT, intent TEXT, params TEXT)''')
conn.commit()

# ML Model
model = RandomForestClassifier(n_estimators=100)

class PredictionRequest(BaseModel):
    session_id: str

class PredictionResponse(BaseModel):
    predicted_intents: list[str]
    confidence: float

# Configurable flag
ENABLE_PREDICTION = True

@app.post("/register")
async def register_tool():
    if ENABLE_PREDICTION:
        tool = {
            "name": "predict_next_intent",
            "endpoint": "/predict",
            "params": [{"name": "session_id", "type": "str"}],
            "description": "Predict next user intent based on history"
        }
        return {"status": "registered", "tool": tool}
    return {"status": "disabled"}

@app.post("/predict", response_model=PredictionResponse)
async def predict_intent(request: PredictionRequest):
    # Fetch recent interactions
    cursor.execute("SELECT intent, params FROM interactions WHERE session_id = ? ORDER BY timestamp DESC LIMIT 10", (request.session_id,))
    history = cursor.fetchall()
    
    if not history:
        return PredictionResponse(predicted_intents=["default"], confidence=0.0)
    
    # Featurize history (simple: intent counts)
    intents = [row[0] for row in history]
    features = np.array([intents.count(i) for i in set(intents)]).reshape(1, -1)
    
    # Predict
    try:
        pred = model.predict(features)[0]
        confidence = model.predict_proba(features)[0].max()
    except:
        pred = "default"
        confidence = 0.0
    
    return PredictionResponse(predicted_intents=[pred], confidence=confidence)

async def train_model():
    while True:
        cursor.execute("SELECT intent, params FROM interactions ORDER BY timestamp DESC LIMIT 1000")
        data = cursor.fetchall()
        if len(data) > 10:
            intents = [row[0] for row in data]
            features = np.array([[intents[:i].count(intent) for intent in set(intents)] for i in range(1, len(intents))])
            labels = intents[1:]
            model.fit(features, labels)
            logger.info("Model retrained")
        await asyncio.sleep(3600)  # Train hourly

async def log_interaction(session_id: str, intent: str, params: dict):
    timestamp = datetime.now().isoformat()
    cursor.execute("INSERT INTO interactions VALUES (?, ?, ?, ?)", 
                  (session_id, timestamp, intent, json.dumps(params)))
    conn.commit()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    if ENABLE_PREDICTION:
        await websocket.send_json({"tools": ["predict_next_intent"]})
    else:
        await websocket.send_json({"tools": []})

# Background task for training
asyncio.create_task(train_model())