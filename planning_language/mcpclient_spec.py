
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
TAINTS_PKL = "taints.pkl"
DB_ADD_PKL = "database_additions.pkl"

import logging

# Silence the internal MCP SDK logger
logging.getLogger("mcp").setLevel(logging.WARNING)

# If you are using standard logging for your own code, configure it like this:
logging.basicConfig(level=logging.WARNING)



# taken from MCP specification
class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.server_name = None

    async def connect_to_server(self, server_name: str, path: str):
        """Connect to an MCP server
        
        Args:
            path: Path to the server script (.py or .js)
        """
        self.server_name = server_name
        # print("start connect")
        is_python = path.endswith('.py')
        # is_js = server_script_path.endswith('.js')
        # if not (is_python or is_js):
        #     raise ValueError("Server script must be a .py or .js file")
        #print(path)       
        env_config = {
            **os.environ,
            "PYTHONUNBUFFERED": "1",
            "LOG_LEVEL": "WARNING",       # Standard log level env for many servers
            "FASTMCP_LOG_LEVEL": "WARNING" # Specific override if using FastMCP
        }
        arriving_path = os.environ['ARRIVING_PATH']
        if is_python:
            command = "python3"

            silent_bootstrap = (
                "import logging, sys, os; "
                "logging.basicConfig(level=logging.WARNING, force=True); "
                "logging.getLogger('mcp').setLevel(logging.WARNING); "
                "exec(open(sys.argv[1]).read())"
            )

            server_params = StdioServerParameters(
                command=command,
                args=["-c", silent_bootstrap, arriving_path + path],
                env=env_config
            )
            #print("did it get here in the mcp client server setup")
        else:
             command = "npx"
             server_params = StdioServerParameters(
                command=command,
                args=["-y", "@modelcontextprotocol/server-filesystem", arriving_path + "editable_files/"],
                env=None
            )
       
        # 1. Setting errlog=None safely detaches the stream without breaking execution
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params, errlog=None)
        )
        
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

    async def process_query(self, tool: str, args: dict, current_id)-> str:

        with sqlite3.connect(QUERIES_DB) as conn:
            cursor = conn.cursor()
            insert_query = "INSERT INTO requests (query_id, request_server, request_tool, request_params) VALUES (?, ?, ?, ?)"
            #print("INSERTING REQUEST", tool, args)
            cursor.execute(insert_query, (current_id, self.server_name, tool, json.dumps(args),))
            #print("first exec")
            taints_query = "INSERT INTO disclosures (request_id, taint, principal_disclosed_to, time, params, arg_names) VALUES (?, ?, ?, ?, ?, ?)"
            get_last_request_id = "SELECT request_id FROM requests WHERE request_id = last_insert_rowid()"
            last_row_data = cursor.execute(get_last_request_id, ())
            last_request_id = last_row_data.fetchall()[0][0]
            #print("second exec")
            #principle_disclosed_to = f"{self.server_name}"
            #if "tool_ambiguous" not in tool_type:
            #    principle_disclosed_to += f":{tool}"
            #if "custom" in tool_type:
            #    principle_disclosed_to += f":custom:{extra_info}"

            #for single_taint in current_taints:
            #    all_args = ""
            #    if single_taint not in taint_arg_matches:
            #        all_args += f"preset:control_logic,"
            #    else:
            #        for one_arg in taint_arg_matches[single_taint]:
            #            all_args += f"{one_arg},"
            #    if len(all_args) > 0:
            #        if all_args[-1] == ",":
            #            all_args = all_args[:-1]
                #print("third exec", last_request_id, single_taint, principle_disclosed_to)
            #    cursor.execute(taints_query, (last_request_id, single_taint, principle_disclosed_to, time.time(), json.dumps(args), all_args,))

        with open("counting_metrics.pkl", "rb") as file:
            user_interactions, actual_user_interactions, mcp_calls = pickle.load(file)

        mcp_calls += 1

        with open("counting_metrics.pkl", "wb") as file:
            pickle.dump([user_interactions, actual_user_interactions, mcp_calls], file)


        result = await self.session.call_tool(tool, args)
        result = dict(result)

        return result
         
      
    async def cleanup(self):
        """Clean up resources"""
    
        await self.exit_stack.aclose()


