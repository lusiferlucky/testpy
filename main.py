import importlib.util
import subprocess
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def home():
    return {"message": "Hello from FastAPI!"}

@app.get("/check_playwright")
async def check_playwright():
    playwright_installed = importlib.util.find_spec("playwright") is not None
    if playwright_installed:
        version = subprocess.run(["playwright", "--version"], capture_output=True, text=True).stdout.strip()
        return {"playwright_installed": True, "version": version}
    return {"playwright_installed": False, "message": "Playwright is not installed"}


