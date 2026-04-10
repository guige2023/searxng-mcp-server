# Example Configuration for Legacy HTTP MCP Clients

## Using npx to run the server

### Step 1: Start the server with npx

```bash
cd searxng-mcp-crawl
npx .
```

Or with environment variables:

```bash
SEARXNG_BASE_URL="http://localhost:32768" DESIRED_TIMEZONE="Asia/Seoul" npx .
```

The server will start at `http://localhost:32769` by default.

### Step 2: Configure your MCP client

For legacy HTTP MCP clients, use the following configuration:

#### Option 1: Server-Sent Events (SSE) - Recommended

```json
{
  "searxng-enhanced": {
    "url": "http://localhost:32769",
    "type": "http",
    "method": "sse"
  }
}
```

#### Option 2: Simple HTTP POST

```json
{
  "searxng-enhanced": {
    "url": "http://localhost:32769",
    "type": "http",
    "method": "post"
  }
}
```

#### Option 3: With custom port

If you want to use a different port:

```bash
PORT=8080 npx .
```

Then configure:

```json
{
  "searxng-enhanced": {
    "url": "http://localhost:8080",
    "type": "http",
    "method": "sse"
  }
}
```

## API Endpoints

The server provides the following HTTP endpoints:

### 1. POST / - Send MCP requests

Send JSON-RPC requests directly:

```bash
curl -X POST http://localhost:32769 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

### 2. GET / - SSE connection

Open a Server-Sent Events connection for streaming responses:

```bash
curl -N http://localhost:32769
```

The server will respond with:
```
event: endpoint
data: /message/{connection_id}
```

### 3. POST /message/{connection_id} - Send to SSE connection

Send messages to an existing SSE connection:

```bash
curl -X POST http://localhost:32769/message/{connection_id} \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "search_web",
    "params": {
      "name": "search_web",
      "arguments": {
        "query": "machine learning",
        "limit": 5
      }
    }
  }'
```

### 4. GET /health - Health check

Check if the server is running:

```bash
curl http://localhost:32769/health
```

Response:
```json
{
  "status": "ok",
  "plugins": 8,
  "available_tools": [
    "search_web",
    "get_website",
    "get_current_datetime",
    "search",
    "fetch_webpage",
    "runLLM",
    "executor",
    "tool_planner"
  ]
}
```

## Testing the Setup

1. **Start the server:**
   ```bash
   npx .
   ```

2. **In another terminal, test the health endpoint:**
   ```bash
   curl http://localhost:32769/health
   ```

3. **Test listing tools:**
   ```bash
   curl -X POST http://localhost:32769 \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
   ```

4. **Test calling a tool:**
   ```bash
   curl -X POST http://localhost:32769 \
     -H "Content-Type: application/json" \
     -d '{
       "jsonrpc": "2.0",
       "id": 2,
       "method": "tools/call",
       "params": {
         "name": "get_current_datetime",
         "arguments": {}
       }
     }'
   ```

## Troubleshooting

### Server won't start
- Check if Python is installed: `python3 --version`
- Check if SearXNG is running: `curl http://localhost:32768/search?q=test&format=json`
- Check if port 32769 is available: `lsof -i :32769` (Unix) or `netstat -an | findstr 32769` (Windows)

### Connection refused
- Make sure the server is running
- Check firewall settings
- Try using `127.0.0.1` instead of `localhost`

### Tools not working
- Check server logs for errors
- Verify SearXNG_BASE_URL is correct
- Test SearXNG directly to ensure it's working

## Environment Variables

All environment variables that can be used:

```bash
# SearXNG Configuration
SEARXNG_BASE_URL=http://localhost:32768

# Server Configuration
HOST=0.0.0.0          # Bind to all interfaces
PORT=32769            # Server port

# Content Settings
CONTENT_MAX_LENGTH=10000
SEARCH_RESULT_LIMIT=10

# Timezone
DESIRED_TIMEZONE=Asia/Seoul

# User Agent (optional)
USER_AGENT="Mozilla/5.0 ..."
```

Example with all variables:

```bash
SEARXNG_BASE_URL="http://localhost:32768" \
HOST="127.0.0.1" \
PORT="8080" \
DESIRED_TIMEZONE="Asia/Seoul" \
CONTENT_MAX_LENGTH="20000" \
npx .
```
