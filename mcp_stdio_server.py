#!/usr/bin/env python3
"""
MCP Server for SearXNG - Stdio Mode
For use with MCP clients via JSON block configuration (no Docker required)

This server communicates via stdin/stdout using JSON-RPC protocol.
It can be configured in MCP clients like Claude Desktop with a simple JSON block.
"""

import asyncio
import json
import logging
import os
import sys
from typing import Dict, Any, Callable, Awaitable
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Ensure UTF-8 stdio on Windows (prevents Korean mojibake)
if sys.platform == "win32":
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Import the plugin system
from plugin_manager import PluginManager

# Setup logging to stderr (stdout is reserved for JSON-RPC)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


class MCPStdioServer:
    """MCP Server that communicates via stdin/stdout for JSON block configuration."""

    def __init__(self):
        self.plugin_manager = PluginManager(plugins_dir="plugins")
        logger.info("MCP Stdio Server initialized")
        logger.info(f"Loaded {len(self.plugin_manager.plugins)} plugins")

    async def send_json_rpc(self, data: Dict[str, Any]):
        """Send JSON-RPC message to stdout."""
        message_str = json.dumps(data)
        sys.stdout.write(f"{message_str}\n")
        sys.stdout.flush()

    async def send_notification(self, method: str, params: Any):
        """Send notification to client."""
        await self.send_json_rpc({"jsonrpc": "2.0", "method": method, "params": params})

    async def handle_initialize(self, request_id: Any) -> Dict[str, Any]:
        """Handle initialize request."""
        tools_list = self.plugin_manager.list_plugins()

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "searxng-mcp-enhanced", "version": "2.0.0"},
                "capabilities": {"tools": {}},
            },
        }

    async def handle_tools_list(self, request_id: Any) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = self.plugin_manager.list_plugins()

        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}

    async def handle_tools_call(
        self, request_id: Any, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        logger.info(f"Calling tool: {tool_name} with args: {arguments}")

        try:
            # Execute the plugin
            result = await self.plugin_manager.execute_plugin(tool_name, arguments)

            # Format result as text content
            result_text = json.dumps(result, indent=2, ensure_ascii=False)

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": result_text}],
                    "isError": False,
                },
            }

        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                    "isError": True,
                },
            }

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming JSON-RPC request."""
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        logger.info(f"Received method: {method} (ID: {request_id})")

        if method == "initialize":
            return await self.handle_initialize(request_id)

        elif method == "notifications/initialized":
            # No response needed for notifications
            return None

        elif method == "tools/list":
            return await self.handle_tools_list(request_id)

        elif method == "tools/call":
            return await self.handle_tools_call(request_id, params)

        elif method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}

        else:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

    async def run(self):
        """Main server loop - read from stdin, process, write to stdout."""
        logger.info("MCP Stdio Server starting main loop...")
        logger.info("Reading from stdin, writing to stdout")

        while True:
            try:
                # Read line from stdin
                line = sys.stdin.readline()

                if not line:
                    logger.info("EOF received, exiting")
                    break

                # Parse JSON request
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parse error: {e}")
                    error_response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": "Parse error"},
                        "id": None,
                    }
                    await self.send_json_rpc(error_response)
                    continue

                # Handle request
                response = await self.handle_request(request)

                # Send response (only if not a notification)
                if response is not None:
                    await self.send_json_rpc(response)

            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                error_response = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                    "id": None,
                }
                await self.send_json_rpc(error_response)

        logger.info("MCP Stdio Server exiting")


async def main():
    """Main entry point."""
    server = MCPStdioServer()

    try:
        await server.run()
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, exiting")
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
