from fastapi import FastAPI
from starlette.responses import JSONResponse
from router.webhook import router as webhook_router

app = FastAPI(title="Swarm Receiver API", description="FastAPI webhook receiver for LangGraph multi-agent system")

# Register Routers
app.include_router(webhook_router)

@app.get("/")
async def root():
    return JSONResponse(status_code=200, content={"status": "Swarm Receiver Active"})

if __name__ == "__main__":
    import uvicorn
    # Use import string for reload support
    uvicorn.run("main:app", host="localhost", port=8000, reload=True)
