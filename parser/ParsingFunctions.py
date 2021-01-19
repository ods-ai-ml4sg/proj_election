import copy
import pathlib

from bs4 import BeautifulSoup
import pandas as pd
import os
from PIL import Image, ImageFilter
from selenium import webdriver
import time
import pytesseract
from typing import BinaryIO, List, Dict
from io import BytesIO
from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.support.ui import Select
import re
import numpy as np

from enums import CandidateListType

SLEEP_TIME = 0.1

LOAD_ATTEMPTS = 5

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
                                   ]},
           'candidates':{CandidateListType.COMMON.name: ["221",
                                    "220&report_mode=1"
                                    ],
                         CandidateListType.SPECIFIC.name:["220"
                                    ]} }


TYPE = 'type='

def detect_captcha_text(image: BinaryIO) -> str:
    """Detects captcha text
    Args:
        image (bytes): image parsed from html
    Returns:
        string: captcha symbols
    """
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
    """Finds element with captcha and detects captcha text
    Args:
        driver: selenium driver
    Returns:
        Dict: captcha input field and captcha text
    """
    captcha_png = driver.find_element_by_id("captchaImg").screenshot_as_png
    captcha_text = detect_captcha_text(captcha_png).replace("o", "0")
    captcha_input_field = driver.find_element_by_id("captcha")
    return {"captcha_input_field": captcha_input_field, "captcha_text": captcha_text}


def get_through_captcha(driver, url: str):
    """Iterativly tries to get through captcha
    Args:
        driver: selenium driver
        url (str): url link
    Returns:
        None
    """

    flag = 1
    while flag:
        try:
            driver.find_element_by_xpath("//table")
            flag = 0
        except NoSuchElementException:
            captcha_elements = find_and_recognize_captcha(driver)
            captcha_input_field = captcha_elements["captcha_input_field"]
            captcha_text = captcha_elements["captcha_text"]
            captcha_input_field.send_keys(captcha_text)
            driver.find_element_by_id("send").click()
            time.sleep(SLEEP_TIME)


def get_election_result(url: str, driver, candidate_list_type, walk_back=False) -> pd.DataFrame:
    """Load election result data
    Args:
        url (str): url link
        driver : selenium driver
        level: 1/2 position of link to election table from the bottom of the page (1 for UIK data, 2 for summary data)
    """
    driver.get(url)
    time.sleep(SLEEP_TIME)
    get_through_captcha(driver, url)
    links = [element.get_attribute("href") for element in driver.find_elements_by_xpath("//a[@href]")]
    try:
        url = search_for_endings(links, [TYPE + ending for ending in endings['results'][candidate_list_type]])
    except IndexError:
        return None

    link_to_vote_table = driver.find_element_by_xpath('//a[@href="'+url+'"]')
    link_to_vote_table.click()
    table_result = str(BeautifulSoup(driver.page_source, features="lxml").select('table:nth-of-type(5)'))
    if walk_back:
        driver.back()
    if table_result=='[]':
        return None
    else:
        try:
            return pd.read_html(table_result)[0]
        except ValueError as e: # edge case: cancelled elections
            print(e)
            return None


def search_for_endings(list_of_links, endings):
    res = [link for ending in endings for link in list_of_links if link.endswith(ending)]
    assert len(res) >= 0, "Wrong links: {}".format(", ".join(res))
    return res[0]


def test_if_new_layers(driver, propagate = {}, level_name=None, inceptions_level=0, output=[], path=[]) -> list:
    flag_direct_selection = 0
    propagate_copy = copy.deepcopy(propagate)

    # check for summary for common part of elections (e.g. voting for parties)
    try_to_find_summary_if_not_already_present(driver, level_name, propagate_copy, CandidateListType.COMMON.name)

    # check for summary for specific part of elections (e.g. voting for district candidates)
    try_to_find_summary_if_not_already_present(driver, level_name, propagate_copy, CandidateListType.SPECIFIC.name)

    try:
        link_to_real_data = driver.find_element_by_xpath(
            "/html/body/table[2]/tbody/tr[2]/td/a")
        flag_direct_selection = 1

    except NoSuchElementException:
        form = driver.find_element_by_xpath(
            "/html/body/table[2]/tbody/tr[2]/td/form/select")
        flag_direct_selection = 2

    if flag_direct_selection == 1:
        link_to_real_data = driver.find_element_by_xpath(
            "/html/body/table[2]/tbody/tr[2]/td/a")
        link_to_real_data.click()

        path = 'direct' if inceptions_level==0 else path
        output += [{'commission_name':str(k.next),
                    'path':path,
                    'protocol_url':k['value'],
                    **propagate_copy} for k in BeautifulSoup(
                driver.page_source, features="lxml").select('option[value]')]
                           
        return output

    elif flag_direct_selection == 2:
        # if we have a dropdown menu with OIK
        options = BeautifulSoup(driver.page_source, features="lxml").select('option[value]')
        number_of_OIK = len(options)
        options_values = [i.text for i in options]

        # to know how many times we need to walk around
        for i in range(number_of_OIK):
            form = driver.find_element_by_xpath(
                "/html/body/table[2]/tbody/tr[2]/td/form/select")
            Select(form).select_by_visible_text(f'{options_values[i]}')
            driver.find_element_by_xpath(
                "/html/body/table[2]/tbody/tr[2]/td/form/input").click()
            inceptions_level += 1

            test_if_new_layers(driver=driver,
                               propagate=propagate_copy,
                               level_name=options_values[i],
                               inceptions_level=inceptions_level,
                               output = output,
                               path=path+[options_values[i]])
            back_steps(driver)

        return output

    else:
        return


def try_to_find_summary_if_not_already_present(driver, level_name, propagate_copy, candidate_list_type):
    if 'summary_found_' + candidate_list_type not in propagate_copy:
        cur_url = driver.current_url
        table = get_election_result(driver.current_url, driver, candidate_list_type=candidate_list_type, walk_back=True)
        if type(table) == pd.DataFrame:
            propagate_copy['summary_found_' + candidate_list_type] = cur_url
            propagate_copy['summary_level_name_' + candidate_list_type] = level_name


def back_steps(driver) -> int:
    try:
        driver.back()
        driver.find_element_by_xpath("/html/body/table[2]/tbody/tr[2]/td/form")
    except:
        driver.back()
        driver.find_element_by_xpath("/html/body/table[2]/tbody/tr[2]/td/form")
        return None


def get_links_UIK(link: str, driver) -> list:
    driver.get(link)
    get_through_captcha(driver, link)

    list_of_links_to_UIK_data = test_if_new_layers(driver=driver,
                                                   propagate={'election_url': link},
                                                   level_name='direct',
                                                   inceptions_level=0,
                                                   path=[],
                                                   output=[])

    return list_of_links_to_UIK_data


def load_candidates(driver, election_url, candidate_list_type, download_path):
    driver.get(election_url)
    time.sleep(SLEEP_TIME)
    get_through_captcha(driver, election_url)
    links = [element.get_attribute("href") for element in driver.find_elements_by_xpath("//a[@href]")]

    url = search_for_endings(links, [TYPE + ending for ending in endings['candidates'][candidate_list_type]])

    link_to_vote_candidate_page = driver.find_element_by_xpath('//a[@href="'+url+'"]')
    link_to_vote_candidate_page.click()
    print_version = driver.find_element_by_link_text('Версия для печати')
    df = load_excel(print_version, download_path)
    return df

def load_excel(downloadbutton, download_path):
    current_files = get_constant_files(download_path)
    downloadbutton.click()
    new_files = get_constant_files(download_path)
    diff = set(new_files).difference(current_files)
    while len(diff)==0:
        new_files = get_constant_files(download_path)
        diff = set(new_files).difference(current_files)
    if len(diff)!=1:
        raise IOError('file_download_conflict')
    file = pathlib.Path(download_path, list(diff)[0])
    df = pd.read_excel(file)
    os.remove(file)
    return df

def get_constant_files(download_path):
    files = os.listdir(download_path)
    files = [file for file in files if not file.endswith('.crdownload')]
    return files



