from config import settings
from langchain_openai import ChatOpenAI
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from agent.workflow.mcp.client import get_github_mcp_tools
import logging

logger = logging.getLogger(__name__)

async def get_tool_bound_llm():
    """
    Initializes the chosen Chat LLM (OpenAI or NVIDIA) 
    bound with dynamic GitHub tools from MCP.
    """
    # 1. Determine provider from configuration
    provider = settings.LLM_PROVIDER
    logger.info("Initializing LLM with provider: %s", provider)
    
    # 2. Initialize requested LLM
    if provider == "NVIDIA":
        # Using Llama 3.1 405B via NVIDIA AI Endpoints
        llm = ChatNVIDIA(
            model="meta/llama-3.1-405b-instruct",
            api_key=str(settings.NVIDIA_API_KEY),
            temperature=0,
            # Move timeout to model_kwargs to silence warnings
            model_kwargs={"timeout": 30}
        )
    else:
        # Default to GPT-4o
        llm = ChatOpenAI(
            model="gpt-4o", 
            temperature=0,
            api_key=str(settings.OPENAI_API_KEY),
            model_kwargs={"timeout": 30}
        )
    
    # 3. Retrieve tools from the remote MCP server
    # We use a safety wrapper to prevent library bugs (like UnboundLocalError) from crashing the swarm
    try:
        mcp_tools = await get_github_mcp_tools()
        # 4. Bind tools for tool-calling capabilities
        return llm.bind_tools(mcp_tools)
    except Exception as e:
        logger.error("Failed to load MCP tools: %s. Proceeding without external tool support.", e)
        return llm

