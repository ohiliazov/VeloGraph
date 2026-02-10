from urllib.parse import urljoin, urlparse

from loguru import logger

from backend.scripts.base import BaseBikeCrawler
from backend.scripts.constants import artifacts_dir

START_URL = "https://www.trekbikes.com/pl/pl_PL/rowery/c/B100/?pageSize=72&q=%3Arelevance&sort=relevance#"
BASE_URL = "https://www.trekbikes.com"


class TrekBikeCrawler(BaseBikeCrawler):
    brand_name = "trek"

    def normalize_url(self, href: str) -> str:
        href = href.strip()
        if href.startswith(("http://", "https://")):
            return href
        return urljoin(BASE_URL, href)

    def get_slug_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        return path.split("/")[-3] + "__" + path.split("/")[-1]

    def collect_page_urls(self, page) -> set[str]:
        urls: set[str] = set()
        anchors = page.query_selector_all("ul li article div h3 a")
        for a in anchors:
            href = a.get_attribute("href")
            if not href:
                continue
            url = self.normalize_url(href)
            urls.add(url)
        return urls

    def get_next_page_url(self, page) -> str | None:
        next_a = page.query_selector("a#search-page-next")
        if next_a:
            next_href = next_a.get_attribute("href")
            if next_href:
                next_url = self.normalize_url(next_href)
                logger.debug("➡️ Navigating to next catalog page: {}", next_url)
                return next_url
        return None


if __name__ == "__main__":
    BASE_URL = "https://www.trekbikes.com/pl/pl_PL/rowery"
    BIKE_START_URLS = {
        f"{BASE_URL}/rowery-szosowe/rowery-szosowe-wyczynowe/c/B260/": "road",
        f"{BASE_URL}/rowery-szosowe/rowery-gravel/rowery-gravel-z-kierownicami-szosowymi/c/B562/": "gravel",
        f"{BASE_URL}/rowery-szosowe/rowery-gravel/rowery-all-road/c/B564/": "gravel",
        f"{BASE_URL}/rowery-szosowe/rowery-gravel/elektryczne-rowery-gravel/c/B561/": "gravel",
        f"{BASE_URL}/rowery-szosowe/rowery-prze%C5%82ajowe/c/B240/": "gravel",
        f"{BASE_URL}/rowery-szosowe/rowery-triathlonowe/c/B230/": "triathlon",
        f"{BASE_URL}/rowery-g%C3%B3rskie/c/B300/": "mtb",
        f"{BASE_URL}/rowery-hybrydowe/c/B528/": "city",
        f"{BASE_URL}/rowery-szosowe/damskie-rowery-szosowe/c/B522/": "women",
        f"{BASE_URL}/rowery-hybrydowe/damskie-rowery-miejskie/c/B521/": "women",
        f"{BASE_URL}/rowery-hybrydowe/damskie-rowery-crossowe/c/B526/": "women",
        f"{BASE_URL}/rowery-dla-dzieci/c/B506/": "kids",
        f"{BASE_URL}/rowery-elektryczne/c/B507/": "electric",
        f"{BASE_URL}/elektryczne-rowery-hybrydowe/c/B550/": "electric",
    }

    for start_url, _category in BIKE_START_URLS.items():
        crawler = TrekBikeCrawler(start_url, artifacts_dir / "trek" / "bike_urls.json")
        crawler.run()
