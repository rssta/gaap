from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from datetime import datetime
from zoneinfo import ZoneInfo

# Initialize FastMCP server
mcp = FastMCP("time")


@mcp.tool()
async def get_current_time(timezone_name: str, format_str_for_time: str) -> str:
    """
    """
    return datetime.now(tz=ZoneInfo(timezone_name)).strftime(format_str_for_time)


@mcp.tool()
async def convert_time(source_tz: str, time_str: str, format_str_for_time: str, target_tz: str) -> str:
    """
    """
    real_time = datetime.strptime(time_str, format_str_for_time)
    first_time = real_time.replace(tzinfo=ZoneInfo(source_tz))
    return first_time.astimezone(ZoneInfo(target_tz)).strftime(format_str_for_time)


def main():
    # Initialize and run the server
    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()


