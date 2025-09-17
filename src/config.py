from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
import os
from typing import Optional
import logging
import json

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class Config:
    current_date_str: str
    csv_path: str
    csv_modded_path: str
    info_json_path: str
    export_to_history_file_path: str
    export_file_path: str
    config_dir_path: str
    downloads_dir: str
    watch_filename: str = "export.csv"
    poll_interval_sec: float = 1.0

    @staticmethod
    def build(
        base_dir: Optional[str] = None,
        downloads_dir: Optional[str] = None,
        now: Optional[datetime] = None
    ) -> "Config":
        dt = now or datetime.now()
        current_date_str = dt.strftime('%Y-%m-%d_%H-%M-%S')

        base_dir = base_dir or os.getcwd()
        logger.debug(f"Using base_dir={base_dir}")
        
        if os.name == 'nt':  # Windows
            local_appadata = os.getenv("LOCALAPPDATA")
            program_dir = os.path.join(local_appadata, "S-Pankki_to_YNAB")
            logger.debug(f"Program data dir={program_dir}")
                
            config_json_path = os.path.join(program_dir, 'config.json')
            if os.path.exists(config_json_path):
                logger.info(f"Loading app config: {config_json_path}")
                with open(config_json_path, 'r') as f:
                    config_data = json.load(f)

                downloads_dir = config_data.get("downloads_dir")
            else:
                logger.info("App config not found. Creating default config...")
                if not os.path.exists(program_dir):
                    os.makedirs(program_dir)
                downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
                downloads_dir = downloads_path if os.path.exists(downloads_path) else ""
                with open(config_json_path, 'w') as f:
                    json.dump({
                        "downloads_dir": downloads_dir
                    }, f)
                logger.info(f'Created config file: {config_json_path}')
        else:
            downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
            downloads_dir = downloads_path if os.path.exists(downloads_path) else ""
                
        if not downloads_dir:
            logger.error("Downloads directory not configured. Set downloads_dir in LOCALAPPDATA/S-Pankki_to_YNAB/config.json")
            raise FileNotFoundError("Downloads directory not found. Set downloads_dir in AppData/Local/S-Pankki_to_YNAB/config.json")
        if not os.path.exists(downloads_dir):
            logger.error(f"Configured downloads_dir does not exist: {downloads_dir}")
            raise FileNotFoundError(f"Configured downloads_dir does not exist: {downloads_dir}")
        logger.info(f"Watching downloads_dir={downloads_dir}")
 
        result_dir_name = 'RESULTS'
        history_dir_name = 'History'
        config_dir_name = 'Config'

        config_dir_path = os.path.join(base_dir, config_dir_name)
        info_json_path = os.path.join(config_dir_path, 'info.json')
        logger.debug(f"Config dir={config_dir_path}, info_json={info_json_path}")

        export_file_path = os.path.join(base_dir, 'export.csv')
        export_to_history_file_path = os.path.join(
            base_dir, history_dir_name, f'export_{current_date_str}.csv'
        )
        csv_modded_path = os.path.join(
            base_dir, result_dir_name, f'S-Bank_YNAB_{current_date_str}.csv'
        )
        logger.debug(
            f"Paths set: export_file={export_file_path}, history_file={export_to_history_file_path}, results_file={csv_modded_path}"
        )

        return Config(
            current_date_str=current_date_str,
            csv_path=export_file_path,
            csv_modded_path=csv_modded_path,
            info_json_path=info_json_path,
            export_to_history_file_path=export_to_history_file_path,
            export_file_path=export_file_path,
            config_dir_path=config_dir_path,
            downloads_dir=downloads_dir,
        )
