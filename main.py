import requests
import codecs

from json import loads, dumps
from datetime import datetime, timedelta

from typing import Dict

base_url = "https://raw.githubusercontent.com/yasuhitoinoue/covid19-kyoto/master/data/"


def get_json(file_name: str) -> Dict:
    data_json = requests.get(base_url + file_name).text
    return loads(data_json)


def dumps_json(file_name: str, json_data: Dict) -> None:
    with codecs.open("./data/" + file_name, "w", "utf-8") as f:
        f.write(dumps(json_data, ensure_ascii=False, indent=4, separators=(',', ': ')))


class DataJson:
    def __init__(self):
        self.old_data_json = get_json("covid-19-kyoto.json")
        self.old_pcr_json = get_json("covid-19-kyoto_pcr.json")

        self._inspections_summary_json = {}
        self._patients_json = {}
        self._patients_summary_json = {}
        self._main_summary_json = {}
        self._last_update_json = {}

    def patients_json(self) -> Dict:
        if not self._patients_json:
            self.make_patients()
        return self._patients_json

    def patients_summary_json(self) -> Dict:
        if not self._patients_summary_json:
            self.patients_json()
            self.make_patients_summary()
        return self._patients_summary_json

    def inspection_summary_json(self) -> Dict:
        if not self._inspections_summary_json:
            self.make_inspections_summary()
        return self._inspections_summary_json

    def main_summary_json(self) -> Dict:
        if not self._main_summary_json:
            self.make_main_summary()
        return self._main_summary_json

    def last_update_json(self) -> Dict:
        if not self._last_update_json:
            self.make_last_update()
        return self._last_update_json

    def make_patients(self) -> None:
        self._patients_json = {
            "last_update": self.old_data_json["patients"]["date"],
            "data": []
        }
        patients = self.old_data_json["patients"]["data"]
        for patient in patients:
            data = {}
            data["No"] = patient["No"]
            data["リリース日"] = patient["発表日"]
            data["居住地"] = patient["住居地"]
            data["年代と性別"] = patient["年代・性別"]
            discharge_day = patient["退院日"]
            data["退院"] = "〇" if discharge_day else None
            data["date"] = patient["date"]
            self._patients_json["data"].append(data)

    def make_patients_summary(self) -> None:
        self._patients_summary_json = self.old_data_json["patients_summary"]
        self._patients_summary_json["last_update"] = self._patients_summary_json.pop("date")
        for data in self._patients_summary_json["data"]:
            assert isinstance(data, dict)
            data.pop("退院")

    def make_inspections_summary(self) -> None:
        self._inspections_summary_json = {
            "last_update": self.old_data_json["patients"]["date"],
            "data": []
        }
        prev_data = {}
        for inspection in self.old_pcr_json:
            date = datetime.strptime("2020/" + inspection["日付"], "%Y/%m/%d")
            data = {}
            data["日付"] = date.isoformat() + ".000Z"
            data["小計"] = inspection["PCR検査実施人数"]
            if prev_data:
                prev_date = datetime.strptime("2020/" + prev_data["日付"], "%Y/%m/%d")
                inspections_zero_days = (date - prev_date).days
                for i in range(1, inspections_zero_days):
                    self._inspections_summary_json["data"].append(
                        {
                            "日付": (prev_date + timedelta(days=i)).isoformat() + ".000Z",
                            "小計": 0
                        }
                    )
                data["小計"] -= prev_data["PCR検査実施人数"]
            self._inspections_summary_json["data"].append(data)
            prev_data = inspection

    def make_main_summary(self) -> None:
        self._main_summary_json = self.old_data_json["main_summary"]
        self._main_summary_json["last_update"] = self.old_data_json["lastUpdate"]

    def make_last_update(self) -> None:
        self._last_update_json["last_update"] = self.old_data_json["lastUpdate"]


if __name__ == '__main__':
    data_json = DataJson()
    dumps_json("patients.json", data_json.patients_json())
    dumps_json("patients_summary.json", data_json.patients_summary_json())
    dumps_json("inspections_summary.json", data_json.inspection_summary_json())
    dumps_json("main_summary.json", data_json.main_summary_json())
    dumps_json("last_update.json", data_json.last_update_json())
