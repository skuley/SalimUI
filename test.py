import glob
from PyQt5.QtGui import QPixmap
import os

folder_name = 'A:/ETRI_FUEL/Sample1'
file_list = glob.glob(os.path.join(folder_name, "*"))
if len(file_list) > 0:
    png_list = []
    # 그림파일 확장자 명만 찾아서 리스트에 추가
    for file_name in file_list:
        if (file_name.find('.png') == len(file_name) - 4) or (file_name.find('.jpg') == len(file_name) - 4):
            png_list.append(file_name)

    # 그림파일을 하나씩 로드함
    if len(png_list) > 0:
        for png_file in png_list:
            pixmap = QPixmap(png_file)
            png_list.append(png_file)