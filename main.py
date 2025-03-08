import sys
import asyncio
from fastapi import FastAPI
from playwright.async_api import async_playwright

# ✅ FIX: Use correct event loop on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI()

@app.get("/")
async def home():
    return {"message": "Playwright API is running on Fly.io!"}

@app.get("/title")
async def get_title(url: str):
    try:
        print(f"Visiting URL: {url}")  # ✅ Print the URL for debugging

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=60000)

            title = await page.title()  # ✅ Get the page title
            await browser.close()

        return {"message": "Page title fetched successfully!", "title": title}
    except Exception as e:
        import traceback
        error_message = traceback.format_exc()
        print(error_message)
        return {"error": error_message}
