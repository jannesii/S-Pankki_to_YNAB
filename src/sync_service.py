from __future__ import annotations
import json
import logging
import os
import time
import pandas as pd
from typing import Callable, Optional, List, Dict, Any

from .config import Config
from .locale_utils import set_finnish_locale
from .csv_processing import CsvProcessor
from .ynab_client import YNABClient
from .file_ops import move_file

logger = logging.getLogger(__name__)

class SyncService:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.csv = CsvProcessor()

    def _load_api_info(self) -> YNABClient:
        logger.info(f"Loading YNAB credentials from {self.config.info_json_path}")
        with open(self.config.info_json_path, 'r') as f:
            info = json.load(f)
        api_key = info.get('api_key')
        budget_id = info.get('budget_id')
        if not api_key or not budget_id:
            raise RuntimeError("api_key or budget_id missing in info.json")
        logger.debug(f"YNAB budget_id loaded: {budget_id}")
        return YNABClient(api_key=api_key, budget_id=budget_id)

    def process_csv_once(self) -> None:
        try:
            set_finnish_locale()

            ynab = self._load_api_info()
            logger.info(f"Reading CSV for processing: {self.config.csv_path}")
            df = self.csv.process(self.config.csv_path)
            logger.info(f"CSV processed. Rows={len(df)}")

            # Convert to YNAB milliunits
            df['Inflow'] = (df['Inflow'] * 1000).astype(int)
            df['Outflow'] = (df['Outflow'] * 1000).astype(int)
            logger.debug("Converted amounts to milliunits")

            payees = ynab.get_payees()
            transactions = ynab.get_transactions()
            logger.info(f"Fetched YNAB metadata: payees={len(payees)} transactions={len(transactions)}")
            payee_to_category = YNABClient.build_payee_to_category_map(transactions, payees)
            logger.info(f"Derived payee→category mappings: {len(payee_to_category)}")

            bulk = self._build_ynab_transactions(df, payee_to_category)
            logger.info(f"Prepared transactions for upload: {len(bulk)}")
            ynab.bulk_upload(bulk)

            # Save processed CSV and archive original
            os.makedirs(os.path.dirname(self.config.csv_modded_path), exist_ok=True)
            os.makedirs(os.path.dirname(self.config.export_to_history_file_path), exist_ok=True)
            self.csv.save_to_csv(df, self.config.csv_modded_path)
            logger.info(f"Saved processed CSV to {self.config.csv_modded_path}")

            move_file(self.config.export_file_path, self.config.export_to_history_file_path)

        except Exception as e:
            logger.exception(e)

    @staticmethod
    def _build_ynab_transactions(df: pd.DataFrame, payee_to_category: Dict[str, str]) -> List[Dict[str, Any]]:
        logger.info('Preparing YNAB transaction payload...')
        account_id = 'f51e3268-bcf8-4f2a-9572-90f1302d6739'  # keep as provided
        default_category_id = '54d95049-2a45-42ec-aff5-3eed77855044'

        txs: List[Dict[str, Any]] = []
        for idx, row in df.iterrows():
            category_id = payee_to_category.get(row['Payee'], default_category_id)
            amount = int(row['Inflow'] - row['Outflow'])  # already milliunits
            sign = '-' if amount < 0 else ''
            import_id = f"YNAB:{sign}{abs(amount)}:{row['Date']}:1"

            tx = {
                'account_id': account_id,
                'date': row['Date'],
                'amount': amount,
                'payee_name': row['Payee'],
                'category_id': category_id,
                'memo': row['Memo'],
                'import_id': import_id
            }
            txs.append(tx)
        return txs

class DirectoryWatcher:
    def __init__(self, config: Config, on_found: Callable[[], None]) -> None:
        self.config = config
        self.on_found = on_found

    def run(self) -> None:
        logger.info('Booting up directory watcher...')
        full_path = os.path.join(self.config.downloads_dir, self.config.watch_filename)
        logger.info(f"Watching for file: {full_path}")

        while True:
            try:
                if os.path.exists(full_path):
                    # Move into working dir and process
                    logger.info(f"Detected file. Moving into working dir: {full_path} -> {os.getcwd()}")
                    move_file(full_path, os.getcwd())
                    logger.info("Starting CSV processing after move...")
                    self.on_found()
                    logger.info("Processing complete.")
                time.sleep(self.config.poll_interval_sec)
            except KeyboardInterrupt:
                logger.info('Directory watcher interrupted by user.')
                break
            except Exception as e:
                logger.exception(e)
                time.sleep(self.config.poll_interval_sec)
