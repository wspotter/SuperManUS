/**
 * MCP (Model Context Protocol) Server for SuperManUS
 * Handles LLM communication and context management
 */

const express = require('express');
const WebSocket = require('ws');
const { createServer } = require('http');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
const server = createServer(app);
const wss = new WebSocket.Server({ server });

const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// Context store
class ContextManager {
  constructor() {
    this.contexts = new Map();
    this.activeConnections = new Map();
  }

  createContext(sessionId) {
    const context = {
      id: sessionId,
      messages: [],
      metadata: {},
      createdAt: new Date(),
      lastActivity: new Date()
    };
    this.contexts.set(sessionId, context);
    return context;
  }

  getContext(sessionId) {
    return this.contexts.get(sessionId);
  }

  updateContext(sessionId, message) {
    const context = this.contexts.get(sessionId);
    if (context) {
      context.messages.push(message);
      context.lastActivity = new Date();
      
      // Trim context if too large
      if (context.messages.length > 100) {
        context.messages = context.messages.slice(-50);
      }
    }
    return context;
  }

  clearContext(sessionId) {
    this.contexts.delete(sessionId);
  }
}

const contextManager = new ContextManager();

// REST API Routes
app.get('/health', (req, res) => {
  res.json({ 
    status: 'healthy',
    uptime: process.uptime(),
    connections: wss.clients.size
  });
});

app.post('/context/create', (req, res) => {
  const { sessionId } = req.body;
  const context = contextManager.createContext(sessionId);
  res.json({ success: true, context });
});

app.get('/context/:sessionId', (req, res) => {
  const context = contextManager.getContext(req.params.sessionId);
  if (context) {
    res.json({ success: true, context });
  } else {
    res.status(404).json({ success: false, error: 'Context not found' });
  }
});

app.post('/context/:sessionId/message', (req, res) => {
  const { message } = req.body;
  const context = contextManager.updateContext(req.params.sessionId, message);
  
  if (context) {
    // Broadcast to WebSocket clients
    broadcastToSession(req.params.sessionId, {
      type: 'context_update',
      context
    });
    
    res.json({ success: true, context });
  } else {
    res.status(404).json({ success: false, error: 'Context not found' });
  }
});

app.delete('/context/:sessionId', (req, res) => {
  contextManager.clearContext(req.params.sessionId);
  res.json({ success: true });
});

// MCP Protocol Implementation
app.post('/mcp/request', async (req, res) => {
  const { method, params, sessionId } = req.body;
  
  try {
    let result;
    
    switch (method) {
      case 'initialize':
        result = handleInitialize(params, sessionId);
        break;
        
      case 'complete':
        result = await handleComplete(params, sessionId);
        break;
        
      case 'tools/list':
        result = handleToolsList();
        break;
        
      case 'tools/call':
        result = await handleToolCall(params, sessionId);
        break;
        
      case 'resources/list':
        result = handleResourcesList();
        break;
        
      case 'resources/read':
        result = await handleResourceRead(params);
        break;
        
      default:
        throw new Error(`Unknown method: ${method}`);
    }
    
    res.json({ success: true, result });
    
  } catch (error) {
    res.status(400).json({ 
      success: false, 
      error: error.message 
    });
  }
});

// MCP Method Handlers
function handleInitialize(params, sessionId) {
  const context = contextManager.createContext(sessionId);
  
  return {
    protocolVersion: '1.0',
    serverInfo: {
      name: 'SuperManUS MCP Server',
      version: '0.1.0'
    },
    capabilities: {
      tools: true,
      resources: true,
      prompts: true,
      logging: true
    }
  };
}

async function handleComplete(params, sessionId) {
  const context = contextManager.getContext(sessionId);
  
  if (!context) {
    throw new Error('Context not found');
  }
  
  // Simulate completion (would integrate with actual LLM here)
  const completion = {
    text: `Completed: ${params.prompt}`,
    tokens: 10,
    finishReason: 'stop'
  };
  
  contextManager.updateContext(sessionId, {
    role: 'assistant',
    content: completion.text
  });
  
  return completion;
}

function handleToolsList() {
  return {
    tools: [
      {
        name: 'execute_code',
        description: 'Execute code in a sandboxed environment',
        parameters: {
          type: 'object',
          properties: {
            language: { type: 'string' },
            code: { type: 'string' }
          }
        }
      },
      {
        name: 'search_web',
        description: 'Search the web for information',
        parameters: {
          type: 'object',
          properties: {
            query: { type: 'string' }
          }
        }
      },
      {
        name: 'generate_image',
        description: 'Generate an image from text',
        parameters: {
          type: 'object',
          properties: {
            prompt: { type: 'string' }
          }
        }
      }
    ]
  };
}

async function handleToolCall(params, sessionId) {
  const { tool, arguments: args } = params;
  
  // Route to appropriate service
  let result;
  
  switch (tool) {
    case 'execute_code':
      result = await callCodeService(args);
      break;
      
    case 'search_web':
      result = await callSearchService(args);
      break;
      
    case 'generate_image':
      result = await callImageService(args);
      break;
      
    default:
      throw new Error(`Unknown tool: ${tool}`);
  }
  
  return result;
}

function handleResourcesList() {
  return {
    resources: [
      {
        uri: 'memory://context',
        name: 'Current Context',
        mimeType: 'application/json'
      },
      {
        uri: 'memory://sessions',
        name: 'Active Sessions',
        mimeType: 'application/json'
      }
    ]
  };
}

async function handleResourceRead(params) {
  const { uri } = params;
  
  if (uri === 'memory://context') {
    return {
      content: Array.from(contextManager.contexts.values())
    };
  } else if (uri === 'memory://sessions') {
    return {
      content: Array.from(contextManager.contexts.keys())
    };
  }
  
  throw new Error(`Unknown resource: ${uri}`);
}

// Service integration helpers
async function callCodeService(args) {
  // Would call actual code service
  return { output: 'Code executed successfully' };
}

async function callSearchService(args) {
  // Would call actual search service
  return { results: ['Result 1', 'Result 2'] };
}

async function callImageService(args) {
  // Would call actual image service
  return { url: 'http://example.com/image.png' };
}

// WebSocket handling
wss.on('connection', (ws, req) => {
  const sessionId = new URL(req.url, `http://${req.headers.host}`).searchParams.get('session');
  
  if (sessionId) {
    contextManager.activeConnections.set(sessionId, ws);
    
    ws.on('message', (message) => {
      try {
        const data = JSON.parse(message);
        handleWebSocketMessage(sessionId, data, ws);
      } catch (error) {
        ws.send(JSON.stringify({ 
          type: 'error', 
          error: error.message 
        }));
      }
    });
    
    ws.on('close', () => {
      contextManager.activeConnections.delete(sessionId);
    });
    
    ws.send(JSON.stringify({ 
      type: 'connected',
      sessionId 
    }));
  }
});

function handleWebSocketMessage(sessionId, data, ws) {
  const { type, payload } = data;
  
  switch (type) {
    case 'context_update':
      contextManager.updateContext(sessionId, payload);
      broadcastToSession(sessionId, {
        type: 'context_updated',
        context: contextManager.getContext(sessionId)
      });
      break;
      
    case 'ping':
      ws.send(JSON.stringify({ type: 'pong' }));
      break;
      
    default:
      ws.send(JSON.stringify({ 
        type: 'error',
        error: `Unknown message type: ${type}`
      }));
  }
}

function broadcastToSession(sessionId, message) {
  const ws = contextManager.activeConnections.get(sessionId);
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify(message));
  }
}

// Start server
server.listen(PORT, () => {
  console.log(`MCP Server running on port ${PORT}`);
});