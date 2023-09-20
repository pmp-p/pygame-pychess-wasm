import pygame
import os
from src.sound import Sound
from src.theme import Theme

class Config:

    def __init__(self):
        self.themes = []
        self._add_themes()
        self.idx = 0
        self.theme = self.themes[self.idx]
        self.font = pygame.font.SysFont('monospace', 18, bold=True)
        self.move_sound = Sound(
            os.path.join('assets/sounds/move.ogg'))
        self.capture_sound = Sound(
            os.path.join('assets/sounds/capture.ogg'))

    def change_theme(self):
        self.idx += 1
        self.idx %= len(self.themes)
        self.theme = self.themes[self.idx]

    def _add_themes(self):
        #theme pattern = white, black,last black,last white,move on white,move on black
        black = Theme('#f0f0f0','#1E1E1E','#64F0FF','#00DCF0','#F03232','#FAAAAA')
        green = Theme('#C9FFDF','#00B44B','#64F0FF','#00DCF0','#F03232','#FAAAAA')
        orange = Theme('#FFAF82','#E65000','#64F0FF','#00DCF0','#F03232','#FAAAAA')
        yellow = Theme('#FFEB9B','#D2A500','#64F0FF','#00DCF0','#F03232','#FAAAAA')
        purple = Theme('#DCCDFF','#551EFF','#64F0FF','#00DCF0','#F03232','#FAAAAA')
        self.themes = [green, black, orange,yellow, purple]
