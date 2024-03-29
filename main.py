import os
import sys
import time
from collections import OrderedDict
import logging


from playsound import playsound

from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, QTimer, QDateTime, QModelIndex, Qt, QSettings
from PyQt5.QtGui import QImage, QPixmap, QFont, QPalette, QBrush, QColor, QPainter, QIcon
from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QHeaderView, QAbstractItemView, QApplication, QMessageBox
from glob import glob
import cv2
import requests
import numpy as np
import pygame


# import Test_API
from Keywords import Keywords, Alarm
from SettingWindow import SettingWindow
from Inspection import Inspection
from PlayAlarm import PlayAlarm
import json
import pandas as pd
from enum import Enum, auto

form_class = uic.loadUiType("./Ui/save_main_ui_2.ui")[0]

webcam_status = False
stop_webcam_time = 3
ocr_image = []
root_path = 'A:/salim/detected_labels'
warning_sound = './Sound/alert.MP3'
danger_sound = './Sound/alert.MP3'
error_sound = './Sound/alert.MP3'
# root_path = './Image'
init_excel_file = './Database/제품등록정보20211015.xlsx'


class CumulCount(Enum):
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
        for item in list(CumulCount):
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


class Db:
    def __init__(self):
        self.settings = QSettings('Vitasoft', 'SalimProject')
        self.db_file = self.settings.value('db_file')
        self.df = pd.read_excel(self.db_file)
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
        global webcam_status, ocr_image, undetected_label_cnt
        result = {}
        while True:
            undetected_label_cnt = len(glob(os.path.join(root_path, 'unrecognized/*.png')))
            if webcam_status:
                response = requests.get('http://localhost:5000/print_ocr')
                result = json.loads(response.text)
                if result:
                    self.label_cnt.emit(undetected_label_cnt)
                    self.result.emit(result)


def dictlst_to_lst(result_dict):
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
    # print(f'print_lst ---> {print_lst}')
    return print_lst


class WindowClass(QMainWindow, form_class):
    def __init__(self):
        super().__init__()

        self.prior_barcode = 0

        self.setupUi(self)
        self.setWindowIcon(QIcon('./Image/logo.png'))
        self.setWindowTitle("흙살림")
        self.setFont(QFont('나눔스퀘어_ac', 20))

        self.undetected_label_cnt = 0
        self.inspection = Inspection()
        self.final_result_txt = {
            '합격': CumulCount.success_cs,
            '유보': CumulCount.pass_cs,
            '불합격': CumulCount.fail_cs
        }
        self.alert_color = {
            '6': QColor(246, 189, 192),
            '7': QColor(241, 149, 155),
            '8': QColor(240, 116, 112),
            '9': QColor(234, 76, 70),
            '10': QColor(220, 28, 19)
        }

        settings = QSettings('Vitasoft', 'SalimProject')
        if settings.contains('db_file') and settings.value('db_file'):
            # print('Checking for database file in config')
            get_file_nm = settings.value('db_file')
        else:
            get_file_nm = init_excel_file
            settings.setValue('db_file', init_excel_file)

        self.setting_page = SettingWindow(get_file_nm)
        self.actionSettings.triggered.connect(self.show_setting_window)

        self.db = Db()
        self.inspection_setting = self.db.get_product_inspections()

        self.PlayAlarm = PlayAlarm()
        self.PlayAlarm.open_dialog.connect(self.open_msgbox)
        self.PlayAlarm.start()

        timer = QTimer(self)
        timer.timeout.connect(self.show_time)
        timer.start()
        # print(time.time() - start)

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

        # 결과 출력하는 테이블 영역(초기)
        inspection_table = self.inspection_table
        self.reset_inspection_table()
        vert_headers = list(Keywords.vert_headers(Keywords))
        for row in range(5):
            inspection_table.insertRow(row)
            inspection_table.setItem(row, 0, QTableWidgetItem(vert_headers[row].kor()))
        self.insp_tbl_init_row = self.inspection_table.rowCount()
        self.insp_tbl_init_col = self.inspection_table.columnCount()
        inspection_table.setSpan(0, self.insp_tbl_init_col - 1, self.insp_tbl_init_row, self.insp_tbl_init_col - 1)
        inspection_table.cellClicked.connect(self.highlight_inspection)

        # 테이블(객체 오류 개수) 구역 error_cnt_table
        error_cnt_table = self.error_cnt_table
        font = error_cnt_table.font()
        # font.setPointSize(15)
        # error_cnt_table.setFont(font)
        # error_cnt_table.setColumnWidth(0, QHeaderView.Stretch)
        # error_cnt_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # error_cnt_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        header = error_cnt_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)

        error_cnt_table.horizontalHeader().setMinimumHeight(35)
        error_cnt_table.setSelectionMode(QAbstractItemView.NoSelection)
        error_cnt_table.setAutoFillBackground(False)
        # error_cnt_table.setHorizontalHeader(['연속', '누적'])
        error_headers = Keywords.error_headers(Keywords)
        self.error_table_labels = []
        for header in error_headers:
            self.error_table_labels.append(header.kor())
        error_cnt_table.setHorizontalHeaderLabels(self.error_table_labels)
        error_cnt_table.horizontalHeader().setStyleSheet("::section {color: white; font-weight: bold; "
                                                         "background-color: #000030;}")

        # 카메라
        # self.th1 = Camera()
        # # self.th1.label_cnt.connect(self.undetected_label_cnt)
        # self.th1.result.connect(self.get_result)
        # self.th1.start()

        # self.th1.changePixmap.connect(self.set_image)
        self.cumul_result = OrderedDict()
        # for product_name in product_names:
        #     self.cumul_result[product_name] = {}

        results = [{'barcode': '2500000289552', 'cert_mark': ['organic'], 'cert_result': {
            '12100489': {'in_db': True, 'mark_status': 'success',
                         'name': {'db': '김영대', 'ocr_rslt': '김영대', 'score': 1.0},
                         'number': {'db': '12100489', 'ocr_rslt': '12100409', 'score': 0.875}}},
                    'date_time': '02/15/2022, 15:35:24', 'label_id': 157,
                    'label_loc': '/mnt/vitasoft/salim/detected_labels/2500000289552/09.png',
                    'product_name': {'name': '친환경 방울토마토', 'status': 'success'}, 'rot_angle': 270,
                    'weight': {'db': '600g', 'ocr_rslt': '600g', 'score': 1.0, 'status': 'success'}},
                   {'barcode': '2500000289552', 'cert_mark': ['organic'], 'cert_result': {
                       '04329818': {'in_db': False, 'mark_status': 'mark and producer number should be checked',
                                    'number': {'db': '04329818', 'ocr_rslt': '04329818'}},
                       '12100489': {'in_db': True, 'mark_status': 'success',
                                    'name': {'db': '김영대', 'ocr_rslt': '김영대', 'score': 1.0},
                                    'number': {'db': '12100489', 'ocr_rslt': '12100489', 'score': 1.0}}},
                    'date_time': '02/15/2022, 16:40:53', 'label_id': 562,
                    'label_loc': '/mnt/vitasoft/salim/detected_labels/2500000289552/09.png',
                    'product_name': {'name': '친환경 대추방울토마토', 'status': 'success'}, 'rot_angle': 270,
                    'weight': {'db': '600g', 'ocr_rslt': '600g', 'score': 1.0, 'status': 'success'}},
                   {'barcode': 'unrecognized', 'cert_mark': ['organic'], 'cert_result': {
                       '04829818': {'in_db': False, 'mark_status': 'mark and producer number doesn\'t match',
                                    'number': {'db': '04829818', 'ocr_rslt': '04829818'}},
                       '12100489': {'in_db': True, 'mark_status': 'success',
                                    'name': {'db': '김영대', 'ocr_rslt': '김영대', 'score': 1.0},
                                    'number': {'db': '12100489', 'ocr_rslt': '12100489', 'score': 1.0}}},
                    'date_time': '02/15/2022, 16:40:53', 'label_id': 562,
                    'label_loc': '/mnt/vitasoft/salim/detected_labels/2500000289552/09.png',
                    'product_name': {'name': '친환경 대추방울토마토', 'status': 'success'}, 'rot_angle': 270,
                    'weight': {'db': '600g', 'ocr_rslt': '600g', 'score': 1.0, 'status': 'success'}},
                   {'barcode': '2500000279935', 'cert_mark': ['organic'], 'cert_result': {
                       '04829818': {'in_db': False, 'mark_status': 'mark and producer number doesn\'t match',
                                    'number': {'db': '04829818', 'ocr_rslt': '04829818'}},
                       '12100489': {'in_db': True, 'mark_status': 'success',
                                    'name': {'db': '김영대', 'ocr_rslt': '김영대', 'score': 1.0},
                                    'number': {'db': '12100489', 'ocr_rslt': '12100489', 'score': 1.0}}},
                    'date_time': '02/15/2022, 16:40:53', 'label_id': 562,
                    'label_loc': '/mnt/vitasoft/salim/detected_labels/2500000289552/09.png',
                    'product_name': {'name': '친환경 대추방울토마토', 'status': 'success'}, 'rot_angle': 270,
                    'weight': {'db': '600g', 'ocr_rslt': '600g', 'score': 1.0, 'status': 'success'}}

                   ]

        for result in results:
            self.get_result(result)
            time.sleep(1)

    @pyqtSlot(bool)
    def open_msgbox(self):
        self.PlayAlarm.play_status = False
        product_name = self.db.get_product_name_by_barcode(self.prior_barcode)
        self.cumul_result[product_name][Keywords.alarm.eng()] = False
        alert = QMessageBox.critical(self, '불학격', f'{product_name} 불합격 결과 10개 이상', QMessageBox.Yes)
        if alert == QMessageBox.Yes:
            self.setoff_alarm(product_name)

    def setoff_alarm(self, product_name):
        self.PlayAlarm.stop()
        self.cumul_result[product_name][Keywords.alarm.eng()] = False



    # @pyqtSlot(int)
    def add_undlbl_cnt(self):
        self.undetected_label_cnt += 1
        self.undetected_label.setText(f'인식 실패한 라벨: {self.undetected_label_cnt} 개')
        # self.undetected_label.setFont(QFont('나눔스퀘어_ac', 15, QFont.Bold))

    def reset_inspection_table(self):
        # 결과 출력하는 테이블 리셋
        inspection_table = self.inspection_table
        inspection_table.clear()
        inspection_table.setRowCount(0)
        inspection_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        inspection_table.horizontalHeader().setMinimumHeight(35)
        inspection_table.setSelectionMode(QAbstractItemView.NoSelection)
        inspection_table.setAutoFillBackground(False)
        inspection_table.setHorizontalHeaderLabels([keyword.kor() for keyword in Keywords.inspection_headers(Keywords)])
        inspection_table.horizontalHeader().setStyleSheet("::section{color: white; font-weight:bold; "
                                                          "background-color: #000030;}")

    # @pyqtSlot(dict)
    def get_result(self, result_dict):
        self.db.__init__()
        # print(f'result --> {result_dict}')
        if result_dict.get(Keywords.barcode.eng()) != 'unrecognized':
            self.reset_inspection_table()
            barcode = int(result_dict[Keywords.barcode.eng()])
            self.prior_barcode = barcode

            # 이미지 불러오기
            # label_image = result_dict['label_loc']
            rot_angle = result_dict['rot_angle']
            label_image = './Image/default.jpg'
            rot_angle = 0
            self.show_image(label_image, rot_angle)

            '''
                OCR 결과들을 하나하나 확인하여 결과/점수 매기기
                result_dict
                    {'key1': ['v','a','l','u','e'],
                     'key2': [['v','a','l','u','e'], ['v','a','l','u','e']]
                     }
                result_lst
                    [['제품명', '친환경 방울토마토', '친환경 방울토마토', '100%', '승인'],
                     ['중량(수량)', '600g', '600g', '100%', '승인'],
                     ['바코드', '2500000279935', '2500000279935', '100%', '승인'],
                     ['인증마크', '유기농', '1', '100%', '승인'],
                     ['인증정보', '12100409 김영대', '12100489 김영대', '94%', '승인'],
                     ...
                     ]
            '''
            result_dict = self.inspection.inspect_result(result_dict)

            # result_dict를 list로 반환하여 for문 돌면서 결과 출력하기
            self.print_results(dictlst_to_lst(result_dict), barcode)

            # 검사/pass 확인해서 inspection_table 색 칠하기
            self.check_inspection(barcode)

            # 최종 결과 --> 합격, 불합격, 유보
            result_items_lst = self.result_after_inspection()
            final_result, brush = self.get_final_result(result_items_lst)
            # result_items_lst = [inspection_table.item(row_idx, 4).text() for row_idx in
            #                     range(inspection_table.rowCount())]  # ocr 항목들 결과값들 list
            self.print_final_result(final_result, brush)
            '''
                알람 띄우기
                warning은 warning.mp3 한번 재생
                danger는 warning.mp3 5번 재생 (끄기 popup 창 띄워서 제어)
                error은 error_2.mp3 재생 (끄기 popup 창 띄워서 제어)
                
                (끄기 popup 창 띄워서 제어) --> 한번 끄면 계속 꺼놓기
            '''
            # 에러 테이블 출력
            self.error_result(barcode, final_result)

            # 알람 울리기
            self.set_alarm(barcode)
        else:
            self.add_undlbl_cnt()

    def print_results(self, print_lst, barcode):
        # 리스트로 반환된 결과들을 length만큼 행을 만들어 출력한다
        for row_idx, row in enumerate(print_lst):
            self.inspection_table.insertRow(row_idx)
            for col_idx, cell in enumerate(row):
                item = QTableWidgetItem()
                item.setText(cell)
                if col_idx >= 3:
                    item.setTextAlignment(Qt.AlignCenter)
                self.inspection_table.setItem(row_idx, col_idx, QTableWidgetItem(item))
        self.inspection_table.setSpan(0, 5, len(print_lst) + 1, 5)

    def check_inspection(self, barcode):
        inspection_table = self.inspection_table
        inspections = self.inspection_setting
        if barcode in inspections:
            for row_idx in range(inspection_table.rowCount()):
                item = inspection_table.item(row_idx, 0)
                color = Qt.gray
                text = item.text() + ' pass'
                if inspections[barcode][item.text()] == Keywords.inspect.kor():
                    color = Qt.white
                    text = item.text()
                item.setText(text)
                self.set_color_to_row(row_idx, color)

    # 최종 결과 --> 합격, 불합격, 유보
    def print_final_result(self,result_text, brush):
        inspection_table = self.inspection_table
        text = QTableWidgetItem()
        font = QFont()
        font.setFamily('나눔스퀘어_ac')
        font.setPointSize(40)
        font.setBold(True)
        text.setFont(font)
        text.setTextAlignment(Qt.AlignCenter)
        text.setText(result_text)
        text.setForeground(brush)
        inspection_table.setItem(0, self.insp_tbl_init_col - 1, text)

    def error_result(self, barcode, final_result_text):
        # print(final_result_text)
        error_cnt_table = self.error_cnt_table
        error_cnt_table.setRowCount(0)
        # 검사 / pass 로 걸러진 최종 결과
        product_name = self.db.get_product_name_by_barcode(barcode)
        # 누적 테이블에 없으면 새로 PdCumul 인스턴스 생성해서 cumu_result dict에 추가하기
        if product_name not in self.cumul_result:
            rslt_dict = {}
            rslt_dict[Keywords.alarm.eng()] = True
            rslt_dict[Keywords.result.eng()] = PdCumul(product_name)
            self.cumul_result[product_name] = rslt_dict
        pd_class_dict = self.cumul_result[product_name][Keywords.result.eng()]
        pd_class_dict.add_result(self.final_result_txt[final_result_text])
        self.cumul_result.move_to_end(product_name, False) # 새로 증가된 제품은 맨위로 올리기

        for row, pd_name in enumerate(self.cumul_result.keys()):
            cumul_class = self.cumul_result[pd_name][Keywords.result.eng()]  # PdCumul class
            rslt = cumul_class.rslt_dict()
            error_cnt_table.insertRow(row)
            error_cnt_table.setItem(row, 0, QTableWidgetItem(pd_name))
            for col, key in enumerate(rslt.keys()):
                text = QTableWidgetItem()
                text.setTextAlignment(Qt.AlignCenter)
                text.setText(str(rslt[key]))
                if key == Keywords.fail_cs.eng():
                    if Alarm.danger.value < rslt[key] <= Alarm.error.value:
                        text.setForeground(self.alert_color[str(rslt[key])])
                    elif rslt[key] > Alarm.error.value:
                        text.setForeground(self.alert_color[str(Alarm.error.value)])

                error_cnt_table.setItem(row, col + 1, text)

    def result_after_inspection(self):
        inspection_table = self.inspection_table
        lst = []
        for row_idx in range(inspection_table.rowCount()):
            item = inspection_table.item(row_idx, 4)
            item_background = item.background()
            item_text = item.text()
            if item_background == Qt.white:
                lst.append(item_text)
        return lst

    def get_final_result(self, result_lst):
        final_result = Keywords.success.kor()
        brush = QBrush(Qt.blue)
        if Keywords.error.kor() in result_lst:
            final_result = Keywords.fail.kor()
            brush = QBrush(QColor(220, 28, 19))
        elif Keywords.match_fail.kor() in result_lst:
            final_result = Keywords._pass.kor()
            brush = QBrush(QColor(128, 128, 128))
        return final_result, brush

    def set_alarm(self, barcode):
        product_name = self.db.get_product_name_by_barcode(barcode)
        alarm_status = self.cumul_result[product_name][Keywords.alarm.eng()]
        cumul_rslt = self.cumul_result[product_name][Keywords.result.eng()].rslt_dict()
        fail_cs = cumul_rslt[Keywords.fail_cs.eng()]
        self.PlayAlarm.play_status = alarm_status
        if alarm_status:
            self.PlayAlarm.error_cnt = fail_cs


    def show_image(self, image_path, rot_angle):
        from_path = '/mnt/vitasoft/salim/detected_labels'
        image_path = image_path.replace(from_path, root_path)
        # print(image_path)
        opencv_rot_dict = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
        label_image = cv2.imread(image_path)
        label_image = cv2.cvtColor(label_image, cv2.COLOR_BGR2RGB)
        label_image = cv2.resize(label_image, (320, 320))
        if rot_angle != 0:
            label_image = cv2.rotate(label_image, opencv_rot_dict[rot_angle])
        height, width, channel = label_image.shape
        pixmap = QPixmap.fromImage(QImage(label_image.data, width, height, (channel * width), QImage.Format_RGB888))
        self.camera.setPixmap(pixmap)

    def show_setting_window(self):
        self.setting_page.show()

    # ★ 당일 검사 활성화/비활성화
    def highlight_inspection(self, row_idx, column):
        inspection_table = self.inspection_table
        check_keywords = [Keywords.cert_mark.kor(), Keywords.cert_result.kor()]
        highlight_lst = []
        # TODO: 패스일경우 [***** 다시 리팩토링 하기 *****]
        if column == 0:
            item = inspection_table.item(row_idx, column)
            item_text = item.text().replace(' pass', '')
            if item_text in check_keywords:
                same_keyword_rows = inspection_table.findItems(item.text(), Qt.MatchContains)
                for row in same_keyword_rows:
                    highlight_lst.append(row)
            else:
                highlight_lst.append(item)

            for item in highlight_lst:
                text = item.text().replace(' pass', '')
                if item.background() == Qt.gray:
                    color = Qt.white
                else:
                    text = text + ' pass'
                    color = Qt.gray
                item.setText(text)
                self.set_color_to_row(item.row(), color)

    def set_color_to_row(self, row_idx, color):
        for col in range(self.inspection_table.columnCount() - 1):
            self.inspection_table.item(row_idx, col).setBackground(color)

    def start_webcam(self):
        global webcam_status
        question_str = '촬영이 진행중 입니다. 촬영을 정지 하시겠습니까?'
        api_stats = 'end'
        btn_text = '시작'
        if not webcam_status:
            question_str = '촬영을 시작 하시겠습니까?'
            api_stats = 'start'
            btn_text = '정지'

        reply = QMessageBox.question(self, 'Message', question_str, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        if reply == QMessageBox.Yes:
            url = 'http://106.244.74.74:5001/' + api_stats
            response = requests.post(url)
            if response.status_code == 200:
                print(f'---------------- api_{api_stats} ----------------')
                webcam_status = not webcam_status
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
