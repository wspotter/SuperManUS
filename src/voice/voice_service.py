#!/usr/bin/env python3
"""
Voice Service for SuperManUS
Handles speech-to-text and text-to-speech operations
"""

import asyncio
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any, Union
import numpy as np
import soundfile as sf
import torch
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
import whisper
from TTS.api import TTS
import librosa
import webrtcvad
import pyttsx3
import edge_tts

app = FastAPI(title="SuperManUS Voice Service")
logger = logging.getLogger(__name__)

class VoiceProcessor:
    """Processes voice input and generates speech output"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.whisper_model = None
        self.whisper_tiny = None
        self.tts_model = None
        self.kokoro_tts = None
        self.pyttsx_engine = None
        self.vad = webrtcvad.Vad(3)
        self.models_loaded = False
        self.tts_backends = {}
        
    async def initialize(self):
        """Load AI models with multiple backends"""
        try:
            logger.info(f"Loading models on {self.device}")
            
            self.whisper_model = whisper.load_model("base", device=self.device)
            self.whisper_tiny = whisper.load_model("tiny", device=self.device)
            
            try:
                self.kokoro_tts = TTS(
                    model_name="tts_models/en/vctk/vits",
                    progress_bar=False,
                    gpu=self.device == "cuda"
                )
                self.tts_backends["kokoro"] = self.kokoro_tts
                logger.info("Kokoro TTS loaded")
            except:
                logger.warning("Kokoro TTS not available")
            
            try:
                self.tts_model = TTS(
                    model_name="tts_models/en/ljspeech/tacotron2-DDC",
                    progress_bar=False,
                    gpu=self.device == "cuda"
                )
                self.tts_backends["coqui"] = self.tts_model
                logger.info("Coqui TTS loaded")
            except:
                logger.warning("Coqui TTS not available")
            
            try:
                self.pyttsx_engine = pyttsx3.init()
                self.pyttsx_engine.setProperty('rate', 150)
                self.pyttsx_engine.setProperty('volume', 0.9)
                self.tts_backends["pyttsx3"] = self.pyttsx_engine
                logger.info("pyttsx3 loaded (fast offline)")
            except:
                logger.warning("pyttsx3 not available")
            
            self.models_loaded = True
            logger.info(f"Voice models loaded. Available TTS: {list(self.tts_backends.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise
    
    async def transcribe(self, audio_data: bytes, language: str = "en", fast_mode: bool = False) -> Dict[str, Any]:
        """Convert speech to text with fast/accurate modes"""
        
        if not self.models_loaded:
            await self.initialize()
        
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                tmp_path = tmp_file.name
            
            audio, sr = librosa.load(tmp_path, sr=16000)
            
            if self._is_silence(audio, sr):
                return {
                    "text": "",
                    "language": language,
                    "confidence": 0.0,
                    "is_silence": True
                }
            
            model = self.whisper_tiny if fast_mode else self.whisper_model
            model_name = "tiny" if fast_mode else "base"
            
            result = model.transcribe(
                tmp_path,
                language=language,
                task="transcribe",
                fp16=self.device == "cuda"
            )
            
            os.unlink(tmp_path)
            
            return {
                "text": result["text"].strip(),
                "language": result.get("language", language),
                "segments": result.get("segments", []),
                "confidence": self._calculate_confidence(result),
                "model": model_name,
                "fast_mode": fast_mode
            }
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    async def synthesize(self, text: str, voice: str = "default", backend: str = "auto") -> bytes:
        """Convert text to speech with multiple backend options"""
        
        if not self.models_loaded:
            await self.initialize()
        
        try:
            if backend == "auto":
                if "kokoro" in self.tts_backends:
                    backend = "kokoro"
                elif "coqui" in self.tts_backends:
                    backend = "coqui"
                elif "pyttsx3" in self.tts_backends:
                    backend = "pyttsx3"
                else:
                    backend = "edge"
            
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            if backend == "kokoro" and "kokoro" in self.tts_backends:
                self.kokoro_tts.tts_to_file(
                    text=text,
                    file_path=tmp_path,
                    speaker="p225"
                )
            elif backend == "coqui" and "coqui" in self.tts_backends:
                self.tts_model.tts_to_file(
                    text=text,
                    file_path=tmp_path
                )
            elif backend == "pyttsx3" and "pyttsx3" in self.tts_backends:
                self.pyttsx_engine.save_to_file(text, tmp_path)
                self.pyttsx_engine.runAndWait()
            elif backend == "edge":
                communicate = edge_tts.Communicate(text, "en-US-JennyNeural")
                await communicate.save(tmp_path)
            else:
                raise ValueError(f"Backend {backend} not available")
            
            with open(tmp_path, 'rb') as f:
                audio_data = f.read()
            
            os.unlink(tmp_path)
            
            if backend != "pyttsx3":
                processed_audio = await self._enhance_audio(audio_data)
            else:
                processed_audio = audio_data
            
            return processed_audio
            
        except Exception as e:
            logger.error(f"Synthesis failed with backend {backend}: {e}")
            raise
    
    def _is_silence(self, audio: np.ndarray, sample_rate: int) -> bool:
        """Check if audio is mostly silence"""
        
        audio_bytes = (audio * 32767).astype(np.int16).tobytes()
        
        frame_duration = 30
        frame_length = int(sample_rate * frame_duration / 1000) * 2
        
        num_voiced = 0
        num_frames = len(audio_bytes) // frame_length
        
        for i in range(num_frames):
            frame = audio_bytes[i * frame_length:(i + 1) * frame_length]
            if len(frame) == frame_length:
                is_speech = self.vad.is_speech(frame, sample_rate)
                if is_speech:
                    num_voiced += 1
        
        voiced_ratio = num_voiced / max(num_frames, 1)
        return voiced_ratio < 0.1
    
    def _calculate_confidence(self, result: Dict) -> float:
        """Calculate confidence score from Whisper result"""
        
        if not result.get("segments"):
            return 0.0
        
        confidences = []
        for segment in result["segments"]:
            if "no_speech_prob" in segment:
                confidences.append(1.0 - segment["no_speech_prob"])
        
        return np.mean(confidences) if confidences else 0.0
    
    async def _enhance_audio(self, audio_data: bytes) -> bytes:
        """Apply audio enhancement"""
        
        audio, sr = sf.read(io.BytesIO(audio_data))
        
        audio = librosa.effects.preemphasis(audio)
        
        audio = np.clip(audio, -1, 1)
        
        output = io.BytesIO()
        sf.write(output, audio, sr, format='WAV')
        output.seek(0)
        
        return output.read()

processor = VoiceProcessor()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await processor.initialize()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "models_loaded": processor.models_loaded,
        "device": processor.device
    }

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = "en"
):
    """Transcribe audio to text"""
    
    try:
        audio_data = await file.read()
        result = await processor.transcribe(audio_data, language)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/synthesize")
async def synthesize_speech(request: Dict[str, Any]):
    """Synthesize text to speech"""
    
    try:
        text = request.get("text", "")
        voice = request.get("voice", "default")
        
        if not text:
            raise ValueError("No text provided")
        
        audio_data = await processor.synthesize(text, voice)
        
        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process")
async def process_voice(request: Dict[str, Any]):
    """Process voice request (transcribe or synthesize)"""
    
    try:
        task_type = request.get("type", "transcribe")
        
        if task_type == "transcribe":
            if "audio" in request:
                import base64
                audio_data = base64.b64decode(request["audio"])
                result = await processor.transcribe(audio_data)
                return {"type": "transcription", "result": result}
        
        elif task_type == "synthesize":
            text = request.get("text", "")
            audio_data = await processor.synthesize(text)
            import base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            return {"type": "synthesis", "audio": audio_b64}
        
        else:
            raise ValueError(f"Unknown task type: {task_type}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/preload")
async def preload_models(request: Dict[str, Any]):
    """Preload specific models"""
    
    models = request.get("models", [])
    
    if not processor.models_loaded:
        await processor.initialize()
    
    return {"status": "models_loaded", "models": models}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)