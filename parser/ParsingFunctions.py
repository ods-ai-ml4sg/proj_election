import copy
import multiprocessing
import pathlib

import os
import sys
import traceback
import numpy as np

import django

from DataFormatting import DataFormatting

from WalkDownResult import WalkDownResult

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elections_db.settings")
django.setup()
from bs4 import BeautifulSoup
import pandas as pd
import os
from PIL import Image
import time
import pytesseract
from typing import BinaryIO, List, Dict
from io import BytesIO
from selenium.common.exceptions import NoSuchElementException, InvalidArgumentException, WebDriverException
import re
from enums import CandidateListType
from ProtocolRowMapping import ProtocolRowValues

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

SLEEP_TIME = 0.1

"сайт избирательной комиссии субъекта Российской Федерации"

endings = {'results':{CandidateListType.COMMON.name: ['232',
                                                      '234',
                                                      '226',
                                                      '228',
                                                      '242',
                                                      '425',
                                                      '457'
                                                        ],
                      CandidateListType.SPECIFIC.name: ['426',
                                                        '423',
                                                        '463'
                                                        ]
                      },
           'candidates':{CandidateListType.COMMON.name: ["221",
                                                         "220&report_mode=1"
                                                        ],
                         CandidateListType.SPECIFIC.name:["220"
                                                          ]},
           'summary': {CandidateListType.COMMON.name:['465',
                                                      '227',
                                                      '381',
                                                      '379',
                                                      '222',
                                                      '380',
                                                      '458',
                                                      '233'
                                                        ],
                       CandidateListType.SPECIFIC.name: ['464',
                                                         '427',
                                                         # #???
                                                         ]
                       }}


TYPE = 'type='

def init_driver(headless=True):
    '''
    creates webdriver object and global path for candidate excel files download; global variables are used to allow
    multiprocessing implementation
    :param headless: run webdriver in headless mode for better speed and smoother background execution
    :return: returns driver object for convenience, but it is created as global object anyway
    '''
    global download_dir, driver
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--enable-javascript")
    current = multiprocessing.current_process()
    download_dir = pathlib.Path(os.getcwd(), 'downloads', current.name)
    prefs = {"download.default_directory": str(download_dir)}
    chrome_options.add_experimental_option("prefs", prefs)
    os.makedirs(download_dir, exist_ok=True)
    driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)
    return driver

def parse_single_election(election_series):
    global driver, download_dir
    # TODO: no total to check against
    try:
        url = election_series.election_url

        driver.get(url)
        get_through_captcha(driver)

        links = [element.get_attribute("href") for element in driver.find_elements_by_xpath("//a[@href]")]
        summary_links = {'SPECIFIC': find_specific_link(links),
                         'COMMON': find_common_link(links)}
        election_output = WalkDownResult.create_empty()
        for k, v in summary_links.items():
            if v:
                election_output.add(walk_down_from_url_and_collect_uik_results(v, driver, []), add_type=k)

        candidates = get_candidates_df(url, driver, download_dir)

        return election_output, candidates, election_series
    except Exception as e:
        try:
            exc_info = sys.exc_info()
        finally:
            traceback.print_exception(*exc_info)
            print(driver.current_url)
            del exc_info


def detect_captcha_text(image: BinaryIO) -> str:
    stream = BytesIO(image)
    image_rgb = Image.open(stream).convert("RGBA")
    stream.close()
    gray_image = image_rgb.convert("L")

    text_image = pytesseract.image_to_string(gray_image,
                                             config='--psm 7 -c tessedit_char_whitelist=0123456789')
    text_image=re.sub('[\W]', '', text_image)

    if len(text_image) !=5:
        text_image = '00000'

    return text_image

def find_and_recognize_captcha(driver) -> Dict:
    captcha_png = driver.find_element_by_id("captchaImg").screenshot_as_png
    captcha_text = detect_captcha_text(captcha_png).replace("o", "0")
    captcha_input_field = driver.find_element_by_id("captcha")
    return {"captcha_input_field": captcha_input_field, "captcha_text": captcha_text}


def get_through_captcha(driver):
    flag = 1
    while flag:
        try:
            driver.find_element_by_xpath("//table")
            flag = 0
        except NoSuchElementException:
            try:
                captcha_elements = find_and_recognize_captcha(driver)
                captcha_input_field = captcha_elements["captcha_input_field"]
                captcha_text = captcha_elements["captcha_text"]
                captcha_input_field.send_keys(captcha_text)
                driver.find_element_by_id("send").click()
                time.sleep(SLEEP_TIME)
            except WebDriverException:
                pass

def walk_down_from_url_and_collect_uik_results(url, driver, path):

    if driver.current_url!=url:
        driver.get(url)

    try_to_switch_to_local(driver)
    current_level_result = WalkDownResult.create_empty()

    total_table, data_table, commission_name, clickable_links, dropdown_links, is_final = dissect_page(driver)
    path_copy = copy.deepcopy(path)
    path_copy.append(commission_name)

    if type(data_table)==pd.DataFrame:
        current_level_result.add(DataFormatting.prettify_election_dfs(data_table, driver.current_url, path_copy))

    if not is_final:
        if clickable_links:
            for link in clickable_links.values():
                current_level_result.add(walk_down_from_url_and_collect_uik_results(link, driver, path_copy))
        elif dropdown_links:
            for link in dropdown_links.values():
                current_level_result.add(walk_down_from_url_and_collect_uik_results(link, driver, path_copy))

    if type(total_table)==pd.DataFrame:
        total_result = DataFormatting.prettify_election_dfs(total_table, driver.current_url, path_copy)
        compare_result = total_result.compare_totals(current_level_result)
        if bool(compare_result) is False:
            current_level_result.add_compare_errors(driver.current_url)

    return current_level_result

def try_to_switch_to_local(driver):
    local_button_url = get_local_button_url(driver)
    if local_button_url:
        driver.get(local_button_url)
    else:
        current_url = driver.current_url
        region_part = re.search('&region=\d+&|$', current_url).group()
        subregion_part = re.search('&sub_region=\d+&|$', current_url).group()
        region_number = re.search('\d+|$', region_part).group()
        subregion_number = re.search('\d+|$', subregion_part).group()
        if region_part and subregion_part and region_number!="0" and subregion_number=="0":
            new_url = re.sub("&sub_region=0", "&sub_region="+region_number, current_url)
            driver.get(new_url)
            get_through_captcha(driver)



def dissect_page(driver):
    total_table = data_table = None
    is_final=False
    clickable_links, dropdown_links = {}, {}
    soup = BeautifulSoup(driver.page_source, features="lxml")
    tables = soup.findAll('table')
    commission_name = get_commission_name(tables)
    tables_with_protocol_data = find_tables_with_protocol_data_ahocorasick(tables)
    table_two_parts = find_nested_table_of_size_2(tables_with_protocol_data)
    if table_two_parts:
        clickable_links = get_clickable_links_from_table(table_two_parts)
        if clickable_links:
            is_final = check_if_data_table_is_final(clickable_links)
            if is_final:
                clickable_links = {}
    dropdown_links = get_dropdown_links(driver)
    if table_two_parts:
        total_table = tab_to_df(table_two_parts.findAll('table')[0])
        total_table = set_df_columns_summary(total_table)
        data_table = tab_to_df(table_two_parts.findAll('table')[1])
        if type(data_table)==pd.DataFrame:
            data_table = pd.concat([total_table.iloc[:, :-1], data_table], axis=1)
            data_table = remove_clickable_links_columns(data_table, clickable_links)
            if type(data_table)==pd.DataFrame:
                data_table = set_df_columns_summary(data_table)
    elif (len(tables_with_protocol_data)>0) and (len(dropdown_links)==0):
        tab = find_smallest_table(tables_with_protocol_data)
        data_table = tab_to_df(tab)
        data_table = set_df_columns_nonsummary(data_table, commission_name)

    return total_table, data_table, commission_name, clickable_links, dropdown_links, is_final

def set_df_columns_summary(df):
    first_row = df.iloc[0]
    if type(first_row.iloc[2])!=str:
        raise ValueError('bad df structure')
    df.columns = ['code', 'row_name', *first_row.iloc[2:].values]
    return df.iloc[1:]

def set_df_columns_nonsummary(df, commission_name):
    if len(df.columns)!=3:
        raise ValueError('bad df structure')
    df.columns = ['code', 'row_name', commission_name]
    return df

def remove_clickable_links_columns(data_table, clickable_links):
    first_row = data_table.iloc[0].values
    retain = []
    for i, val in enumerate(first_row):
        if val not in clickable_links.keys():
            retain.append(i)
    data_table = data_table.iloc[:, retain]
    if len(data_table.columns)>2:
        return data_table
    else:
        return None

def get_commission_name(table_list):
    commission_name_tables = [t for t in table_list if 'наименование' in t.text.lower() if len(t.findAll('table')) == 0]
    try:
        if len(commission_name_tables)==1:
            return tab_to_df(commission_name_tables[0]).dropna().iat[0,1]
        else:
            return None
    except IndexError: # empty commission_name
        return get_commission_name_fallback(table_list)

def get_commission_name_fallback(table_list):
    table_with_name = [t for t in table_list if 'версия для печати' in t.text.lower()][0]
    first_element = table_with_name.find_all('td')[0]
    return first_element.findAll('a')[-1].text

def find_tables_with_protocol_data(table_list):
    return [t for t in table_list if any((r in t.text.lower() for r in ProtocolRowValues.protocol_row_mapping_reversed.keys()))]

def find_tables_with_protocol_data_ahocorasick(table_list):
    return [t for t in table_list if any((e,f) for e,f in ProtocolRowValues.auto.iter(t.text.lower()))]

def find_smallest_table(table_list):
    sizes = [len(table.text) for table in table_list]
    return table_list[np.argmin(sizes)]

def find_nested_table_of_size_2(table_list):
    nested = [t for t in table_list if len(t.findAll('table')) == 2]
    if len(nested)==1:
        return nested[0]
    else:
        return None

def tab_to_df(table):
    try:
        return pd.read_html(str(table))[0].replace('\u200b', np.nan).dropna(axis=1, how='all')
    except ValueError:
        return None

def get_clickable_links_from_table(table):
    return {link.text.strip():link.get('href') for link in table.findAll('a')}

def check_if_data_table_is_final(clickable_links):
    return len([link for link in clickable_links.keys() if 'уик' in link.lower()])>0

def get_dropdown_links(driver):
    options = BeautifulSoup(driver.page_source, features="lxml").select('option[value]')
    if options:
        return {option.text:option.get('value') for option in options}
    else:
        return {}

def get_summary_table(driver):
    table_result = str(BeautifulSoup(driver.page_source, features="lxml").select('table:nth-of-type(5)'))
    if table_result == '[]':
        return None
    else:
        try:
            return pd.read_html(table_result)[0]
        except ValueError as e:  # edge case: cancelled elections
            print(e)
            return None

def get_local_button_url(driver):
    link_to_lower_data = get_element_if_present("/html/body/table[2]/tbody/tr[2]/td/a", driver)
    if link_to_lower_data:
        return link_to_lower_data.get_attribute("href")
    else:
        return None

def find_common_link(links):
    summary_links = search_for_endings(links, [TYPE + ending for ending in endings['summary']['COMMON']])
    if summary_links:
        return summary_links
    else:
        result_links = search_for_endings(links, [TYPE + ending for ending in endings['results']['COMMON']])
        return result_links

def find_specific_link(links):
    return search_for_endings(links, [TYPE + ending for ending in endings['summary']['SPECIFIC']])

def search_for_endings(list_of_links, endings):
    res = [link for ending in endings for link in list_of_links if link.endswith(ending)]
    if len(res) == 0:
        return None
    return res[0]

def get_element_if_present(xpath, driver):
    try:
        return driver.find_element_by_xpath(xpath)
    except NoSuchElementException:
        return None

def find_tables(driver):
    return  driver.find_elements_by_xpath("/html/body/table")


def get_candidates_df(election_url, driver, download_path):
    if driver.current_url!=election_url:
        driver.get(election_url)
    combined = []
    links = [element.get_attribute("href") for element in driver.find_elements_by_xpath("//a[@href]")]
    for candidate_list_type in ['COMMON', 'SPECIFIC']:
        url = search_for_endings(links, [TYPE + ending for ending in endings['candidates'][candidate_list_type]])
        if url:
            driver.get(url)
            print_version = driver.find_element_by_link_text('Версия для печати')
            df = load_excel(print_version, download_path)
            df = DataFormatting.prettify_candidate_df(df)
            combined.append(df)
    return pd.concat(combined, axis=0).drop_duplicates(['name', 'nominator', 'candidate_birth_date']) if combined else None

def load_excel(downloadbutton, download_path):
    current_files = get_constant_files(download_path)
    for file in current_files:
        os.remove(pathlib.Path(download_path, file))
    downloadbutton.click()
    new_files = get_constant_files(download_path)
    if 'ExcelReportVersion' in driver.current_url:
        raise Exception('candidate file is broken')
    while len(new_files)==0:
        new_files = get_constant_files(download_path)
    if len(new_files)!=1:
        raise IOError('file_download_conflict')
    file = pathlib.Path(download_path, new_files[0])
    df = pd.read_excel(file)
    os.remove(file)
    return df

def get_constant_files(download_path):
    files = os.listdir(download_path)
    files = [file for file in files if not file.endswith('.crdownload')]
    return files



