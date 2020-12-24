import pandas as pd
import numpy as np
import os
import pathlib

def table_to_data(table_df):
    table_df = table_df.dropna()
    result = pd.DataFrame(index=[0])
    for i, row in table_df.iterrows():
        result[row[1].strip()] = int(row[2])
    return result

def xls_to_csv(file_path):
    xls = pd.read_excel(file_path)
    df = pd.DataFrame(index=[0])

    for i, row in xls.iterrows():
        if pd.isna(row[0]) == True:
            continue
        elif row[0] == 1:
            table = xls.loc[i:]
            table = table_to_data(table)
            df = df.join(table)
        elif ('Дата голосования' in str(row[0])) == True:
            date = row[0][row[0].rfind(': ')+1:]
            df['date'] = date.strip()
        elif ('УИК' in str(row[0])) == True:
            uik = row[0][row[0].rfind(': ')+1:]
            df['uik'] = uik.strip()

    return df

    # else:
    #     df.loc[df.index[0], 'notes' == 'check_header']
    #     try:
    #         df = xls_iterator(xls)
    #         df.loc[df.index[0], 'notes' == 'check_header']
    #         return df
    #     except:
    #         return df

def main(report_path):
    df_full = pd.DataFrame()
    for root, dirs, files in os.walk(report_path):
        for name in files:
            xls_path = root + name
            report_csv = xls_to_csv(xls_path)
            df_full = pd.concat([df_full, report_csv])
    return df_full

if __name__ == '__main__':
    report_path = './reports/'
    # columns = ['level_1_ik', 'level_2_ik', 'uik',
    #            'total_participant', 'ballot_issued', 'ballot_find', 'ballot_invalid',
    #            'yes', 'no',
    #            'date', 'notes']
    final = main(report_path)
    final.to_csv('./xls_to_csv/result.csv', index=False)