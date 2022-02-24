import os
import sys
import time
from multiprocessing import Process
from playsound import playsound

from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, QTimer, QDateTime, QModelIndex, Qt
from PyQt5.QtGui import QImage, QPixmap, QFont, QPalette, QBrush, QColor, QPainter
from PyQt5.QtWidgets import *
from glob import glob
import cv2
import requests

# import Test_API
from Keywords import Keywords
from SettingWindow import SettingWindow
import json
import pandas as pd
from enum import Enum, auto

form_class = uic.loadUiType("./Ui/save_main_ui_2.ui")[0]

webcam_status = False
stop_webcam_time = 3

undetected_label_cnt = 0
ocr_image = []
root_path = 'A:/salim/detected_labels'
# root_path = './Image'
check_inspection_daily = {}
prior_barcode = 0
stacked_result = {}

class Cumul_Count(Enum):
    success_cs = "합격"
    success_cu = auto()
    pass_cs = "유보"
    pass_cu = auto()
    fail_cs = "불합격"
    fail_cu = auto()
    total = auto()

    def __str__(self):
        return self.name

class PdCumul:
    def __init__(self, pd_name):
        self.pd_name = pd_name
        self.cu_dict = {}
        self.cs_dict = {}
        self.prior_target = ''
        for item in list(Cumul_Count):
            if '_cs' in str(item):
                self.cs_dict[str(item)] = 0
            else:
                self.cu_dict[str(item)] = 0

    def clear(self):
        for key in self.cs_dict.keys():
            self.cs_dict[key] = 0

        for key in self.cu_dict.keys():
            self.cu_dict[key] = 0

    def add_result(self, target):
        target = str(target)
        self.cs_dict[target] += 1
        if self.prior_target != target:
            self.prior_target = target
            rest = [item for item in self.cs_dict.keys() if item != target]
            for item in rest:
                self.cs_dict[item] = 0
        cumul_target = target.replace('_cs', '_cu')
        self.cu_dict[cumul_target] += 1
        self.cu_dict['total'] += 1

    def rslt_dict(self):
        result = {}
        result.update(self.cs_dict)
        result.update(self.cu_dict)
        return result

    def product_name(self):
        return self.pd_name

class Db():
    def __init__(self):
        self.df = pd.read_excel('./Database/제품등록정보20211015.xlsx')
        self.df = self.df[self.df['라벨제품명'].str.contains('운영중단') == False]
        self.df = self.df.fillna('')

    def get_product_names(self):
        lst = ['라벨제품명', '중량(수량)', '단위']
        df = self.df[lst].values.tolist()
        product_names = []
        for idx in df:
            product_names.append(''.join([str(word) for word in idx]))
        return product_names

    def get_product_nick_names(self):
        nick_names = list(self.df['라벨제품명별칭'])
        return nick_names

    def get_product_name_by_barcode(self, barcode):
        df = self.df[self.df['바코드'].astype(float) == barcode]
        lst = ['라벨제품명', '중량(수량)', '단위']
        df = df[lst].values.tolist()
        return ''.join([str(word) for word in df[0]])

    def get_product_barcodes(self):
        barcodes = list(self.df['바코드'])
        return barcodes

    def get_product_inspections(self):
        lst = ['제품명검사', '중량(입수)검사', '바코드검사', '인증마크검사', '인증정보검사']
        inspections = self.df[lst]
        # inspections = inspections.replace('검사', 'O')
        # inspections = inspections.replace('pass', 'X')
        inspections_lst = inspections.values.tolist()
        barcodes = self.get_product_barcodes()
        check_dict = {}
        lst = ['제품명', '중량(수량)', '바코드', '인증마크', '인증정보']
        for idx, item in enumerate(inspections_lst):
            inspection_dict = {}
            for value_idx, value in enumerate(item):
                inspection_dict[lst[value_idx]] = value
            check_dict[barcodes[idx]] = inspection_dict
        return check_dict


class Camera(QThread):
    result = pyqtSignal(dict)
    label_cnt = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.active = False
        self.frames_path = ''
        self.frame_cnt = 0
        self.old_output = []

    def run(self):
        global webcam_status, stop_webcam_time, ocr_image, undetected_label_cnt
        result = {}
        while True:
            undetected_label_cnt = len(glob(os.path.join(root_path, 'unrecognized/*.png')))
            if webcam_status:
                response = requests.get('http://localhost:5000/print_ocr')
                result = json.loads(response.text)
                if result:
                    self.label_cnt.emit(undetected_label_cnt)
                    self.result.emit(result)

# class ErrorTblHeaders(QHeaderView):



class WindowClass(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("흙살림")
        self.setFont(QFont('나눔스퀘어_ac', 12))

        self.final_result_txt = {
            '합격': Cumul_Count.success_cs,
            '유보': Cumul_Count.pass_cs,
            '불합격': Cumul_Count.fail_cs
        }

        self.db = Db()
        self.inspection_setting = self.db.get_product_inspections()

        self.actionSettings.triggered.connect(self.show_setting_window)

        timer = QTimer(self)
        timer.timeout.connect(self.show_time)
        timer.start()

        # -------- Tab1 검사화면 inspection_window --------
        self.btn_start.clicked.connect(self.start_webcam)

        # self.img_column.setText('검출이미지')
        self.camera = self.label_img
        self.camera.setScaledContents(True)
        self.default_img = cv2.imread('./Image/default.jpg')
        self.default_img = cv2.resize(self.default_img, (200, 200))
        height, width, channel = self.default_img.shape
        pixmap = QPixmap.fromImage(
            QImage(self.default_img.data, width, height, (channel * width), QImage.Format_RGB888))
        self.camera.setPixmap(pixmap)

        # 결과 출력하는 테이블 영역
        inspection_table = self.inspection_table
        self.reset_inspection_table()
        insp_headers = list(Keywords.insp_headers(Keywords))
        for row in range(5):
            inspection_table.insertRow(row)
            inspection_table.setItem(row, 0, QTableWidgetItem(insp_headers[row].kor()))
        self.insp_tbl_init_row = self.inspection_table.rowCount()
        self.insp_tbl_init_col = self.inspection_table.columnCount()
        inspection_table.setSpan(0, self.insp_tbl_init_col- 1, self.insp_tbl_init_row, self.insp_tbl_init_col -1)
        inspection_table.cellClicked.connect(self.highlight_inspection)

        # 테이블(객체 오류 개수) 구역 error_cnt_table
        error_cnt_table = self.error_cnt_table
        font = error_cnt_table.font()
        font.setPointSize(15)
        error_cnt_table.setColumnWidth(0, QHeaderView.Stretch)
        error_cnt_table.setFont(font)
        error_cnt_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        error_cnt_table.setSelectionMode(QAbstractItemView.NoSelection)
        error_cnt_table.setAutoFillBackground(False)
        col = error_cnt_table.columnCount()
        row = error_cnt_table.rowCount()
        # error_cnt_table.setHorizontalHeader(['연속', '누적'])
        error_headers = Keywords.error_headers(Keywords)
        self.error_table_labels = []
        for header in error_headers:
            self.error_table_labels.append(header.kor())
        error_cnt_table.setHorizontalHeaderLabels(self.error_table_labels)
        error_cnt_table.horizontalHeader().setStyleSheet("::section {color: white; font-weight: bold; "
                                                         "background-color: #ACE7FF;}")



        # 카메라
        # self.th1 = Camera()
        # self.th1.label_cnt.connect(self.undetected_label_cnt)
        # self.th1.result.connect(self.get_result)
        # self.th1.start()

        # self.th1.changePixmap.connect(self.set_image)
        self.cumul_result = {}
        # product_names = self.db.get_product_names()
        # for product_name in product_names:
        #     self.cumul_result[product_name] = {}


        # self.check_table_rowcnt = self.inspection_check_table.rowCount()
        # self.check_table_colcnt = self.inspection_check_table.columnCount()
        # self.reset_inspection_table()
        # self.reset_inspection_check_table(prior_barcode)
        # self.inspection_check_table.setAutoFillBackground(Qt.lightGray)

        results = [{'barcode': '2500000279935', 'cert_mark': ['organic'], 'cert_result': {
                       '12100489': {'in_db': True, 'mark_status': 'success',
                                    'name': {'db': '김영대', 'ocr_rslt': '김영대', 'score': 1.0},
                                    'number': {'db': '12100489', 'ocr_rslt': '12100409', 'score': 0.875}}},
                    'date_time': '02/15/2022, 15:35:24', 'label_id': 157,
                    'label_loc': '/mnt/vitasoft/salim/detected_labels/2500000279935/0157.png',
                    'product_name': {'name': '친환경 방울토마토', 'status': 'success'}, 'rot_angle': 180,
                    'weight': {'db': '600g', 'ocr_rslt': '600g', 'score': 1.0, 'status': 'success'}},
                   {'barcode': '2500000252983', 'cert_mark': ['organic'], 'cert_result': {
                       '04829818': {'in_db': False, 'mark_status': 'success',
                                    'number': {'db': '04829818', 'ocr_rslt': '04829818'}},
                       '04829811': {'in_db': False, 'mark_status': 'success',
                                    'number': {'db': '04829818', 'ocr_rslt': '04829811'}},
                       '04829813': {'in_db': False, 'mark_status': 'success',
                                    'number': {'db': '04829818', 'ocr_rslt': '04829813'}},
                       '04829814': {'in_db': False, 'mark_status': 'success',
                                    'number': {'db': '04829818', 'ocr_rslt': '04829814'}},
                       '04829815': {'in_db': False, 'mark_status': 'success',
                                    'number': {'db': '04829818', 'ocr_rslt': '04829815'}},
                       '04829816': {'in_db': False, 'mark_status': 'success',
                                    'number': {'db': '04829818', 'ocr_rslt': '04829816'}},
                       '12100489': {'in_db': True, 'mark_status': 'success',
                                    'name': {'db': '김영대', 'ocr_rslt': '김영대', 'score': 1.0},
                                    'number': {'db': '12100489', 'ocr_rslt': '12100489', 'score': 1.0}}},
                    'date_time': '02/15/2022, 16:40:53', 'label_id': 562,
                    'label_loc': '/mnt/vitasoft/salim/detected_labels/2500000279935/0562.png',
                    'product_name': {'name': '친환경 대추방울토마토', 'status': 'success'}, 'rot_angle': 0,
                    'weight': {'db': '600g', 'ocr_rslt': '600g', 'score': 1.0, 'status': 'success'}}
                   ]

        for result in results:
            self.get_result(result)

        # 인식 실패한 라벨
        self.undetected_label.setText(f'인식 실패한 라벨: {str(undetected_label_cnt)} 개')
        self.undetected_label.setFont(QFont('나눔스퀘어_ac', 15, QFont.Bold))

    def inspect_result(self, result):
        return_dict = {'product_name': [], 'weight': [], 'barcode': [], 'cert_mark': [], 'cert_result': []}

        for key, value in result.items():
            cert_third_num = []
            if key == 'product_name':
                return_dict[key].append(value['name'])
                return_dict[key].append(value['name'])
                if value['status'] == 'success':
                    return_dict[key].append('100%')
                    return_dict[key].append('승인')

            if key == 'weight':
                return_dict[key].append(value['ocr_rslt'])
                return_dict[key].append(value['db'])
                return_dict[key].append(f"{round(value['score'] * 100)}%")
                return_dict[key].append('승인')

            if key == 'barcode':
                return_dict[key].append(value)
                return_dict[key].append(value)
                return_dict[key].append('100%')
                return_dict[key].append('승인')

            if key == 'cert_mark':
                if value:
                    for mark in value:
                        mark_lst = []
                        mark_lst.append(Keywords[mark].kor())
                        cert_numbers = [item['number']['ocr_rslt'] for item in result['cert_result'].values()]
                        mark_lst.append(', '.join([number[2] for number in cert_numbers]))
                        mark_status = [number['mark_status'] for number in result['cert_result'].values()]
                        count = 0
                        for status in mark_status:
                            if 'success' == status:
                                count += 1
                        raw_score = 0.0

                        if len(mark_status) > 0:
                            raw_score = count / len(mark_status)

                        score = f"{round(raw_score * 100)}%"
                        mark_lst.append(score)

                        if count == len(mark_status) and raw_score >= 0.9:
                            mark_lst.append('승인')
                        elif 'fail' in mark_status:
                            mark_lst.append('오류')
                        else:
                            mark_lst.append('매칭실패')
                        return_dict[key].append(mark_lst)
                else:
                    mark_lst = ['', '', '0.0', '매칭실패']
                    return_dict[key].append(mark_lst)

            if key == 'cert_result':
                if value:
                    for num_key, num_value in value.items():
                        cert_lst = []
                        if num_value['in_db']:
                            cert_lst.append(f"{num_value['number']['ocr_rslt']} {num_value['name']['ocr_rslt']}")
                            cert_lst.append(f"{num_value['number']['db']} {num_value['name']['db']}")
                            raw_score = (num_value['name']['score'] + num_value['number']['score']) / 2.0
                            cert_lst.append(f"{round(raw_score * 100)}%")
                            result = '오류'
                            if raw_score >= 0.9:
                                result = '승인'
                            cert_lst.append(result)
                        else:
                            name = ''
                            number = ''
                            if 'name' in num_value and 'number' in num_value:
                                name = num_value['name']['ocr_rslt']
                                number = num_value['number']['ocr_rslt']
                            elif 'number' in num_value.keys():
                                number = num_value['number']['ocr_rslt']
                            elif 'name' in num_value.keys():
                                name = num_value['name']['ocr_rslt']
                            cert_lst.append(f"{name} {number}")
                            cert_lst.append("조회 실패")
                            cert_lst.append('0%')
                            cert_lst.append('매칭실패')
                        return_dict[key].append(cert_lst)
                else:
                    return_dict[key].append(['', '', '0%', '매칭실패'])

        return return_dict

    # def check_insp_daily(self):
    #     global check_inspection_daily
    #     check_lst = []
    #     # TODO: DB class 만들어서 refactoring 하기
    #     df = self.db.get_product_inspections()
    #     df = df.replace('검사', 'O')
    #     df = df.replace('pass', 'X')
    #     for idx in range(len(df)):
    #         check_lst.append(list(df.iloc[idx].to_dict().values()))
    #     barcode_lst = list(df['바코드'].to_dict().values())
    #     for idx, barcode in enumerate(barcode_lst):
    #         check_inspection_daily[barcode] = check_lst[idx]

    @pyqtSlot(int)
    def undetected_label_cnt(self, label_cnt):
        self.undetected_label.setText(f'인식 실패한 라벨: {label_cnt} 개')
        self.undetected_label.setFont(QFont('나눔스퀘어_ac', 15, QFont.Bold))

    def reset_inspection_table(self):
        # 결과 출력하는 테이블 리셋
        inspection_table = self.inspection_table
        inspection_table.clear()
        inspection_table.setRowCount(0)
        inspection_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        inspection_table.setSelectionMode(QAbstractItemView.NoSelection)
        inspection_table.setAutoFillBackground(False)
        self.inspection_table_labels = ['검사대상', '인식결과', '등록정보', '싱크율', '결과', '종합판단']
        inspection_table.setHorizontalHeaderLabels(self.inspection_table_labels)
        inspection_table.horizontalHeader().setStyleSheet("::section{color: white; font-weight:bold; "
                                                          "background-color: #ACE7FF;}")


    @pyqtSlot(dict)
    def get_result(self, result_dict):
        global prior_barcode
        inspection_table = self.inspection_table
        self.reset_inspection_table()
        print(f'result --> {result_dict}')
        if result_dict.get(Keywords.barcode.eng()) != 'unrecognized':
            barcode = int(result_dict[Keywords.barcode.eng()])
            prior_barcode = barcode
            # 이미지 불러오기
            # label_image = result_dict['label_loc']
            # from_path = '/mnt/vitasoft/salim/detected_labels'
            # label_image = label_image.replace(from_path, root_path)
            # print(label_image)
            # self.show_image(label_image, result_dict['rot_angle'])
            height, width, channel = self.default_img.shape
            pixmap = QPixmap.fromImage(
                QImage(self.default_img.data, width, height, (channel * width), QImage.Format_RGB888))
            self.camera.setPixmap(pixmap)

            # OCR 결과들을 하나하나 확인하여 결과/점수 매기기
            result_dict = self.inspect_result(result_dict)

            # ocr(result_dict)를 list로 반환하여 결과 출력하기
            print_lst = self.result_dict_to_lst(result_dict)
            self.print_result(print_lst, barcode)

    def result_dict_to_lst(self, result_dict):
        # print(f'result_dict --> {result_dict}')
        import numpy as np
        print_lst = []
        for key, value in result_dict.items():
            nd_array = np.array(value)
            if nd_array.ndim >= 2:
                for item in value:
                    item.insert(0, Keywords[key].kor())
                    print_lst.append(item)
            else:
                value.insert(0, Keywords[key].kor())
                print_lst.append(value)
        print(f'print_lst ---> {print_lst}')
        return print_lst

    def set_final_result(self):
        inspection_table = self.inspection_table
        row_cnt = inspection_table.rowCount()
        result_items_lst = [inspection_table.item(row_idx, 4).text() for row_idx in
                            range(1, row_cnt)]  # ocr 항목들 결과값들 list
        final_result_text = Keywords.success.kor()
        text = QTableWidgetItem()
        text.setText(final_result_text)
        font = QFont()
        font.setFamily('나눔스퀘어_ac')
        font.setPointSize(40)
        font.setBold(True)
        text.setFont(font)
        text.setTextAlignment(Qt.AlignCenter)
        brush = QBrush(Qt.blue)
        if Keywords.error.kor() in result_items_lst:
            final_result_text = Keywords.fail.kor()
            text.setText(final_result_text)
            brush = QBrush(Qt.red)
        elif Keywords.match_fail.kor() in result_items_lst:
            final_result_text = Keywords._pass.kor()
            text.setText(final_result_text)
            brush = QBrush(QColor(128, 128, 128))
        text.setForeground(brush)
        inspection_table.setItem(0, self.insp_tbl_init_col - 1, text)
        return final_result_text

    def print_result(self, print_lst, barcode):
        # 리스트로 반환된 결과들을 length만큼 행을 만들어 출력한다
        for row_idx, row in enumerate(print_lst):
            self.inspection_table.insertRow(row_idx)
            for col_idx, cell in enumerate(row):
                item = QTableWidgetItem()
                item.setText(cell)
                if col_idx >= 3:
                    item.setTextAlignment(Qt.AlignCenter)
                self.inspection_table.setItem(row_idx, col_idx, QTableWidgetItem(item))
        self.inspection_table.setSpan(0, 5, row_idx+1, 5)
        self.print_cumul_result(barcode)
        self.check_inspection(barcode)

    def print_cumul_result(self, barcode):
        final_result_text = self.set_final_result()
        product_name = self.db.get_product_name_by_barcode(barcode)
        if product_name not in self.cumul_result:
            self.cumul_result[product_name] = PdCumul(product_name)
        self.cumul_result[product_name].add_result(self.final_result_txt[final_result_text])

        error_cnt_table = self.error_cnt_table
        error_cnt_table.setRowCount(0)
        for idx, key in enumerate(self.cumul_result.keys()):
            error_cnt_table.insertRow(idx)
            error_cnt_table.setItem(idx, 0, QTableWidgetItem(key))
            for value_idx, value in enumerate(self.cumul_result[key].rslt_dict().values()):
                text = QTableWidgetItem()
                text.setTextAlignment(Qt.AlignCenter)
                text.setText(str(value))
                error_cnt_table.setItem(idx, value_idx + 1, text)

    def show_image(self, image_path, rot_angle):
        opencv_rot_dict = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
        label_image = cv2.imread(image_path)
        label_image = cv2.cvtColor(label_image, cv2.COLOR_BGR2RGB)
        label_image = cv2.resize(label_image, (320, 320))
        if rot_angle != 0:
            label_image = cv2.rotate(label_image, opencv_rot_dict[rot_angle])
        height, width, channel = label_image.shape
        pixmap = QPixmap.fromImage(QImage(label_image.data, width, height, (channel * width), QImage.Format_RGB888))
        self.camera.setPixmap(pixmap)

    def check_inspection(self, barcode):
        inspection_table = self.inspection_table
        inspections = self.inspection_setting
        if barcode in inspections:
            for row_idx in range(inspection_table.rowCount()):
                item = inspection_table.item(row_idx, 0)
                color = Qt.gray
                if inspections[barcode][item.text()] == Keywords.inspect.kor():
                    color = Qt.white
                item.setBackground(color)

    def show_setting_window(self):
        self.setting_page = SettingWindow()
        self.setting_page.show()

    # ★ 당일 검사 활성화/비활성화
    def highlight_inspection(self, row, column):
        inspection_table = self.inspection_table
        check_keywords = [Keywords.cert_mark.kor(), Keywords.cert_result.kor()]
        highlight_lst = []
        # TODO: 패스일경우 [***** 다시 리팩토링 하기 *****]
        if column == 0:
            item = inspection_table.item(row, column)
            item_text = item.text().replace(' pass', '')
            if item_text in check_keywords:
                same_keyword_rows = inspection_table.findItems(item.text(), Qt.MatchContains)
                for row in same_keyword_rows:
                    highlight_lst.append(row)
            else:
                highlight_lst.append(item)

            for item in highlight_lst:
                if item.background() == Qt.gray:
                    item.setText(f'{item_text}')
                    item.setBackground(Qt.white)
                else:
                    item.setText(f'{item_text} pass')
                    item.setBackground(Qt.gray)
        # self.set_inspection_setting()

    def set_inspection_setting(self):
        inspection_check_table = self.inspection_check_table
        inspection_row_cnt = inspection_check_table.rowCount()

        check_lst = []
        for row in range(inspection_row_cnt):
            check = 'O'
            if row != 0:
                item = inspection_check_table.item(row, 0)
                if item.background().color() == Qt.gray:
                    check = 'X'
                check_lst.append(check)
        self.inspection_setting[prior_barcode] = check_lst

    def start_webcam(self):
        global webcam_status
        question_str = '촬영이 진행중 입니다. 촬영을 정지 하시겠습니까?'
        api_stats = 'end'
        btn_text = '시작'
        if not webcam_status:
            question_str = '촬영을 시작 하시겠습니까?'
            api_stats = 'start'
            btn_text = '정지'
            # if not check_inspection_daily:
            #      self.check_insp_daily()

        reply = QMessageBox.question(self, 'Message', question_str, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        if reply == QMessageBox.Yes:
            webcam_status = not webcam_status
            url = 'http://106.244.74.74:5001/' + api_stats
            response = requests.post(url)
            if response.status_code == 200:
                print(f'---------------- api_{api_stats} ----------------')
                self.btn_start.setText(btn_text)

    def show_time(self):
        current_date_time = QDateTime.currentDateTime()
        label_time = current_date_time.toString('yyyy년 MM월 dd일 AP hh:mm:ss')
        self.current_date_time.setText(label_time)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.showMaximized()
    sys.exit(app.exec_())
