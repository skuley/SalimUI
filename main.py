import sys
import time

import cv2
import pyzbar.pyzbar
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, QTimer, QDateTime, QModelIndex, Qt
from PyQt5.QtGui import QImage, QPixmap, QFont, QPalette, QBrush, QColor, QPainter
from PyQt5.QtWidgets import *
from glob import glob
import cv2

from SettingWindow import SettingWindow

form_class = uic.loadUiType("./Ui/save_main_ui.ui")[0]

webcam_status = False
stop_webcam_time = 3
check_inspection_daily = {
    'pattern': True,
    'name': True,
    'weight': True,
    'barcode': True,
    'cert_mark': True,
    'cert_info': True
}
undetected_label_cnt = 0
ocr_image = []


class Camera(QThread):
    changePixmap = pyqtSignal(QImage)
    # barcode_result = pyqtSignal(dict)
    check_empty_time = pyqtSignal()
    result = pyqtSignal(dict)
    tracking_count = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.active = False
        self.frames_path = ''
        self.frame_cnt = 0
        self.old_output = []

    def run(self):
        global webcam_status, stop_webcam_time, ocr_image
        video_path = 'A:/salim/sample_videos/20211104_0941.mp4'
        video = cv2.VideoCapture(video_path)
        while video.isOpened():
            if webcam_status:
                ret, frame = video.read()
                if ret:
                    if len(ocr_image) < 1:
                        ocr_image.append(frame)
                    # old_output, count = pp.tracking(frame, old_output, count)
                    # self.result.emit(ocr_parsed_result)
                    frame = cv2.resize(frame, (200, 200))
                    height, width, channel = frame.shape
                    qImg1 = QImage(frame.data, width, height, (channel * width), QImage.Format_RGB888)
                    self.changePixmap.emit(qImg1)

class UndetectedLabel(QThread):
    label_cnt = pyqtSignal(int)
    def __init__(self):
        super().__init__()

    def run(self):
        global undetected_label_cnt
        while True:
            undetected_label_cnt = len(glob('./Image/labels/undetected/*.png'))
            self.label_cnt.emit(undetected_label_cnt)

class WindowClass(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("흙살림")
        self.setFont(QFont('나눔스퀘어_ac', 12))

        self.actionSettings.triggered.connect(self.show_setting_window)
        # self.action_label_settings.triggered.connect(self.show_label_edit_window)

        # current_date_time 라벨 실시간
        timer = QTimer(self)
        timer.timeout.connect(self.show_time)
        timer.start()
        # -------- 프로그램 처음 실행시 open할 탭 화면 지정하기 --------
        # self.window_tab.setCurrentIndex(0)

        # -------- Tab1 검사화면 inspection_window --------
        self.btn_start.clicked.connect(self.start_webcam)
        self.btn_stop.clicked.connect(self.stop_webcam)

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

        self.th1 = Camera()
        self.th1.changePixmap.connect(self.set_image)
        self.th1.check_empty_time.connect(self.check_belt)
        self.th1.result.connect(self.show_result)
        self.th1.start()

        self.row_cnt = self.inspection_table.rowCount()
        self.col_cnt = self.inspection_table.columnCount()
        self.reset_table()

        # 인식 실패한 라벨
        self.undetected_label.setText(f'인식 실패한 라벨: {str(undetected_label_cnt)} 개')
        self.undetected_label.setFont(QFont('나눔스퀘어_ac', 15, QFont.Bold))

        # 실시간으로 인식 실패한 라벨 갯수 파악하기
        self.count_undetected_label = UndetectedLabel()
        self.count_undetected_label.start()
        self.count_undetected_label.label_cnt.connect(self.undetected_label_cnt)

        # 테이블(오류) 구역 error_table
        # error_table = self.error_table
        # error_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    @pyqtSlot(int)
    def undetected_label_cnt(self, label_cnt):
        self.undetected_label.setText(f'인식 실패한 라벨: {label_cnt} 개')
        self.undetected_label.setFont(QFont('나눔스퀘어_ac', 15, QFont.Bold))

    def reset_table(self):
        inspection_table = self.inspection_table
        inspection_check_list = self.inspection_check_list
        inspection_table.clear()
        inspection_check_list.clear()
        inspection_table.setRowCount(self.row_cnt)
        inspection_check_list.setRowCount(self.row_cnt)

        inspection_check_list.setAutoFillBackground(Qt.lightGray)
        rows_title = ['구분', '제품패턴', '제품명', '중량(입수)', '바코드', '인증마크']
        for row in range(self.row_cnt):
            inspection_check_list.setItem(row, 0, QTableWidgetItem(rows_title[row]))

        inspection_check_list.cellClicked.connect(self.test_fn)

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
        if not 'error' in result.keys():
            self.set_ocr_result_to_table(result)
        else:
            pass

    def set_ocr_result_to_table(self, result):
        inspection_table = self.inspection_table
        inspection_check_list = self.inspection_check_list
        barcode_num = result['barcode']

        row = inspection_table.rowCount()

        for row_idx, key in enumerate(result.keys()):
            if key == 'cert_nums':
                cert_num_lst = result['cert_nums']
                cert_num_len = len(cert_num_lst)
                for idx in range(0, cert_num_len):
                    row = row + idx
                    inspection_check_list.insertRow(row)
                    inspection_check_list.setItem(row, 0, QTableWidgetItem('인증정보' + str(idx + 1)))
                    inspection_table.insertRow(row)
                    cert_num_name = cert_num_lst[idx]['ocr_num'] + ' ' + cert_num_lst[idx]['ocr_name']

                    inspection_table.setItem(row, 0, QTableWidgetItem(cert_num_name))
                    inspection_table.setSpan(0, self.col_cnt, row + 1, 1)
            elif key == 'cert_mark':
                inspection_table.setItem(row_idx + 1, 0, QTableWidgetItem(result[key]['ocr']))
                inspection_table.setItem(row_idx + 1, 1, QTableWidgetItem(','.join(result[key]['db'])))
            else:
                inspection_table.setItem(row_idx + 1, 0, QTableWidgetItem(result[key]['ocr']))
                inspection_table.setItem(row_idx + 1, 1, QTableWidgetItem(result[key]['db']))

    def show_setting_window(self):
        self.setting_page = SettingWindow()
        self.setting_page.show()

    # ★ 당일 검사 활성화/비활성화
    def test_fn(self, row):
        inspection_check_list = self.inspection_check_list
        if row == 0:
            pass
        else:
            item = inspection_check_list.item(row, 0)
            # item.setBackground(QBrush(QColor(220, 220, 220)))
            # TODO : check_inspection_daily 활설화/해제 하기
            if item.background() == Qt.gray:
                item.setBackground(Qt.white)
            else:
                item.setBackground(Qt.gray)

    def start_webcam(self):
        global webcam_status
        if not webcam_status:
            reply = QMessageBox.question(self, 'Message', '촬영을 시작하시겠습니까?', QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                webcam_status = True
            else:
                webcam_status = False

    def stop_webcam(self):
        global webcam_status
        if webcam_status:
            webcam_status = False
            reply = QMessageBox.question(self, 'Message', '촬영을 정지하시겠습니까?', QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if reply == QMessageBox.Yes:
                webcam_status = False
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
