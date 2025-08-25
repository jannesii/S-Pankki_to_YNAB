from dataclasses import dataclass
import requests
import os
import pandas as pd
import csv
import locale
from datetime import datetime
import time
import json
import shutil
import logging

@dataclass
class Config:
    current_date_str: str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    csv_path: str
    csv_modded_path: str
    info_json_path: str
    export_to_history_file_path: str
    export_file_path: str
    log_path: str
    config_dir_path: str

def init_logging(config: Config):
    logging.basicConfig(
        filename=config.log_path,
        level=logging.INFO,
        format='%(levelname)s - %(asctime)s - %(message)s'
    )

def set_locale():
    # Set the desired locale to format decimal values with a comma
    logging.info(f'Setting locale...')
    locale.setlocale(locale.LC_ALL, 'fi_FI.UTF-8')


def initialize_config() -> Config:
    config = Config()
    current_date_str = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    current_dir = os.getcwd()
    config.csv_path = os.path.join(current_dir, 'export.csv')
    result_dir_name = 'RESULTS'

    config_dir_name = 'Config'
    config.config_dir_path = os.path.join(current_dir, config_dir_name)

    history_dir_name = 'History'

    config.export_file_path = os.path.join(current_dir, f'export.csv')
    config.export_to_history_file_path = os.path.join(
        current_dir, history_dir_name, f'export_{current_date_str}.csv')

    config.csv_modded_path = os.path.join(
        current_dir, result_dir_name, f'S-Bank_YNAB_{current_date_str}.csv')

    info_json_name = 'info.json'
    config.info_json_path = os.path.join(config.config_dir_path, info_json_name)

    log_txt_name = 'log.txt'
    config.log_path = os.path.join(config.config_dir_path, log_txt_name)

    return config


def read_and_process_csv(csv_path):
    logging.info(f'Reading and processing csv...')
    df = pd.read_csv(csv_path, sep=';', decimal=',')
    df = replace_finnish_characters(df)
    df = rename_and_remove_columns(df)
    df = create_outflow_inflow_columns(df)
    df = create_payee_column(df)
    df = combine_columns(df)
    df['Date'] = pd.to_datetime(
        df['Date'], format='%d.%m.%Y').dt.strftime('%Y-%m-%d')
    df = df[['Date', 'Payee', 'Memo', 'Outflow', 'Inflow']]
    return df



def replace_finnish_characters(df):
    logging.info(f'Replacing finnish character...')
    for col in ['Maksaja', 'Saajan nimi', 'Viesti', 'Tapahtumalaji']:
        df[col] = df[col].str.replace('ä', 'a').str.replace(
            'ö', 'o').str.replace('Ä', 'A').str.replace('Ö', 'O')
    return df


def rename_and_remove_columns(df):
    logging.info(f'Renaming and removing columns...')
    df.rename(columns={'Maksupäivä': 'Date'}, inplace=True)
    columns_to_remove = ['Kirjauspäivä', 'Saajan tilinumero',
                         'Saajan BIC-tunnus', 'Viitenumero', 'Arkistointitunnus']
    df.drop(columns=columns_to_remove, inplace=True)
    return df


def create_outflow_inflow_columns(df):
    logging.info(f'Creating inflow and outflow columns...')
    df['Outflow'] = df['Summa'].apply(lambda x: abs(x) if x < 0 else 0)
    df['Inflow'] = df['Summa'].apply(lambda x: x if x > 0 else 0)
    df = df[(df['Inflow'] != 0) | (df['Outflow'] != 0)]
    df.reset_index(drop=True, inplace=True)
    return df


def create_payee_column(df):
    logging.info(f'Creating payee column...')

    def determine_payee(row):
        if row['Outflow'] != 0 and row['Inflow'] == 0:
            return row['Saajan nimi']
        elif row['Inflow'] != 0 and row['Outflow'] == 0:
            return row['Maksaja']
        else:
            return ''
    df['Payee'] = df.apply(determine_payee, axis=1)
    df.drop(columns=['Maksaja', 'Saajan nimi', 'Summa'], inplace=True)
    return df


def combine_columns(df):
    logging.info(f'Combining columns...')
    df['Memo'] = df['Tapahtumalaji'] + ' | ' + df['Viesti']
    df.drop(['Tapahtumalaji', 'Viesti'], axis=1, inplace=True)
    return df


def save_to_csv(df, csv_path, mode='w', header=True):
    logging.info(f'Saving csv...')
    df.to_csv(csv_path, index=False, sep=';', decimal=',', float_format='%.2f',
              quoting=csv.QUOTE_MINIMAL, quotechar='"', mode=mode, header=header)


def get_payees(headers, budget_id):
    logging.info(f'Trying to fetch payees through API...')
    url = f'https://api.youneedabudget.com/v1/budgets/{budget_id}/payees'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return {payee['id']: payee['name'] for payee in response.json()['data']['payees']}
    else:
        logging.exception(f'Failed to fetch payees: {response.status_code}')
        return {}


def fetch_transactions(headers, budget_id):
    logging.info(f'Trying to fetch transactions through API...')
    url = f'https://api.youneedabudget.com/v1/budgets/{budget_id}/transactions'
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()['data']['transactions']
    else:
        logging.exception(f'Failed to fetch transactions: {response.status_code}')
        return []


def create_payee_to_category_mapping(transactions, payees):
    logging.info(f'Creating payee to category mapping...')
    payee_to_category = {}
    for transaction in transactions:
        payee_id = transaction['payee_id']
        category_id = transaction['category_id']
        if payee_id and category_id and payee_id in payees:
            payee_to_category[payees[payee_id]] = category_id
    return payee_to_category


def upload_transactions_to_ynab(df_final, payee_to_category, API_KEY, BUDGET_ID):
    logging.info(f'Uploading transactions to YNAB...')

    headers = {'Authorization': f'Bearer {API_KEY}'}
    account_id = 'f51e3268-bcf8-4f2a-9572-90f1302d6739'

    transactions = []
    for index, row in df_final.iterrows():
        category_id = payee_to_category.get(
            row['Payee'], '54d95049-2a45-42ec-aff5-3eed77855044')

        # Calculate amount and import_id
        amount = int(row['Inflow'] - row['Outflow'])
        sign = '-' if amount < 0 else ''
        import_id = f'YNAB:{sign}{abs(amount)}:{row["Date"]}:1'

        transaction = {
            'account_id': account_id,
            'date': row['Date'],
            'amount': amount,
            'payee_name': row['Payee'],
            'category_id': category_id,
            'memo': row['Memo'],
            'import_id': import_id
        }
        transactions.append(transaction)

    bulk_payload = {'transactions': transactions}
    if not transactions:
        text = "INFO: No transactions to upload."
        logging.info(text)
        return
    try:
        response = requests.post(
            f'https://api.youneedabudget.com/v1/budgets/{BUDGET_ID}/transactions/bulk', headers=headers, json=bulk_payload)

        if response.status_code == 201:
            success_text = f'Bulk transaction upload successful!'
            logging.info(success_text)
        else:
            failure_text = f'Error in bulk transaction upload: {response.status_code} - {response.text}'
            logging.error(failure_text)
    except Exception as e:
        logging.exception(e)


def move_file(source, destination):
    """
    Moves a file from the source path to the destination path.

    :param source: The path of the file to move.
    :param destination: The destination path where the file should be moved.
    """
    try:
        shutil.move(source, destination)
        logging.info(f'File moved from {source} to {destination}')
    except FileNotFoundError:
        logging.exception(f'The file {source} does not exist.')
    except PermissionError:
        logging.exception(f'Permission denied: Unable to move the file {source}.')
    except Exception as e:
        logging.exception(f'Error moving file: {e}')


def scan_directory_for_file():
    config: Config = initialize_config()
    init_logging(config=config)

    logging.info('Booting up...')
    directory = os.path.join(os.path.expanduser("~"), "Downloads")
    filename = 'export.csv'
    full_path = os.path.join(directory, filename)
    interval = 1

    while True:
        # List all files in the directory
        files = os.listdir(directory)

        # Check if the file is found
        if filename in files:
            # Activate your desired function or action here
            # For example:
            move_file(full_path,
                      os.getcwd())

            process_csv(config)

        # Wait for the specified interval before scanning again
        time.sleep(interval)




def process_csv(config: Config):
    try:
        set_locale()

        # Get API key and Budget ID through JSON
        with open(config.info_json_path, 'r') as file:
            info = json.load(file)

        API_KEY = info.get('api_key')
        BUDGET_ID = info.get('budget_id')

        # Read and process the CSV file
        df = read_and_process_csv(config.csv_path)

        # Multiply all values in 'inflow' and 'outflow' columns by 1000 and convert to integers
        df['Inflow'] = (df['Inflow'] * 1000).astype(int)
        df['Outflow'] = (df['Outflow'] * 1000).astype(int)

        # Prepare for uploading transactions to YNAB
        headers = {
            'Authorization': f'Bearer {API_KEY}'}
        payees = get_payees(headers, BUDGET_ID)
        transactions = fetch_transactions(
            headers, BUDGET_ID)
        payee_to_category = create_payee_to_category_mapping(
            transactions, payees)

        # Upload transactions to YNAB
        upload_transactions_to_ynab(
            df, payee_to_category, API_KEY, BUDGET_ID)

        # Save the non-duplicate transactions to a new CSV file
        save_to_csv(df, config.csv_modded_path)

        move_file(config.export_file_path, config.export_to_history_file_path)

    except Exception as e:
        logging.exception(e)


def main():
    scan_directory_for_file()


if __name__ == '__main__':
    main()
