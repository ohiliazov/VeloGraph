from elasticsearch import Elasticsearch
from loguru import logger
from sqlalchemy import delete

from backend.config import es_settings
from backend.core.db import SessionLocal
from backend.core.models import BikeFamilyORM
from backend.scripts import populate_es as es_pop
from backend.scripts.constants import artifacts_dir
from backend.scripts.kross.kross_crawler import KrossBikeCrawler
from backend.scripts.kross.kross_downloader import KrossBikeDownloader
from backend.scripts.kross.kross_extractor import KrossBikeExtractor
from backend.scripts.kross.kross_populator import KrossBikePopulator
from backend.scripts.trek.trek_crawler import TrekBikeCrawler
from backend.scripts.trek.trek_downloader import TrekBikeDownloader
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
    trek_urls = artifacts_dir / "trek" / "bike_urls.json"
    logger.info("🌐 Trek: collecting URLs (force={})", FORCE_CRAWLER)
    urls = TrekBikeCrawler(urls_path=trek_urls).run(force=FORCE_CRAWLER)

    logger.info("🌐 Trek: downloading HTMLs (force={})", FORCE_DOWNLOADER)
    TrekBikeDownloader(html_path=trek_html).run(urls=urls, force=FORCE_DOWNLOADER)

    # Kross
    kross_html = artifacts_dir / "kross" / "raw_htmls"
    kross_urls = artifacts_dir / "kross" / "bike_urls.json"
    logger.info("🌐 Kross: collecting URLs (force={})", FORCE_CRAWLER)
    urls = KrossBikeCrawler(urls_path=kross_urls).run(force=FORCE_CRAWLER)
    logger.info("🌐 Kross: downloading HTMLs (force={})", FORCE_DOWNLOADER)
    KrossBikeDownloader(html_path=kross_html).run(urls=urls, force=FORCE_DOWNLOADER)


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
