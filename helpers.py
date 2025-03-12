import os
import logging
import base64
import json
import time
from datetime import datetime
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
from constants import CONSENT_BUTTONS, CONSENT_COOKIE_NAME, EXPECTED_CONSENT_VALUE, TARGET_SCRIPT_PATTERN

def setup_logging(url):
    """Create log directory and setup logging for the test."""
    today_date = datetime.now().strftime("%Y-%m-%d")
    log_folder = f"logs/{today_date}"
    os.makedirs(log_folder, exist_ok=True)

    domain = urlparse(url).netloc.replace("www.", "")
    log_file = os.path.join(log_folder, f"{domain}.txt")

    logging.basicConfig(filename=log_file, level=logging.INFO, 
                      format="%(asctime)s - %(message)s", 
                      datefmt="%Y-%m-%d %H:%M:%S",
                      encoding="utf-8")
    
    return log_file

def log_message(log_file, message, level="info"):
    """Log messages to both console and file with different levels."""
    levels = {
        "info": logging.info,
        "warning": logging.warning,
        "error": logging.error,
        "critical": logging.critical
    }
    
    log_function = levels.get(level, logging.info)
    
    # Print to console
    print(message)
    
    # Write to log file
    log_function(message)
    
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

def launch_browser():
    """Launch Playwright browser and return context and page."""
    # browser = sync_playwright().start().chromium.launch(headless=true, slow_mo=100)
    browser = sync_playwright().start().chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    return browser, context, page

def clear_cookies_and_storage(context, page, url, log_file):
    """Clear cookies, local storage, and session storage."""
    log_message(log_file, "🧹 Clearing cookies and storage...")
    context.clear_cookies()
    page.goto(url)
    page.evaluate("localStorage.clear(); sessionStorage.clear();")

def click_consent_button(page, log_file):
    """Try to click consent button based on multiple selectors and expected texts."""
    for consent in CONSENT_BUTTONS:
        selector = consent["selector"]
        expected_text = consent["text"]
        
        buttons = page.locator(selector).all()
        for button in buttons:
            button_text = button.inner_text().strip()
            if expected_text.lower() in button_text.lower():
                log_message(log_file, f"✅ Found consent button [{selector}] with text '{button_text}', clicking...")
                button.click()
                page.wait_for_timeout(1000)  # Wait for effects
                return True

    log_message(log_file, "❌ No matching consent button found!", level="error")
    return False

def check_consent_cookie(context, log_file):
    """Check if the consent cookie exists and verify its value."""
    log_message(log_file, f"🔎 Checking for '{CONSENT_COOKIE_NAME}' cookie...")
    cookies = context.cookies()
    consent_cookie = next((c for c in cookies if c["name"] == CONSENT_COOKIE_NAME), None)

    if consent_cookie:
        log_message(log_file, f"✅ Found '{CONSENT_COOKIE_NAME}' cookie: {consent_cookie['value']}")
        try:
            decoded_value = base64.b64decode(consent_cookie['value']).decode('utf-8')
            log_message(log_file, f"🔍 Decoded Cookie Value: {decoded_value}")

            if EXPECTED_CONSENT_VALUE in decoded_value:
                log_message(log_file, "🎉 Consent stored successfully in the cookie!")
                return True
            else:
                log_message(log_file, "⚠️ Expected consent value not found in decoded cookie!", level="warning")
        except Exception as e:
            log_message(log_file, f"⚠️ Failed to decode cookie value: {e}", level="error")
    else:
        log_message(log_file, f"❌ '{CONSENT_COOKIE_NAME}' cookie not found!", level="warning")
    return False

def check_script_load(page, log_file):
    """Check if the target script is loaded on the page."""
    log_message(log_file, "⏳ Checking for script load...")
    scripts = page.locator("script").all()
    loaded_scripts = [script.get_attribute("src") for script in scripts if script.get_attribute("src")]

    log_message(log_file, f"📜 Loaded Scripts: {loaded_scripts}")

    for script in loaded_scripts:
        if TARGET_SCRIPT_PATTERN in script:
            log_message(log_file, f"✅ Target script found: {script}")
            return True

    log_message(log_file, "❌ Target script NOT found!", level="error")
    return False

def monitor_ajax_requests(page, log_file, target_url=None):
    """Monitor and log AJAX (XHR & Fetch) requests and responses."""
    log_message(log_file, f"📡 Monitoring AJAX requests for {target_url or 'ALL URLs'}...")
    ajax_data = []
    request_map = {}

    def handle_request(request):
        if request.resource_type in ["xhr", "fetch"]:
            if target_url and target_url not in request.url:
                return

            request_info = {
                "url": request.url,
                "method": request.method,
                "request_headers": dict(request.headers),
                "request_body": request.post_data if request.method == "POST" else None,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            }
            request_map[request.url] = request_info

            message = f"🔍 AJAX Request: {request.method} {request.url}"
            if request.method == "POST":
                message += f"\n📤 POST Data: {request.post_data or 'N/A'}"
            log_message(log_file, message)

    def handle_response(response):
        if response.request.resource_type in ["xhr", "fetch"]:
            if target_url and target_url not in response.url:
                return

            request_info = request_map.get(response.url, {
                "url": response.url,
                "method": response.request.method,
                "request_headers": dict(response.request.headers),
                "request_body": None,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            })

            try:
                response_body = response.text()
                response_info = {
                    **request_info,
                    "status": response.status,
                    "response_headers": dict(response.headers),
                    "response_body": response_body
                }
                ajax_data.append(response_info)

                message = (f"📥 AJAX Response: {response.url} "
                         f"(Status: {response.status})")
                try:
                    json.loads(response_body)
                    message += f"\n📥 Full JSON Response:\n{response_body}"
                except json.JSONDecodeError:
                    message += f"\n📥 Response Body (non-JSON):\n{response_body}"
                
                log_message(log_file, message)

            except Exception as e:
                log_message(log_file, f"⚠️ Error processing response: {e}", 
                          level="error")

            if response.url in request_map:
                del request_map[response.url]

    page.on("request", handle_request)
    page.on("response", handle_response)

    return ajax_data

def check_ajax_request_and_response(page, log_file, target_url, jsl_param, jsappid_param, apptype_param, expected_response):
    """Check AJAX request parameters and response content."""
    log_message(log_file, f"🔎 Checking for AJAX request to '{target_url}' with parameters...")
    request_found = False
    printed_request = False

    def check_request(route, request):
        nonlocal request_found, printed_request
        if target_url in request.url and request.method == "GET":
            params = urlparse(request.url).query
            if all(param in params for param in [jsl_param, jsappid_param, apptype_param]):
                log_message(log_file, f"✅ Found AJAX request with required parameters")
                if not printed_request:
                    log_message(log_file, f"Request URL: {request.url}")
                    printed_request = True
                request_found = True
            route.continue_()
        else:
            route.continue_()

    def check_response(response):
        nonlocal request_found
        if target_url in response.url and request_found:
            try:
                response_text = response.text()
                log_message(log_file, f"Response: {response_text}")
                if expected_response in response_text:
                    log_message(log_file, f"🎉 Response contains expected text: '{expected_response}'")
                    return True
            except Exception as e:
                log_message(log_file, f"⚠️ Error reading response: {e}", level="error")
        return False

    page.route("**/*", check_request)
    page.on("response", check_response)