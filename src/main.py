import logging
import asyncio
from psycopg_pool import AsyncConnectionPool
from fastapi import FastAPI
from starlette.responses import JSONResponse
from router.webhook import router as webhook_router
from config import settings
from agent.workflow.graph.graph import get_compiled_swarm_with_checkpointer

# Configure global logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager

# Global DB Pool (Psycopg AsyncConnectionPool)
db_pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles application startup and shutdown.
    Initializes the PostgreSQL connection pool and Thread Weaver checkpointer.
    """
    global db_pool
    logger.info("Initializing PostgreSQL Connection Pool (Psycopg) for Thread Weaver...")
    try:
        # Neon/Cloud Postgres Fix: Enable global autocommit for the pool
        # This prevents psycopg from wrapping the checkpointer's 'CREATE INDEX CONCURRENTLY' in a transaction.
        db_pool = AsyncConnectionPool(
            conninfo=str(settings.DATABASE_URL), 
            open=False,
            kwargs={"autocommit": True} 
        )
        await db_pool.open()
        
        # Initialize checkpointer and setup tables
        await get_compiled_swarm_with_checkpointer(db_pool)
        logger.info("PostgreSQL Checkpointer initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize PostgreSQL pool: %s", e)
        logger.warning("System will fall back to stateless execution for now.")
    
    yield  # --- Application is running ---
    
    if db_pool:
        logger.info("Closing PostgreSQL Connection Pool...")
        await db_pool.close()

app = FastAPI(
    title="Swarm Receiver API", 
    description="FastAPI webhook receiver with Thread Weaver Persistence",
    lifespan=lifespan
)

# Register Routers
app.include_router(webhook_router)

@app.get("/")
async def root():
    return JSONResponse(status_code=200, content={"status": "Swarm Receiver Active", "persistance": "enabled" if db_pool else "disabled"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
