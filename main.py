import os
import sys
import time
from multiprocessing import Process

import cv2
import pyzbar.pyzbar
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, QTimer, QDateTime, QModelIndex, Qt
from PyQt5.QtGui import QImage, QPixmap, QFont, QPalette, QBrush, QColor, QPainter
from PyQt5.QtWidgets import *
from glob import glob
import cv2
import requests

import Test_API
from SettingWindow import SettingWindow
import json
import pandas as pd

form_class = uic.loadUiType("./Ui/save_main_ui.ui")[0]

webcam_status = False
stop_webcam_time = 3

undetected_label_cnt = 0
ocr_image = []
label_image_path = 'A:/salim/detected_labels'
check_inspection_daily = {}

mark_kor = {
    'organic': '유기농',
    'nonpesticide': '무농약',
    'gap': 'GAP(우수관리인증)',
    'antibiotic': '무항생제',
    'animal': '동물복지',
    'haccp': '안전관리인증HACCP',
    'pgi': '지리적표시',
    'traditional': '전통식품',
    'master': '식품명인',
    'processed': '가공식품',
    'carbon': '저탄소(LOW CARBON)'
}

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
            undetected_label_cnt = len(glob(os.path.join(label_image_path, 'unrecognized/*.png')))
            if webcam_status:
                response = requests.get('http://localhost:5000/print_ocr')
                result = json.loads(response.text)
                if result:
                    self.label_cnt.emit(undetected_label_cnt)
                    self.result.emit(result)


        # while video.isOpened():
        #     if webcam_status:
        #         ret, frame = video.read()
        #         if ret:
        #             if len(ocr_image) < 1:
        #                 ocr_image.append(frame)
        #             # old_output, count = pp.tracking(frame, old_output, count)
        #             # self.result.emit(ocr_parsed_result)
        #             frame = cv2.resize(frame, (200, 200))
        #             height, width, channel = frame.shape
        #             qImg1 = QImage(frame.data, width, height, (channel * width), QImage.Format_RGB888)
        #             self.changePixmap.emit(qImg1)


class UndetectedLabel(QThread):
    label_cnt = pyqtSignal(int)
    def __init__(self):
        super().__init__()

    def run(self):
        global undetected_label_cnt, webcam_status
        while True:
            if webcam_status:
                undetected_label_cnt = len(glob(os.path.join(label_image_path, 'unrecognized/*.png')))
        self.label_cnt.emit(undetected_label_cnt)


class ServerManagement(QThread):
    def __init__(self):
        super().__init__()

    def run(self) -> None:
        server = Process(target=Test_API.app.run(host='0.0.0.0', port=5000))
        server.start()
        server.join()


class WindowClass(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("흙살림")
        self.setFont(QFont('나눔스퀘어_ac', 12))
        self.prior_barcode = 0

        self.actionSettings.triggered.connect(self.show_setting_window)
        # self.action_label_settings.triggered.connect(self.show_label_edit_window)

        self.server_manage = ServerManagement()
        self.server_manage.start()

        # current_date_time 라벨 실시간
        timer = QTimer(self)
        timer.timeout.connect(self.show_time)
        timer.start()
        
        # -------- 프로그램 처음 실행시 open할 탭 화면 지정하기 --------
        # self.window_tab.setCurrentIndex(0)

        # -------- Tab1 검사화면 inspection_window --------
        self.btn_start.clicked.connect(self.start_webcam)
        # self.btn_stop.clicked.connect(self.stop_webcam)

        # self.img_column.setText('검출이미지')
        self.camera = self.label_img
        self.camera.setScaledContents(True)
        default_img = cv2.imread('./Image/default.jpg')
        default_img = cv2.resize(default_img, (200, 200))
        height, width, channel = default_img.shape
        pixmap = QPixmap.fromImage(QImage(default_img.data, width, height, (channel * width), QImage.Format_RGB888))
        self.camera.setPixmap(pixmap)

        # 테이블(객체 오류 개수) 구역 error_cnt_table
        error_cnt_table = self.error_cnt_table
        font = error_cnt_table.font()
        font.setPointSize(20)
        error_cnt_table.setFont(font)
        error_cnt_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        error_cnt_table.setSelectionMode(QAbstractItemView.NoSelection)
        error_cnt_table.setAutoFillBackground(False)
        col = error_cnt_table.columnCount()
        row = error_cnt_table.rowCount()

        # 카메라
        self.th1 = Camera()
        self.th1.label_cnt.connect(self.undetected_label_cnt)
        self.th1.result.connect(self.show_result)
        self.th1.start()
        # result = {'barcode': '2500000279935', 'cert_mark': ['organic'], 'cert_result': {'04829818': {'in_db': False, 'mark_status': 'success', 'number': {'db': '04829818', 'ocr_rslt': '04829818'}}, '12100489': {'in_db': True, 'mark_status': 'success', 'name': {'db': '김영대', 'ocr_rslt': '김영대', 'score': 1.0}, 'number': {'db': '12100489', 'ocr_rslt': '12100489', 'score': 1.0}}}, 'date_time': '02/15/2022, 16:40:53', 'label_id': 562, 'label_loc': '/mnt/vitasoft/salim/detected_labels/2500000279935/0562.png', 'product_name': {'name': '친환경 방울토마토', 'status': 'success'}, 'rot_angle': 0, 'weight': {'db': '600g', 'ocr_rslt': '600g', 'score': 1.0, 'status': 'success'}}

        # self.th1.check_empty_time.connect(self.check_belt)
        # self.th1.changePixmap.connect(self.set_image)

        self.row_cnt = self.inspection_table.rowCount()
        self.col_cnt = self.inspection_table.columnCount()
        self.check_table_rowcnt = self.inspection_check_table.rowCount()
        self.check_table_colcnt = self.inspection_check_table.columnCount()
        self.reset_inspection_table()
        self.reset_inspection_check_table(self.prior_barcode)
        self.inspection_check_table.setAutoFillBackground(Qt.lightGray)
        self.inspection_check_table.cellClicked.connect(self.highlight_inspection)

        # self.show_result(result)

        # 인식 실패한 라벨
        self.undetected_label.setText(f'인식 실패한 라벨: {str(undetected_label_cnt)} 개')
        self.undetected_label.setFont(QFont('나눔스퀘어_ac', 15, QFont.Bold))



        # 실시간으로 인식 실패한 라벨 갯수 파악하기
        # self.count_undetected_label = UndetectedLabel()
        # self.count_undetected_label.start()
        # self.count_undetected_label.label_cnt.connect(self.undetected_label_cnt)

        # 테이블(오류) 구역 error_table
        # error_table = self.error_table
        # error_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def check_insp_daily(self):
        global check_inspection_daily
        check_lst = []
        df = pd.read_excel('./Database/제품등록정보20211015.xlsx')
        lst = ['제품명검사', '중량(입수)검사', '인증마크검사', '인증정보검사']  # '바코드',
        df[lst] = df[lst].replace('검사', 'O')
        df[lst] = df[lst].replace('pass', 'X')
        for idx in range(len(df[lst])):
            check_lst.append(list(df[lst].iloc[idx].to_dict().values()))
        barcode_lst = list(df['바코드'].to_dict().values())
        for idx, barcode in enumerate(barcode_lst):
            check_inspection_daily[barcode] = check_lst[idx]

    @pyqtSlot(int)
    def undetected_label_cnt(self, label_cnt):
        self.undetected_label.setText(f'인식 실패한 라벨: {label_cnt} 개')
        self.undetected_label.setFont(QFont('나눔스퀘어_ac', 15, QFont.Bold))

    def reset_inspection_table(self):
        # 결과 출력하는 테이블
        inspection_table = self.inspection_table
        inspection_table.clear()
        inspection_table.setRowCount(self.row_cnt)

        # 테이블(검사) 구역 inspection_table
        inspection_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        inspection_table.setSelectionMode(QAbstractItemView.NoSelection)
        inspection_table.setAutoFillBackground(False)

        # 기본 구분
        columns_title = ['인식결과', '등록정보', '싱크율', '결과']
        for column in range(self.col_cnt - 1):
            inspection_table.setItem(0, column, QTableWidgetItem(columns_title[column]))

        inspection_table.setSpan(0, self.col_cnt - 1, self.row_cnt, 1)

        # 알람 설정 테이블
    def reset_inspection_check_table(self, barcode):
        inspection_check_table = self.inspection_check_table
        inspection_check_table.clear()
        inspection_check_table.setRowCount(self.check_table_rowcnt)
        rows_title = ['구분', '제품명', '중량(입수)', '바코드', '인증마크', '인증정보']
        for row in range(self.row_cnt):
            inspection_check_table.setItem(row, 0, QTableWidgetItem(rows_title[row]))
        if self.prior_barcode != barcode:
            self.check_inspection(self.prior_barcode)

        # self.reset_inspection_check_table_table()


    @pyqtSlot(dict)
    def show_result(self, result):
        self.reset_inspection_table()
        print(f'result --> {result}')
        info_lst = []
        if result.get('barcode'):
            barcode = int(result['barcode'])
            # 알람 설정 세팅하기
            if barcode != self.prior_barcode:
                self.reset_inspection_check_table(barcode)

            # 이미지 불러오기
            label_image = result['label_loc']
            nas_path = '/mnt/vitasoft/salim/detected_labels'
            label_image = label_image.replace(nas_path, label_image_path)
            self.show_image(label_image, result['rot_angle'])

            result_dict = self.inspection_result(result)

            # ocr 결과 출력하기
            mark_idx = len(result_dict['cert_result'])
            insert_row = mark_idx + self.row_cnt
            if insert_row > self.row_cnt:
                diff = insert_row - self.row_cnt
                for row in range(diff):
                    self.inspection_table.insertRow(self.row_cnt+row)
                    self.inspection_check_table.insertRow(self.check_table_rowcnt+row)

                self.inspection_table.setSpan(0, self.col_cnt - 1, self.row_cnt + diff, 1)
            self.print_result(result_dict)


    def inspection_result(self, result):
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
                for mark in value:
                    mark_lst = []
                    mark_lst.append(mark_kor[mark])
                    cert_numbers = [item['number']['ocr_rslt'] for item in result['cert_result'].values()]
                    mark_lst.append(', '.join([number[2] for number in cert_numbers]))
                    mark_status = [number['mark_status'] for number in result['cert_result'].values()]
                    count = 0
                    for status in mark_status:
                        if 'success' == status:
                            count += 1
                    if len(mark_status) > 0:
                        raw_score = count / len(mark_status)
                    else:
                        raw_score = 0.0
                    score = f"{round(raw_score * 100)}%"
                    mark_lst.append(score)
                    if raw_score >= 0.9:
                        mark_lst.append('승인')
                    return_dict[key].append(mark_lst)

            if key == 'cert_result':
                for num_key, num_value in value.items():
                    cert_lst = []
                    if num_value['in_db']:
                        cert_lst.append(f"{num_value['number']['ocr_rslt']} {num_value['name']['ocr_rslt']}")
                        cert_lst.append(f"{num_value['number']['db']} {num_value['name']['db']}")
                        raw_score = (num_value['name']['score'] + num_value['number']['score']) / 2.0
                        cert_lst.append(f"{round(raw_score) * 100}%")
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
                        cert_lst.append(f"{name}, {number}")
                        cert_lst.append("매칭실패")
                        cert_lst.append('0%')
                        cert_lst.append('매칭실패')
                    return_dict[key].append(cert_lst)

        return return_dict

    def print_result(self, result_dict):
        for row, key in enumerate(result_dict.keys()):
            for col in range(self.col_cnt-2):
                if row < 3:
                    self.inspection_table.setItem(row+1, col, QTableWidgetItem(result_dict[key][col]))
                else:
                    mark_lst = result_dict[key]
                    self.check_inspection(self.prior_barcode)
                    for idx, mark in enumerate(mark_lst):
                        self.inspection_table.setItem(row+1+idx, col, QTableWidgetItem(mark[col]))
                # elif key == 'cert_result':
                #     mark_lst = result_dict[key]



                        # if col == 0:
                        #     self.inspection_table.setItem(cell_row, col, QTableWidgetItem(mark))
                        #     self.inspection_check_table.setItem(cell_row, col, QTableWidgetItem(f'인증마크{mark_idx + 1}'))
                        # if col == 1:
                        #     db = tuple([item[2] for item in result_dict['cert_marks'][-1]])
                        #     self.inspection_table.setItem(cell_row, col, QTableWidgetItem(', '.join(db)))
                        # if col == 2:
                        #     self.inspection_table.setItem(cell_row, col, QTableWidgetItem(''))
                        # if col == 3:
                        #     self.inspection_table.setItem(cell_row, col, QTableWidgetItem(''))
                        # if col == 4:
                        #     self.inspection_table.setItem(cell_row, col, QTableWidgetItem(''))
                # if row == 4:
                    # if col == 0:
                    #     ocr = ' '.join(mark[col])
                    #     self.inspection_table.setItem(cell_row, col, QTableWidgetItem(ocr))
                    #     self.inspection_check_table.setItem(cell_row, col, QTableWidgetItem(f'인증정보{mark_count + 1}'))
                        # if col == 1:
                        #
                        # if col == 2:
                        #
                        # if col == 3:
                        #
                        # if col == 4:



    def show_image(self, image_path, rot_angle):
        opencv_rot_dict = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
        label_image = cv2.imread(image_path)
        label_image = cv2.resize(label_image, (320, 320))
        if rot_angle != 0:
            label_image = cv2.rotate(label_image,opencv_rot_dict[rot_angle])
        height, width, channel = label_image.shape
        pixmap = QPixmap.fromImage(QImage(label_image.data, width, height, (channel * width), QImage.Format_RGB888))
        self.camera.setPixmap(pixmap)

    def check_inspection(self, barcode):
        inspection_check_table = self.inspection_check_table
        self.prior_barcode = barcode
        if barcode in check_inspection_daily:
            for idx, row in enumerate(check_inspection_daily[barcode]):
                item = inspection_check_table.item(idx+1, 0)
                item.setBackground(Qt.white)
                if row == 'O':
                    item.setBackground(Qt.gray)


    def show_setting_window(self):
        self.setting_page = SettingWindow()
        self.setting_page.show()

    # ★ 당일 검사 활성화/비활성화
    def highlight_inspection(self, row):
        inspection_check_table = self.inspection_check_table
        if row != 0:
            item = inspection_check_table.item(row, 0)
            if item.background() == Qt.gray:
                item.setBackground(Qt.white)
            else:
                item.setBackground(Qt.gray)

    def start_webcam(self):
        global webcam_status
        question_str = '촬영이 진행중 입니다. 촬영을 정지 하시겠습니까?'
        api_stats = 'end'
        btn_text = '시작'
        if not webcam_status:
            question_str = '촬영을 시작 하시겠습니까?'
            api_stats = 'start'
            btn_text = '정지'
            self.check_insp_daily()

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
