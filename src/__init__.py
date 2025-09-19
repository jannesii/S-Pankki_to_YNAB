from __future__ import annotations
import logging
import os
from .config import Config
from .sync_service import SyncService, DirectoryWatcher

logger = logging.getLogger(__name__)

def main() -> None:
    try:
        api_key, budget_id = os.getenv("API_KEY"), os.getenv("BUDGET_ID")
        if not api_key or not budget_id:
            raise ValueError("API_KEY and BUDGET_ID environment variables must be set")
        
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