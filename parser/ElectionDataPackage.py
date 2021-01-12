import os
from collections import namedtuple

import django
import pandas as pd
import numpy as np
from django.db.models import Max, Field, ForeignKey
from django_pandas.io import read_frame

from DataLoad.CommissionDataDownloader import CommissionDataDownloader

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elections_db.settings")
django.setup()

from ORM.models import Election, CommissionProtocol, CandidatePerformance, Nominator


class ElectionDataPackage:

    '''
    This class collects and handles all data that's related to a set of elections
    '''

    ID='id'

    protocol_row_mapping = {CommissionProtocol.amount_of_voters.field.name: 
                                {"Число участников голосования, включенных в список участников голосования на момент окончания голосования",
                                 "число избирателей, внесенных в списки на момент окончания голосования",
                                 "Число избирателей, внесенных в список на момент окончания голосования",
                                 "Число избирателей, включенных в список",
                                 "число избирателей, внесенных в список избирателей на момент окончания голосования",
                                 "число избирателей, внесенных в список",
                                 "число избирателей, участников референдума, внесенных в список на момент окончания голосования",
                                 "число избирателей, включенных в список избирателей на момент окончания голосования,",
                                 "число участников референдума, внесенных в список на момент окончания голосования"
                                 },
                            CommissionProtocol.ballots_given_out_total.field.name:
                                {"Число бюллетеней, выданных участникам голосования"
                                 },
                            CommissionProtocol.ballots_found_total.field.name:
                                {"Число бюллетеней, содержащихся в ящиках для голосования"
                                 },
                            CommissionProtocol.invalid_ballots.field.name:
                                {"Число недействительных бюллетеней",
                                 "число недействительных избирательных бюллетеней",
                                 "общее число недействительных бюллетеней"
                                 },
                            CommissionProtocol.valid_ballots.field.name:
                                {"Число действительных бюллетеней",
                                 "Число действительных избирательных бюллетеней"
                                 },
                            CommissionProtocol.ballots_received.field.name:
                                {"Число бюллетеней, полученных УИК",
                                 "число бюллетеней, полученных участковой избирательной комиссией",
                                 "Число избирательных бюллетеней, полученных участковой комиссией",
                                 "число бюллетеней, полученных участковыми комиссиями",
                                 "число избирательных бюллетеней, полученных участковой избирательной комиссией",
                                 "число бюллетеней, полученных участковой комиссией",
                                 },
                            CommissionProtocol.ballots_given_out_early.field.name:
                                {"Число избирательных бюллетеней, выданных избирателям, проголосовавшим досрочно",
                                 "число бюллетеней, выданных избирателям, проголосовавшим досрочно",
                                 "число бюллетеней, выданных избирателям, проголосовавшим досрочно, в том числе",
                                 "число бюллетеней, выданных досрочно, в том числе:",
                                 "число бюллетеней, выданных избирателям, участникам референдума, проголосовавшим досрочно, в том числе отдельной строкой",
                                 "число бюллетеней, выданных участникам референдума, проголосовавшим досрочно"
                                 },
                            CommissionProtocol.ballots_given_out_early_at_superior_commission.field.name:
                                {"Число бюллетеней, проголосовавшим досрочно в ИКМО, ОИК",
                                 "Число избирательных бюллетеней, выданных избирателям, проголосовавшим досрочно, в помещении территориальной избирательной комиссии",
                                 "число бюллетеней, выданных избирателям, проголосовавшим досрочно в помещении территориальной избирательной комиссии",
                                 "в помещении тик", # число бюллетеней, выданных досрочно, в том числе:
                                 "в том числе в помещении муниципиальной (территориальной) комиссии", # Число избирательных бюллетеней, выданных избирателям, проголосовавшим досрочно
                                 "проголосовавшим в помещении территориальной (окружной) комиссии, избирательной комиссии муниципального образования", # число бюллетеней, выданных избирателям, участникам референдума, проголосовавшим досрочно, в том числе отдельной строкой
                                 "в том числе в помещении территориальной (окружной) комиссии, комиссии муниципального образования", # Число бюллетеней, выданных избирателям, проголосовавшим досрочно
                                 "в том числе в помещении муниципальной (окружной) комиссии", #Число бюллетеней, выданных избирателям, проголосовавшим досрочно
                                 "в том числе в помещении избирательной комиссии муниципального образования", #	Число избирательных бюллетеней, выданных избирателям, проголосовавшим досрочно
                                 },
                            CommissionProtocol.ballots_given_out_early_far_away.field.name:
                                {"в труднодоступных или отдаленных местностях" #число бюллетеней, выданных избирателям, проголосовавшим досрочно, в том числе
                                 },
                            CommissionProtocol.ballots_given_out_early_at_uik.field.name:
                                {"в помещениях участковых избирательных комиссий", # число бюллетеней, выданных избирателям, проголосовавшим досрочно, в том числе
                                 },
                            CommissionProtocol.ballots_given_out_at_stations.field.name:
                                {"Число бюллетеней, выданных в помещении в день голосования",
                                 "число бюллетеней, выданных избирателям в помещении для голосования в день голосования",
                                 "Число избирательных бюллетеней, выданных избирателям, в помещении для голосования в день голосования",
                                 "число бюллетеней, выданных избирателям в помещениях для голосования",
                                 "число бюллетеней, выданных в помещении для голосования в день голосования",
                                 "число избирательных бюллетеней, выданных в помещении для голосования в день голосования"
                                 "число бюллетеней, выданных в уик",
                                 "число избирательных бюллетеней, выданных избирателям в помещении для голосования в день голосования",
                                 "число бюллетеней, выданных участковой комиссией в помещении",
                                 "число бюллетеней, выданных избирателям, участникам референдума в помещении для голосования в день голосования",
                                 "число бюллетеней, выданных участникам референдума в помещении для голосования в день голосования"
                                 },
                            CommissionProtocol.ballots_given_out_outside.field.name:
                                {"Число бюллетеней, выданных вне помещения в день голосования",
                                 "число бюллетеней, выданных избирателям, проголосовавшим вне помещения для голосования",
                                 "Число избирательных бюллетеней, выданных избирателям, проголосовавшим вне помещения для голосования",
                                 "число избирательных бюллетеней, выданных вне помещения для голосования в день голосования",
                                 "число бюллетеней, выданных избирателям, проголосовавшим вне помещения для голосования в день голосов",
                                 "число избирательных бюллетеней, выданных избирателям, проголосовавшим вне помещения для голосования в день голосования",
                                 "число бюллетеней, выданных избирателям, участникам референдума, проголосовавшим вне помещения для голосования",
                                 "число бюллетеней, выданных избирателям, проголосовавшим вне помещений для голосования",
                                 "число бюллетеней, выданных участникам референдума, проголосовавшим вне помещения для голосования в день голосования",
                                 "число бюллетеней, выданных вне уик",
                                 "число бюллетеней, выданных избирателям вне помещения",
                                 "число бюллетеней, выданных вне помещения для голосования в день голосов"
                                 },
                            CommissionProtocol.canceled_ballots.field.name:
                                {"Число погашенных избирательных бюллетеней",
                                 "число погашенных бюллетеней"
                                 },
                            CommissionProtocol.ballots_found_outside.field.name:
                                {"Число бюллетеней, содержащихся в переносных ящиках",
                                 "Число избирательных бюллетеней, содержащихся в переносных ящиках для голосования",
                                 "число бюллетеней, содержащихся в переносных ящиках для голосования",
                                 "число бюллетеней, содерж. в переносных ящиках"
                                 },
                            CommissionProtocol.ballots_found_at_station.field.name:
                                {"Число бюллетеней, содержащихся в стационарных ящиках",
                                 "Число избирательных бюллетеней, содержащихся в стационарных ящиках для голосования",
                                 "число бюллетеней, содержащихся в стационарных ящиках для голосования",
                                 "число бюллетеней, содерж. в стационарных ящиках"
                                 },
                            CommissionProtocol.lost_ballots.field.name:
                                {"Число утраченных избирательных бюллетеней",
                                 "число утраченных бюллетеней",
                                 "число бюллетеней по актам об утрате"
                                 },
                            CommissionProtocol.appeared_ballots.field.name:
                                {"Число не учтенных при получении бюллетеней",
                                 "Число бюллетеней, не учтенных при получении",
                                 "число избирательных бюллетеней, не учтенных при получении"
                                 },
                            }

    candidates_technical = {"Against":
                                {'против',
                                 "нет"},
                            "For":
                                {"за",
                                 "да"}
                            }

    candidates_technical_values = [inner for outer in candidates_technical.values() for inner in outer]

    protocol_row_mapping_with_t_candidates = z = {**protocol_row_mapping, **candidates_technical}

    protocol_row_mapping_reversed = {alias.lower():database_column for database_column, list_of_values in
                                     protocol_row_mapping_with_t_candidates.items() for alias in list_of_values}


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
        self.connection = engine.connect()
        locked = self.connection.execute('SELECT pg_try_advisory_lock(23)').fetchall()[0][0]

        self.upload_nominators()

        self.create_indices_manually()
        Election.objects.filter(name__in=self.election_metadata['name'].tolist()).delete()
        self.upload_df_to_database_on_model(self.election_metadata, Election)
        self.upload_df_to_database_on_model(self.protocol_uik_data, CommissionProtocol)
        self.upload_df_to_database_on_model(self.candidate_performance, CandidatePerformance)
        self.connection.execute('SELECT pg_advisory_unlock(23)')

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
        self.protocol_uik_data[self.ID] = self.protocol_uik_data[CommissionProtocol.protocol_url.field.name]
        self.candidate_performance['commission_id'] = self.candidate_performance['protocol_url']
        self.candidate_performance['election_id'] = self.candidate_performance['election_url']
        self.protocol_uik_data['election_id'] = self.protocol_uik_data['election_url']

        self.candidate_performance = CommissionDataDownloader._repalace_old_index_with_new(nominator_frame, self.candidate_performance,
                                                                                'nominator')

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
                                                                                           'commission_id')
        self.candidate_performance = CommissionDataDownloader._repalace_old_index_with_new(election_index,
                                                                                           self.candidate_performance,
                                                                                           'election_id')


    def upload_df_to_database_on_model(self, df, model):
        model_fields = set(self.get_field_names(model))
        if self.ID not in df.columns:
            model_fields.discard(self.ID)
        for field in model_fields.difference(df.columns):
            df[field] = np.nan
        df[model_fields].to_sql(model.objects.model._meta.db_table,
                                if_exists='append', index=False, con=self.connection, method='multi', chunksize=1000)


    def upload_nominators(self):
        CommissionDataDownloader.update_nominators(self.nominators, self.connection)


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
            candidate_data_by_type = candidate_data[election_result_type]

            candidate_performance_by_type = pd.melt(candidate_performance_by_type, id_vars=['commission', 'protocol_url'],
                                            var_name=CandidatePerformance.name.field.name,
                                            value_name=CandidatePerformance.votes.field.name).dropna()
            protocol_by_type.loc[:, 'election_url'] = election_data['election_url']
            candidate_performance_by_type.loc[:, 'election_url'] = election_data['election_url']
            protocol_by_type.loc[:, 'election_type'] = election_result_type
            candidate_performance_by_type.loc[:, 'election_type'] = election_result_type
            performance_frame_size = candidate_performance_by_type.shape[0]
            candidate_performance_by_type = pd.merge(candidate_performance_by_type, candidate_data_by_type, on='name', how='left')
            if performance_frame_size!=candidate_performance_by_type.shape[0]:
                raise ValueError('Duplicate candidates found')
            combined_protocols.append(protocol_by_type)
            combined_performance.append(candidate_performance_by_type)
            combined_nominators.append(candidate_data_by_type.nominator.drop_duplicates())
        combined_protocols = pd.concat(combined_protocols, axis=0)
        combined_performance = pd.concat(combined_performance, axis=0)
        combined_nominators = pd.concat(combined_nominators).drop_duplicates()
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
        missing_cols = set(cls.protocol_row_mapping.keys()).difference(ser.index.tolist())
        for item in missing_cols:
            ser[item] = 0


