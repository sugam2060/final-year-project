import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_mcp_adapters.tools import load_mcp_tools
from config import settings

async def get_github_mcp_tools():
    """
    Connects to the GitHub Copilot MCP server and retrieves dynamic tools.
    """
    # Header injection (Constraint 3: Secret management)
    headers = {
        "Authorization": f"Bearer {str(settings.GITHUB_TOKEN)}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Connect to the remote MCP server via SSE
    async with sse_client(
        url="https://api.githubcopilot.com/mcp/",
        headers=headers
    ) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            
            # Use the LangChain adapter to discover and convert tools
            # Note: In a production long-running app, we would manage the session lifecyle more carefully.
            mcp_tools = await load_mcp_tools(session)
            return mcp_tools
