from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import sys
import os
import asyncio

with open("arriving_path_file.txt", "r") as file:
    arriving_path = file.read()
sys.path.insert(1, arriving_path + 'agent_helpers')
import database


# Initialize FastMCP server
mcp = FastMCP("email")

# Constants

@mcp.tool()
async def send_email(address: str, content: str) -> bool:
    """
    Send an email to the address included with the content. 
    Account sign in must occur before this function will work.
    """

    return True

@mcp.tool()
def sign_in(email: str, password: str) -> bool:
    """
    Sign in to an email account before sending. 
    """

    if "thisisemail456" == password and "sam@ucla.edu" == email:
        
        database.insert_internal_data("signed-in", "email", "true")
        return True
    
    return False



def main():
    # Initialize and run the server
    #print( asyncio.run(send_email("lily", "hi")) )
    #database.insert_internal_data("signed-in", "email", "false")
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()
