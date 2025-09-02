import logging
import pandas as pd
import csv

logger = logging.getLogger(__name__)

class CsvProcessor:
    def __init__(self) -> None:
        pass

    def process(self, csv_path: str) -> pd.DataFrame:
        logger.info('Reading and processing csv...')
        df = pd.read_csv(csv_path, sep=';', decimal=',')
        logger.debug(f"CSV loaded: rows={len(df)} cols={list(df.columns)}")
        df = self._replace_finnish_characters(df)
        logger.debug(f"After finnish char replace: cols={list(df.columns)}")
        df = self._rename_and_remove_columns(df)
        logger.debug(f"After rename/remove: cols={list(df.columns)}")
        df = self._create_outflow_inflow_columns(df)
        logger.debug(
            f"After inflow/outflow: rows={len(df)} pos={int((df['Inflow']>0).sum())} neg={int((df['Outflow']>0).sum())}"
        )
        df = self._create_payee_column(df)
        missing_payee = int(df['Payee'].isna().sum()) if 'Payee' in df.columns else -1
        logger.debug(f"After payee: cols={list(df.columns)} missing_payee={missing_payee}")
        df = self._combine_columns(df)
        logger.debug(f"After memo combine: cols={list(df.columns)}")
        if 'Date' not in df.columns:
            logger.error("Expected 'Date' column not found before date normalization")
            raise KeyError("'Date' column missing")
        df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y').dt.strftime('%Y-%m-%d')
        df = df[['Date', 'Payee', 'Memo', 'Outflow', 'Inflow']]
        logger.debug(f"CSV normalized: rows={len(df)} cols={list(df.columns)}")
        return df

    def save_to_csv(self, df: pd.DataFrame, csv_path: str, mode: str = 'w', header: bool = True) -> None:
        logger.info('Saving csv...')
        df.to_csv(
            csv_path,
            index=False,
            sep=';',
            decimal=',',
            float_format='%.2f',
            quoting=csv.QUOTE_MINIMAL,
            quotechar='"',
            mode=mode,
            header=header
        )

    @staticmethod
    def _replace_finnish_characters(df: pd.DataFrame) -> pd.DataFrame:
        logger.info('Replacing finnish characters...')
        for col in ['Maksaja', 'Saajan nimi', 'Viesti', 'Tapahtumalaji']:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace('ä', 'a')
                    .str.replace('ö', 'o')
                    .str.replace('Ä', 'A')
                    .str.replace('Ö', 'O')
                )
        return df

    @staticmethod
    def _rename_and_remove_columns(df: pd.DataFrame) -> pd.DataFrame:
        logger.info('Renaming and removing columns...')
        if 'Maksupäivä' in df.columns:
            df.rename(columns={'Maksupäivä': 'Date'}, inplace=True)
        columns_to_remove = ['Kirjauspäivä', 'Saajan tilinumero', 'Saajan BIC-tunnus', 'Viitenumero', 'Arkistointitunnus']
        existing = [c for c in columns_to_remove if c in df.columns]
        if existing:
            df.drop(columns=existing, inplace=True)
        return df

    @staticmethod
    def _create_outflow_inflow_columns(df: pd.DataFrame) -> pd.DataFrame:
        logger.info('Creating inflow and outflow columns...')
        # Expect 'Summa' column with decimals as comma already parsed by pandas (decimal=',')
        df['Outflow'] = df['Summa'].apply(lambda x: abs(x) if x < 0 else 0)
        df['Inflow'] = df['Summa'].apply(lambda x: x if x > 0 else 0)
        df = df[(df['Inflow'] != 0) | (df['Outflow'] != 0)].reset_index(drop=True)
        return df

    @staticmethod
    def _create_payee_column(df: pd.DataFrame) -> pd.DataFrame:
        logger.info('Creating payee column...')
        def determine_payee(row):
            # Outflow case
            if row['Outflow'] != 0 and row['Inflow'] == 0:
                return row['Saajan nimi']
            # Inflow case
            elif row['Inflow'] != 0 and row['Outflow'] == 0:
                maksaja = str(row.get('Maksaja', '') or '')
                if 'VIPPS MOBILEPAY' in maksaja.upper():
                    return row.get('Viesti', '')
                return row['Maksaja']
            return ''
        df['Payee'] = df.apply(determine_payee, axis=1)
        df.drop(columns=[c for c in ['Maksaja', 'Saajan nimi', 'Summa'] if c in df.columns], inplace=True)
        return df


    @staticmethod
    def _combine_columns(df: pd.DataFrame) -> pd.DataFrame:
        logger.info('Combining columns...')
        df['Memo'] = df['Tapahtumalaji'].astype(str) + ' | ' + df['Viesti'].astype(str)
        df.drop([c for c in ['Tapahtumalaji', 'Viesti'] if c in df.columns], axis=1, inplace=True)
        return df
