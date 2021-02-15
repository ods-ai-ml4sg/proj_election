from datetime import date
import requests as r
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
import re

CIK_LIST_URL="http://www.vybory.izbirkom.ru/region/izbirkom"

HEADERS="""Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9
Accept-Encoding: gzip, deflate
Accept-Language: en-US,en;q=0.9,ru;q=0.8,fr;q=0.7
Cache-Control: no-cache
Connection: keep-alive
Content-Length: 152
Content-Type: application/x-www-form-urlencoded
Cookie: __utmc=252441553; __utmz=252441553.1607361652.1.1.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided); izbSession=fa90d86f-6f89-4877-b62d-aadc79fe48f9; __utma=252441553.205305655.1607361652.1607361652.1607636441.2; __utmt=1; JSESSIONID=e9d818ee7ceb67a6f1733013b352; __utmb=252441553.2.10.1607636441
DNT: 1
Host: www.vybory.izbirkom.ru
Origin: http://www.vybory.izbirkom.ru
Pragma: no-cache
Referer: http://www.vybory.izbirkom.ru/region/izbirkom
Upgrade-Insecure-Requests: 1
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36 OPR/71.0.3770.441"""

HEADERS=dict(i.split(': ') for i in HEADERS.split("\n"))
DATA_STRING="""start_date={start_date}&urovproved=1&urovproved=2&vidvibref=all&vibtype=all&end_date={end_date}&sxemavib=all&action=search_by_calendar&region=0&ok=%C8%F1%EA%E0%F2%FC"""
REQUEST_DATE_FORMAT = "%d.%m.%Y"

MONTHS={
    'февраля':2,
    'марта':3,
    'апреля':4,
    'мая':5,
    'июня':6,
    'июля':7,
    'августа':8,
    'сентября':9,
    'октября':10,
    'ноября':11,
    'декабря':12,
    'января':1}

def get_upper_level_links(start_date:date, end_date:date, headers=HEADERS, url=CIK_LIST_URL):

    resp=r.post(url, headers=headers, data=DATA_STRING.format(start_date=start_date.strftime(REQUEST_DATE_FORMAT),
                                                              end_date=end_date.strftime(REQUEST_DATE_FORMAT)))

    soup=BeautifulSoup(resp.content, features="lxml")

    total_number_of_entries=int(soup.select("form+table nobr")[0].text.split(": ")[1])
    print("Total number of entries is:",total_number_of_entries)

    table=soup.select("form+table+table")[0]

    dates=[i for i,j in enumerate(table.select('tr')) if j.has_attr("bgcolor")]

    dct={}
    for i,j in enumerate(table.select('tr')):
        #if current line is a date, create a new entry in dct
        if i in dates:
            current=j.text.strip()
            dct[current]=[]
        else: #add the data into current entry
            dct[current].append(j)

    df = pd.concat(list(map(create_df_from_soup_by_date, dct.items())), ignore_index=True)

    df[['vrn', 'region', 'prver']] = df[['vrn', 'region', 'prver']].astype(int)
    df[['day', 'month', 'year']] = df.election_date.str.split(expand=True).loc[:, :2]

    df.month = df.month.map(MONTHS)
    df.election_date = [date(int(year), month, int(day)) for year, month, day in zip(df.year, df.month, df.day)]
    df['loc2'] = df['loc2'].replace("", None).fillna(method = 'ffill')
    assert(total_number_of_entries==df.shape[0])

    return df

def create_df_from_soup_by_date(soup):
    y, x = soup
    ddct = []
    for i in x:
        # if no tag is present, the region is the same as in previous entry
        if i.select('nobr'):
            location = i.select('nobr b')[0].text.strip()

        loc2, topic = i.select('td')
        loc2 = loc2.text.split(location)[-1].strip()

        text = topic.text
        link = topic.select('a')[0].get('href')

        ddct.append({
            'loc1': location,
            'loc2': loc2,
            'name': text,
            'election_url': link,
            'vrn': re.findall('vrn=(.*?)&', link)[0],
            'region': re.findall('region=(.*?)&', link)[0],
            'prver': re.findall('prver=(.*?)&', link)[0],
            'pronetvd': re.findall('pronetvd=(.*)', link)[0]
        })

    return pd.DataFrame(ddct).assign(election_date=y)

if __name__ == '__main__':
    df= get_upper_level_links(date(2010,1,1), date(2021,1,1), headers=HEADERS, url=CIK_LIST_URL)
