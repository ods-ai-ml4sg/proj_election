#!/usr/bin/env python
# coding: utf-8
import logging
import multiprocessing
import os
import pathlib
from datetime import date

import django
import pandas as pd
from django_pandas.io import read_frame
from selenium import webdriver
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager

from UpperLevelLinkCollector import get_upper_level_links
from selenium.webdriver.chrome.options import Options

from ParsingFunctions import get_links_UIK, get_election_result, load_candidates
import numpy as np

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elections_db.settings")
django.setup()

from ORM.models import CandidatePerformance, Election

from ElectionDataPackage import ElectionDataPackage




logger = logging.getLogger(__name__)


def init_driver(headless=True):
    '''
    creates webdriver object and global path for candidate excel files download; global variables are used to allow
    multiprocessing implementation
    :param headless: run webdriver in headless mode for better speed and smoother background execution
    :return: returns driver object for convenience, but it is created as global object anyway
    '''
    global download_dir, driver
    chrome_options = Options()
    download_dir = pathlib.Path(os.getcwd(), 'downloads')
    if headless:
        chrome_options.add_argument("--headless")
        current = multiprocessing.current_process()
        download_dir = pathlib.Path(download_dir, current.name)
    os.makedirs(download_dir, exist_ok=True)
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    return driver

class ElectionParser:

    candidate_column_translate = {'ФИО кандидата': CandidatePerformance.name.field.name,
                                  'Субъект выдвижения': "nominator",
                                  'Субьект выдвижения': "nominator",
                                  "Партия": "nominator",
                                  'Дата рождения кандидата': CandidatePerformance.candidate_birth_date.field.name,
                                  'Регистрация': 'registration',
                                  'регистрация': 'registration',
                                  'избрание': 'elected'
                                  }

    def __init__(self):
        self.unmapped_row = set()

    def get_protocol_and_candidate_performance_from_url_list(self, election_result_type, url_list):
        results_data = {i: get_election_result(i, driver, election_result_type=election_result_type) for i in
                        url_list}

        # WORKAROUND: there is currently a problem, where instead of having both types of election data on uik pages
        # in mixed election; a separate "common" district is present that carries all results of common type elections
        # In result, we can have uiks without common type data associated with common type summaries
        # To fix this issue it's better to collect data going down from summary tables,
        # not uik pages (that contain links to a wide variety of data, e.g. candidate)
        results_data = {k: v for k, v in results_data.items() if type(v) == pd.DataFrame}

        for url in results_data.keys():
            results_data[url] = self.prettify_election_dfs(results_data[url], url)

        protocols = pd.concat([v['protocol_data'] for v in results_data.values()], axis=1)
        candidate_performance = pd.concat([v['candidate_data'] for v in results_data.values()], axis=1)

        return protocols, candidate_performance

    def get_results_from_single_election_series(self, election_series):
        '''
        :param election_series: pd.Series that is a row from df returned by get_upper_level_links()
        :return: {'election_package': ElectionDataPackage(...), 'unmapped_rows': {}} if everything is ok
                or
                {'election_package': None, 'unmapped_rows': set{...} if at least one stage of parsing / transforming failed
        '''
        logger.info('Loading election {}'.format(election_series['name']))
        uik_links_data = get_links_UIK(election_series.election_url, driver=driver)
        uik_links_data = pd.DataFrame.from_dict(uik_links_data, orient='columns')
        self.check_for_missing_summaries(uik_links_data)

        results_data_all = {}
        candidates_performance_all = {}
        candidates_all = {}
        for election_result_type in ['common', 'specific']:
            summary_column = 'summary_found_'+ election_result_type
            if summary_column not in uik_links_data.columns:
                continue
            uik_links_data_by_type= uik_links_data[~uik_links_data[summary_column].isna()]
            unique_summaries = \
                uik_links_data_by_type.loc[uik_links_data_by_type[summary_column]!=uik_links_data_by_type.protocol_url,
                                           summary_column].unique().tolist()

            try:
                if unique_summaries:
                    summary_protocols, summary_candidate_performance = self.get_protocol_and_candidate_performance_from_url_list(
                        election_result_type, unique_summaries)

                uik_protocols, uik_candidate_performance = self.get_protocol_and_candidate_performance_from_url_list(
                    election_result_type, uik_links_data_by_type.protocol_url)
            except ValueError as e:
                print(e)
                return {'election_package': None, 'unmapped_rows': self.unmapped_row}

            if unique_summaries:
                for summary_link in summary_protocols.columns:
                    # WORKAROUND: check get_protocol_and_candidate_performance_from_url_list()
                    uiks_for_summary = \
                        uik_protocols.columns.intersection(
                            uik_links_data_by_type.loc[uik_links_data_by_type[summary_column] == summary_link, 'protocol_url'].tolist())
                    self.check_sums_vs_summary_data(uik_protocols[uiks_for_summary],
                                                    summary_protocols[summary_link])

                    self.check_sums_vs_summary_data(uik_candidate_performance[uiks_for_summary],
                                                    summary_candidate_performance[summary_link])

            results_protocols = pd.merge(uik_protocols.T.reset_index().rename(columns={'index': 'protocol_url'}),
                                    uik_links_data_by_type[['commission', 'protocol_url']], on='protocol_url')
            results_candidate_performance = pd.merge(uik_candidate_performance.T.reset_index().rename(columns={'index': 'protocol_url'}),
                                    uik_links_data_by_type[['commission', 'protocol_url']], on='protocol_url')

            results_data_all[election_result_type] = results_protocols
            candidates_performance_all[election_result_type] = results_candidate_performance

            # TODO load parties
            try:
                candidates = load_candidates(driver, election_series.election_url, election_result_type, download_dir)
                candidates = self.prettify_candidate_df(candidates)
                candidates_all[election_result_type] = candidates
            except IndexError: #in referendums and party-only elections
                return {'election_package': None, 'unmapped_rows': {}}

        package = ElectionDataPackage.create_packages(election_data=election_series,
                                                      candidate_performance=candidates_performance_all,
                                                      candidate_data=candidates_all,
                                                      results_data=results_data_all)

        return {'election_package': package, 'unmapped_rows': {}}


    def check_for_missing_summaries(self, uik_links_data):
        '''
        check if all elections have summary info to check against;
        '''
        summaries = pd.DataFrame(index=uik_links_data.index)
        for election_result_type in ['common', 'specific']:
            column = 'summary_found_' + election_result_type
            try:
                summaries[column] = uik_links_data[column]
            except KeyError:
                summaries[column] = np.empty(uik_links_data.shape[0])
        summary_found = (
                    summaries.summary_found_common.isna() & summaries.summary_found_specific.isna())
        uiks_without_summary = uik_links_data.protocol_url[summary_found].tolist()
        if uiks_without_summary:
            logger.warning("{} uiks without summary".format(str(len(uiks_without_summary))))

    def check_sums_vs_summary_data(self, results_data: pd.DataFrame, summary_data: pd.Series):
        '''
        check that sum of UIK results matches aggregate results at some upper commission lvl
        :param results_data: df with individual UIK links as column names
        :param summary_data:
        '''
        results_data = results_data.dropna().sum(axis=1)
        assert (results_data.sort_index()!=summary_data.sort_index().dropna()).sum()==0

    def prettify_election_dfs(self, df, link: str):
        '''
        convert uik results df created by parsing html table to two standardized tables: protocol df and candidate
        performance df; while parsed are very different, returned df have standard form
        :param df:
        :param link: link to uik results page (this page contains direct links to actual results tables)
        '''
        assert len(df.columns) == 3

        df.columns = ['code', 'row_name', 'count']

        try:
            df['count'] = df['count'].str.replace(' .*', "", regex=True) # removing percentages, e.g. "10 20%"
        except AttributeError: # not a string column
            pass
        df['count'] = df['count'].astype(np.float)

        first_candidate_row = df.loc[df['count'].isna() & df['code'].isna()].index
        df.drop('code', axis=1, inplace=True)
        if len(first_candidate_row)==0:
            raise ValueError('wrong number of zero rows in election df, cant parse')

        protocol_rows= df[df.index<first_candidate_row[0]].dropna(how='all').reset_index(drop=True)
        candidate_rows = df[df.index>=first_candidate_row[0]].dropna(how='all').reset_index(drop=True)
        #handling single candidate elections/ referenda: these dfs have candidate name/question as well as general yes/no answers
        # TODO multi question referenda?
        if np.isnan(candidate_rows.iloc[0]['count']):
            candidate_names = candidate_rows.row_name.iloc[1:].tolist()
            if len(candidate_names)==len([c for c in candidate_names if c.lower() in ElectionDataPackage.candidates_technical_values]):
                candidate_rows.loc[1, 'row_name'] = candidate_rows.loc[0, 'row_name']
                candidate_rows = candidate_rows.iloc[1:]
            else:
                raise ValueError('possible new wording for techical candidates: {}'.format(", ".join(candidate_names)))
        protocol_rows['row_name'] = protocol_rows['row_name'].str.lower()
        unmapped_row = set(protocol_rows.row_name.dropna().tolist()).difference(set(ElectionDataPackage.protocol_row_mapping_reversed.keys()))
        if len(unmapped_row)>0:
            self.unmapped_row |= unmapped_row
            raise ValueError('unmapped rows found')
        protocol_rows = protocol_rows.set_index('row_name')['count'].rename(link)
        candidate_rows = candidate_rows.set_index('row_name')['count'].rename(link)
        protocol_rows.index = [ElectionDataPackage.protocol_row_mapping_reversed[col] if col in ElectionDataPackage.protocol_row_mapping_reversed else col for
                      col in protocol_rows.index]
        ElectionDataPackage.add_protocol_items_if_missing(protocol_rows)
        return {'candidate_data':candidate_rows, 'protocol_data':protocol_rows}

    def prettify_candidate_df(self, candidate_df):
        '''
        :param candidate_df: df created with pd.read_excel() of 'Print Version' of candidate lists from CIK webpage
        :return: standardized candidate df
        '''
        first_row_index = candidate_df[candidate_df.iloc[:,1]=='ФИО кандидата'].index
        if len(first_row_index)!=1:
            raise ValueError('cant parse candidate excel')
        else:
            first_row_index = first_row_index[0]+2
        assert np.isnan(candidate_df.iloc[:,0].loc[first_row_index-1])

        rename_dict = {}
        for df_col in candidate_df.columns:
            for item in self.candidate_column_translate:
                if (candidate_df[df_col]==item).sum()==1:
                    rename_dict[df_col] = self.candidate_column_translate[item]
        candidate_df = candidate_df[list(rename_dict.keys())].rename(columns=rename_dict)
        candidate_df = candidate_df[candidate_df.index >= first_row_index]
        if len(candidate_df.columns)!=5:
            raise ValueError('cant parse candidate excel: wrong columns')
        candidate_df = candidate_df[candidate_df['registration'] == 'зарегистрирован']
        if candidate_df.shape[0]==0:
            raise ValueError('cant parse candidate excel: wrong registration info')
        return candidate_df



    def unpack_single_election_output(self, election_package_collector, unmapped_rows_collector, single_election_output):
        '''
        unpack output of get_results_from_single_election_series
        '''
        unmapped_rows_collector.update(single_election_output['unmapped_rows'])
        if type(single_election_output['election_package']) == ElectionDataPackage:
            election_package_collector += single_election_output['election_package']

    def update_unmapped_rows_file(self, path, new_unmapped_rows):
        with open(path, 'r') as f:
            current_unmapped_rows = set(f.read().splitlines())
        with open(path, 'w+') as f:
            f.write(list(current_unmapped_rows.update(new_unmapped_rows)))

    def parse_elections_main(self, start_date:date, end_date:date, debug, overwrite=False, n_processes=4,
                             upload_chunk_size=20):
        if debug and n_processes>1:
            print('debug mode, ignoring n_processes')
        driver = init_driver(headless=not debug)
        df_with_links_to_elections = get_upper_level_links(start_date, end_date)

        if not overwrite:
            elections_in_db = read_frame(Election.objects.all())['election_url'].values
            df_with_links_to_elections = df_with_links_to_elections[~df_with_links_to_elections.election_url.isin(elections_in_db)]

        election_df_split = np.array_split(df_with_links_to_elections, np.ceil(df_with_links_to_elections.shape[0] / upload_chunk_size))


        if debug:
            for election_chunk in tqdm(election_df_split,
                                       desc="Elections parsed and uploaded to db:",
                                       unit_scale=upload_chunk_size):
                unmapped_rows_collector = set()
                election_package_collector = []
                for _ , j in tqdm(election_chunk.iterrows(),
                                  desc="Elections parsed in chunk:",
                                  total=election_chunk.shape[0]):
                    single_election_output = self.get_results_from_single_election_series(j)
                    self.unpack_single_election_output(election_package_collector,
                                                       unmapped_rows_collector,
                                                       single_election_output)

                self.update_unmapped_rows_file('unmapped_rows.txt', unmapped_rows_collector)
                if election_package_collector is not None:
                    ElectionDataPackage.combine_packages(election_package_collector).upload_to_database()

        else:
            driver.close()
            driver = None
            pool = multiprocessing.Pool(processes=n_processes, initializer=init_driver, initargs=[True])

            for election_chunk in tqdm(election_df_split,
                                       desc="Elections parsed and uploaded to db:",
                                       unit_scale=upload_chunk_size):
                unmapped_rows_collector = set()
                election_package_collector = []
                results = list(tqdm(pool.imap(self.get_results_from_single_election_series, election_chunk.iterrows()),
                                    total=election_chunk.shape[0],
                                    unit_scale=upload_chunk_size))
                for single_election_output in results:
                    self.unpack_single_election_output(election_package_collector,
                                                       single_election_output,
                                                       unmapped_rows_collector)
                self.update_unmapped_rows_file('unmapped_rows.txt', unmapped_rows_collector)
                if election_package_collector is not None:
                    ElectionDataPackage.combine_packages(election_package_collector).upload_to_database()

            pool.close()

if __name__ == '__main__':
    ElectionParser().parse_elections_main(date(2020,9,12), date(2020,12,14), debug=True, upload_chunk_size=20)