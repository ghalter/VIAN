from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject
from core.corpus.shared.sqlalchemy_entities import *
import numpy as np

class VisScreenshot(QObject):
    onImageChanged = pyqtSignal(object)

    def __init__(self, dbscreenshot, features):
        super(VisScreenshot, self).__init__()
        self.dbscreenshot = dbscreenshot
        self.path = dbscreenshot.file_path
        self.image_cache = dict()
        if len(dbscreenshot.masks) > 0:
            self.mask = dbscreenshot.masks[0]
        else:
            self.mask = None
        self.current_image = np.zeros(shape=(50,35,3), dtype=np.uint8)
        self.features = features

class VisSegment(QObject):
    def __init__(self, id, project_id, start, end):
        super(VisSegment, self).__init__()
        self.t_start = start
        self.t_end = end
        self.id = id
        self.project_id = project_id
