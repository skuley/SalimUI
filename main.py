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
check_inspection_daily = []

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
        # self.th1.check_empty_time.connect(self.check_belt)
        # self.th1.changePixmap.connect(self.set_image)

        self.row_cnt = self.inspection_table.rowCount()
        self.col_cnt = self.inspection_table.columnCount()
        self.reset_table()

        # 인식 실패한 라벨
        self.undetected_label.setText(f'인식 실패한 라벨: {str(undetected_label_cnt)} 개')
        self.undetected_label.setFont(QFont('나눔스퀘어_ac', 15, QFont.Bold))

        inspection_check_list = self.inspection_check_list
        inspection_check_list.clear()
        inspection_check_list.setRowCount(self.row_cnt)

        inspection_check_list.setAutoFillBackground(Qt.lightGray)
        rows_title = ['구분', '제품명', '중량(입수)', '바코드', '인증마크']
        for row in range(self.row_cnt):
            inspection_check_list.setItem(row, 0, QTableWidgetItem(rows_title[row]))

        inspection_check_list.cellClicked.connect(self.highlight_inspection)

        # 실시간으로 인식 실패한 라벨 갯수 파악하기
        # self.count_undetected_label = UndetectedLabel()
        # self.count_undetected_label.start()
        # self.count_undetected_label.label_cnt.connect(self.undetected_label_cnt)

        # 테이블(오류) 구역 error_table
        # error_table = self.error_table
        # error_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    def check_insp_daily(self):
        global check_inspection_daily
        df = pd.read_excel('./Database/제품등록정보20211015.xlsx')
        lst = ['바코드', '제품명검사', '중량(입수)검사', '인증마크검사', '인증정보검사']
        df[lst] = df[lst].replace('검사', 'O')
        df[lst] = df[lst].replace('pass', 'X')
        for idx in range(len(df[lst])):
            check_inspection_daily.append(list(df[lst].iloc[idx].to_dict().values()))

    @pyqtSlot(int)
    def undetected_label_cnt(self, label_cnt):
        self.undetected_label.setText(f'인식 실패한 라벨: {label_cnt} 개')
        self.undetected_label.setFont(QFont('나눔스퀘어_ac', 15, QFont.Bold))

    def reset_table(self):
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


    @pyqtSlot(dict)
    def show_result(self, result):
        self.reset_table()
        print(f'result --> {result}')
        info_lst = []
        barcode = 0
        if result.get('barcode'):
            barcode = int(result['barcode'])
            print(barcode)
            # 알람 설정 세팅하기
            for item in check_inspection_daily:
                if barcode in item:
                    item.pop(item.index(int(barcode)))
                    info_lst = item
                    print(f'info_lst --> {info_lst}')

            # 이미지 불러오기
            label_image = result['label_loc']
            nas_path = '/mnt/vitasoft/salim/detected_labels'
            label_image = label_image.replace(nas_path, label_image_path)
            self.show_image(label_image, result['rot_angle'])

            result_dict = self.inspection_result(result)

            # ocr 결과 출력하기
            self.print_result(result_dict)


        else:
            pass

        if self.prior_barcode != barcode:
            # self.init_inspection(info_lst)
            self.prior_barcode = barcode

    def inspection_result(self, result):
        product_name = {}
        weight = {}
        cert_marks = []
        cert_results = []
        barcode = {}

        for key, value in result.items():
            cert_third_num = []
            if key == 'product_name':
                product_name['ocr'] = result[key]['name']
                product_name['db'] = result[key]['name']
                if result[key]['status'] == 'success':
                    product_name['score'] = 1.0

            if key == 'weight':
                weight['ocr'] = result[key]['ocr_rslt']
                weight['db'] = result[key]['db']
                weight['score'] = result[key]['score']

            if key == 'barcode':
                barcode['ocr'] = value
                barcode['db'] = value
                barcode['score'] = 1.0

            if key == 'cert_mark':
                for mark in value:
                    cert_marks.append(mark)

            if key == 'cert_result':
                for num_key, num_value in value.items():
                    cert_lst = []
                    if num_value['in_db']:
                        cert_lst.append((num_value['name']['ocr_rslt'], num_value['number']['ocr_rslt']))
                        cert_lst.append((num_value['name']['db'], num_value['number']['db']))
                        cert_lst.append((num_value['name']['score'] + num_value['number']['score']) / 2.0)
                        cert_lst.append(num_value['mark_status'])
                    else:
                        name = ''
                        number = ''
                        if 'name' in num_value.keys() and 'number' in num_value.keys():
                            name = num_value['name']['ocr_rslt']
                            number = num_value['number']['ocr_rslt']
                        elif 'number' in num_value.keys():
                            number = num_value['number']['ocr_rslt']
                        elif 'name' in num_value.keys():
                            name = num_value['name']['ocr_rslt']
                        cert_lst.append((name, number))
                        cert_lst.append((None, None))
                        cert_lst.append(0.0)
                        cert_lst.append('fail')
                    cert_results.append(cert_lst)

        return {'product_name': product_name, 'weight': weight, 'barcode': barcode, 'cert_marks': cert_marks, 'cert_results': cert_results}


    def print_result(self, result_dict):
        for row, key in enumerate(result_dict.keys()):
            mark_idx = len(result_dict['cert_results'])
            insert_row = mark_idx + row
            if insert_row >= row:
                self.inspection_table.insertRow(insert_row)
                self.inspection_check_list.insertRow(insert_row)
            for col in range(self.col_cnt):
                # cell = self.inspection_table.item(row, col)
                if row < 3:
                    if col == 0:
                        self.inspection_table.setItem(row+1, col, QTableWidgetItem(result_dict[key]['ocr']))
                    if col == 1:
                        self.inspection_table.setItem(row+1, col, QTableWidgetItem(result_dict[key]['db']))
                    if col == 2:
                        score = result_dict[key]['score'] * 100
                        score = '{0:.0f}%'.format(score)
                        self.inspection_table.setItem(row+1, col, QTableWidgetItem(score))
                else:
                    if col == 0:
                        for mark_idx, mark in enumerate(result_dict[key]):
                            if row == 3:
                                self.inspection_table.setItem(insert_row, col, QTableWidgetItem(mark))
                                self.inspection_check_list.setItem(insert_row, col, QTableWidgetItem('인증마크2'))
                            if row == 4:
                                ocr = ' '.join(mark[col])
                                self.inspection_table.setItem(insert_row, col, QTableWidgetItem(ocr))
                                self.inspection_check_list.setItem(insert_row, col, QTableWidgetItem(f'인증정보{mark_idx}'))


    def show_image(self, image_path, rot_angle):
        opencv_rot_dict = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
        label_image = cv2.imread(image_path)
        label_image = cv2.resize(label_image, (200, 200))
        if rot_angle != 0:
            label_image = cv2.rotate(label_image,opencv_rot_dict[rot_angle])
        height, width, channel = label_image.shape
        pixmap = QPixmap.fromImage(QImage(label_image.data, width, height, (channel * width), QImage.Format_RGB888))
        self.camera.setPixmap(pixmap)

    def init_inspection(self, info_lst):
        inspection_check_list = self.inspection_check_list

        for idx, row in enumerate(info_lst):
            item = inspection_check_list.item(idx+1, 0)
            if row == 'O':
                item.setBackground(Qt.gray)
            else:
                item.setBackground(Qt.white)

    def show_setting_window(self):
        self.setting_page = SettingWindow()
        self.setting_page.show()

    # ★ 당일 검사 활성화/비활성화
    def highlight_inspection(self, row):
        inspection_check_list = self.inspection_check_list
        if row == 0:
            pass
        else:
            item = inspection_check_list.item(row, 0)
            # item.setBackground(QBrush(QColor(220, 220, 220)))
            if item.background() == Qt.gray:
                item.setBackground(Qt.white)
            else:
                item.setBackground(Qt.gray)

    def start_webcam(self):
        global webcam_status

        if not webcam_status:
            question_str = '촬영을 시작 하시겠습니까?'
            api_stats = 'start'
            btn_text = '정지'
            self.check_insp_daily()
        else:
            question_str = '촬영이 진행중 입니다. 촬영을 정지 하시겠습니까?'
            api_stats = 'end'
            btn_text = '시작'

        reply = QMessageBox.question(self, 'Message', question_str, QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

        if reply == QMessageBox.Yes:
            webcam_status = not webcam_status
            url = 'http://106.244.74.74:5001/' + api_stats
            response = requests.post(url)
            if response.status_code == 200:
                print(f'---------------- api_{api_stats} ----------------')
                self.btn_start.setText(btn_text)


    def stop_webcam(self):
        global webcam_status
        if webcam_status:
            webcam_status = False
            reply = QMessageBox.question(self, 'Message', '촬영을 정지하시겠습니까?', QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                webcam_status = False
                requests.post('http://106.244.74.74:5001/end')
                print('---------------- api ended ----------------')
            else:
                webcam_status = True
        else:
            QMessageBox.about(self, 'Message', '촬영이 정지된 상태입니다.')


    @pyqtSlot()
    def check_belt(self, ):
        QMessageBox.about(self, 'Message', '촬영이 정지됩니다.')

    @pyqtSlot(QImage)
    def set_image(self, qImg1):
        inspection_table = self.inspection_table
        pixmap = QPixmap.fromImage(qImg1)
        self.camera.setPixmap(pixmap)

    def show_time(self):
        current_date_time = QDateTime.currentDateTime()
        label_time = current_date_time.toString('yyyy년 MM월 dd일 AP hh:mm:ss')
        self.current_date_time.setText(label_time)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.showMaximized()
    sys.exit(app.exec_())
