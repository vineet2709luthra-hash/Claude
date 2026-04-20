from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    print("Opening Higgsfield...")
    page.goto("https://higgsfield.ai", timeout=30000)
    print(f"Page title: {page.title()}")
    print(f"URL: {page.url}")
    page.screenshot(path="/home/user/Claude/higgsfield_screenshot.png")
    print("Screenshot saved to higgsfield_screenshot.png")
    browser.close()
