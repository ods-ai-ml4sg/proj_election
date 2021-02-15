import os
import time
from collections import namedtuple

import django
import pandas as pd
import numpy as np
import sqlalchemy
from django.db.models import Max, Field, ForeignKey
from django_pandas.io import read_frame
from sqlalchemy.exc import DataError, IntegrityError

from DataLoad.CommissionDataDownloader import CommissionDataDownloader
from ProtocolRowMapping import ProtocolRowValuesVerified

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elections_db.settings")
django.setup()

from ORM.models import Election, CommissionProtocol, CandidatePerformance, Nominator


class ElectionDataPackage:

    '''
    This class collects and handles all data that's related to a set of elections
    '''

    ID='id'
    UPLOAD_RETRY_TIMES = 3
    UPLOAD_RETRY_INTERVAL_SECONDS = 5

    def __init__(self, protocol_uik_data: pd.DataFrame, candidate_performance: pd.DataFrame, nominators, election_metadata: pd.DataFrame):
        self.protocol_uik_data = protocol_uik_data
        self.candidate_performance = candidate_performance
        self.nominators = nominators
        self.election_metadata = election_metadata

    def upload_to_database(self):
        engine = CommissionDataDownloader.create_sqlalchemy_engine()
        with engine.begin() as connection:
            Election.objects.filter(name__in=self.election_metadata['name'].tolist()).delete()
            if type(self.nominators)==pd.Series:
                self.upload_nominators(connection)
            try:
                self.create_indices_manually()
                self.upload_df_to_database_on_model(self.election_metadata, Election, connection)
                self.upload_df_to_database_on_model(self.protocol_uik_data, CommissionProtocol, connection)
                self.upload_df_to_database_on_model(self.candidate_performance, CandidatePerformance, connection)
            except Exception as e:
                raise ValueError(e)



    @classmethod
    def get_field_names(cls, model):
        return [field.name+'_id' if isinstance(field, ForeignKey) else field.name
                for field in model._meta.get_fields(include_parents=False) if isinstance(field, Field)]

    def create_indices_manually(self):
        '''
        we create indices and foreign keys manually to avoid postprocessing inside db
        '''
        nominator_frame = read_frame(Nominator.objects.all())[['name', 'id']]
        max_election_id = Election.objects.aggregate(Max(self.ID))['id__max']
        max_protocol_id = CommissionProtocol.objects.aggregate(Max(self.ID))['id__max']
        max_election_id = max_election_id if max_election_id is not None else -1
        max_protocol_id = max_protocol_id if max_protocol_id is not None else -1
        self.election_metadata[self.ID] = self.election_metadata[Election.election_url.field.name]
        try:
            self.protocol_uik_data[self.ID] = self.protocol_uik_data[CommissionProtocol.protocol_url.field.name]+ \
                                              self.protocol_uik_data['candidate_list_type'] + \
                                              self.protocol_uik_data['commission_name']
        except KeyError:
            self
        self.candidate_performance['protocol_id'] = self.candidate_performance['protocol_url'] + \
                                                    self.candidate_performance['candidate_list_type'] + \
                                                    self.candidate_performance['commission_name']
        self.candidate_performance['election_id'] = self.candidate_performance['election_url']
        self.protocol_uik_data['election_id'] = self.protocol_uik_data['election_url']

        try:
            self.candidate_performance = CommissionDataDownloader._repalace_old_index_with_new(nominator_frame, self.candidate_performance,
                                                                                    'nominator')
        except KeyError:
            pass

        election_index = CommissionDataDownloader._make_new_index(self.election_metadata, max_election_id+1)
        protocol_index = CommissionDataDownloader._make_new_index(self.protocol_uik_data, max_protocol_id + 1)
        self.election_metadata = CommissionDataDownloader._repalace_old_index_with_new(election_index, self.election_metadata, self.ID)
        self.protocol_uik_data = CommissionDataDownloader._repalace_old_index_with_new(election_index,
                                                                                       self.protocol_uik_data,
                                                                                       'election_id')
        self.protocol_uik_data = CommissionDataDownloader._repalace_old_index_with_new(protocol_index,
                                                                                       self.protocol_uik_data,
                                                                                       self.ID)
        self.candidate_performance = CommissionDataDownloader._repalace_old_index_with_new(protocol_index,
                                                                                           self.candidate_performance,
                                                                                           'protocol_id')
        self.candidate_performance = CommissionDataDownloader._repalace_old_index_with_new(election_index,
                                                                                           self.candidate_performance,
                                                                                           'election_id')


    def upload_df_to_database_on_model(self, df, model, connection):
        model_fields = set(self.get_field_names(model))
        if self.ID not in df.columns:
            model_fields.discard(self.ID)
        for field in model_fields.difference(df.columns):
            df[field] = np.nan
        df[model_fields].to_sql(model.objects.model._meta.db_table,
                                if_exists='append', index=False, con=connection, method='multi', chunksize=1000,
                                dtype={'path': sqlalchemy.types.JSON})

    def upload_nominators(self, connection):
        CommissionDataDownloader.update_nominators(self.nominators, connection)

    @classmethod
    def create_package(cls, walkdown, candidates, election_metadata):
        nominators = None
        candidate_performance = walkdown.candidate_performance
        protocol_data = walkdown.protocol_data
        performance_frame_size = candidate_performance.shape[0]
        if type(candidates)==pd.DataFrame:
            try:
                candidate_performance = pd.merge(candidate_performance, candidates, on=['name'],
                                                  how='left')
            except KeyError:
                return
            if performance_frame_size != candidate_performance.shape[0]:
                raise ValueError('Duplicate candidates found')

            nominators = candidates.nominator.drop_duplicates()

        return ElectionDataPackage(protocol_uik_data= protocol_data.assign(election_url = election_metadata['election_url']),
                                   candidate_performance= candidate_performance.assign(election_url = election_metadata['election_url']),
                                   nominators = nominators,
                                   election_metadata = election_metadata.to_frame().T)



