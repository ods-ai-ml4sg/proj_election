import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elections_db.settings")
django.setup()

from ORM.models import CommissionProtocol
import ahocorasick

class ProtocolRowValues:




    protocol_row_guessing = {CommissionProtocol.amount_of_voters.field.name:
                                 {'present_any':['включен', 'внесен', 'включён']},
                             CommissionProtocol.invalid_ballots.field.name:
                                 {'present_any':['недействительн']},
                             CommissionProtocol.valid_ballots.field.name:
                                 {'present_any':['действительн']},
                             CommissionProtocol.ballots_received.field.name:
                                 {'present_any':['полученн']},
                             CommissionProtocol.ballots_given_out_early.field.name:
                                 {'present_any':['досрочно'],
                                  'absent_all': ['икмо', 'оик', 'территориальн', 'окружн', 'муниципальн', 'тик', 'в помещен']},
                             CommissionProtocol.ballots_given_out_early_at_superior_commission.field.name:
                                 {'present_any': ['икмо', 'оик', 'территориальн', 'окружн', 'муниципальн', 'тик']},
                             CommissionProtocol.ballots_given_out_at_stations.field.name:
                                 {'present_any': ['в помещ', 'в уик', 'на участ', ' на избир'],
                                  'present_all': ['выданн'],
                                  'absent_all': ['досрочно', ' вне ']},
                             CommissionProtocol.ballots_given_out_outside.field.name:
                                 {'present_any': ['вне помещен', 'вне уик', 'вне участ'],
                                  'absent_all': ['досрочно']},
                             CommissionProtocol.canceled_ballots.field.name:
                                 {'present_any': ['погаш']},
                             CommissionProtocol.ballots_found_outside.field.name:
                                 {'present_any': ['перенос']},
                             CommissionProtocol.ballots_found_at_station.field.name:
                                 {'present_any': ['стационар']},
                             CommissionProtocol.lost_ballots.field.name:
                                 {'present_any': ['утрач', 'утрат']},
                             CommissionProtocol.appeared_ballots.field.name:
                                 {'present_any': ['не учтен', 'неучтен', 'неучтён', 'не учтён']}
                             }


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
                                 "число бюллетеней, полученных участковыми избирательными комиссиями'"
                                 },
                            CommissionProtocol.ballots_given_out_early.field.name:
                                {"Число избирательных бюллетеней, выданных избирателям, проголосовавшим досрочно",
                                 "число бюллетеней, выданных избирателям, проголосовавшим досрочно",
                                 "число бюллетеней, выданных избирателям, проголосовавшим досрочно, в том числе",
                                 "число бюллетеней, выданных избирателям, проголосовавшим досрочно, в том числе:",
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
                                 "в помещении территориальной избирательной комиссии", #"число бюллетеней, выданных избирателям, проголосовавшим досрочно, в том числе:"
                                 },
                            CommissionProtocol.ballots_given_out_early_far_away.field.name:
                                {"в труднодоступных или отдаленных местностях" #число бюллетеней, выданных избирателям, проголосовавшим досрочно, в том числе
                                 },
                            CommissionProtocol.ballots_given_out_early_at_uik.field.name:
                                {"в помещениях участковых избирательных комиссий", # число бюллетеней, выданных избирателям, проголосовавшим досрочно, в том числе
                                 "число избирательных бюллетеней, выданных избирателям проголосовавшим досрочно в помещении избирательной комиссии"
                                 },
                            CommissionProtocol.ballots_given_out_at_stations.field.name:
                                {"Число бюллетеней, выданных в помещении в день голосования",
                                 "число бюллетеней, выданных в помещении для голосования",
                                 "число бюллетеней, выданных избирателям в помещении для голосования в день голосования",
                                 "Число избирательных бюллетеней, выданных избирателям, в помещении для голосования в день голосования",
                                 "число бюллетеней, выданных избирателям в помещениях для голосования",
                                 "число бюллетеней, выданных в помещении для голосования в день голосования",
                                 "число избирательных бюллетеней, выданных в помещении для голосования в день голосования"
                                 "число бюллетеней, выданных в уик",
                                 "число избирательных бюллетеней, выданных избирателям в помещении для голосования в день голосования",
                                 "число бюллетеней, выданных участковой комиссией в помещении",
                                 "число бюллетеней, выданных избирателям, участникам референдума в помещении для голосования в день голосования",
                                 "число бюллетеней, выданных участникам референдума в помещении для голосования в день голосования",
                                 "число избирательных бюллетеней, выданных в помещении для голосования в день голосования",
                                 "число бюллетеней, выданных избирателям в помещениях для голосования в день голосования"
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
                                 "число бюллетеней, выданных вне помещения для голосования в день голосов",
                                 "число бюллетеней, выданных вне помещения для голосования",
                                 "число бюллетеней, выданных избирателям, проголосовавшим вне помещения для голосования в день голосования"
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
                                 "число бюллетеней, содерж. в стационарных ящиках",
                                 "число бюллетеней в стационарных ящиках"
                                 },
                            CommissionProtocol.lost_ballots.field.name:
                                {"Число утраченных избирательных бюллетеней",
                                 "число утраченных бюллетеней",
                                 "число бюллетеней по актам об утрате",
                                 "число утреченных бюллетеней"
                                 },
                            CommissionProtocol.appeared_ballots.field.name:
                                {"Число не учтенных при получении бюллетеней",
                                 "Число бюллетеней, не учтенных при получении",
                                 "число избирательных бюллетеней, не учтенных при получении",
                                 "число бюллетеней по актам об избытке"
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

    protocol_row_mapping_reversed_with_candidates = {alias.lower():database_column for database_column, list_of_values in
                                                     protocol_row_mapping_with_t_candidates.items() for alias in list_of_values}

    protocol_row_mapping_reversed = {alias.lower():database_column for database_column, list_of_values in
                                     protocol_row_mapping.items() for alias in list_of_values}


    auto = ahocorasick.Automaton()
    for key in protocol_row_mapping_reversed.keys():
        auto.add_word(key, key)
    auto.make_automaton()

    @classmethod
    def verify_mapping(cls):
        for correct_mapping, set_of_variations in cls.protocol_row_mapping.items():
            for variation in set_of_variations:
                guessed_mapping = cls.guess_mapping(variation)
                if guessed_mapping:
                    if guessed_mapping.lower()!=correct_mapping.lower():
                        raise AssertionError('Fault in row name guesser')


    @classmethod
    def guess_mapping(cls, string_to_guess):
        for mapping, rules in cls.protocol_row_guessing.items():
            if 'present_any' in rules:
                present = [rule for rule in rules['present_any'] if rule in string_to_guess.lower()]
                if not present:
                    continue
            if 'absent_all' in rules:
                present = [rule for rule in rules['absent_all'] if rule in string_to_guess.lower()]
                if present:
                    continue
            if 'present_all' in rules:
                present = [rule for rule in rules['present_all'] if rule in string_to_guess.lower()]
                if len(rules['present_all'])!=len(present):
                    continue
            return mapping
        return None

    @classmethod
    def get_rename_dict_and_unmapped_rows(cls, list_of_row_names):
        renamer = {}
        unmapped_rows = set()
        for current_row_name in list_of_row_names:
            if current_row_name.lower() in cls.protocol_row_mapping_reversed_with_candidates:
                renamer[current_row_name] = cls.protocol_row_mapping_reversed_with_candidates[current_row_name]
            else:
                guessed = cls.guess_mapping(current_row_name)
                if guessed:
                    renamer[current_row_name] = guessed
                else:
                    unmapped_rows.add(current_row_name.lower())
        if len(set(renamer.values()))!=len(renamer.keys()):
            raise AssertionError
        return renamer, unmapped_rows


class ProtocolRowValuesVerified(ProtocolRowValues):
    ProtocolRowValues.verify_mapping()