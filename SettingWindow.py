from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

import pandas as pd

setting_class = uic.loadUiType("./Ui/setting.ui")[0]

class SettingWindow(QDialog, setting_class):
    def __init__(self):
        super().__init__()
        # self.resize(1000, 700)
        self.setupUi(self)
        self.setWindowTitle("설정")
        self.setFont(QFont('나눔스퀘어_ac', 12))

        setting_table = self.setting_table
        setting_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        setting_table.setFocusPolicy(Qt.NoFocus)
        setting_table.setSelectionMode(QAbstractItemView.NoSelection)
        setting_table.setAutoFillBackground(False)

        save = self.buttonBox.button(QDialogButtonBox.Save)
        save.setText('저장')
        save.clicked.connect(self.save_setting)

        self.buttonBox.button(QDialogButtonBox.Cancel).setText('취소')

        reset = self.buttonBox.button(QDialogButtonBox.Reset)
        reset.setText('초기화')
        reset.clicked.connect(self.reset_setting)
        self.settings = pd.read_excel('./Database/제품등록정보20211015.xlsx')
        # self.settings = pd.read_excel('제품등록정보20211015.xlsx', header=None)
        # self.settings = pd.read_excel('제품등록정보20211015.xlsx', names=list(self.settings.iloc[1])).iloc[1:].reset_index(drop=True).fillna('')
        self.insp_lst = ['ERP품목명', '제품패턴검사', '제품명검사', '중량(입수)검사', '바코드검사', '인증마크검사', '인증정보검사']
        self.setting_lst = self.settings[self.insp_lst].values.tolist()
        self.setting_table_row_count = self.setting_table.rowCount()
        self.get_inspection()

    def get_inspection(self):
        self.setting_table.setRowCount(0)
        for row_idx, item in enumerate(self.setting_lst):
            self.setting_table.insertRow(row_idx)
            check_box_lst = []
            col = 0
            for idx, string in enumerate(item):
                if idx == 0:
                    check_box_lst.insert(0, string)
                    product_name = QTableWidgetItem(str(string))
                    product_name.setFont(QFont('나눔스퀘어_ac', 9))
                    self.setting_table.setItem(row_idx, col, product_name)
                    self.setting_table.setColumnWidth(idx, 30)
                else:
                    ckbox = QCheckBox()
                    if string.__eq__('검사'):
                        ckbox.setCheckState(Qt.Checked)

                    cellWidget = QWidget()
                    layoutCB = QHBoxLayout(cellWidget)
                    layoutCB.addWidget(ckbox)
                    layoutCB.setAlignment(Qt.AlignCenter)
                    layoutCB.setContentsMargins(0, 0, 0, 0)
                    cellWidget.setLayout(layoutCB)
                    self.setting_table.setCellWidget(row_idx, col, cellWidget)
                col += 1
                # self.setting_table.resizeColumnsToContents()

    def save_setting(self):
        setting_table = self.setting_table
        row = setting_table.rowCount()
        col = setting_table.columnCount()
        row_lst = []
        table_lst = []
        for row_idx in range(row):
            for col_idx in range(col):
                if col_idx == 0:
                    row_lst.append(setting_table.item(row_idx, col_idx).data(0))
                else:
                    if setting_table.cellWidget(row_idx, col_idx).children()[1].checkState() == 2:
                        row_lst.append('검사')
                    else:
                        row_lst.append('pass')
            table_lst.append(row_lst.copy())
            row_lst.clear()
        table_lst.insert(0, self.insp_lst)
        save_df = pd.DataFrame(table_lst[1:], columns=table_lst[0])
        self.settings[self.insp_lst] = save_df
        try:
            self.settings.to_excel('./Database/제품등록정보20211015.xlsx', index=False)
            QMessageBox.about(self, 'Success', '성공적으로 저장되었습니다.')
        except PermissionError:
            QMessageBox.critical(self, 'Error', '엑셀 파일이 열려 있습니다.\n파일을 닫고 다시 설정 해주시길 바랍니다.')

    def reset_setting(self):
        self.get_inspection()