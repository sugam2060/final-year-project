import asyncio
import logging
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

from agent.workflow.mcp.client import get_github_mcp_tools

async def list_tools():
    try:
        tools = await get_github_mcp_tools()
        print(f"Total Tools: {len(tools)}")
        print("TOOL_LIST_START")
        for tool in tools:
            print(f"- {tool.name}")
        print("TOOL_LIST_END")
    except Exception as e:
        print(f"Error fetching tools: {e}")

if __name__ == "__main__":
    asyncio.run(list_tools())
