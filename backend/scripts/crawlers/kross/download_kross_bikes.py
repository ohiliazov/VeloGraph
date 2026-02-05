import json
import time
import zipfile

from loguru import logger
from playwright.sync_api import sync_playwright

from backend.scripts.constants import artifacts_dir

kross_artifacts = artifacts_dir / "kross"
kross_bike_urls_path = kross_artifacts / "bike_urls.json"

if not kross_bike_urls_path.exists():
    kross_bike_urls = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Optionally block images/fonts to speed up
        page.route(
            "**/*",
            lambda r: r.abort() if r.request.resource_type in ["image", "font"] else r.continue_(),
        )

        # Start at main catalog page
        logger.info("🌐 Opening Kross catalog page: {}", "https://kross.pl/rowery")
        page.goto("https://kross.pl/rowery", wait_until="networkidle")

        while True:
            # --- Extract all bike URLs on this page ---
            product_buttons = page.query_selector_all("div.products a.action.secondary")
            for btn in product_buttons:
                if href := btn.get_attribute("href"):
                    kross_bike_urls.add(href)

            logger.info(
                "🔎 Found {} bikes on this page, total unique collected: {}",
                len(product_buttons),
                len(kross_bike_urls),
            )

            # --- Find next page button ---
            next_btn = page.query_selector("a.action.next")
            if next_btn:
                if next_href := next_btn.get_attribute("href"):
                    logger.debug("➡️ Navigating to next catalog page: {}", next_href)
                    page.goto(next_href, wait_until="networkidle")
                    time.sleep(1)  # wait for JS
            else:
                logger.info("🛑 No more catalog pages detected. Stopping pagination.")
                break

        browser.close()

    # Save all URLs
    with open(kross_bike_urls_path, "w", encoding="utf-8") as f:
        json.dump(list(kross_bike_urls), f, indent=2)

    logger.success("💾 Saved {} bike URLs to {}", len(kross_bike_urls), kross_bike_urls_path)
else:
    with open(kross_bike_urls_path, encoding="utf-8") as f:
        kross_bike_urls = set(json.load(f))
    logger.info("📥 Loaded {} bike URLs from {}", len(kross_bike_urls), kross_bike_urls_path)


# Folder to save HTML
kross_bike_archive_path = kross_artifacts / "raw_htmls.zip"

# Determine which HTMLs already exist in the archive
existing: set[str] = set()
if kross_bike_archive_path.exists():
    with zipfile.ZipFile(kross_bike_archive_path, "r") as zread:
        existing = set(zread.namelist())

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    # Optional: block images/fonts to speed up
    page.route(
        "**/*",
        lambda r: r.abort() if r.request.resource_type in ["image", "font"] else r.continue_(),
    )

    # Open the archive in append mode once and stream pages into it
    with zipfile.ZipFile(kross_bike_archive_path, "a", zipfile.ZIP_DEFLATED) as zwrite:
        for idx, url in enumerate(kross_bike_urls, start=1):
            slug = url.rstrip("/").split("/")[-1]
            name = f"{slug}.html"

            if name in existing:
                logger.debug("⏭️ [{:d}/{:d}] Skipping existing HTML for {}", idx, len(kross_bike_urls), url)
                continue

            logger.info("⬇️ [{:d}/{:d}] Fetching: {}", idx, len(kross_bike_urls), url)
            page.goto(url, wait_until="load")
            time.sleep(1)  # extra wait for JS

            # Save rendered HTML
            html = page.content()
            zwrite.writestr(name, html)
            logger.debug("💾 Saved HTML to archive {} (entry: {}, slug: {})", kross_bike_archive_path, name, slug)

    browser.close()
