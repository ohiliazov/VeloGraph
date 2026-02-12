import json

import httpx
from loguru import logger

from scripts.constants import artifacts_dir


class TrekAPICrawler:
    def __init__(self):
        self.client = httpx.Client(base_url="https://api.trekbikes.com/occ/v2/gb")
        self.trek_artifacts = artifacts_dir / "trek"
        self.output_path = self.trek_artifacts / "all_product_codes.json"
        self.output_json_dir = self.trek_artifacts / "raw_jsons"

        self.output_json_dir.mkdir(parents=True, exist_ok=True)

    def collect_product_codes(self, overwrite: bool = False) -> list[int]:
        logger.info(f"Collecting product codes ({overwrite=})...")
        if self.output_path.exists() and not overwrite:
            return json.loads(self.output_path.read_text())

        all_product_codes = set()

        current_page = 0
        while True:
            logger.info(f"Collecting product codes from page {current_page}...")
            print("Current page:", current_page)
            resp = self.client.get(
                "/products/search",
                params={"fields": "BASIC", "pageSize": 100, "currentPage": current_page},
            )

            if products := resp.json()["products"]:
                for product in products:
                    if product["productType"] == "BikeProduct":
                        all_product_codes.add(int(product["code"]))
            else:
                logger.info("No more pages found.")
                break

            logger.info(f"Total bikes found: {len(all_product_codes)}")
            current_page += 1

        all_product_codes = sorted(all_product_codes)

        self.output_path.write_text(json.dumps(all_product_codes, indent=2))

        return all_product_codes

    def collect_product_data(self, product_code: int, overwrite: bool = False) -> dict:
        json_path = self.output_json_dir / f"{product_code}.json"

        if json_path.exists() and not overwrite:
            logger.info(f"Data already exists for product code {product_code}. Skipping...")
            return json.loads(json_path.read_text())

        logger.info(f"Collecting data for product code {product_code}...")
        details = self.client.get(f"/products/{product_code}/full").json()
        sizing = self.client.get(f"/products/{product_code}/sizing").json()

        data = {"details": details, "sizing": sizing}
        json_path.write_text(json.dumps(data, indent=2))

        return data


if __name__ == "__main__":
    crawler = TrekAPICrawler()

    for product_code in crawler.collect_product_codes():
        crawler.collect_product_data(product_code)
