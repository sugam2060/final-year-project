from langchain_openai import ChatOpenAI
from agent.workflow.mcp.client import get_github_mcp_tools

async def get_tool_bound_llm():
    """
    Initializes a ChatOpenAI model bound with dynamic GitHub tools from MCP.
    """
    # Initialize base LLM (Constraint 2: Explicit timeouts)
    llm = ChatOpenAI(
        model="gpt-4o", 
        temperature=0,
        timeout=30 # Mandatory timeout for LLM
    )
    
    # Retrieve tools from the remote MCP server
    mcp_tools = await get_github_mcp_tools()
    
    # Bind tools for tool-calling capabilities
    return llm.bind_tools(mcp_tools)
