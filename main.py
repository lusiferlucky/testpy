from fastapi import FastAPI
from playwright.async_api import async_playwright

app = FastAPI()

@app.get("/title")
async def get_title(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        title = await page.title()
        await browser.close()
        return {"title": title}
