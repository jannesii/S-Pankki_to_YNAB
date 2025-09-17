from __future__ import annotations
import logging
import os
from .config import Config
from .sync_service import SyncService, DirectoryWatcher

logger = logging.getLogger(__name__)

def main() -> None:
    try:
        env = os.getenv("ENV", "Development")
        logger.info(f"Starting program in {env} environment")
        config = Config.build()

        service = SyncService(config)

        watcher = DirectoryWatcher(
            config=config,
            on_found=service.process_csv_once
        )
        watcher.run()
    except Exception:
        logger.exception("Fatal error in main execution")