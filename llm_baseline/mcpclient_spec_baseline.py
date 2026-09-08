
import asyncio
from typing import Optional
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import sqlite3
import json
import os
import pickle
import time

# constants
QUERIES_DB = "queries_4.db"


# taken from MCP specification
class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.server_name = None

    async def connect_to_server(self, server_name: str, server_script_path: str):
        """Connect to an MCP server
        
        Args:
            server_script_path: Path to the server script (.py or .js)
        """

        self.server_name = server_name
        # print("start connect")
        is_python = server_script_path.endswith('.py')
        # is_js = server_script_path.endswith('.js')
        # if not (is_python or is_js):
        #     raise ValueError("Server script must be a .py or .js file")
            
        arriving_path = os.environ['ARRIVING_PATH']
        if is_python:
            command = "python3"
            server_params = StdioServerParameters(
                command=command,
                args=[arriving_path + server_script_path],
                env=None
            )
        else:
             command = "npx"
             server_params = StdioServerParameters(
                command=command,
                args=["-y", "@modelcontextprotocol/server-filesystem", arriving_path + "editable_files/"],
                env=None
            )
        
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        
        await self.session.initialize()
        
        # List available tools
        #response = await self.session.list_tools()
        #tools = response.tools
        #print("\nConnected to server with tools:", [tool.name for tool in tools])
    
    async def list_available_tools(self):
        response = await self.session.list_tools()
        tools = response.tools
        return tools


    async def process_query(self, tool, args, current_id) -> str:
        
        with sqlite3.connect(QUERIES_DB) as conn:
            cursor = conn.cursor()
            insert_query = "INSERT INTO requests (query_id, request_server, request_tool, request_params) VALUES (?, ?, ?, ?)"
            cursor.execute(insert_query, (current_id, self.server_name, tool, json.dumps(args),))
        if type(args) != dict:
            args = {"val": args}
        result = await self.session.call_tool(tool, args)
        result = dict(result)
        
        with open("counting_metrics.pkl", "rb") as file:
            user_interactions, actual_user_interactions, mcp_calls = pickle.load(file)

        mcp_calls += 1

        with open("counting_metrics.pkl", "wb") as file:
            pickle.dump([user_interactions, actual_user_interactions, mcp_calls], file)

        with sqlite3.connect(QUERIES_DB) as conn:
            cursor = conn.cursor()
            new_id = cursor.lastrowid
            insert_query = "UPDATE requests SET request_result = ? WHERE request_id = ?"
            cursor.execute(insert_query, (str(result), new_id,))

        return result

    
    async def cleanup(self):
        """Clean up resources"""
    
        await self.exit_stack.aclose()

