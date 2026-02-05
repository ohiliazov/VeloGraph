from pathlib import Path

from loguru import logger

artifacts_dir = Path(__file__).parent.parent / "downloads"


if __name__ == "__main__":
    logger.info("🗂️ Artifacts directory: {}", artifacts_dir)
