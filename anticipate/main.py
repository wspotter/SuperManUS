import asyncio
import websockets
from voice_module import VoicePipeline
import json
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def call_mcp_tool(ws, tool: str, params: dict):
    await ws.send(json.dumps({"tool": tool, "params": params}))
    response = json.loads(await ws.recv())
    return response.get("result")

async def main():
    voice = VoicePipeline()
    session_id = "user_123"  # Example; use unique ID per session
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect('ws://mcp-server:8000/ws') as ws:
            tools = json.loads(await ws.recv())["tools"]
            logger.info(f"Available tools: {tools}")
            
            # Check for prediction module
            predict_enabled = "predict_next_intent" in tools
            predicted_intent = None
            
            if predict_enabled:
                async with session.post('http://mcp-server:8000/predict', 
                                     json={"session_id": session_id}) as resp:
                    pred = await resp.json()
                    predicted_intent = pred["predicted_intents"][0] if pred["confidence"] > 0.7 else None
            
            while True:
                user_input = await voice.listen()
                intent, params = voice.process(user_input)
                
                # Log interaction
                await log_interaction(session_id, intent, params)
                
                # Use predicted intent if available and relevant
                if predict_enabled and predicted_intent == intent:
                    result = await call_mcp_tool(ws, intent, params)
                else:
                    result = await call_mcp_tool(ws, intent, params)
                
                # Async prefetch next prediction
                if predict_enabled:
                    async with session.post('http://mcp-server:8000/predict', 
                                         json={"session_id": session_id}) as resp:
                        pred = await resp.json()
                        predicted_intent = pred["predicted_intents"][0] if pred["confidence"] > 0.7 else None
                        if predicted_intent:
                            asyncio.create_task(call_mcp_tool(ws, predicted_intent, {}))  # Prefetch
                            
                response = voice.generate_response(result)
                await voice.speak(response)

if __name__ == "__main__":
    asyncio.run(main())