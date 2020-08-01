import inspect

from datetime import datetime, timedelta

from typing import Dict

from config import patients_file_url, summary_file_url
from util import get_json, dumps_json, requests_xlsx, jst, SUMMARY_INIT, print_log


patients_first_cell = 3
summary_fitst_cell = 3


class DataJson:
    def __init__(self):
        # 運用方式の変更により、jsonからの取得は廃止
        # self.old_data_json = get_json("covid-19-kyoto.json")
        # self.old_pcr_json = get_json("covid-19-kyoto_pcr.json")

        # データ取得元のファイル
        self.patients_sheet = requests_xlsx(patients_file_url, "patients.xlsx")["covid-19-kyoto"]
        # self.patients_sheet = openpyxl.load_workbook("")
        self.summary_sheet = requests_xlsx(summary_file_url, "summary.xlsx")["Sheet1"]

        # データ取得に使う変数
        self.patients_count = patients_first_cell
        self.summary_count = summary_fitst_cell
        self.summary_values = []
        self.last_update = datetime.today().astimezone(jst).strftime("%Y/%m/%d %H:%M")

        # 以下内部変数
        self._inspections_summary_json = {}
        self._patients_json = {}
        self._patients_summary_json = {}
        self._main_summary_json = {}
        self._last_update_json = {}

        # 初期化(最大行数の取得)
        self.get_patients()
        self.get_summaries()

    def json_template_of_patients(self) -> Dict:
        # patients_sheetを用いるデータ向けのテンプレート
        return {
            "data": [],
            "last_update": self.get_patients_last_update()
        }

    def json_template_of_summaries(self) -> Dict:
        # summaries_sheetを用いるデータ向けのテンプレート
        return {
            "data": [],
            "last_update": self.get_summaries_last_update()
        }

    def dump_and_check_all_data(self) -> None:
        # xxx_json の名を持つ関数のリストを生成する(_で始まる内部変数は除外する)
        # ちなみに、以降生成するjsonを増やす場合は"_json"で終わる関数と"_"で始まる、関数に対応する内部変数を用意すれば自動で認識される
        json_list = [
            member[0] for member in inspect.getmembers(self) if member[0][-4:] == "json" and member[0][0] != "_"
        ]
        for json in json_list:
            # 関数は"_json"で終わっているので、それを拡張子に直す必要がある
            json_name = json[:-5] + ".json"
            print_log("data_manager", f"Make {json_name}...")
            # evalで文字列から関数を呼び出し、jsonを出力
            print_log("data_manager", f"Dumps {json_name}...")
            dumps_json(json_name, eval("self." + json + "()"))

    # 内部変数にデータが保管されているか否かを確認し、保管されていなければ生成し、返す。
    # 以下Dictを返す関数はこれに同じ
    def patients_json(self) -> Dict:
        if not self._patients_json:
            self.make_patients()
        return self._patients_json

    def patients_summary_json(self) -> Dict:
        if not self._patients_summary_json:
            self.patients_json()
            self.make_patients_summary()
        return self._patients_summary_json

    def inspections_summary_json(self) -> Dict:
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
        # patients.jsonのデータを作成する
        self._patients_json = self.json_template_of_patients()
        # patients_sheetからデータを読み取っていく
        for i in range(patients_first_cell, self.patients_count):
            discharged = self.patients_sheet.cell(row=i, column=13).value
            data = {
                "No": i - 2,
                "リリース日": self.patients_sheet.cell(row=i, column=2).value,
                "居住地": self.patients_sheet.cell(row=i, column=6).value,
                "年代と性別": str(self.patients_sheet.cell(row=i, column=5).value).strip(),
                "退院": "〇" if discharged else None,
                "date": self.patients_sheet.cell(row=i, column=3).value.strftime("%Y-%m-%d")
            }
            # print(data)
            self._patients_json["data"].append(data)

    def make_patients_summary(self) -> None:
        # 内部データテンプレート
        def make_data(date, value=1):
            data = {"日付": date, "小計": value}
            return data

        # patients_summary.jsonの作成
        self._patients_summary_json = self.json_template_of_patients()

        # 以前のデータを保管する
        # これは、前の患者データと日付が同じであるか否かを比較するための変数
        prev_data = {}
        for patients_data in sorted(self.patients_json()["data"], key=lambda x: x['リリース日']):
            date = patients_data["リリース日"]
            if prev_data:
                prev_date = datetime.strptime(prev_data["日付"], "%Y-%m-%dT%H:%M:%S.%fZ")
                # 前のデータと日付が離れている場合、その分0のデータを埋める必要があるので、そのために差を取得する
                patients_zero_days = (datetime.strptime(date, "%Y-%m-%dT%H:%M:%S.%fZ") - prev_date).days
                # 前のデータと日付が同じ場合、前のデータに人数を加算していく
                if prev_data["日付"] == date:
                    prev_data["小計"] += 1
                    # 加算し終えたら戻る
                    continue
                else:
                    # 前のデータと日付が離れていた場合、前のデータをjsonに登録する
                    self._patients_summary_json["data"].append(prev_data)
                    # 前のデータとの日付の差が2日以上の場合は空いている日にち分、0を埋める
                    if patients_zero_days >= 2:
                        for i in range(1, patients_zero_days):
                            self._patients_summary_json["data"].append(
                                make_data((prev_date + timedelta(days=i)).isoformat() + ".000Z", 0)
                            )
            # 新しいデータを作成し、前もって前のデータとして格納しておく
            prev_data = make_data(date)
        # 最後のデータをjsonに登録する
        self._patients_summary_json["data"].append(prev_data)
        prev_date = datetime.strptime(prev_data["日付"], "%Y-%m-%dT%H:%M:%S.%fZ")
        # 最終更新のデータから日付が開いている場合、0で埋める
        patients_zero_days = (datetime.now() - prev_date).days
        for i in range(1, patients_zero_days):
            self._patients_summary_json["data"].append(
                make_data((prev_date + timedelta(days=i)).isoformat() + ".000Z", 0)
            )

    def make_inspections_summary(self) -> None:
        # 内部データテンプレート
        def make_data(date, value=1):
            data = {"日付": date, "小計": value}
            return data

        # inspections_summary.jsonの作成
        self._inspections_summary_json = self.json_template_of_summaries()

        # 以前のデータを保管する
        # これは、前の検査データと日付が同じであるか否かを比較するための変数
        prev_data = {}
        for i in range(summary_fitst_cell, self.summary_count):
            date = self.summary_sheet.cell(row=i, column=1).value
            data = make_data(
                date.isoformat() + ".000Z",
                int(self.summary_sheet.cell(row=i, column=2).value)
            )
            if prev_data:
                prev_date = datetime.strptime(prev_data["日付"], "%Y-%m-%dT%H:%M:%S.000Z")
                # 前のデータと日付が離れている場合、その分0のデータを埋める必要があるので、そのために差を取得する
                inspections_zero_days = (date - prev_date).days
                for j in range(1, inspections_zero_days):
                    self._inspections_summary_json["data"].append(
                        make_data(
                            (prev_date + timedelta(days=j)).isoformat() + ".000Z",
                            0
                        )
                    )
                # 取得できるデータが累計なので、前のデータ分を引く
                data["小計"] -= prev_data["小計"]
            # 取得できるデータが累計なので、引いたデータ分は後で元に戻すので、コピーをjsonに登録する
            self._inspections_summary_json["data"].append(data.copy())
            if prev_data:
                # 前のデータがある場合は、その日の小計なので、前のデータ分を足して累計に戻す
                data["小計"] += prev_data["小計"]
            prev_data = data
        # 最終更新のデータから日付が開いている場合、0で埋める
        # patients_zero_days = (datetime.now() - prev_date).days
        # for i in range(1, patients_zero_days):
        #     self._inspections_summary_json["data"].append(
        #         make_data(
        #             (prev_date + timedelta(days=i)).isoformat() + ".000Z",
        #             0
        #         )
        #     )

    def make_main_summary(self) -> None:
        # main_summary.jsonの作成
        # これに関してはテンプレートが大きいのでSUMMARY_INITとして別ファイルに退避している
        self._main_summary_json = SUMMARY_INIT
        self._main_summary_json["last_update"] = self.get_summaries_last_update()

        # 使われる値をリストにする
        self.summary_values = [
            self.summary_sheet.cell(row=self.summary_count - 1, column=2).value,
            self.summary_sheet.cell(row=self.summary_count - 1, column=4).value,
            self.summary_sheet.cell(row=self.summary_count - 1, column=16).value,
            self.summary_sheet.cell(row=self.summary_count - 1, column=17).value,
            self.summary_sheet.cell(row=self.summary_count - 1, column=18).value,
            self.summary_sheet.cell(row=self.summary_count - 1, column=19).value,
            self.summary_sheet.cell(row=self.summary_count - 1, column=15).value
        ]
        # なぜかfloatになるので、intに統一
        self.summary_values = list(map(int, self.summary_values))

        self.set_summary_values(self._main_summary_json)

    def set_summary_values(self, obj) -> None:
        # リストの先頭の値を"value"にセットする
        obj["value"] = self.summary_values[0]
        # objが辞書型で"children"を持っている場合のみ実行
        if isinstance(obj, dict) and obj.get("children"):
            for child in obj["children"]:
                # 再帰させて値をセット
                self.summary_values = self.summary_values[1:]
                self.set_summary_values(child)

    def make_last_update(self) -> None:
        self._last_update_json["last_update"] = self.last_update

    def get_patients_last_update(self) -> str:
        return datetime.strptime(
            self.patients_sheet.cell(row=1, column=1).value, "%Y-%m-%dT%H:%M:%S.%fZ"
        ).strftime("%Y/%m/%d %H:%M")

    def get_summaries_last_update(self) -> str:
        return datetime.strptime(
            self.summary_sheet.cell(row=1, column=1).value, "%Y-%m-%dT%H:%M:%S.%fZ"
        ).strftime("%Y/%m/%d %H:%M")

    def get_patients(self) -> None:
        # 何行分患者のデータがあるかを取得
        while self.patients_sheet:
            self.patients_count = self.patients_count + 1
            value = self.patients_sheet.cell(row=self.patients_count, column=2).value
            if not value:
                self.patients_count = self.patients_count - 3
                break

    def get_summaries(self) -> None:
        # 何行分サーマリーデータがあるかを取得
        while self.summary_sheet:
            self.summary_count += 1
            value = self.summary_sheet.cell(row=self.summary_count, column=1).value
            if not value:
                break


if __name__ == '__main__':
    data_json = DataJson()
    data_json.dump_and_check_all_data()
