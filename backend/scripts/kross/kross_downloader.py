from pathlib import Path

from backend.scripts.base import BaseBikeDataDownloader
from backend.scripts.constants import artifacts_dir

START_URL = "https://kross.pl/rowery"


class KrossBikeDownloader(BaseBikeDataDownloader):
    def __init__(self, html_path: Path | None = None):
        brand_name = "kross"
        html_path = html_path or (artifacts_dir / brand_name / "raw_htmls")
        super().__init__(brand_name=brand_name, html_dir=html_path)

    def get_slug_from_url(self, url: str) -> str:
        return url.rstrip("/").split("/")[-1]
