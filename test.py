import sys

from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, QTimer, QDateTime, QModelIndex, Qt, QSettings
from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QHeaderView, QAbstractItemView, QApplication, QMessageBox, \
    QDialog, QDialogButtonBox
import time
import threading
from playsound import playsound

play_status = True

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

form_class = uic.loadUiType("./Ui/test.ui")[0]
alert_ui = uic.loadUiType("./Ui/alert.ui")[0]


class PlayAlarm(QThread):
    def __init__(self, alarm_type):
        super().__init__()
        self.alarm_type = alarm_type

    def run(self):
        if self.alarm_type == 5:
            playsound('./Sound/alert.MP3', True)
        else:
            while True:
                playsound('./Sound/alert.MP3', True)

    def kill(self):
        self.kill()


class Alert(QDialog, alert_ui):
    def __init__(self, alarm_type):
        super().__init__()
        self.setupUi(self)
        if alarm_type != 0:
            self.play_alarm = PlayAlarm(alarm_type)
            self.play_alarm.start()

        ok = self.buttonBox.button(QDialogButtonBox.Ok)
        ok.setText('확인')
        ok.clicked.connect(self.set_off_alarm)

    def set_off_alarm(self):
        global play_status
        self.play_alarm.kill()
        play_status = False

class WindowClass(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.th1 = Camera()
        self.th1.start()
        self.th1.cnt.connect(self.show_tbl)

        self.warning = 5
        self.error = 10

        self.alert_dialog = Alert(0)

    @pyqtSlot(int)
    def show_tbl(self, cnt):
        global play_status
        tableWidget = self.table
        tableWidget.setItem(0, 0, QTableWidgetItem(str(cnt)))

        if play_status:
            if cnt % self.warning == 0 or cnt % self.error == 0:
                # QMessageBox.critical(self,'Critical Title','Critical Message')
                self.alert_dialog.__init__(self.warning)
                self.alert_dialog.show()
                # self.warning_status = False


        print(cnt)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    sys.exit(app.exec_())
