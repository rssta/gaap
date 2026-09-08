from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import sys
import os
import subprocess

arriving_path = os.environ['ARRIVING_PATH']
sys.path.insert(1, arriving_path + 'agent_helpers')
import database


# Initialize FastMCP server
mcp = FastMCP("terminal")

# Constants

@mcp.tool()
async def execute_terminal_command(full_command_and_args: str) -> tuple:
    """
    Execute an arbitrary terminal command.
    """
    segments = full_command_and_args.strip().split()
    output = subprocess.run(segments, capture_output=True)
    return (output.stdout, output.stderr)

def main():
    # Initialize and run the server
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
