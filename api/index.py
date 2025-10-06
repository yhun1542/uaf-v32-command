"""
UAF V32 Command Hub - Vercel Serverless Entry Point
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v32.command.routes import router as command_router
from v32.connectors.routes import router as connector_router

app = FastAPI(title="UAF V32 Command Hub", version="32.0.1")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(command_router, prefix="/v32/command", tags=["Command Hub"])
app.include_router(connector_router, prefix="/v32/connectors", tags=["Data Connectors"])

# Health check
@app.get("/health")
def health(): 
    return {"status": "ok", "version": "32.0.1", "component": "UAF V32 Core"}

# Serve static files
@app.get("/")
async def read_root():
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "static")
    index_file = os.path.join(static_dir, "index.html")
    return FileResponse(index_file)

@app.get("/{path:path}")
async def serve_static(path: str):
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "src", "static")
    file_path = os.path.join(static_dir, path)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Fallback to index.html for SPA routing
    index_file = os.path.join(static_dir, "index.html")
    return FileResponse(index_file)

# Vercel serverless handler
handler = app
