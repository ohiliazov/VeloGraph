import json
from urllib.parse import unquote, urlparse

from loguru import logger
from playwright.sync_api import sync_playwright

from backend.scripts.base.base_downloader import BaseDownloader
from backend.scripts.constants import artifacts_dir

API_BASE = "https://api.trekbikes.com/occ/v2/pl/products/{pid}/sizing?lang=pl_PL&curr=PLN"
POLISH_TO_ASCII = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
        "Ą": "A",
        "Ć": "C",
        "Ę": "E",
        "Ł": "L",
        "Ń": "N",
        "Ó": "O",
        "Ś": "S",
        "Ź": "Z",
        "Ż": "Z",
    }
)


def polish_to_ascii(text: str) -> str:
    table = str.maketrans(POLISH_TO_ASCII)
    return unquote(text).translate(table)


class TrekDownloader(BaseDownloader):
    brand_name = "trek"

    def get_slug_from_url(self) -> str:
        parsed = urlparse(self.input_url)
        path = parsed.path.rstrip("/")
        return polish_to_ascii(path.split("/")[-3]) + "__" + path.split("/")[-1]

    def _download_sizing_json(self):
        slug = self.get_slug_from_url()
        json_path = self.output_dir / f"{self.get_slug_from_url()}_sizing.json"

        if json_path.exists() and not self.overwrite:
            logger.info("⏭️ Skipping existing file {}", json_path)
            return
        pid = slug.split("__")[1]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            target_url = API_BASE.format(pid=pid)
            logger.info("📥 Downloading sizing JSON: {}", target_url)
            resp = page.request.get(target_url, timeout=15000)
            if not resp.ok:
                logger.error("❌ Bad status {} for {}", resp.status, target_url)
                raise Exception(f"Bad status {resp.status} for {target_url}")
            self._save_file(json.dumps(resp.json(), ensure_ascii=False), json_path)
            logger.success("✅ Saved sizing JSON: {}", json_path.name)

    def run(self):
        super().run()
        self._download_sizing_json()


if __name__ == "__main__":
    with open(artifacts_dir / "trek" / "bike_urls.json") as f:
        bike_urls = json.load(f)

    output_dir = artifacts_dir / "trek" / "raw_htmls"

    for url in bike_urls:
        downloader = TrekDownloader(url, output_dir, overwrite=False)
        downloader.run()
