import datetime
import os

import numpy as np
import pandas as pd
import django

from WalkDownResult import WalkDownResult

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elections_db.settings")
django.setup()
from ProtocolRowMapping import ProtocolRowValuesVerified

from ORM.models import CommissionProtocol, CandidatePerformance


class DataFormatting:

    total_composition = {CommissionProtocol.ballots_given_out_total.field.name:
                            [CommissionProtocol.ballots_given_out_early.field.name,
                             CommissionProtocol.ballots_given_out_at_stations.field.name,
                             CommissionProtocol.ballots_given_out_outside.field.name],
                         CommissionProtocol.ballots_found_total.field.name:
                            [CommissionProtocol.ballots_found_outside.field.name,
                             CommissionProtocol.ballots_found_at_station.field.name]}

    candidate_column_translate = {'ФИО кандидата': CandidatePerformance.name.field.name,
                                  'Субъект выдвижения': "nominator",
                                  'Субьект выдвижения': "nominator",
                                  "Партия": "nominator",
                                  'Дата рождения кандидата': CandidatePerformance.candidate_birth_date.field.name,
                                  'Регистрация': 'registration',
                                  'регистрация': 'registration',
                                  'избрание': 'elected'
                                  }

    @classmethod
    def prettify_candidate_df(cls, candidate_df):
        '''
        :param candidate_df: df created with pd.read_excel() of 'Print Version' of candidate lists from CIK webpage
        :return: standardized candidate df
        '''
        first_row_index = candidate_df[candidate_df.iloc[:, 1] == 'ФИО кандидата'].index
        if len(first_row_index) != 1:
            raise ValueError('cant parse candidate excel')
        else:
            first_row_index = first_row_index[0] + 2
        rename_dict = {}
        for df_col in candidate_df.columns:
            for item in cls.candidate_column_translate:
                if (candidate_df[df_col] == item).sum() == 1:
                    rename_dict[df_col] = cls.candidate_column_translate[item]
        candidate_df = candidate_df[list(rename_dict.keys())].rename(columns=rename_dict)
        candidate_df = candidate_df[candidate_df.index >= first_row_index]
        if len(candidate_df.columns) != 5:
            raise ValueError('cant parse candidate excel: wrong columns')
        candidate_df = candidate_df[candidate_df['registration'] == 'зарегистрирован']
        candidate_df[CandidatePerformance.candidate_birth_date.field.name] = \
            [cls.format_date(d) for d in candidate_df[CandidatePerformance.candidate_birth_date.field.name].values]
        if candidate_df.shape[0] == 0:
            raise ValueError('cant parse candidate excel: wrong registration info')
        return candidate_df


    @classmethod
    def prettify_election_dfs(cls, df, url, path):
        '''
        convert uik results df created by parsing html table to two standardized tables: protocol df and candidate
        performance df; while parsed are very different, returned df have standard form
        :param df:
        :param link: link to uik results page (this page contains direct links to actual results tables)
        '''
        value_columns = df.columns[2:]
        for col in value_columns:
            try:
                df[col] = df[col].str.replace(' .*', "", regex=True)  # removing percentages, e.g. "10 20%"
            except AttributeError:  # not a string column
                pass
            df[col] = df[col].astype(np.float)

        first_candidate_row = df.loc[df.iloc[:, 2].isna() & df['code'].isna()].index
        df.drop('code', axis=1, inplace=True)
        if len(first_candidate_row) == 0:
            raise ValueError('wrong number of zero rows in election df, cant parse')

        protocol_rows = df[df.index < first_candidate_row[0]].dropna(how='all').reset_index(drop=True)
        candidate_rows = df[df.index >= first_candidate_row[0]].dropna(how='all').reset_index(drop=True)
        # handling single candidate elections/ referenda: these dfs have candidate name/question as well as general yes/no answers
        # TODO multi question referenda?
        if np.sum(np.isnan(candidate_rows.iloc[0].iloc[1:].astype(float))):
            candidate_names = candidate_rows.row_name.iloc[1:].tolist()
            if len(candidate_names) == len(
                    [c for c in candidate_names if c.lower() in ProtocolRowValuesVerified.candidates_technical_values]):
                candidate_rows.loc[1, 'row_name'] = candidate_rows.loc[0, 'row_name']
                candidate_rows = candidate_rows.iloc[1:]
            else:
                raise ValueError('possible new wording for techical candidates: {}'.format(", ".join(candidate_names)))
        protocol_rows['row_name'] = protocol_rows['row_name'].str.lower()
        protocol_rows = protocol_rows.loc[~protocol_rows['row_name'].str.contains('открепит')]

        renamer, unmapped_rows = ProtocolRowValuesVerified.get_rename_dict_and_unmapped_rows(protocol_rows.row_name)
        protocol_rows.row_name.replace(renamer, inplace=True)
        cls.add_protocol_items_if_missing(protocol_rows)

        candidate_rows = pd.melt(candidate_rows, id_vars='row_name', var_name='commission_name',
                                 value_name=CandidatePerformance.votes.field.name).rename(columns={'row_name': 'name'})
        protocol_rows = protocol_rows.set_index('row_name').T.reset_index().rename(columns={'index': 'commission_name'})
        protocol_rows = cls.add_commission_name_and_path(protocol_rows, url, path)
        candidate_rows = cls.add_commission_name_and_path(candidate_rows, url, path)

        return WalkDownResult(protocol_rows, candidate_rows, {k:url for k in unmapped_rows}, [])

    @classmethod
    def add_commission_name_and_path(cls, df, url, path):
        df['protocol_url'] = url
        df['path'] = [path for _ in range(len(df.index))]
        return df

    @classmethod
    def add_protocol_items_if_missing(cls, df):
        # add aggregate columns
        df.set_index('row_name', inplace=True)
        for total_item, included_items in cls.total_composition.items():
            if total_item not in df.index:
               df.loc[total_item] = df.loc[df.index & included_items].sum(axis=0)
        # add other columns
        missing_cols = set(ProtocolRowValuesVerified.protocol_row_mapping.keys()).difference(df.index.tolist())
        for item in missing_cols:
            df.loc[item] = np.nan
        df.reset_index(inplace=True)

    @classmethod
    def format_date(cls, str_date):
        return datetime.datetime.strptime(str_date, "%d.%m.%Y").date()