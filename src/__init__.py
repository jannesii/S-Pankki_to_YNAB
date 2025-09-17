from __future__ import annotations
import logging
from .config import Config
from .sync_service import SyncService, DirectoryWatcher

logger = logging.getLogger(__name__)

def main() -> None:
    try:
        config = Config.build()

        service = SyncService(config)

        watcher = DirectoryWatcher(
            config=config,
            on_found=service.process_csv_once
        )
        watcher.run()
    except Exception:
        logger.exception("Fatal error in main execution")