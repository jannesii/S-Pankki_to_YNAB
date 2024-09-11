import requests
import os
import pandas as pd
import csv
import locale
from datetime import datetime
import time
import json
import shutil


def set_locale():
    """Set the desired locale to format decimal values with a comma."""
    print('INFO: Setting locale...')
    try:
        locale.setlocale(locale.LC_ALL, 'fi_FI.UTF-8')
    except locale.Error as e:
        print(f'ERROR: Failed to set locale: {e}')
        raise


def initialize_paths():
    """Initialize file and directory paths used throughout the script."""
    current_date_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    current_dir = os.getcwd()
    
    paths = {
        "csv_path": os.path.join(current_dir, 'export.csv'),
        "result_dir": os.path.join(current_dir, 'RESULTS'),
        "history_dir": os.path.join(current_dir, 'History'),
        "config_dir": os.path.join(current_dir, 'Config'),
        "script_dir": os.path.join(current_dir, 'Excel_Script'),
        "export_to_history": os.path.join(current_dir, 'History', f'export_{current_date_str}.csv'),
        "csv_modded": os.path.join(current_dir, 'RESULTS', f'S-Bank_YNAB_{current_date_str}.csv'),
        "csv_duplicate_check": os.path.join(current_dir, 'RESULTS', 'DUPLICATE_CHECK.csv'),
        "info_json": os.path.join(current_dir, 'Config', 'info.json')
    }

    os.makedirs(paths["result_dir"], exist_ok=True)
    os.makedirs(paths["history_dir"], exist_ok=True)
    return paths


def read_and_process_csv(csv_path):
    """Read and process the CSV file."""
    print('INFO: Reading and processing CSV...')
    df = pd.read_csv(csv_path, sep=';', decimal=',')
    df = replace_finnish_characters(df)
    df = rename_and_remove_columns(df)
    df = create_outflow_inflow_columns(df)
    df = create_payee_column(df)
    df = combine_columns(df)
    df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y').dt.strftime('%Y-%m-%d')
    return df[['Date', 'Payee', 'Memo', 'Outflow', 'Inflow']]


def replace_finnish_characters(df):
    """Replace Finnish-specific characters with their ASCII equivalents."""
    print('INFO: Replacing Finnish characters...')
    replace_map = str.maketrans("äöÄÖ", "aoAO")
    for col in ['Maksaja', 'Saajan nimi', 'Viesti', 'Tapahtumalaji']:
        df[col] = df[col].str.translate(replace_map)
    return df


def rename_and_remove_columns(df):
    """Rename and remove unnecessary columns."""
    print('INFO: Renaming and removing columns...')
    df.rename(columns={'Maksupäivä': 'Date'}, inplace=True)
    columns_to_remove = ['Kirjauspäivä', 'Saajan tilinumero', 'Saajan BIC-tunnus', 'Viitenumero', 'Arkistointitunnus']
    return df.drop(columns=columns_to_remove)


def create_outflow_inflow_columns(df):
    """Create Outflow and Inflow columns based on transaction amounts."""
    print('INFO: Creating Outflow and Inflow columns...')
    df['Outflow'] = df['Summa'].apply(lambda x: abs(x) if x < 0 else 0)
    df['Inflow'] = df['Summa'].apply(lambda x: x if x > 0 else 0)
    return df[(df['Inflow'] != 0) | (df['Outflow'] != 0)].reset_index(drop=True)


def create_payee_column(df):
    """Create Payee column based on transaction type."""
    print('INFO: Creating Payee column...')
    
    def determine_payee(row):
        if row['Outflow'] != 0:
            return row['Saajan nimi']
        if row['Inflow'] != 0:
            return row['Maksaja']
        return ''
    
    df['Payee'] = df.apply(determine_payee, axis=1)
    return df.drop(columns=['Maksaja', 'Saajan nimi', 'Summa'])


def combine_columns(df):
    """Combine Tapahtumalaji and Viesti columns into Memo."""
    print('INFO: Combining columns into Memo...')
    df['Memo'] = df['Tapahtumalaji'] + ' | ' + df['Viesti']
    return df.drop(columns=['Tapahtumalaji', 'Viesti'])


def save_to_csv(df, csv_path, mode='w', header=True):
    """Save DataFrame to a CSV file."""
    print(f'INFO: Saving CSV to {csv_path}...')
    df.to_csv(csv_path, index=False, sep=';', decimal=',', float_format='%.2f', quoting=csv.QUOTE_MINIMAL, quotechar='"', mode=mode, header=header)


def get_api_info(info_json_path):
    """Load API key and budget ID from JSON configuration file."""
    print('INFO: Loading API key and Budget ID from configuration...')
    try:
        with open(info_json_path, 'r') as file:
            info = json.load(file)
            return info['api_key'], info['budget_id']
    except (FileNotFoundError, KeyError) as e:
        print(f'ERROR: Failed to load API info: {e}')
        raise


def get_payees(headers, budget_id):
    """Fetch payees from the YNAB API."""
    print('INFO: Fetching payees from YNAB API...')
    url = f'https://api.youneedabudget.com/v1/budgets/{budget_id}/payees'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return {payee['id']: payee['name'] for payee in response.json()['data']['payees']}
    
    print(f'ERROR: Failed to fetch payees: {response.status_code}')
    return {}


def fetch_transactions(headers, budget_id):
    """Fetch transactions from the YNAB API."""
    print('INFO: Fetching transactions from YNAB API...')
    url = f'https://api.youneedabudget.com/v1/budgets/{budget_id}/transactions'
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()['data']['transactions']
    
    print(f'ERROR: Failed to fetch transactions: {response.status_code}')
    return []


def create_payee_to_category_mapping(transactions, payees):
    """Map payees to categories based on existing transactions."""
    print('INFO: Creating payee to category mapping...')
    return {
        payees[transaction['payee_id']]: transaction['category_id']
        for transaction in transactions
        if transaction['payee_id'] in payees and transaction['category_id']
    }


def upload_transactions_to_ynab(df_final, payee_to_category, api_key, budget_id):
    """Upload transactions to YNAB."""
    print('INFO: Uploading transactions to YNAB...')
    
    headers = {'Authorization': f'Bearer {api_key}'}
    account_id = 'f51e3268-bcf8-4f2a-9572-90f1302d6739'

    transactions = [
        {
            'account_id': account_id,
            'date': row['Date'],
            'amount': int(row['Inflow'] - row['Outflow']),
            'payee_name': row['Payee'],
            'category_id': payee_to_category.get(row['Payee'], '54d95049-2a45-42ec-aff5-3eed77855044'),
            'memo': row['Memo'],
            'import_id': f'YNAB:{"-" if row["Inflow"] < row["Outflow"] else ""}{abs(row["Inflow"] - row["Outflow"])}:{row["Date"]}:1'
        }
        for _, row in df_final.iterrows()
    ]

    if not transactions:
        print("INFO: No transactions to upload.")
        return

    try:
        response = requests.post(f'https://api.youneedabudget.com/v1/budgets/{budget_id}/transactions/bulk', headers=headers, json={'transactions': transactions})

        if response.status_code == 201:
            print(f'INFO: Bulk transaction upload successful! Uploaded {len(transactions)} transactions.')
        else:
            print(f'ERROR: Bulk transaction upload failed: {response.status_code} - {response.text}')
    except requests.RequestException as e:
        print(f'ERROR: Exception during transaction upload: {e}')


def move_file(source, destination):
    """Move a file from the source path to the destination path."""
    try:
        shutil.move(source, destination)
        print(f'INFO: File moved from {source} to {destination}')
    except (FileNotFoundError, PermissionError) as e:
        print(f'ERROR: Could not move file: {e}')
    except Exception as e:
        print(f'ERROR: Unexpected error during file move: {e}')


def scan_directory_for_file(directory, filename, interval=1):
    """Scan a directory for a specific file at regular intervals."""
    while True:
        print(f'Scanning for {filename} in {directory}...')
        if filename in os.listdir(directory):
            print(f'INFO: {filename} found in {directory}.')
            move_file(os.path.join(directory, filename), os.path.join(r'C:\\Users\\Janne\\OneDrive - Epedu O365\\Omat Projektit\\Excel', filename))
            process_csv()
        time.sleep(interval)


def process_csv():
    """Process the CSV file, handle API interaction, and save results."""
    try:
        set_locale()
        paths = initialize_paths()
        api_key, budget_id = get_api_info(paths["info_json"])

        df = read_and_process_csv(paths["csv_path"])
        df['Inflow'] = (df['Inflow'] * 1000).astype(int)
        df['Outflow'] = (df['Outflow'] * 1000).astype(int)

        headers = {'Authorization': f'Bearer {api_key}'}
        payees = get_payees(headers, budget_id)
        transactions = fetch_transactions(headers, budget_id)
        payee_to_category = create_payee_to_category_mapping(transactions, payees)

        upload_transactions_to_ynab(df, payee_to_category, api_key, budget_id)
        save_to_csv(df, paths["csv_modded"])
        move_file(paths["csv_path"], paths["export_to_history"])

    except Exception as e:
        print(f'ERROR: An error occurred during processing: {e}')


def main():
    """Main entry point for the script."""
    scan_directory_for_file(r"C:\\Users\\Janne\\Downloads", 'export.csv')


if __name__ == '__main__':
    main()
