# S‑Pankki to YNAB

A small Windows‑focused tool that watches your Downloads folder for S‑Pankki account export (`export.csv`), converts it into YNAB’s CSV format, and bulk‑uploads the transactions to your YNAB budget via the YNAB API. It also saves the processed CSV under `RESULTS/` and archives the original under `History/`.

## Features
- Watches `%UserProfile%\\Downloads` (configurable) for `export.csv`
- Converts S‑Pankki CSV (semicolon + decimal comma) into YNAB columns
- Maps payees to categories based on your existing YNAB transactions
- Uploads in bulk to reduce API calls
- Saves outputs to timestamped files for traceability

## Project Layout
- `main.py`: Entry point. Sets up logging and starts the watcher
- `src/__init__.py`: Bootstraps `Config`, `SyncService`, and `DirectoryWatcher`
- `src/config.py`: Paths, timestamps, and runtime configuration
- `src/sync_service.py`: Orchestrates CSV processing and YNAB API upload
- `src/csv_processing.py`: Pandas transforms to YNAB CSV columns
- `src/ynab_client.py`: Minimal YNAB API client (requests)
- `src/file_ops.py`: Safe file move helper
- `Config/info.json`: Your YNAB API credentials (see below)

## Requirements
- Windows 10/11 (developed with Windows paths and locale assumptions)
- Python 3.9+ recommended
- Packages: `pandas`, `requests`

Install into a virtual environment:

```
python -m venv .venv
.\\.venv\\Scripts\\activate
pip install pandas requests
```

## First‑Run Setup
1. Create `Config/info.json` in the project root with your YNAB details:
   - Path: `Config/info.json`
   - Contents:
     ```json
     { "api_key": "<YNAB Personal Access Token>", "budget_id": "<Your Budget ID>" }
     ```
   - Tip: Keep real secrets out of version control. This repo’s `.gitignore` already ignores `*.json`, but don’t commit real tokens.
2. Run `python main.py` once. On first run, the app writes a local settings file here:
   - `%LOCALAPPDATA%\\S-Pankki_to_YNAB\\config.json`
   - It contains: `{ "downloads_dir": "C:\\\\\Users\\\\<you>\\\\Downloads" }`
   - Edit this if your S‑Pankki exports land somewhere else.

## Usage
- Export transactions from S‑Pankki as `export.csv` into your Downloads directory.
- Start the tool:
  - `python main.py`
- The watcher polls every second. When `export.csv` appears, it will:
  - Move it into the project working directory
  - Process and convert to YNAB format
  - Fetch your YNAB payees/transactions, map payees → categories
  - Bulk upload transactions to YNAB
  - Save files:
    - Processed: `RESULTS/S-Bank_YNAB_<timestamp>.csv`
    - Original archived: `History/export_<timestamp>.csv`

Logs are written to `run.log` and echoed to the console.

## Configuration Notes
- Downloads folder: `%LOCALAPPDATA%\\S-Pankki_to_YNAB\\config.json` → `downloads_dir`
- Watched filename: default is `export.csv` (see `src/config.py`)
- Account and category defaults used for uploads are set here:
  - `src/sync_service.py` → `_build_ynab_transactions`
    - `account_id`: hard‑coded placeholder
    - `default_category_id`: fallback if no mapping exists
  Update these to match your YNAB account/category IDs.

## How It Works (brief)
- `CsvProcessor` reads `export.csv` with `sep=';'` and `decimal=','`, cleans up Finnish characters, renames columns, splits `Summa` into `Inflow/Outflow`, derives `Payee`, builds `Memo`, and normalizes `Date` to `YYYY-MM-DD`.
- Amounts are converted to YNAB milliunits before upload.
- `YNABClient` fetches payees and transactions to build a payee→category map, then performs a bulk upload.

## Build a Standalone EXE (optional)
- One‑file build using PyInstaller is wired via PowerShell:
  - `build_exe.ps1` → produces `S-pankki_to_YNAB.exe` in the repo root
  - Prereqs inside your venv: `pip install pyinstaller pandas requests`
  - Run: `powershell -ExecutionPolicy Bypass -File .\\build_exe.ps1`

## Troubleshooting
- Locale warning: If `fi_FI.UTF-8` is not available on Windows, processing continues with default locale; CSV parsing uses explicit separators/decimals.
- API failures: Check `Config/info.json` values and network access; see `run.log` for status codes and error bodies.
- No file detected: Confirm the watched filename is `export.csv` and that `%LOCALAPPDATA%\\S-Pankki_to_YNAB\\config.json` points to the correct `downloads_dir`.
- Wrong account/category: Update IDs in `src/sync_service.py` as noted above.

## Security
- `Config/info.json` contains secrets; treat it like a credential. Do not share or commit real keys.

## License
No license specified. If you plan to share or publish, consider adding a license file.

