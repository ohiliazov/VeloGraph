import json

from backend.scripts.base.base_downloader import BaseDownloader
from backend.scripts.constants import artifacts_dir


class KrossDownloader(BaseDownloader):
    brand_name = "kross"

    def get_slug_from_url(self) -> str:
        return self.input_url.rstrip("/").split("/")[-1]


if __name__ == "__main__":
    with open(artifacts_dir / "kross" / "bike_urls.json") as f:
        bike_urls = json.load(f)

    output_dir = artifacts_dir / "kross" / "raw_htmls"

    for url in bike_urls:
        downloader = KrossDownloader(url, output_dir, overwrite=False)
        downloader.run()
