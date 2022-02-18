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
root_path = 'A:/salim/detected_labels'
# root_path = 'C:/Users/skuley/Desktop/2500000145629'
check_inspection_daily = {}
prior_barcode = 0
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

stacked_result = {}

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

    def get_product_barcodes(self):
        barcodes = list(self.df['바코드'])
        return barcodes

    def get_product_inspections(self):
        lst = ['제품명검사', '중량(입수)검사', '바코드검사', '인증마크검사', '인증정보검사']
        inspections = self.df[lst]
        inspections = inspections.replace('검사', 'O')
        inspections = inspections.replace('pass', 'X')
        inspections_lst = inspections.values.tolist()
        barcodes = self.get_product_barcodes()
        check_dict = {}
        for idx, barcode in enumerate(barcodes):
            check_dict[barcode] = inspections_lst[idx]
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

        self.db = Db()
        self.inspection_setting = self.db.get_product_inspections()

        self.actionSettings.triggered.connect(self.show_setting_window)
        # self.action_label_settings.triggered.connect(self.show_label_edit_window)

        # self.server_manage = ServerManagement()
        # self.server_manage.start()

        # current_date_time 라벨 실시간
        timer = QTimer(self)
        timer.timeout.connect(self.show_time)
        timer.start()

        # -------- Tab1 검사화면 inspection_window --------
        self.btn_start.clicked.connect(self.start_webcam)

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
        # self.th1 = Camera()
        # self.th1.label_cnt.connect(self.undetected_label_cnt)
        # self.th1.result.connect(self.get_result)
        # self.th1.start()
        result = {'barcode': '2500000145629', 'cert_mark': ['organic'], 'cert_result': {'04829818': {'in_db': False, 'mark_status': 'success', 'number': {'db': '04829818', 'ocr_rslt': '04829818'}}, '12100489': {'in_db': True, 'mark_status': 'success', 'name': {'db': '김영대', 'ocr_rslt': '김영대', 'score': 1.0}, 'number': {'db': '12100489', 'ocr_rslt': '12100489', 'score': 1.0}}}, 'date_time': '02/15/2022, 16:40:53', 'label_id': 562, 'label_loc': 'C:/Users/skuley/Desktop/2500000145629/0048.png', 'product_name': {'name': '친환경 방울토마토', 'status': 'success'}, 'rot_angle': 0, 'weight': {'db': '600g', 'ocr_rslt': '600g', 'score': 1.0, 'status': 'success'}}

        # self.th1.check_empty_time.connect(self.check_belt)
        # self.th1.changePixmap.connect(self.set_image)

        self.row_cnt = self.inspection_table.rowCount()
        self.col_cnt = self.inspection_table.columnCount()
        self.check_table_rowcnt = self.inspection_check_table.rowCount()
        self.check_table_colcnt = self.inspection_check_table.columnCount()
        self.reset_inspection_table()
        self.reset_inspection_check_table(prior_barcode)
        self.inspection_check_table.setAutoFillBackground(Qt.lightGray)
        self.inspection_check_table.cellClicked.connect(self.highlight_inspection)

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

                        if count == 2 and raw_score >= 0.9:
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
        # if prior_barcode != barcode:
        self.check_inspection(prior_barcode)

    # @pyqtSlot(dict)
    def get_result(self, result_dict):
        global prior_barcode
        inspection_table = self.inspection_table
        print(f'result --> {result_dict}')
        if result_dict.get('barcode'):
            barcode = int(result_dict['barcode'])
            prior_barcode = barcode
            self.reset_inspection_table()
            self.reset_inspection_check_table(barcode)

            # 이미지 불러오기
            label_image = result_dict['label_loc']
            from_path = '/mnt/vitasoft/salim/detected_labels'
            label_image = label_image.replace(from_path, root_path)
            self.show_image(label_image, result_dict['rot_angle'])

            # result_dict = self.inspect_result(result_dict)
            result_dict = {'product_name': ['유기농 표고버섯', '유기농 표고버섯', '100%', '승인'], 'weight': ['300g', '300g', '100%', '승인'], 'barcode': ['2500000145629', '2500000145629', '100%', '승인'], 'cert_mark': [['', '', '0%', '매칭실패']], 'cert_result': [['12100179 금사행버섯문과', '12100779 흙사랑버섯분과', '82%', '오류']]}
            # 인증정보 갯수만큼 행 늘리기
            mark_idx = len(result_dict['cert_result'])
            insert_row = mark_idx + self.row_cnt - 1
            if insert_row > self.row_cnt:
                diff = insert_row - self.row_cnt
                for row in range(diff):
                    inspection_table.insertRow(self.row_cnt+row)
                    self.inspection_check_table.insertRow(self.check_table_rowcnt+row)
                    self.inspection_check_table.setItem(self.check_table_rowcnt+row, 0, QTableWidgetItem('인증정보'))
                inspection_table.setSpan(0, self.col_cnt - 1, self.row_cnt + diff, 1)
                
            # ocr 결과 출력하기
            self.print_result(result_dict)

    def set_final_result(self):
        inspection_table = self.inspection_table
        result_items_lst = [inspection_table.item(row_idx, 3).text() for row_idx in range(1, self.row_cnt)] # ocr 항목들 결과값들 list
        final_result_text = '합격'
        text = QTableWidgetItem()
        text.setText(final_result_text)
        font = QFont()
        font.setFamily('나눔스퀘어_ac')
        font.setPointSize(40)
        font.setBold(True)
        text.setFont(font)
        text.setTextAlignment(Qt.AlignCenter)
        brush = QBrush(QColor(0, 0, 0))
        if '오류' in result_items_lst:
            final_result_text = '불합격'
            text.setText(final_result_text)
            brush = QBrush(QColor(0, 0, 255))
        elif '매칭실패' in result_items_lst:
            final_result_text = '유보'
            text.setText(final_result_text)
            brush = QBrush(QColor(128, 128, 128))
        text.setForeground(brush)
        inspection_table.setItem(0, self.col_cnt-1, text)
        return final_result_text

    def print_result(self, result_dict):
        global stacked_result
        print(f'result_dict --> {result_dict}')
        total_product_label_cnt = len(glob(os.path.join(root_path, str(result_dict['barcode'][0]), '*.png')))
        for row, key in enumerate(result_dict.keys()):
            for col in range(self.col_cnt-1):
                if row < 3:
                    self.inspection_table.setItem(row+1, col, QTableWidgetItem(result_dict[key][col]))
                else:
                    mark_lst = result_dict[key]
                    for idx, mark in enumerate(mark_lst):
                        self.inspection_table.setItem(row+1+idx, col, QTableWidgetItem(mark[col]))

        final_result_text = self.set_final_result()
        product_name = result_dict['product_name'][1] # db 에 있는 제품명
        if product_name in stacked_result.keys():
            stacked_result[product_name]['총인식'] = total_product_label_cnt
            stacked_result[product_name][final_result_text] += 1
        else:
            product = {}
            product[product_name] = {}
            print(stacked_result)



    def show_image(self, image_path, rot_angle):
        opencv_rot_dict = {90: cv2.ROTATE_90_CLOCKWISE, 180: cv2.ROTATE_180, 270: cv2.ROTATE_90_COUNTERCLOCKWISE}
        label_image = cv2.imread(image_path)
        label_image = cv2.cvtColor(label_image, cv2.COLOR_BGR2RGB)
        label_image = cv2.resize(label_image, (320, 320))
        if rot_angle != 0:
            label_image = cv2.rotate(label_image,opencv_rot_dict[rot_angle])
        height, width, channel = label_image.shape
        pixmap = QPixmap.fromImage(QImage(label_image.data, width, height, (channel * width), QImage.Format_RGB888))
        self.camera.setPixmap(pixmap)

    def check_inspection(self, barcode):
        global prior_barcode
        inspection_check_table = self.inspection_check_table
        inspection_row_cnt = inspection_check_table.rowCount()
        prior_barcode = barcode
        inspections = self.inspection_setting
        if barcode in inspections:
            for idx, check_item in enumerate(inspections[barcode]):
                item = inspection_check_table.item(idx+1, 0)
                color = Qt.gray
                if check_item == 'O':
                    color = Qt.white
                item.setBackground(color)


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
        self.set_inspection_setting()

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
        if prior_barcode != 0:
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
