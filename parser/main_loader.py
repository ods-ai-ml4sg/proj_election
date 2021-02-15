#!/usr/bin/env python
# coding: utf-8
import concurrent
import logging
import multiprocessing
import os
import pathlib
import pickle
from datetime import date
import django
from django_pandas.io import read_frame
from selenium import webdriver
from tqdm import tqdm
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
from UpperLevelLinkCollector import get_upper_level_links
from selenium.webdriver.chrome.options import Options

from ParsingFunctions import parse_single_election, init_driver

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elections_db.settings")
django.setup()

from ORM.models import Election

from ElectionDataPackage import ElectionDataPackage




class ElectionParser:

    def update_unmapped_rows_file(self, path, new_unmapped_rows: dict):
        try:
            current_unmapped_rows = pd.read_csv(path, index_col=None)
        except(FileNotFoundError, EOFError):
            current_unmapped_rows = pd.DataFrame(columns=['string', 'url'])
        new_unmapped_rows = pd.DataFrame([(k,v) for k,v in new_unmapped_rows.items()], columns=['string', 'url'])
        current_unmapped_rows = current_unmapped_rows.append(new_unmapped_rows)
        current_unmapped_rows.drop_duplicates('string', inplace=True)
        current_unmapped_rows.to_csv(path, index=False)

    def parse_elections_main(self, start_date:date, end_date:date, debug, overwrite=False, n_processes=1):
        df_with_links_to_elections = get_upper_level_links(start_date, end_date)

        if not overwrite:
            elections_in_db = read_frame(Election.objects.all())['election_url'].values
            df_with_links_to_elections = df_with_links_to_elections[~df_with_links_to_elections.election_url.isin(elections_in_db)]

        pbar_complete = tqdm(total=df_with_links_to_elections.shape[0], desc='Elections loaded')
        pbar_failed = tqdm(total=df_with_links_to_elections.shape[0], desc='Elections failed')

        def callback_load(returned):
            res = returned.result()
            if type(res)!=tuple:
                pbar_failed.update(1)
                return
            walkdown, candidates, election_series = res
            if walkdown.unmapped_rows:
                self.update_unmapped_rows_file('unmapped_rows.txt', walkdown.unmapped_rows)
                pbar_failed.update(1)
                return
            if walkdown.errors:
                pbar_failed.update(1)
                return
            package = ElectionDataPackage.create_package(walkdown=walkdown,
                                                         candidates=candidates,
                                                         election_metadata=election_series
                                                         )
            package.upload_to_database()
            pbar_complete.update(1)

        with concurrent.futures.ProcessPoolExecutor(max_workers=n_processes, initializer=init_driver, initargs=[not debug]) as worker_pool:
            futures = [worker_pool.submit(parse_single_election, row) for _, row in df_with_links_to_elections.iterrows()]
            [fut.add_done_callback(callback_load) for fut in futures]




if __name__ == '__main__':
    ElectionParser().parse_elections_main(date(2011,1,1), date(2020,12,1), debug=True, n_processes=1, overwrite=False)