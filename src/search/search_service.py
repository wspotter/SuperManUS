#!/usr/bin/env python3
"""
Search Service for SuperManUS
Handles web searching, scraping, and information retrieval
"""

import asyncio
import logging
import os
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import aiohttp
from fastapi import FastAPI, HTTPException
import uvicorn
from duckduckgo_search import DDGS
from googlesearch import search as google_search
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urlparse, urljoin
import hashlib

app = FastAPI(title="SuperManUS Search Service")
logger = logging.getLogger(__name__)

class SearchEngine:
    """Multi-source web search and information extraction"""
    
    def __init__(self):
        self.ddgs = DDGS()
        self.session = None
        self.cache = {}
        self.cache_ttl = 3600
        self.selenium_driver = None
        self.initialized = False
        
    async def initialize(self):
        """Initialize search service"""
        try:
            logger.info("Initializing search service")
            
            self.session = aiohttp.ClientSession(
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            
            try:
                self.selenium_driver = webdriver.Chrome(options=chrome_options)
                logger.info("Selenium driver initialized")
            except:
                logger.warning("Selenium not available - JavaScript rendering disabled")
            
            self.initialized = True
            logger.info("Search service initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            raise
    
    async def search(self, 
                    query: str,
                    num_results: int = 10,
                    engine: str = "duckduckgo") -> List[Dict[str, Any]]:
        """Search the web using specified engine"""
        
        if not self.initialized:
            await self.initialize()
        
        cache_key = self._get_cache_key(query, engine, num_results)
        
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            if datetime.now() - cached['timestamp'] < timedelta(seconds=self.cache_ttl):
                logger.info(f"Returning cached results for: {query}")
                return cached['results']
        
        try:
            if engine == "duckduckgo":
                results = await self._search_duckduckgo(query, num_results)
            elif engine == "google":
                results = await self._search_google(query, num_results)
            elif engine == "combined":
                ddg_results = await self._search_duckduckgo(query, num_results // 2)
                google_results = await self._search_google(query, num_results // 2)
                results = self._merge_results(ddg_results, google_results)
            else:
                raise ValueError(f"Unknown search engine: {engine}")
            
            self.cache[cache_key] = {
                'results': results,
                'timestamp': datetime.now()
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    async def _search_duckduckgo(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Search using DuckDuckGo"""
        
        try:
            results = []
            
            for r in self.ddgs.text(query, max_results=num_results):
                results.append({
                    'title': r.get('title', ''),
                    'url': r.get('link', ''),
                    'snippet': r.get('body', ''),
                    'source': 'duckduckgo'
                })
            
            return results
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []
    
    async def _search_google(self, query: str, num_results: int) -> List[Dict[str, Any]]:
        """Search using Google"""
        
        try:
            results = []
            
            for url in google_search(query, num_results=num_results, stop=num_results):
                title, snippet = await self._fetch_meta(url)
                results.append({
                    'title': title,
                    'url': url,
                    'snippet': snippet,
                    'source': 'google'
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return []
    
    async def scrape(self, url: str, extract_type: str = "all") -> Dict[str, Any]:
        """Scrape content from URL"""
        
        if not self.initialized:
            await self.initialize()
        
        try:
            if self._needs_javascript(url) and self.selenium_driver:
                content = await self._scrape_with_selenium(url)
            else:
                content = await self._scrape_with_requests(url)
            
            soup = BeautifulSoup(content, 'html.parser')
            
            extracted = {}
            
            if extract_type in ["all", "text"]:
                extracted["text"] = self._extract_text(soup)
            
            if extract_type in ["all", "links"]:
                extracted["links"] = self._extract_links(soup, url)
            
            if extract_type in ["all", "images"]:
                extracted["images"] = self._extract_images(soup, url)
            
            if extract_type in ["all", "meta"]:
                extracted["meta"] = self._extract_meta(soup)
            
            if extract_type in ["all", "structured"]:
                extracted["structured"] = self._extract_structured_data(soup)
            
            extracted["url"] = url
            extracted["timestamp"] = datetime.now().isoformat()
            
            return extracted
            
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {e}")
            raise
    
    async def extract_article(self, url: str) -> Dict[str, Any]:
        """Extract article content from URL"""
        
        try:
            content = await self.scrape(url, "all")
            
            soup = BeautifulSoup(content.get("text", ""), 'html.parser')
            
            article = soup.find('article') or soup.find('main') or soup.find('div', class_=re.compile('content|article|post'))
            
            if article:
                article_text = article.get_text(strip=True, separator='\n')
            else:
                article_text = content.get("text", "")
            
            title = content.get("meta", {}).get("title", "")
            
            author = self._extract_author(soup)
            date = self._extract_date(soup)
            
            paragraphs = [p.strip() for p in article_text.split('\n\n') if p.strip()]
            
            summary = self._generate_summary(paragraphs)
            
            return {
                "title": title,
                "author": author,
                "date": date,
                "content": article_text,
                "paragraphs": paragraphs,
                "summary": summary,
                "url": url,
                "word_count": len(article_text.split())
            }
            
        except Exception as e:
            logger.error(f"Article extraction failed: {e}")
            raise
    
    async def monitor(self, url: str, interval: int = 300) -> Dict[str, Any]:
        """Monitor a URL for changes"""
        
        try:
            current = await self.scrape(url, "text")
            current_hash = hashlib.md5(current["text"].encode()).hexdigest()
            
            cache_key = f"monitor_{url}"
            
            if cache_key in self.cache:
                previous_hash = self.cache[cache_key]["hash"]
                previous_time = self.cache[cache_key]["timestamp"]
                
                if current_hash != previous_hash:
                    changes = {
                        "changed": True,
                        "url": url,
                        "previous_check": previous_time,
                        "current_check": datetime.now().isoformat(),
                        "content_hash": current_hash
                    }
                else:
                    changes = {
                        "changed": False,
                        "url": url,
                        "last_change": previous_time,
                        "current_check": datetime.now().isoformat()
                    }
            else:
                changes = {
                    "changed": None,
                    "url": url,
                    "first_check": datetime.now().isoformat(),
                    "content_hash": current_hash
                }
            
            self.cache[cache_key] = {
                "hash": current_hash,
                "timestamp": datetime.now().isoformat()
            }
            
            return changes
            
        except Exception as e:
            logger.error(f"Monitoring failed: {e}")
            raise
    
    async def _scrape_with_requests(self, url: str) -> str:
        """Scrape using aiohttp"""
        
        async with self.session.get(url, timeout=30) as response:
            return await response.text()
    
    async def _scrape_with_selenium(self, url: str) -> str:
        """Scrape using Selenium for JavaScript-heavy sites"""
        
        try:
            self.selenium_driver.get(url)
            
            WebDriverWait(self.selenium_driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            await asyncio.sleep(2)
            
            return self.selenium_driver.page_source
            
        except Exception as e:
            logger.warning(f"Selenium scraping failed, falling back: {e}")
            return await self._scrape_with_requests(url)
    
    def _needs_javascript(self, url: str) -> bool:
        """Check if URL likely needs JavaScript rendering"""
        
        js_sites = ['twitter.com', 'x.com', 'instagram.com', 'facebook.com', 'linkedin.com']
        domain = urlparse(url).netloc.lower()
        
        return any(site in domain for site in js_sites)
    
    async def _fetch_meta(self, url: str) -> Tuple[str, str]:
        """Fetch title and description from URL"""
        
        try:
            async with self.session.get(url, timeout=10) as response:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                title = soup.find('title')
                title = title.text if title else url
                
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                snippet = meta_desc.get('content', '') if meta_desc else ''
                
                return title, snippet
                
        except:
            return url, ""
    
    def _extract_text(self, soup: BeautifulSoup) -> str:
        """Extract readable text from HTML"""
        
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        text = soup.get_text(strip=True, separator=' ')
        
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract all links from HTML"""
        
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            
            links.append({
                'text': link.get_text(strip=True),
                'url': absolute_url,
                'relative': href
            })
        
        return links
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract all images from HTML"""
        
        images = []
        
        for img in soup.find_all('img'):
            src = img.get('src', '')
            if src:
                absolute_url = urljoin(base_url, src)
                images.append({
                    'src': absolute_url,
                    'alt': img.get('alt', ''),
                    'title': img.get('title', '')
                })
        
        return images
    
    def _extract_meta(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract meta information"""
        
        meta = {}
        
        title = soup.find('title')
        if title:
            meta['title'] = title.text.strip()
        
        for tag in soup.find_all('meta'):
            if tag.get('name'):
                meta[tag['name']] = tag.get('content', '')
            elif tag.get('property'):
                meta[tag['property']] = tag.get('content', '')
        
        return meta
    
    def _extract_structured_data(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract structured data (JSON-LD, microdata)"""
        
        structured = []
        
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                structured.append(data)
            except:
                pass
        
        return structured
    
    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract article author"""
        
        author_tags = [
            ('meta', {'name': 'author'}),
            ('meta', {'property': 'article:author'}),
            ('span', {'class': re.compile('author|byline')}),
            ('div', {'class': re.compile('author|byline')})
        ]
        
        for tag, attrs in author_tags:
            element = soup.find(tag, attrs)
            if element:
                if tag == 'meta':
                    return element.get('content', '')
                else:
                    return element.get_text(strip=True)
        
        return ""
    
    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract article date"""
        
        date_tags = [
            ('meta', {'property': 'article:published_time'}),
            ('time', {}),
            ('span', {'class': re.compile('date|time')})
        ]
        
        for tag, attrs in date_tags:
            element = soup.find(tag, attrs)
            if element:
                if tag == 'meta':
                    return element.get('content', '')
                elif tag == 'time':
                    return element.get('datetime', element.get_text(strip=True))
                else:
                    return element.get_text(strip=True)
        
        return ""
    
    def _generate_summary(self, paragraphs: List[str]) -> str:
        """Generate simple summary from paragraphs"""
        
        if not paragraphs:
            return ""
        
        summary_sentences = []
        word_count = 0
        max_words = 150
        
        for para in paragraphs[:3]:
            sentences = para.split('. ')
            for sentence in sentences:
                if word_count + len(sentence.split()) <= max_words:
                    summary_sentences.append(sentence)
                    word_count += len(sentence.split())
                else:
                    break
            if word_count >= max_words:
                break
        
        return '. '.join(summary_sentences) + '.'
    
    def _merge_results(self, results1: List[Dict], results2: List[Dict]) -> List[Dict]:
        """Merge and deduplicate search results"""
        
        seen_urls = set()
        merged = []
        
        for result in results1 + results2:
            if result['url'] not in seen_urls:
                seen_urls.add(result['url'])
                merged.append(result)
        
        return merged
    
    def _get_cache_key(self, *args) -> str:
        """Generate cache key from arguments"""
        
        key_str = '_'.join(str(arg) for arg in args)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def cleanup(self):
        """Cleanup resources"""
        
        if self.session:
            await self.session.close()
        
        if self.selenium_driver:
            self.selenium_driver.quit()

engine = SearchEngine()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await engine.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await engine.cleanup()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "initialized": engine.initialized,
        "cache_size": len(engine.cache)
    }

@app.post("/search")
async def search_web(request: Dict[str, Any]):
    """Search the web"""
    
    try:
        results = await engine.search(
            query=request.get("query", ""),
            num_results=request.get("num_results", 10),
            engine=request.get("engine", "duckduckgo")
        )
        return {"results": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scrape")
async def scrape_url(request: Dict[str, Any]):
    """Scrape content from URL"""
    
    try:
        result = await engine.scrape(
            url=request.get("url", ""),
            extract_type=request.get("extract_type", "all")
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract")
async def extract_article(request: Dict[str, Any]):
    """Extract article content"""
    
    try:
        result = await engine.extract_article(
            url=request.get("url", "")
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/monitor")
async def monitor_url(request: Dict[str, Any]):
    """Monitor URL for changes"""
    
    try:
        result = await engine.monitor(
            url=request.get("url", ""),
            interval=request.get("interval", 300)
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query")
async def process_query(request: Dict[str, Any]):
    """Process search query"""
    
    try:
        query = request.get("query", "")
        task_type = request.get("type", "search")
        
        if task_type == "search":
            results = await engine.search(query)
            return {"type": "search_results", "results": results}
        
        elif task_type == "research":
            search_results = await engine.search(query, num_results=5)
            
            articles = []
            for result in search_results[:3]:
                try:
                    article = await engine.extract_article(result['url'])
                    articles.append(article)
                except:
                    pass
            
            return {
                "type": "research",
                "search_results": search_results,
                "articles": articles
            }
        
        else:
            raise ValueError(f"Unknown task type: {task_type}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process")
async def process_request(request: Dict[str, Any]):
    """Process search request"""
    
    return await process_query(request)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)