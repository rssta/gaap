from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
import sys
import os
import asyncio
import subprocess
import pickle
import re
import codecs

with open("arriving_path_file.txt", "r") as file:
    arriving_path = file.read().strip()


# Initialize FastMCP server
mcp = FastMCP("python-exec")

# Constants


def unescape_match(match):
    """
    Takes an isolated escape sequence string (e.g., r'\t' or r'\x41')
    and returns its actual evaluated character.
    """
    return codecs.decode(match.group(0).encode('ascii'), 'unicode_escape')

@mcp.tool()
async def python_run(code, func_name, input_val):
    """
    Execute a block of self contained python code with arguments.
    """
    #code = code.encode('utf-8').decode('unicode_escape')
    # Regex pattern to match a backslash (not preceded by another backslash), 
    # followed by standard single characters, hex, unicode, or octal sequences.
    pattern = r'(?<!\\)\\(?:[ntrbfva\'"]|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|[0-7]{1,3})'
    
    # Process only the targeted escape sequences, leaving everything else untouched
    code = re.sub(pattern, unescape_match, code)
    with open(f"{arriving_path}python_output.pkl", "wb") as file:
            pickle.dump(None, file)

    # define file
    file_code = f'import pickle\n\n{code}\n\nwith open("{arriving_path}python_input.pkl", "rb") as file:\n    input_val = pickle.load(file)\n\noutput = {func_name}(input_val)\n\nwith open("{arriving_path}python_output.pkl", "wb") as file:\n    pickle.dump(output, file)'

    with open(f"{arriving_path}python_run.py", "w") as file:
        file.write(file_code)

    with open(f"{arriving_path}python_input.pkl", "wb") as file:
        pickle.dump(input_val, file)

    subprocess.run(["uv", "run", f"{arriving_path}python_run.py"])
    
    try:
        with open(f"{arriving_path}python_output.pkl", "rb") as file:
            output = pickle.load(file)
    except Exception as e:
        output = None
    return output


def main():
    # Initialize and run the server
    mcp.run(transport='stdio')
    #asyncio.run(python_run("def multiply(input_item: list):\n    return input_item[0]*input_item[1]", "multiply", [4,5]))

if __name__ == "__main__":
    main()
    
