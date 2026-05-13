"""
Mini Photoshop — Web App
Backend: FastAPI
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from routers import image as image_router

app = FastAPI(title="Mini Photoshop")

# Static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

# Routers
app.include_router(image_router.router, prefix="/api")


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")
