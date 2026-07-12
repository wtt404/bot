from playwright.async_api import async_playwright

_playwright = None
_browser = None
_context = None


async def start_browser():
    global _playwright, _browser, _context

    _playwright = await async_playwright().start()

    _browser = await _playwright.chromium.launch(
        headless=True
    )

    _context = await _browser.new_context(
        viewport={"width": 1920, "height": 1080}
    )


async def stop_browser():
    global _playwright, _browser, _context

    if _context:
        await _context.close()

    if _browser:
        await _browser.close()

    if _playwright:
        await _playwright.stop()


async def new_page():
    return await _context.new_page()