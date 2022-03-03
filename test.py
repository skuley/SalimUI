import sys

from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal, QTimer, QDateTime, QModelIndex, Qt, QSettings
from PyQt5.QtWidgets import QMainWindow, QTableWidgetItem, QHeaderView, QAbstractItemView, QApplication, QMessageBox
import time


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

class WindowClass(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.th1 = Camera()
        self.th1.start()
        self.th1.cnt.connect(self.show_tbl)

        self.warning = 5
        self.error = 10

    @pyqtSlot(int)
    def show_tbl(self, cnt):
        tableWidget = self.table
        tableWidget.setItem(0, 0, QTableWidgetItem(str(cnt)))

        if cnt % self.warning == 0 or cnt % self.error == 0:
            QMessageBox.critical(self,'Critical Title','Critical Message')


        print(cnt)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = WindowClass()
    myWindow.show()
    sys.exit(app.exec_())
