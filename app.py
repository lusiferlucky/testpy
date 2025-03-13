import json
import psutil
import os
from flask import Flask, render_template, jsonify
from datetime import datetime
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from helpers import (
    setup_logging, launch_browser, clear_cookies_and_storage, 
    click_consent_button, check_consent_cookie, check_script_load, 
    monitor_ajax_requests, log_message
)
from constants import TARGET_URL, JSALOAD_URL, JSACONFIG_URL

app = Flask(__name__)

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)  # Convert bytes to MB

def get_file_size(filename):
    return os.path.getsize(filename) / (1024 * 1024) if os.path.exists(filename) else 0

def visit_and_check_consent():
    """Main function to visit a URL, check for consent, and log AJAX requests."""
    log_file = setup_logging(TARGET_URL)
    log_message(log_file, f"\n========================================")
    log_message(log_file, f"📌 [TEST STARTED] Visiting: {TARGET_URL}")
    log_message(log_file, f"========================================")

    memory_before = get_memory_usage()
    result = {"metadata": {"target_url": TARGET_URL, "timestamp": datetime.utcnow().isoformat()}, "requests": {"JSALOAD": [], "JSACONFIG": []}}

    try:
        browser, context, page = launch_browser()
        clear_cookies_and_storage(context, page, TARGET_URL, log_file)
        log_message(log_file, f"🌍 Navigating to {TARGET_URL}...")

        jsa_config_ajax_response = monitor_ajax_requests(page, log_file, JSACONFIG_URL)
        jsa_load_ajax_response = monitor_ajax_requests(page, log_file, JSALOAD_URL)
        page.goto(TARGET_URL)
        page.wait_for_timeout(5000)

        consent_clicked = click_consent_button(page, log_file)
        page.wait_for_timeout(5000)
        script_loaded = check_script_load(page, log_file)

        if script_loaded:
            check_consent_cookie(context, log_file)

        result["requests"]["JSALOAD"].extend(jsa_load_ajax_response)
        result["requests"]["JSACONFIG"].extend(jsa_config_ajax_response)
        result["page_info"] = {"consent_clicked": consent_clicked, "script_loaded": script_loaded}

    except Exception as e:
        log_message(log_file, f"❌ Error encountered: {e}", level="error")
        result["error"] = str(e)
    
    finally:
        if 'browser' in locals():
            browser.close()
        with open("consent_test_results.json", "w") as json_file:
            json.dump(result, json_file, indent=4)

        memory_after = get_memory_usage()
        file_size = get_file_size("consent_test_results.json")
        log_message(log_file, f"💾 Storage used: {file_size:.2f} MB")
        log_message(log_file, f"🔍 Memory usage: {memory_after - memory_before:.2f} MB")
        log_message(log_file, "========================================")
        log_message(log_file, "✅ [TEST COMPLETED]")
        log_message(log_file, "========================================")

    return result


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run-test', methods=['GET'])
def run_test():
    result = visit_and_check_consent()
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
