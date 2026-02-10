from loguru import logger

from backend.scripts.base import BaseBikeCrawler
from backend.scripts.constants import artifacts_dir


class KrossBikeCrawler(BaseBikeCrawler):
    brand_name = "kross"

    def collect_page_urls(self, page) -> set[str]:
        urls: set[str] = set()
        product_buttons = page.query_selector_all("div.products a.action.secondary")
        for btn in product_buttons:
            if href := btn.get_attribute("href"):
                urls.add(href)
        return urls

    def get_next_page_url(self, page) -> str | None:
        next_btn = page.query_selector("a.action.next")
        if next_btn and (next_href := next_btn.get_attribute("href")):
            logger.debug("➡️ Navigating to next catalog page: {}", next_href)
            return next_href
        return None


if __name__ == "__main__":
    BIKE_START_URLS = {
        "https://kross.pl/rowery/rowery-szosowe": "road",
        "https://kross.pl/rowery/rowery-gravel": "gravel",
        "https://kross.pl/rowery/rowery-gorskie": "mtb",
        "https://kross.pl/rowery/rowery-turystyczne": "touring",
        "https://kross.pl/rowery/rowery-miejskie": "city",
        "https://kross.pl/rowery/rowery-damskie": "women",
        "https://kross.pl/rowery/rowery-dla-dzieci": "kids",
    }
    for start_url, _category in BIKE_START_URLS.items():
        crawler = KrossBikeCrawler(start_url, artifacts_dir / "kross" / "bike_urls.json")
        crawler.run()
