#!/usr/bin/env python3
"""
Code Service for SuperManUS
Handles code generation, analysis, and refactoring
"""

import asyncio
import logging
import os
import re
import ast
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import torch
from fastapi import FastAPI, HTTPException
import uvicorn
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    CodeLlamaTokenizer,
    pipeline
)
import tree_sitter
from tree_sitter_python import language as python_language
from tree_sitter_javascript import language as js_language
import black
import autopep8
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings

app = FastAPI(title="SuperManUS Code Service")
logger = logging.getLogger(__name__)

class CodeAnalyzer:
    """Analyzes, generates and refactors code"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        self.embeddings = None
        self.code_pipeline = None
        self.parser = None
        self.models_loaded = False
        self.language_parsers = {}
        
    async def initialize(self):
        """Load AI models and parsers"""
        try:
            logger.info(f"Loading code models on {self.device}")
            
            model_name = "codellama/CodeLlama-7b-Python-hf"
            self.tokenizer = CodeLlamaTokenizer.from_pretrained(model_name)
            
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto" if self.device == "cuda" else None,
                load_in_8bit=self.device == "cuda"
            )
            
            self.code_pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1,
                max_new_tokens=512,
                temperature=0.7,
                do_sample=True
            )
            
            self.embeddings = HuggingFaceEmbeddings(
                model_name="microsoft/codebert-base",
                model_kwargs={'device': self.device}
            )
            
            self.parser = tree_sitter.Parser()
            self.language_parsers['python'] = python_language()
            self.language_parsers['javascript'] = js_language()
            self.parser.set_language(self.language_parsers['python'])
            
            self.models_loaded = True
            logger.info("Code models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise
    
    async def generate(self, 
                      prompt: str,
                      language: str = "python",
                      max_length: int = 512,
                      temperature: float = 0.7) -> Dict[str, Any]:
        """Generate code from natural language prompt"""
        
        if not self.models_loaded:
            await self.initialize()
        
        try:
            formatted_prompt = self._format_prompt(prompt, language)
            
            result = self.code_pipeline(
                formatted_prompt,
                max_new_tokens=max_length,
                temperature=temperature,
                do_sample=True,
                top_p=0.95,
                repetition_penalty=1.2
            )
            
            generated_code = result[0]['generated_text']
            
            code = self._extract_code(generated_code, language)
            
            formatted_code = await self.format_code(code, language)
            
            analysis = await self.analyze(formatted_code, language)
            
            return {
                "code": formatted_code,
                "language": language,
                "analysis": analysis,
                "prompt": prompt
            }
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise
    
    async def analyze(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Analyze code structure and quality"""
        
        try:
            if language in self.language_parsers:
                self.parser.set_language(self.language_parsers[language])
                tree = self.parser.parse(bytes(code, "utf8"))
                
                functions = self._extract_functions(tree.root_node, code)
                classes = self._extract_classes(tree.root_node, code)
                imports = self._extract_imports(tree.root_node, code)
            else:
                functions = []
                classes = []
                imports = []
            
            metrics = self._calculate_metrics(code)
            
            issues = await self._find_issues(code, language)
            
            complexity = self._calculate_complexity(code, language)
            
            return {
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "metrics": metrics,
                "issues": issues,
                "complexity": complexity
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {
                "error": str(e),
                "functions": [],
                "classes": [],
                "imports": [],
                "metrics": {},
                "issues": [],
                "complexity": 0
            }
    
    async def refactor(self, code: str, language: str = "python", target: str = "improve") -> Dict[str, Any]:
        """Refactor code based on target criteria"""
        
        if not self.models_loaded:
            await self.initialize()
        
        try:
            analysis = await self.analyze(code, language)
            
            prompt = self._create_refactor_prompt(code, target, analysis)
            
            result = self.code_pipeline(
                prompt,
                max_new_tokens=len(code) * 2,
                temperature=0.3,
                do_sample=True
            )
            
            refactored_code = self._extract_code(result[0]['generated_text'], language)
            
            formatted_code = await self.format_code(refactored_code, language)
            
            new_analysis = await self.analyze(formatted_code, language)
            
            improvements = self._compare_analyses(analysis, new_analysis)
            
            return {
                "original": code,
                "refactored": formatted_code,
                "improvements": improvements,
                "target": target
            }
            
        except Exception as e:
            logger.error(f"Refactoring failed: {e}")
            raise
    
    async def format_code(self, code: str, language: str = "python") -> str:
        """Format code according to language standards"""
        
        try:
            if language == "python":
                try:
                    return black.format_str(code, mode=black.Mode())
                except:
                    return autopep8.fix_code(code)
            else:
                return code
                
        except Exception as e:
            logger.warning(f"Formatting failed: {e}")
            return code
    
    async def explain(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Generate explanation for code"""
        
        if not self.models_loaded:
            await self.initialize()
        
        try:
            prompt = f"""Explain this {language} code in simple terms:

```{language}
{code}
```

Explanation:"""
            
            result = self.code_pipeline(
                prompt,
                max_new_tokens=256,
                temperature=0.5,
                do_sample=True
            )
            
            explanation = result[0]['generated_text'].split("Explanation:")[-1].strip()
            
            analysis = await self.analyze(code, language)
            
            return {
                "explanation": explanation,
                "key_concepts": self._extract_concepts(code, language),
                "complexity": analysis.get("complexity", 0),
                "purpose": self._infer_purpose(code, analysis)
            }
            
        except Exception as e:
            logger.error(f"Explanation failed: {e}")
            raise
    
    def _format_prompt(self, prompt: str, language: str) -> str:
        """Format prompt for code generation"""
        
        return f"""Write {language} code for the following task:
{prompt}

```{language}"""
    
    def _extract_code(self, text: str, language: str) -> str:
        """Extract code from generated text"""
        
        code_blocks = re.findall(rf'```{language}?\n(.*?)```', text, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        
        lines = text.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            if line.strip().startswith('```'):
                in_code = not in_code
                continue
            if in_code or (line.startswith(' ') or line.startswith('\t')):
                code_lines.append(line)
        
        return '\n'.join(code_lines).strip()
    
    def _extract_functions(self, node, source: str) -> List[Dict[str, Any]]:
        """Extract function definitions from AST"""
        
        functions = []
        
        def visit(node):
            if node.type == 'function_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    functions.append({
                        'name': source[name_node.start_byte:name_node.end_byte],
                        'start_line': node.start_point[0] + 1,
                        'end_line': node.end_point[0] + 1
                    })
            
            for child in node.children:
                visit(child)
        
        visit(node)
        return functions
    
    def _extract_classes(self, node, source: str) -> List[Dict[str, Any]]:
        """Extract class definitions from AST"""
        
        classes = []
        
        def visit(node):
            if node.type == 'class_definition':
                name_node = node.child_by_field_name('name')
                if name_node:
                    classes.append({
                        'name': source[name_node.start_byte:name_node.end_byte],
                        'start_line': node.start_point[0] + 1,
                        'end_line': node.end_point[0] + 1
                    })
            
            for child in node.children:
                visit(child)
        
        visit(node)
        return classes
    
    def _extract_imports(self, node, source: str) -> List[str]:
        """Extract import statements from AST"""
        
        imports = []
        
        def visit(node):
            if node.type in ['import_statement', 'import_from_statement']:
                imports.append(source[node.start_byte:node.end_byte])
            
            for child in node.children:
                visit(child)
        
        visit(node)
        return imports
    
    def _calculate_metrics(self, code: str) -> Dict[str, int]:
        """Calculate code metrics"""
        
        lines = code.split('\n')
        
        return {
            'lines': len(lines),
            'loc': len([l for l in lines if l.strip() and not l.strip().startswith('#')]),
            'comments': len([l for l in lines if l.strip().startswith('#')]),
            'blank_lines': len([l for l in lines if not l.strip()])
        }
    
    async def _find_issues(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Find potential issues in code"""
        
        issues = []
        
        if language == "python":
            try:
                compile(code, '<string>', 'exec')
            except SyntaxError as e:
                issues.append({
                    'type': 'syntax_error',
                    'line': e.lineno,
                    'message': str(e)
                })
        
        long_lines = []
        for i, line in enumerate(code.split('\n'), 1):
            if len(line) > 100:
                long_lines.append(i)
        
        if long_lines:
            issues.append({
                'type': 'style',
                'lines': long_lines,
                'message': 'Lines exceed 100 characters'
            })
        
        return issues
    
    def _calculate_complexity(self, code: str, language: str) -> int:
        """Calculate cyclomatic complexity"""
        
        if language != "python":
            return 0
        
        try:
            tree = ast.parse(code)
            complexity = 1
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.While, ast.For)):
                    complexity += 1
                elif isinstance(node, ast.ExceptHandler):
                    complexity += 1
            
            return complexity
            
        except:
            return 0
    
    def _create_refactor_prompt(self, code: str, target: str, analysis: Dict) -> str:
        """Create refactoring prompt"""
        
        issues = analysis.get('issues', [])
        
        prompt = f"""Refactor this code to {target}:

```python
{code}
```

Issues to address: {issues}

Refactored code:
```python"""
        
        return prompt
    
    def _compare_analyses(self, before: Dict, after: Dict) -> List[str]:
        """Compare analysis results"""
        
        improvements = []
        
        if after['metrics']['loc'] < before['metrics']['loc']:
            improvements.append(f"Reduced lines of code by {before['metrics']['loc'] - after['metrics']['loc']}")
        
        if after['complexity'] < before['complexity']:
            improvements.append(f"Reduced complexity from {before['complexity']} to {after['complexity']}")
        
        if len(after['issues']) < len(before['issues']):
            improvements.append(f"Fixed {len(before['issues']) - len(after['issues'])} issues")
        
        return improvements
    
    def _extract_concepts(self, code: str, language: str) -> List[str]:
        """Extract key programming concepts from code"""
        
        concepts = []
        
        patterns = {
            'loops': r'(for|while)\s+',
            'conditionals': r'if\s+',
            'functions': r'def\s+' if language == 'python' else r'function\s+',
            'classes': r'class\s+',
            'async': r'(async|await)\s+',
            'exceptions': r'(try|except|catch)\s+'
        }
        
        for concept, pattern in patterns.items():
            if re.search(pattern, code):
                concepts.append(concept)
        
        return concepts
    
    def _infer_purpose(self, code: str, analysis: Dict) -> str:
        """Infer the purpose of the code"""
        
        functions = analysis.get('functions', [])
        if functions:
            func_names = [f['name'] for f in functions]
            return f"Implements {', '.join(func_names[:3])}"
        
        return "General purpose code"

analyzer = CodeAnalyzer()

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    await analyzer.initialize()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "models_loaded": analyzer.models_loaded,
        "device": analyzer.device
    }

@app.post("/generate")
async def generate_code(request: Dict[str, Any]):
    """Generate code from prompt"""
    
    try:
        result = await analyzer.generate(
            prompt=request.get("prompt", ""),
            language=request.get("language", "python"),
            max_length=request.get("max_length", 512),
            temperature=request.get("temperature", 0.7)
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze")
async def analyze_code(request: Dict[str, Any]):
    """Analyze code structure"""
    
    try:
        result = await analyzer.analyze(
            code=request.get("code", ""),
            language=request.get("language", "python")
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/refactor")
async def refactor_code(request: Dict[str, Any]):
    """Refactor code"""
    
    try:
        result = await analyzer.refactor(
            code=request.get("code", ""),
            language=request.get("language", "python"),
            target=request.get("target", "improve")
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/explain")
async def explain_code(request: Dict[str, Any]):
    """Explain code"""
    
    try:
        result = await analyzer.explain(
            code=request.get("code", ""),
            language=request.get("language", "python")
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/format")
async def format_code(request: Dict[str, Any]):
    """Format code"""
    
    try:
        formatted = await analyzer.format_code(
            code=request.get("code", ""),
            language=request.get("language", "python")
        )
        return {"formatted": formatted}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process")
async def process_code(request: Dict[str, Any]):
    """Process code request"""
    
    try:
        task_type = request.get("type", "generate")
        
        if task_type == "generate":
            return await analyzer.generate(
                prompt=request.get("prompt", ""),
                language=request.get("language", "python")
            )
        elif task_type == "analyze":
            return await analyzer.analyze(
                code=request.get("code", ""),
                language=request.get("language", "python")
            )
        elif task_type == "refactor":
            return await analyzer.refactor(
                code=request.get("code", ""),
                language=request.get("language", "python")
            )
        else:
            raise ValueError(f"Unknown task type: {task_type}")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/preload")
async def preload_models(request: Dict[str, Any]):
    """Preload specific models"""
    
    if not analyzer.models_loaded:
        await analyzer.initialize()
    
    return {"status": "models_loaded"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)