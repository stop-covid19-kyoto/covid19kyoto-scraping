import openpyxl
import requests
import codecs
import shutil
import time
import os

from json import loads, dumps
from datetime import datetime, timedelta, timezone

from typing import Dict

jst = timezone(timedelta(hours=9), 'JST')
base_url = "https://raw.githubusercontent.com/yasuhitoinoue/covid19-kyoto/master/data/"

SUMMARY_INIT = {
    'attr': '検査実施人数',
    'value': 0,
    'children': [
        {
            'attr': '陽性患者数',
            'value': 0,
            'children': [
                {
                    'attr': '入院中・入院調整中',
                    'value': 0,
                },
                {
                    'attr': '宿泊施設',
                    'value': 0,
                },
                {
                    'attr': '自宅療養',
                    'value': 0,
                },
                {
                    'attr': '死亡',
                    'value': 0
                },
                {
                    'attr': '退院・解除',
                    'value': 0
                }
            ]
        }
    ]
}


def print_log(type: str, message: str) -> None:
    print(f"[{datetime.now(jst).strftime('%Y-%m-%d %H:%M:%S+09:00')}][covid19-scraping:{type}]: {message}")


def get_json(file_name: str) -> Dict:
    data_json = requests.get(base_url + file_name).text
    return loads(data_json)


def dumps_json(file_name: str, json_data: Dict) -> None:
    with codecs.open("./data/" + file_name, "w", "utf-8") as f:
        f.write(dumps(json_data, ensure_ascii=False, indent=4, separators=(',', ': ')))


def requests_xlsx(url: str, filename: str) -> openpyxl.workbook.workbook.Workbook:
    print_log("request", "Request xlsx file...")
    filename = "./data/" + filename
    failed_count = 0
    status_code = 404
    while not status_code == 200:
        try:
            res = requests.get(url, stream=True)
            status_code = res.status_code
        except Exception:
            if failed_count >= 5:
                raise Exception(f"Failed get xlsx file from \"{url}\"!")
            print_log("request", f"Failed get xlsx file from \"{url}\". retrying...")
            failed_count += 1
            time.sleep(5)
    with open(filename, 'wb') as f:
        res.raw.decode_content = True
        shutil.copyfileobj(res.raw, f)
    return openpyxl.load_workbook(filename)
