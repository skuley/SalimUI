from glob import glob
import cv2
from playsound import playsound
import pyzbar.pyzbar as pyzbar
import time
import pyaudio
import wave

CHUNK = 1024
imgs = glob('../sample_img/*')
error_cnt = 0
audio = pyaudio.PyAudio()
for img in imgs:
    img = cv2.imread(img)
    barcode = pyzbar.decode(img)
    print(barcode)
    if not barcode:
        playsound('alert.MP3')
        error_cnt += 1
        if error_cnt >= 1:

            playsound('error.MP3')
            break
    cv2.imshow('img', img)

    time.sleep(1)

print(error_cnt)