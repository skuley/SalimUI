import sys

from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, QTimer, QDateTime, QModelIndex, Qt, QSettings
from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QHeaderView, QAbstractItemView, QApplication, QMessageBox, \
    QDialog, QDialogButtonBox
import time
import pygame
from playsound import playsound
from multiprocessing import Process
import threading


class Camera(QThread):
    cnt = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.count = 0

    def run(self):
        while True:
            self.count += 1
            self.cnt.emit(self.count)
            time.sleep(1)
            if self.count > 20:
                self.count = 0


form_class = uic.loadUiType("./Ui/test5.ui")[0]
alert_ui = uic.loadUiType("./Ui/alert.ui")[0]


class Alert(QDialog, alert_ui):
    def __init__(self):
        super().__init__()
        self.setupUi(self)


class PlaySound(QThread):
    open_dialog = pyqtSignal(bool)
    error_cnt = 0
    play_status = True

    def __init__(self):
        super().__init__()
        self.cnt = 0
        pygame.init()
        # pygame.mixer.set_num_channels(1)
        sd_dict = {}
        sd_dict['section1'] = pygame.mixer.Sound(file='./Sound/alert.MP3')
        sd_dict['section2'] = pygame.mixer.Sound(file='./Sound/alert.MP3')
        sd_dict['section3'] = pygame.mixer.Sound(file='./Sound/error.MP3')
        self.sound = sd_dict

    def run(self):
        cnt = 0
        while True:
            if self.play_status:
                if cnt != self.error_cnt:
                    pygame.mixer.stop()
                    cnt = self.error_cnt
                    alarm = 'section1'
                    loop = 0
                    if 5 <= self.error_cnt < 10:
                        alarm = 'section2'
                    elif 10 <= self.error_cnt:
                        alarm = 'section3'
                        self.open_dialog.emit(True)
                        loop = -1

                    # sound = pygame.mixer.Sound(alarm)
                    self.sound[alarm].play(loop)
                    print(cnt, alarm)

    def stop(self):
        pygame.mixer.stop()
        self.error_cnt = 0



class WindowClass(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.th1 = Camera()
        self.th1.start()
        self.th1.cnt.connect(self.show_tbl)

        self.th2 = PlaySound()
        self.th2.open_dialog.connect(self.show_dialog)
        self.th2.start()

        self.warning = 5
        self.error = 10

        self.alert_dialog = Alert()
        ok = self.alert_dialog.buttonBox.button(QDialogButtonBox.Ok)
        ok.setText('확인')
        ok.clicked.connect(self.set_off_alarm)

    def show_dialog(self):
        self.th2.play_status = False
        self.alert_dialog.show()

    def set_off_alarm(self):
        self.th2.stop()
        self.th2.cnt = 0
        # self.th2.play_status = False

    @pyqtSlot(int)
    def show_tbl(self, cnt):
        tableWidget = self.table
        tableWidget.setItem(0, 0, QTableWidgetItem(str(cnt)))
        if cnt == 1:
            self.th2.play_status=True

        self.th2.error_cnt = cnt
        # self.th2.play_status = True





if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    sys.exit(app.exec_())