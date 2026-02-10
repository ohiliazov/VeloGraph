import json

from elasticsearch import Elasticsearch
from loguru import logger
from sqlalchemy import delete

from backend.config import es_settings
from backend.core.db import SessionLocal
from backend.core.models import BikeFamilyORM
from backend.scripts import populate_es as es_pop
from backend.scripts.constants import artifacts_dir
from backend.scripts.kross.kross_crawler import KrossBikeCrawler
from backend.scripts.kross.kross_downloader import KrossDownloader
from backend.scripts.kross.kross_extractor import KrossBikeExtractor
from backend.scripts.kross.kross_populator import KrossBikePopulator
from backend.scripts.trek.trek_crawler import TrekBikeCrawler
from backend.scripts.trek.trek_downloader import TrekDownloader
from backend.scripts.trek.trek_extractor import TrekBikeExtractor
from backend.scripts.trek.trek_populator import TrekBikePopulator

# --- CONFIGURATION ---
# Set FORCE to True to force re-crawling, re-extracting, and re-creating ES indices.
FORCE_CRAWLER = False
FORCE_DOWNLOADER = False
FORCE_EXTRACTOR = True
FORCE_POPULATOR = True
# ---------------------


def crawl_all():
    logger.info("--- 1/4: CRAWLING ---")

    # Trek
    trek_html = artifacts_dir / "trek" / "raw_htmls"
    trek_urls_path = artifacts_dir / "trek" / "bike_urls.json"
    logger.info("🌐 Trek: collecting URLs (force={})", FORCE_CRAWLER)
    TREK_BASE_URL = "https://www.trekbikes.com/pl/pl_PL/rowery"
    TREK_START_URLS = {
        f"{TREK_BASE_URL}/rowery-szosowe/rowery-szosowe-wyczynowe/c/B260/": "road",
        f"{TREK_BASE_URL}/rowery-szosowe/rowery-gravel/rowery-gravel-z-kierownicami-szosowymi/c/B562/": "gravel",
        f"{TREK_BASE_URL}/rowery-szosowe/rowery-gravel/rowery-all-road/c/B564/": "gravel",
        f"{TREK_BASE_URL}/rowery-szosowe/rowery-gravel/elektryczne-rowery-gravel/c/B561/": "gravel",
        f"{TREK_BASE_URL}/rowery-szosowe/rowery-prze%C5%82ajowe/c/B240/": "gravel",
        f"{TREK_BASE_URL}/rowery-szosowe/rowery-triathlonowe/c/B230/": "triathlon",
        f"{TREK_BASE_URL}/rowery-g%C3%B3rskie/c/B300/": "mtb",
        f"{TREK_BASE_URL}/rowery-hybrydowe/c/B528/": "city",
        f"{TREK_BASE_URL}/rowery-szosowe/damskie-rowery-szosowe/c/B522/": "women",
        f"{TREK_BASE_URL}/rowery-hybrydowe/damskie-rowery-miejskie/c/B521/": "women",
        f"{TREK_BASE_URL}/rowery-hybrydowe/damskie-rowery-crossowe/c/B526/": "women",
        f"{TREK_BASE_URL}/rowery-dla-dzieci/c/B506/": "kids",
        f"{TREK_BASE_URL}/rowery-elektryczne/c/B507/": "electric",
        f"{TREK_BASE_URL}/elektryczne-rowery-hybrydowe/c/B550/": "electric",
    }

    all_trek_urls = set()
    if not trek_urls_path.exists() or FORCE_CRAWLER:
        for start_url in TREK_START_URLS:
            urls = TrekBikeCrawler(start_url=start_url, output_path=trek_urls_path).run()
            all_trek_urls.update(urls)
    else:
        with open(trek_urls_path, encoding="utf-8") as f:
            all_trek_urls = json.load(f)

    logger.info("🌐 Trek: downloading HTMLs (force={})", FORCE_DOWNLOADER)
    for url in sorted(all_trek_urls):
        TrekDownloader(input_url=url, output_dir=trek_html, overwrite=FORCE_DOWNLOADER).run()

    # Kross
    kross_html = artifacts_dir / "kross" / "raw_htmls"
    kross_urls_path = artifacts_dir / "kross" / "bike_urls.json"
    logger.info("🌐 Kross: collecting URLs (force={})", FORCE_CRAWLER)

    # Since Kross doesn't have a single START_URL but several, we use the ones from its __main__
    KROSS_START_URLS = [
        "https://kross.pl/rowery/rowery-szosowe",
        "https://kross.pl/rowery/rowery-gravel",
        "https://kross.pl/rowery/rowery-gorskie",
        "https://kross.pl/rowery/rowery-turystyczne",
        "https://kross.pl/rowery/rowery-miejskie",
        "https://kross.pl/rowery/rowery-damskie",
        "https://kross.pl/rowery/rowery-dla-dzieci",
    ]

    all_kross_urls = set()
    if not kross_urls_path.exists() or FORCE_CRAWLER:
        for start_url in KROSS_START_URLS:
            urls = KrossBikeCrawler(start_url=start_url, output_path=kross_urls_path).run()
            all_kross_urls.update(urls)
    else:
        with open(kross_urls_path, encoding="utf-8") as f:
            all_kross_urls = json.load(f)

    logger.info("🌐 Kross: downloading HTMLs (force={})", FORCE_DOWNLOADER)
    for url in sorted(all_kross_urls):
        KrossDownloader(input_url=url, output_dir=kross_html, overwrite=FORCE_DOWNLOADER).run()


def extract_all():
    logger.info("--- 2/4: EXTRACTING ---")

    # Trek
    trek_html = artifacts_dir / "trek" / "raw_htmls"
    trek_json = artifacts_dir / "trek" / "extracted_jsons"
    logger.info("🧪 Trek: extracting from {} -> {} (force={})", trek_html, trek_json, FORCE_EXTRACTOR)
    TrekBikeExtractor(html_path=trek_html, json_path=trek_json).process_all(force=FORCE_EXTRACTOR)

    # Kross
    kross_html = artifacts_dir / "kross" / "raw_htmls"
    kross_json = artifacts_dir / "kross" / "extracted_jsons"
    logger.info("🧪 Kross: extracting from {} -> {} (force={})", kross_html, kross_json, FORCE_EXTRACTOR)
    KrossBikeExtractor(html_path=kross_html, json_path=kross_json).process_all(force=FORCE_EXTRACTOR)


def populate_db_all():
    logger.info("--- 3/4: POPULATING DB ---")

    # Clear brand families to avoid duplicates
    with SessionLocal() as session:
        logger.info("🗑️ Clearing existing 'Trek' families from DB…")
        session.execute(delete(BikeFamilyORM).where(BikeFamilyORM.brand_name == "Trek"))
        session.commit()

    with SessionLocal() as session:
        trek_json = artifacts_dir / "trek" / "extracted_jsons"
        logger.info("📥 Ingesting Trek JSONs from {}", trek_json)
        populator = TrekBikePopulator(json_dir=trek_json)
        count = populator.populate_all(session)
        logger.info("✅ Trek populated: {} files", count)

    with SessionLocal() as session:
        logger.info("🗑️ Clearing existing 'Kross' families from DB…")
        session.execute(delete(BikeFamilyORM).where(BikeFamilyORM.brand_name == "Kross"))
        session.commit()

    with SessionLocal() as session:
        kross_json = artifacts_dir / "kross" / "extracted_jsons"
        logger.info("📥 Ingesting Kross JSONs from {}", kross_json)
        populator = KrossBikePopulator(json_dir=kross_json)
        count = populator.populate_all(session)
        logger.info("✅ Kross populated: {} files", count)


def populate_es_all():
    logger.info("--- 4/4: POPULATING ES ---")
    es = Elasticsearch(es_settings.url)

    if not es.ping():
        logger.error("❌ Could not connect to Elasticsearch at {}", es_settings.url)
        raise SystemExit(1)

    if FORCE_POPULATOR:
        logger.warning("🗑️ Recreating ES indices (frames + groups)…")
        es_pop.create_index(es)
        es_pop.create_group_index(es)

    with SessionLocal() as session:
        success, failed = es_pop.populate_index(es, session)
        logger.success("ES indexing finished. Success: {}, Failed: {}", success, failed)


def main():
    logger.info("🏁 Starting full VeloGraph data pipeline…")

    # 1) Crawl
    crawl_all()

    # 2) Extract
    extract_all()

    # 3) Populate DB
    populate_db_all()

    # 4) Populate ES
    populate_es_all()

    logger.success("✨ VeloGraph pipeline completed successfully!")


if __name__ == "__main__":
    main()
