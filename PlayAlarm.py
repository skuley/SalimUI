from PyQt5.QtCore import pyqtSlot, QThread, pyqtSignal
import pygame
import time

class PlayAlarm(QThread):
    open_dialog = pyqtSignal(bool)
    error_cnt = 0
    play_status = False

    def __init__(self):
        super().__init__()
        self.cnt = 0
        # pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, allowedchanges=pygame.AUDIO_ALLOW_ANY_CHANGE)
        pygame.mixer.init(frequency=8000)
        # pygame.mixer.set_num_channels(1)
        sd_dict = {}
        sd_dict['section1'] = pygame.mixer.Sound(file='./Sound/alert.MP3')
        sd_dict['section2'] = pygame.mixer.Sound(file='./Sound/alert.MP3')
        sd_dict['section3'] = pygame.mixer.Sound(file='./Sound/error.MP3')
        self.sound = sd_dict

    def run(self):
        cnt = 0
        while True:
            if self.play_status and cnt != self.error_cnt:
                pygame.mixer.stop()
                cnt = self.error_cnt
                alarm = 'section1'
                loop = 0
                if 5 <= self.error_cnt < 10:
                    alarm = 'section2'
                elif 10 <= self.error_cnt:
                    self.open_dialog.emit(True)
                    alarm = 'section3'
                    loop = -1

                self.sound[alarm].play(loop)
                print(cnt, alarm, self.play_status)

    def stop(self):
        pygame.mixer.stop()
        # self.error_cnt = 0