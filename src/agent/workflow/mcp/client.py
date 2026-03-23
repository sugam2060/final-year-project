from langchain_mcp_adapters.client import MultiServerMCPClient
from config import settings

async def get_github_mcp_tools():
    """
    Connects to the GitHub Copilot MCP server and retrieves dynamic tools 
    using the correct HTTP stateless transport.
    """
    # Initialize the MultiServer client with the HTTP transport configuration
    client = MultiServerMCPClient({
        "github": {
            "transport": "http",  # Matches your JSON config and fixes the 405!
            "url": "https://api.githubcopilot.com/mcp/",
            "headers": {
                "Authorization": f"Bearer {str(settings.GITHUB_TOKEN)}",
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        }
    })
    
    # LangChain handles the correct POST handshake and tool translation automatically
    # This avoids the manual sse_client management and handles discrete JSON-RPC messages.
    mcp_tools = await client.get_tools()
    return mcp_tools
