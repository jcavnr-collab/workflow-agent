"""
screenshot_board.py

Uses Playwright to log into Miro and take a full screenshot of the workflow
board, saving it as .tmp/workflow.png.

Works on any Miro plan — no export API or Enterprise required.

Usage:
    python tools/screenshot_board.py

Output:
    .tmp/workflow.png

Requirements in .env:
    MIRO_EMAIL     - Your Miro account email
    MIRO_PASSWORD  - Your Miro account password
    (board URL is read from .tmp/board_info.json)

Notes:
    - First run installs Chromium (~120MB, one-time).
    - Board must finish loading before the screenshot is taken.
      Increase LOAD_WAIT_MS if the board is complex and still rendering.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

load_dotenv()

LOAD_WAIT_MS = 8000   # ms to wait for board content to render after load
OUTPUT_PATH = Path(".tmp/workflow.png")


def screenshot_board(board_url: str, email: str, password: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            device_scale_factor=2,
        )
        page = context.new_page()

        # Step 1: Go to login page
        print("  Navigating to Miro login...")
        page.goto("https://miro.com/login/", wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

        # Step 2: Fill email and password (both on same page)
        print("  Filling credentials...")
        page.locator('input[name="email"]').wait_for(state="visible", timeout=10000)
        page.locator('input[name="email"]').fill(email)
        page.locator('input[name="password"]').fill(password)

        # Step 3: Submit login form
        print("  Submitting login...")
        page.locator('button[type="submit"]').first.click()

        # Step 4: Wait until we're past the login pages (dashboard or app)
        print("  Waiting for login to complete...")
        page.wait_for_url(lambda url: "miro.com/app" in url or "miro.com/dashboard" in url or "miro.com/welcome" in url, timeout=20000)
        page.wait_for_timeout(2000)
        print(f"  Logged in. Current URL: {page.url}")

        # Step 5: Navigate to the board
        print("  Loading board...")
        page.goto(board_url, wait_until="domcontentloaded", timeout=30000)

        # Step 6: Wait for the board canvas element to appear
        print(f"  Waiting {LOAD_WAIT_MS}ms for board to fully render...")
        try:
            page.wait_for_selector('canvas, [data-testid="canvas"], [class*="canvas"]', timeout=15000)
        except PlaywrightTimeout:
            pass  # Proceed anyway and hope content is loaded
        page.wait_for_timeout(LOAD_WAIT_MS)

        # Step 7: Fit content to screen
        print("  Fitting content to view...")
        # Click the empty top-left corner (outside the diagram) to get focus
        # without accidentally selecting a shape/connector
        page.mouse.click(60, 200)
        page.wait_for_timeout(400)
        page.keyboard.press("Escape")   # deselect anything
        page.wait_for_timeout(300)
        page.keyboard.press("Control+Shift+h")
        page.wait_for_timeout(1000)

        # Step 8: Hide UI chrome for cleaner output
        page.evaluate("""() => {
            const hide = [
                '[class*="toolbar"]', '[class*="panel__header"]',
                '[class*="collaboration"]', '[class*="presence"]',
                '[class*="sidebar"]', '[class*="bottomBar"]',
                '[class*="actionBar"]', '[class*="topBar"]',
                '[class*="watermark"]', '[class*="teamName"]',
            ];
            hide.forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.style.display = 'none');
            });
        }""")
        page.wait_for_timeout(500)

        # Step 9: Screenshot
        OUTPUT_PATH.parent.mkdir(exist_ok=True)
        raw_path = str(OUTPUT_PATH).replace(".png", "_raw.png")
        page.screenshot(path=raw_path, full_page=False)

        browser.close()

        # Step 10: Crop to content using Pillow (removes empty grey canvas)
        _crop_to_content(raw_path, str(OUTPUT_PATH))
        print(f"  Screenshot saved to {OUTPUT_PATH}")
        return str(OUTPUT_PATH)


def _crop_to_content(src: str, dst: str, padding: int = 60):
    """
    Crop to the diagram area by finding coloured pixels that stand out from
    the Miro canvas grey (#ececec) and sidebar chrome.
    Excludes a fixed strip on the left (sidebar) and top (toolbar).
    """
    try:
        import numpy as np
        from PIL import Image

        img = Image.open(src).convert("RGB")
        w, h = img.size

        # Strip fixed UI chrome (sidebar ~40px left, toolbar ~50px top, at 1x;
        # device_scale_factor=2 means these are doubled in pixels)
        sidebar_px = 80   # 40px toolbar at 2x
        toolbar_px = 100  # 50px toolbar at 2x
        bottom_px  = 100  # bottom bar

        canvas = img.crop((sidebar_px, toolbar_px, w, h - bottom_px))
        arr = np.array(canvas)

        # Miro canvas background is ~#ececec = (236,236,236)
        # Look for pixels that are NOT close to this grey
        grey = np.array([236, 236, 236])
        diff = np.abs(arr.astype(int) - grey).max(axis=2)
        mask = diff > 25  # pixels that differ from background by >25 on any channel

        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)

        if rows.any() and cols.any():
            rmin, rmax = np.where(rows)[0][[0, -1]]
            cmin, cmax = np.where(cols)[0][[0, -1]]
            rmin = max(0, rmin - padding)
            rmax = min(arr.shape[0], rmax + padding)
            cmin = max(0, cmin - padding)
            cmax = min(arr.shape[1], cmax + padding)
            canvas = canvas.crop((cmin, rmin, cmax, rmax))

        canvas.save(dst)
        import os
        os.remove(src)
        print(f"  Cropped to {canvas.size[0]}x{canvas.size[1]}px")
    except ImportError:
        import shutil
        shutil.move(src, dst)


def main():
    board_info = json.loads(Path(".tmp/board_info.json").read_text())
    board_url = board_info["board_url"]
    email = os.environ["MIRO_EMAIL"]
    password = os.environ["MIRO_PASSWORD"]

    print(f"Screenshotting board: {board_url}")
    path = screenshot_board(board_url, email, password)

    # Update export_info.json so deliver_workflow.py picks up the PNG
    export_info_path = Path(".tmp/export_info.json")
    if export_info_path.exists():
        export_info = json.loads(export_info_path.read_text())
    else:
        export_info = {"board_url": board_url, "board_id": board_info["board_id"]}

    export_info["png_path"] = path
    export_info["export_available"] = True
    export_info_path.write_text(json.dumps(export_info, indent=2))

    size_kb = Path(path).stat().st_size // 1024
    print(f"Done. PNG is {size_kb}KB at {path}")
    return path


if __name__ == "__main__":
    main()
