from mcp.server.fastmcp import FastMCP

import sqlite3
import os

mcp = FastMCP("sqlite")

@mcp.tool()
async def execute_sql_command(db_path, query):
    """
    Execute a given sql command where db_path is the path from editable_files directory to the database and query is the query you want to execute as a string. Do not use sqlite path, instead create a path from editable_files to the database you want to access
    """
    with open("arriving_path_file.txt", "r") as file:
        arriving_path = file.read()
    db_path = arriving_path + db_path
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

if __name__ == "__main__":
    mcp.run(transport="stdio")
