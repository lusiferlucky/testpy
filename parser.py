from playwright.sync_api import sync_playwright

def get_title(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            title = page.title()
            browser.close()
        return title
    except Exception as e:
        return f"Error: {str(e)}"
