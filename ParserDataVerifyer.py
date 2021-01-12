'''
making sure the parsed data matches external data for constitution vote
'''


import pandas as pd

old_data = pd.read_csv('results_external.txt', sep='\t').drop(['name', 'url'], axis=1)
parsed_data = pd.read_csv('data_01_07_2020_constitution_voting.csv').drop(['URL субъекта федерации', 'URL ТИКА'], axis=1)

rename_columns = {'Число участников голосования, включенных в список участников голосования на момент окончания голосования':'amount_of_voters',
                  'Число бюллетеней, выданных участникам голосования':'ballots_given_out_total',
                  'Число бюллетеней, содержащихся в ящиках для голосования':'valid_ballots',
                  'Число недействительных бюллетеней':'invalid_ballots',
                  'Субъект федерации':'reg',
                  'Избирательная комиссия':'uik',
                  'ТИК':' tik'}

similar_latin_cyrillic = {'\u0043': '\u0421', #C
                          '\u0063': '\u0441', #c
                          '\u0041': '\u0410', #A
                          '\u0061': '\u0430', #a
                          '\u004F': '\u041E', #O
                          '\u006F': '\u043E', #o
                          '\u004B': '\u041A', #K
                          '\u0058': '\u0425', #X
                          '\u0078': '\u0445', #x
                          '\u0045': '\u0415', #E
                          '\u0065': '\u0435', #e
                          '\u0048': '\u041D', #H
                          '\u0050': '\u0420', #P
                          '\u0042': '\u0412', #B
                          '\u004D': '\u041C', #M
                          '\u0079': '\u0443', #y
                          '\u0054': '\u0422'  #T
                          }

old_data = old_data.rename(columns=rename_columns)
parsed_data = parsed_data.rename(columns=rename_columns)
parsed_data.columns = [a.strip() for a in parsed_data.columns]

for df in [parsed_data, old_data]:
    df['tik'] = df['tik'].replace(similar_latin_cyrillic, regex=True)
    df['tik'] = df['tik'].str.replace("ТИК", "")
    df['reg'] = df['reg'].str.strip()
    df['tik'] = df['tik'].str.strip()

old_data['tik'] = old_data['tik'].str.replace(r'\A\d* *', "")

compare = pd.merge(old_data, parsed_data, on = ['reg', 'tik', 'uik'], suffixes=['_old', '_parsed'], how = 'outer')

# Отсутствующие ТИК
print(set(parsed_data.tik).symmetric_difference(set(old_data.tik)))
print(set(old_data.tik).difference(set(parsed_data.tik)))

compare = compare.dropna()

cols_to_check = ['amount_of_voters', 'ballots_given_out_total', 'valid_ballots', 'invalid_ballots', "ДА", "НЕТ"]
for check_col in cols_to_check:
    colname = check_col + "_diff"
    compare[colname] = compare[check_col + "_old"] - compare[check_col + "_parsed"]
    print((compare[colname] != 0).sum())

problems = compare[(compare[[a+'_diff' for a in cols_to_check]]!=0).any(axis=1)]

