#!/usr/bin/env python3
"""
Image Service for SuperManUS
Handles image generation, manipulation and analysis
"""

import asyncio
import io
import logging
import os
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
import torch
from PIL import Image
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
from diffusers import (
    StableDiffusionPipeline,
    StableDiffusionImg2ImgPipeline,
    StableDiffusionInpaintPipeline,
    DPMSolverMultistepScheduler
)
from transformers import CLIPImageProcessor, CLIPModel
import cv2

app = FastAPI(title="SuperManUS Image Service")
logger = logging.getLogger(__name__)

class ImageGenerator:
    """Generates and manipulates images using Stable Diffusion"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.txt2img_pipeline = None
        self.img2img_pipeline = None
        self.inpaint_pipeline = None
        self.clip_model = None
        self.clip_processor = None
        self.models_loaded = False
        
    async def initialize(self):
        """Load AI models"""
        try:
            logger.info(f"Loading image models on {self.device}")
            
            model_id = "stabilityai/stable-diffusion-2-1"
            
            self.txt2img_pipeline = StableDiffusionPipeline.from_pretrained(
                model_id,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                safety_checker=None,
                requires_safety_checker=False
            ).to(self.device)
            
            self.txt2img_pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
                self.txt2img_pipeline.scheduler.config
            )
            
            self.img2img_pipeline = StableDiffusionImg2ImgPipeline(
                vae=self.txt2img_pipeline.vae,
                text_encoder=self.txt2img_pipeline.text_encoder,
                tokenizer=self.txt2img_pipeline.tokenizer,
                unet=self.txt2img_pipeline.unet,
                scheduler=self.txt2img_pipeline.scheduler,
                safety_checker=None,
                feature_extractor=None,
                requires_safety_checker=False
            ).to(self.device)
            
            self.clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            self.clip_processor = CLIPImageProcessor.from_pretrained("openai/clip-vit-base-patch32")
            
            if self.device == "cuda":
                self.txt2img_pipeline.enable_xformers_memory_efficient_attention()
                self.img2img_pipeline.enable_xformers_memory_efficient_attention()
            
            self.models_loaded = True
            logger.info("Image models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise
    
    async def generate(self, 
                      prompt: str,
                      negative_prompt: str = "",
                      width: int = 512,
                      height: int = 512,
                      steps: int = 25,
                      guidance_scale: float = 7.5,
                      seed: Optional[int] = None) -> bytes:
        """Generate image from text prompt"""
        
        if not self.models_loaded:
            await self.initialize()
        
        try:
            generator = None
            if seed is not None:
                generator = torch.Generator(device=self.device).manual_seed(seed)
            
            image = self.txt2img_pipeline(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                generator=generator
            ).images[0]
            
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return img_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    async def transform(self,
                       image_data: bytes,
                       prompt: str,
                       strength: float = 0.75,
                       guidance_scale: float = 7.5) -> bytes:
        """Transform existing image with prompt"""
        
        if not self.models_loaded:
            await self.initialize()
        
        try:
            init_image = Image.open(io.BytesIO(image_data)).convert("RGB")
            init_image = init_image.resize((512, 512))
            
            image = self.img2img_pipeline(
                prompt=prompt,
                image=init_image,
                strength=strength,
                guidance_scale=guidance_scale
            ).images[0]
            
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return img_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Transform failed: {e}")
            raise
    
    async def analyze(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze image content"""
        
        if not self.models_loaded:
            await self.initialize()
        
        try:
            image = Image.open(io.BytesIO(image_data)).convert("RGB")
            
            inputs = self.clip_processor(images=image, return_tensors="pt")
            image_features = self.clip_model.get_image_features(**inputs)
            
            np_image = np.array(image)
            cv_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
            
            edges = cv2.Canny(cv_image, 100, 200)
            num_edges = np.count_nonzero(edges)
            
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            contrast = gray.std()
            
            hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
            saturation = hsv[:, :, 1].mean()
            
            dominant_colors = self._get_dominant_colors(np_image)
            
            return {
                "dimensions": {"width": image.width, "height": image.height},
                "format": image.format,
                "mode": image.mode,
                "complexity": {
                    "edges": int(num_edges),
                    "contrast": float(contrast),
                    "saturation": float(saturation)
                },
                "dominant_colors": dominant_colors,
                "feature_vector": image_features[0].detach().numpy().tolist()[:10]
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
    
    def _get_dominant_colors(self, image: np.ndarray, n_colors: int = 5) -> List[str]:
        """Extract dominant colors from image"""
        
        pixels = image.reshape(-1, 3)
        
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        colors = kmeans.cluster_centers_.astype(int)
        
        hex_colors = ['#%02x%02x%02x' % tuple(color) for color in colors]
        
        return hex_colors
    
    async def upscale(self, image_data: bytes, scale: int = 2) -> bytes:
        """Upscale image using AI"""
        
        try:
            image = Image.open(io.BytesIO(image_data))
            
            new_width = image.width * scale
            new_height = image.height * scale
            
            upscaled = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            np_image = np.array(upscaled)
            np_image = cv2.bilateralFilter(np_image, 9, 75, 75)
            upscaled = Image.fromarray(np_image)
            
            img_buffer = io.BytesIO()
            upscaled.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            return img_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Upscaling failed: {e}")
            raise

generator = ImageGenerator()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await generator.initialize()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "models_loaded": generator.models_loaded,
        "device": generator.device
    }

@app.post("/generate")
async def generate_image(request: Dict[str, Any]):
    """Generate image from text"""
    
    try:
        prompt = request.get("prompt", "")
        if not prompt:
            raise ValueError("No prompt provided")
        
        image_data = await generator.generate(
            prompt=prompt,
            negative_prompt=request.get("negative_prompt", ""),
            width=request.get("width", 512),
            height=request.get("height", 512),
            steps=request.get("steps", 25),
            guidance_scale=request.get("guidance_scale", 7.5),
            seed=request.get("seed")
        )
        
        return StreamingResponse(
            io.BytesIO(image_data),
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=generated.png"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transform")
async def transform_image(
    file: UploadFile = File(...),
    prompt: str = "",
    strength: float = 0.75
):
    """Transform existing image"""
    
    try:
        image_data = await file.read()
        
        result = await generator.transform(
            image_data=image_data,
            prompt=prompt,
            strength=strength
        )
        
        return StreamingResponse(
            io.BytesIO(result),
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=transformed.png"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """Analyze image content"""
    
    try:
        image_data = await file.read()
        result = await generator.analyze(image_data)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upscale")
async def upscale_image(
    file: UploadFile = File(...),
    scale: int = 2
):
    """Upscale image"""
    
    try:
        image_data = await file.read()
        result = await generator.upscale(image_data, scale)
        
        return StreamingResponse(
            io.BytesIO(result),
            media_type="image/png",
            headers={"Content-Disposition": "attachment; filename=upscaled.png"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process")
async def process_image(request: Dict[str, Any]):
    """Process image request"""
    
    try:
        task_type = request.get("type", "generate")
        
        if task_type == "generate":
            image_data = await generator.generate(
                prompt=request.get("prompt", ""),
                negative_prompt=request.get("negative_prompt", "")
            )
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            return {"type": "generation", "image": image_b64}
        
        elif task_type == "analyze":
            image_b64 = request.get("image", "")
            image_data = base64.b64decode(image_b64)
            result = await generator.analyze(image_data)
            return {"type": "analysis", "result": result}
        
        else:
            raise ValueError(f"Unknown task type: {task_type}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/preload")
async def preload_models(request: Dict[str, Any]):
    """Preload specific models"""
    
    models = request.get("models", [])
    
    if not generator.models_loaded:
        await generator.initialize()
    
    return {"status": "models_loaded", "models": models}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)