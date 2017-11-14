import os

from PyQt5 import uic
from enum import Enum

from core.gui.ewidgetbase import EDockWidget
from PyQt5.QtWidgets import QToolBar, QWidget, QHBoxLayout


class PerspectiveManager(EDockWidget):
    def __init__(self, main_window):
        super(PerspectiveManager, self).__init__(main_window)
        path = os.path.abspath("qt_ui/PerspectiveManager.ui")
        uic.loadUi(path, self)

        for persp in Perspective:
            self.comboBox_Perspective.addItem(persp.name)

        self.comboBox_Perspective.setCurrentText(Perspective.Annotation.name)
        self.comboBox_Perspective.currentIndexChanged.connect(self.on_perspective_changed)



    def on_perspective_changed(self):
        self.main_window.switch_perspective(self.comboBox_Perspective.currentText())



class Perspective(Enum):
        VideoPlayer = 1
        Annotation = 2
        ScreenshotsManager = 3
        Analyses = 4



