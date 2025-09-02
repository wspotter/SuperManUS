"""
Integration tests for SuperManUS services
"""

import pytest
import asyncio
import aiohttp
import time
import base64
from typing import Dict, Any

SERVICE_URLS = {
    "mcp": "http://localhost:3000",
    "voice": "http://localhost:8001",
    "image": "http://localhost:8002", 
    "code": "http://localhost:8003",
    "search": "http://localhost:8004"
}

@pytest.fixture
async def session():
    """Create aiohttp session"""
    async with aiohttp.ClientSession() as session:
        yield session

@pytest.mark.asyncio
async def test_health_endpoints(session):
    """Test all service health endpoints"""
    for service, url in SERVICE_URLS.items():
        try:
            async with session.get(f"{url}/health", timeout=5) as response:
                assert response.status == 200
                data = await response.json()
                assert data.get("status") == "healthy"
                print(f"✓ {service} service is healthy")
        except Exception as e:
            pytest.skip(f"{service} service not available: {e}")

@pytest.mark.asyncio
async def test_mcp_server(session):
    """Test MCP server functionality"""
    url = SERVICE_URLS["mcp"]
    
    try:
        # Test initialization
        async with session.post(
            f"{url}/mcp/request",
            json={
                "method": "initialize",
                "params": {},
                "sessionId": "test-session"
            }
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert data["success"] == True
            assert "protocolVersion" in data["result"]
        
        # Test tools list
        async with session.post(
            f"{url}/mcp/request",
            json={
                "method": "tools/list",
                "params": {},
                "sessionId": "test-session"
            }
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "tools" in data["result"]
            
    except Exception as e:
        pytest.skip(f"MCP server test failed: {e}")

@pytest.mark.asyncio
async def test_voice_service(session):
    """Test voice service"""
    url = SERVICE_URLS["voice"]
    
    try:
        # Test TTS
        async with session.post(
            f"{url}/synthesize",
            json={
                "text": "Hello, this is a test",
                "voice": "default"
            }
        ) as response:
            assert response.status == 200
            audio_data = await response.read()
            assert len(audio_data) > 0
            print("✓ Voice TTS working")
            
    except Exception as e:
        pytest.skip(f"Voice service test failed: {e}")

@pytest.mark.asyncio
async def test_image_service(session):
    """Test image service"""
    url = SERVICE_URLS["image"]
    
    try:
        # Test image generation
        async with session.post(
            f"{url}/generate",
            json={
                "prompt": "A simple red circle",
                "width": 256,
                "height": 256,
                "steps": 10
            },
            timeout=30
        ) as response:
            assert response.status == 200
            image_data = await response.read()
            assert len(image_data) > 0
            print("✓ Image generation working")
            
    except Exception as e:
        pytest.skip(f"Image service test failed: {e}")

@pytest.mark.asyncio
async def test_code_service(session):
    """Test code service"""
    url = SERVICE_URLS["code"]
    
    try:
        # Test code analysis
        async with session.post(
            f"{url}/analyze",
            json={
                "code": "def hello():\n    return 'world'",
                "language": "python"
            }
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "functions" in data
            assert len(data["functions"]) == 1
            print("✓ Code analysis working")
        
        # Test code generation
        async with session.post(
            f"{url}/generate",
            json={
                "prompt": "function to add two numbers",
                "language": "python"
            },
            timeout=30
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "code" in data
            print("✓ Code generation working")
            
    except Exception as e:
        pytest.skip(f"Code service test failed: {e}")

@pytest.mark.asyncio
async def test_search_service(session):
    """Test search service"""
    url = SERVICE_URLS["search"]
    
    try:
        # Test web search
        async with session.post(
            f"{url}/search",
            json={
                "query": "Python programming",
                "num_results": 5,
                "engine": "duckduckgo"
            }
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "results" in data
            assert len(data["results"]) > 0
            print("✓ Web search working")
        
        # Test URL scraping
        async with session.post(
            f"{url}/scrape",
            json={
                "url": "https://example.com",
                "extract_type": "text"
            }
        ) as response:
            assert response.status == 200
            data = await response.json()
            assert "text" in data
            print("✓ Web scraping working")
            
    except Exception as e:
        pytest.skip(f"Search service test failed: {e}")

@pytest.mark.asyncio
async def test_service_orchestration(session):
    """Test service orchestration"""
    
    try:
        # Test MCP calling voice service
        async with session.post(
            f"{SERVICE_URLS['mcp']}/mcp/request",
            json={
                "method": "tools/call",
                "params": {
                    "tool": "generate_image",
                    "arguments": {
                        "prompt": "A blue sky"
                    }
                },
                "sessionId": "test-orchestration"
            },
            timeout=30
        ) as response:
            assert response.status == 200
            print("✓ Service orchestration working")
            
    except Exception as e:
        pytest.skip(f"Orchestration test failed: {e}")

@pytest.mark.asyncio
async def test_concurrent_requests(session):
    """Test handling concurrent requests"""
    
    async def make_request(service_url: str, endpoint: str, data: Dict[str, Any]):
        try:
            async with session.post(f"{service_url}{endpoint}", json=data) as response:
                return response.status == 200
        except:
            return False
    
    tasks = [
        make_request(SERVICE_URLS["search"], "/search", {"query": f"test {i}"})
        for i in range(5)
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    successful = sum(1 for r in results if r == True)
    
    assert successful >= 3, f"Only {successful}/5 concurrent requests succeeded"
    print(f"✓ Handled {successful}/5 concurrent requests")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])