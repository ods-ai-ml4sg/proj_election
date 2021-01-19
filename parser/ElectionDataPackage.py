import os
import time
from collections import namedtuple

import django
import pandas as pd
import numpy as np
import sqlalchemy
from django.db.models import Max, Field, ForeignKey
from django_pandas.io import read_frame
from sqlalchemy.exc import DataError

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

    total_composition = {CommissionProtocol.ballots_given_out_total.field.name:
                            [CommissionProtocol.ballots_given_out_early.field.name,
                             CommissionProtocol.ballots_given_out_at_stations.field.name,
                             CommissionProtocol.ballots_given_out_outside.field.name],
                         CommissionProtocol.ballots_found_total.field.name:
                            [CommissionProtocol.ballots_found_outside.field.name,
                             CommissionProtocol.ballots_found_at_station.field.name]}



    def __init__(self, protocol_uik_data: pd.DataFrame, candidate_performance: pd.DataFrame, nominators, election_metadata: pd.DataFrame):
        self.protocol_uik_data = protocol_uik_data
        self.candidate_performance = candidate_performance
        self.nominators = nominators
        self.election_metadata = election_metadata

    def upload_to_database(self):
        engine = CommissionDataDownloader.create_sqlalchemy_engine()
        with engine.begin() as connection: # handles
            locked = self.try_to_lock_tables(connection)
            if locked:
                self.upload_nominators(connection)
                self.create_indices_manually()
                Election.objects.filter(name__in=self.election_metadata['name'].tolist()).delete()
                self.upload_df_to_database_on_model(self.election_metadata, Election, connection)
                self.upload_df_to_database_on_model(self.protocol_uik_data, CommissionProtocol, connection)
                self.upload_df_to_database_on_model(self.candidate_performance, CandidatePerformance, connection)
                connection.execute('SELECT pg_advisory_unlock(23)')

    def try_to_lock_tables(self, connection):
        for attempt in range(self.UPLOAD_RETRY_TIMES):
            locked = connection.execute('SELECT pg_try_advisory_lock(23)').fetchall()[0][0]
            if locked:
                return True
            else:
                time.sleep(self.UPLOAD_RETRY_INTERVAL_SECONDS)
            return False

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
        max_election_id = max_election_id if max_election_id else -1
        max_protocol_id = max_protocol_id if max_protocol_id else -1
        self.election_metadata[self.ID] = self.election_metadata[Election.election_url.field.name]
        self.protocol_uik_data[self.ID] = self.protocol_uik_data[CommissionProtocol.protocol_url.field.name]+ \
                                          self.protocol_uik_data['election_type']
        self.candidate_performance['protocol_id'] = self.candidate_performance['protocol_url'] + \
                                                    self.candidate_performance['election_type']
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
    def create_packages(cls,
                        election_data: pd.Series,
                        candidate_performance: dict,
                        candidate_data: dict,
                        results_data: dict):
        combined_protocols=[]
        combined_performance=[]
        combined_nominators=[]
        for election_result_type in results_data.keys():
            protocol_by_type = results_data[election_result_type]
            candidate_performance_by_type= candidate_performance[election_result_type]

            candidate_performance_by_type = pd.melt(candidate_performance_by_type, id_vars=['commission_name', 'protocol_url', 'path'],
                                            var_name=CandidatePerformance.name.field.name,
                                            value_name=CandidatePerformance.votes.field.name).dropna()
            protocol_by_type.loc[:, 'election_url'] = election_data['election_url']
            candidate_performance_by_type.loc[:, 'election_url'] = election_data['election_url']
            protocol_by_type.loc[:, 'election_type'] = election_result_type
            candidate_performance_by_type.loc[:, 'election_type'] = election_result_type
            performance_frame_size = candidate_performance_by_type.shape[0]
            if candidate_data:
                candidate_data_by_type = candidate_data[election_result_type]
                candidate_performance_by_type = pd.merge(candidate_performance_by_type, candidate_data_by_type, on='name', how='left')
                if performance_frame_size!=candidate_performance_by_type.shape[0]:
                    raise ValueError('Duplicate candidates found')
                combined_nominators.append(candidate_data_by_type.nominator.drop_duplicates())

            combined_protocols.append(protocol_by_type)
            combined_performance.append(candidate_performance_by_type)


        combined_protocols = pd.concat(combined_protocols, axis=0)
        combined_performance = pd.concat(combined_performance, axis=0)

        combined_nominators = pd.concat(combined_nominators).drop_duplicates() if combined_nominators else pd.Series()
        return ElectionDataPackage(protocol_uik_data= combined_protocols,
                                   candidate_performance= combined_performance,
                                   nominators = combined_nominators,
                                   election_metadata = election_data.to_frame().T)


    @classmethod
    def combine_packages(cls, list_of_packages):
        return ElectionDataPackage(
            protocol_uik_data= pd.concat([pack.protocol_uik_data for pack in list_of_packages], axis=0),
            candidate_performance=pd.concat([pack.candidate_performance for pack in list_of_packages], axis=0),
            nominators=pd.concat([pack.nominators for pack in list_of_packages], axis=0).drop_duplicates(),
            election_metadata=pd.concat([pack.election_metadata for pack in list_of_packages], axis=0)
            )

    @classmethod
    def add_protocol_items_if_missing(cls, ser):
        # add aggregate columns
        for total_item, included_items in cls.total_composition.items():
            if total_item not in ser.index:
               ser[total_item] = ser[ser.index & included_items].sum()
        # add other columns
        missing_cols = set(ProtocolRowValuesVerified.protocol_row_mapping.keys()).difference(ser.index.tolist())
        for item in missing_cols:
            ser[item] = 0


