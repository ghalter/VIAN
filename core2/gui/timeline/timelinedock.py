import os

import numpy as np


from PyQt5.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QLineEdit, QScrollArea
from PyQt5.QtGui import QColor, QPixmap, QImage, QGradient
from PyQt5.QtCore import QPoint, QPointF, QTimer, pyqtSignal, pyqtSlot, Qt, QRectF, QRect

from PyQt5 import QtCore, QtWidgets, QtGui, uic

from core2.container.project import VIANProject, Segmentation, Segment, MovieDescriptor
from core2.gui.docks.vian_dock import VIANDockWidget
from core2.gui.timeline.timeline_dataset import TimelineDataset


from core.data.computation import ms_to_string, ms_to_frames, frame2ms

class TimelineDock(VIANDockWidget):
    def __init__(self, main_window):
        super(TimelineDock, self).__init__(main_window, "Timeline")
        self.timeline = Timeline(self)
        self.setWidget(self.timeline)


class Timeline(QtWidgets.QWidget):
    CONTROLS_WIDTH = 150
    TIMEBAR_HEIGHT = 50

    onTimeChanged = pyqtSignal(int)

    def __init__(self, parent):
        super(Timeline, self).__init__(parent)
        self.entries = []

        self.is_scaling = False

        self.area = QScrollArea(self)
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.area)
        self.center = QtWidgets.QWidget()
        self.area.setWidget(self.center)

        # self.center.setFixedSize(10000, 512)
        self.relative_corner = QPoint(0,0)
        self.bars_widget = QWidget(self.center)

        self.controls_widget = QWidget(self.center)
        self.controls_widget.setStyleSheet("QWidget{background: rgb(100,200,100);}")

        self.duration = 720000000
        self.time_scale = 0.001

        self.center.setFixedSize(int(self.duration * self.time_scale), 512)

        self.timebar = TimebarDrawing(self.center, self)
        self.timebar.setFixedHeight(self.TIMEBAR_HEIGHT)
        self.timebar.move(self.CONTROLS_WIDTH, 0)
        # self.center.addWidget(self.controls_widget)
        # self.center.addWidget(self.bars_widget)

        self.controls_widget.move(0, self.TIMEBAR_HEIGHT)
        self.controls_widget.setFixedWidth(self.CONTROLS_WIDTH)
        self.bars_widget.move(self.CONTROLS_WIDTH, self.TIMEBAR_HEIGHT)

        self.create_entry(TimelineControl(self), TimelineBar(self))
        self.create_entry(TimelineControl(self), TimelineBar(self))
        self.create_entry(TimelineControl(self), TimelineBar(self))

        self.area.horizontalScrollBar().valueChanged.connect(self._scroll_h)
        self.area.verticalScrollBar().valueChanged.connect(self._scroll_v)


    def create_entry(self, ctrl, bar):
        ctrl.setParent(self.controls_widget)
        bar.setParent(self.bars_widget)
        ctrl.bar = bar
        self.entries.append(dict(ctrl=ctrl, bar=bar))
        self._redraw()

    def _scroll_h(self):
        value = int(self.area.horizontalScrollBar().value() - 9)
        print(self.area.mapToParent(QtCore.QPoint(value, 0)))
        self.controls_widget.move(self.area.mapToParent(QtCore.QPoint(value, 0)).x(), self.TIMEBAR_HEIGHT)

        self.relative_corner = QtCore.QPoint(value, self.relative_corner.y())
        self.timebar.move(self.relative_corner.x() + self.CONTROLS_WIDTH, 0)
        # self.update_visualizations()

    def _scroll_v(self):
        value = self.area.verticalScrollBar().value()
        # self.time_bar.move(self.scrollArea.mapToParent(QtCore.QPoint(0, value)))
        self.relative_corner = QtCore.QPoint(self.relative_corner.x(), value)
        # self.time_bar.move(self.relative_corner)
        # self.time_bar.raise_()
        # self.time_scrubber.raise_()

    def _redraw(self):
        y = 0
        for e in self.entries:
            ctrl, bar = e['ctrl'], e['bar']
            # ctrl = TimelineControl()
            ctrl.move(0, y)
            ctrl.update_bar()
            y += ctrl.height()
        self.controls_widget.setFixedHeight(y)
        self.bars_widget.setFixedHeight(y)

    def scaled_duration(self, fx = 1.0):
        return int(self.time_scale * self.duration / fx)

    def wheelEvent(self, a0: QtGui.QWheelEvent) -> None:

        if self.is_scaling:
            if a0.angleDelta().y() > 0:
                self._scale_timeline(self.time_scale + 0.001)
            else:
                self._scale_timeline(self.time_scale - 0.001)
        else:
            super(Timeline, self).wheelEvent(a0)

    def _scale_timeline(self, new_value):
        self.time_scale = np.clip(new_value, 0.0001, 1000)
        self.update()

    def resizeEvent(self, a0: QtGui.QResizeEvent) -> None:
        super(Timeline, self).resizeEvent(a0)
        self.timebar.setFixedWidth(self.width())

    def keyPressEvent(self, QKeyEvent):
        if QKeyEvent.key() == Qt.Key_Control:
            self.area.verticalScrollBar().setEnabled(False)
            self.is_scaling = True
        elif QKeyEvent.key() == Qt.Key_Shift:
            pass
            # self.shift_pressed = True
            # self.sticky_move = True
        else:
            QKeyEvent.ignore()
        super(Timeline, self).keyPressEvent(QKeyEvent)

    def keyReleaseEvent(self, QKeyEvent):
        if QKeyEvent.key() == Qt.Key_Control:
            self.is_scaling = False
            self.area.verticalScrollBar().setEnabled(True)
            # self.main_window.keyReleaseEvent(QKeyEvent)
        elif QKeyEvent.key() == Qt.Key_Shift:
            pass
            # self.shift_pressed = False
            # self.sticky_move = False
        else:
            QKeyEvent.ignore()
        super(Timeline, self).keyReleaseEvent(QKeyEvent)



    @pyqtSlot(object)
    def on_loaded(self, project:VIANProject):
        if isinstance(project.media_descriptor, MovieDescriptor):
            self.duration = project.media_descriptor.duration
        self._init_timeline()

    def _init_timeline(self):
        self.bars_widget.setFixedWidth(self.scaled_duration())
        self.center.setFixedWidth(self.scaled_duration() + self.CONTROLS_WIDTH)
        self.update()


class TimelineControl(QWidget):
    def __init__(self, parent):
        super(TimelineControl, self).__init__(parent)
        self.bar = None

        self.setLayout(QVBoxLayout())
        self.line_edit_name = QLabel(self)
        self.line_edit_name.setText("New Segmentation")
        self.layout().addWidget(self.line_edit_name)

    def update_bar(self):
        if self.bar is not None:
            self.bar.move(self.bar.x(), self.y())
            self.bar.setFixedHeight(self.height())

class TimelineBar(QWidget):
    def __init__(self, parent):
        super(TimelineBar, self).__init__(parent)
        self.timeline = parent
        self.background_color = QColor(255,0,0)
        self.resize(self.timeline.scaled_duration(),self.height())

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing, True)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        pen.setColor(QtGui.QColor(255, 255, 255))
        qp.fillRect(self.rect(), self.background_color)
        qp.end()

class TimeBar(QWidget):
    def __init__(self, parent):
        super(TimeBar, self).__init__(parent)


class TimeScrubber(QWidget):
    def __init__(self, parent):
        super(TimeScrubber, self).__init__(parent)


class TimebarDrawing(QtWidgets.QWidget):
    def __init__(self, parent, timeline):
        super(TimebarDrawing, self).__init__(parent)
        self.timeline = timeline
        self.background_color = QtGui.QColor(50,50,50,230)
        self.scale_image = None

        self.colormetry_progress = 0

        self.is_hovered = False
        self.was_playing = False
        self.a = 10
        self.b = 50
        self.c = 200
        self.d = 1000
        self.split_threshold = 100
        self.time_offset = 0
        self.show()

    def paintEvent(self, QPaintEvent):
        qp = QtGui.QPainter()
        pen = QtGui.QPen()
        qp.begin(self)
        qp.setRenderHint(QtGui.QPainter.Antialiasing, True)
        qp.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        pen.setColor(QtGui.QColor(255, 255, 255))
        qp.fillRect(self.rect(),self.background_color)

        t_start = float(self.pos().x()) * self.timeline.time_scale
        t_end = t_start + float(self.width() * self.timeline.time_scale)
        p_break = np.ceil(np.log10(self.split_threshold * self.timeline.time_scale))
        self.time_offset = 0

        if (t_end - t_start) > 100000:
            res_factor = 1
        elif (t_end - t_start) > 10000:
            res_factor = 10
        elif (t_end - t_start) > 1000:
            res_factor = 100
        else:
            res_factor = 1000

        # if the zoom allows to display minutes or hours, we want the labels to be set in a
        # heximal manner
        if p_break >= 2:
            decimal_heximal = 0.6
        else:
            decimal_heximal = 1.0

        h_text = 15
        h = 15
        h2 = 45
        print(int(t_start * res_factor), int(t_end * res_factor))
        for i in range(int(t_start * res_factor), int(t_end * res_factor)):
            pos = round((float(i / res_factor) - t_start) / self.timeline.time_scale + self.time_offset)

            if (i * 1000 / res_factor) % (((10 ** (p_break))* 1000) * decimal_heximal) == 0:
                s = ms_to_string(i * (1000 / res_factor), include_ms=p_break < 0.01)
                qp.drawText(QtCore.QPoint(pos - (len(s) / 2) * 7, h_text), s)

            if (i * 1000 / res_factor) % (((10 ** p_break * 1000)) * decimal_heximal) == 0:
                h = 25
                pen.setWidth(1)
                qp.setPen(pen)
                a = QtCore.QPoint(pos, h)
                b = QtCore.QPoint(pos, h2)
                qp.drawLine(a, b)

            elif (i * 1000 / res_factor) % int(((10 ** p_break * 1000)* decimal_heximal / 2)) == 0:
                h = 30
                pen.setWidth(1)
                qp.setPen(pen)
                a = QtCore.QPoint(pos, h)
                b = QtCore.QPoint(pos, h2)
                qp.drawLine(a, b)
            elif (i * 1000 / res_factor) % int(((10 ** (p_break - 1)) * 1000)) == 0:
                h = 35
                pen.setWidth(1)
                qp.setPen(pen)
                a = QtCore.QPoint(pos, h)
                b = QtCore.QPoint(pos, h2)
                qp.drawLine(a, b)

        # Draw the colormetry progress Bar
        if  0.0 < self.colormetry_progress:
            pen.setColor(QtGui.QColor(35,165,103))
            pen.setWidth(3)
            t_progress = (self.timeline.duration * self.colormetry_progress)
            qp.setPen(pen)
            qp.drawLine(QPoint(0, self.height() - 2),
                        QPoint((t_progress - (self.pos().x()) * self.timeline.scale) /self.timeline.scale, self.height() - 2))
        qp.end()

    # def mouseReleaseEvent(self, QMouseEvent):
    #     self.timeline.set_time_indicator_visibility(False)
    #     if QMouseEvent.button() == Qt.LeftButton:
    #         if self.was_playing:
    #             self.timeline.main_window.player.play()
    #         if self.timeline.selector is not None:
    #             self.timeline.end_selector()
    #
    #     if QMouseEvent.button() == Qt.RightButton:
    #         if self.timeline.selector is not None:
    #             self.timeline.end_selector()
    #         QMouseEvent.ignore()
    #
    # def mousePressEvent(self, QMouseEvent):
    #     self.was_playing = self.timeline.main_window.player.is_playing()
    #     self.timeline.set_time_indicator_visibility(True)
    #     if QMouseEvent.buttons() & Qt.LeftButton:
    #         if self.was_playing:
    #             self.timeline.main_window.player.pause()
    #         pos = self.mapToParent(QMouseEvent.pos()).x()
    #
    #         self.timeline.move_scrubber(pos)
    #         if self.timeline.shift_pressed:
    #             self.timeline.start_selector(self.mapToParent(QMouseEvent.pos()))
    #
    #     if QMouseEvent.buttons() & Qt.RightButton:
    #         self.timeline.start_selector(self.mapToParent(QMouseEvent.pos()))
    #
    # def mouseMoveEvent(self, QMouseEvent):
    #     if QMouseEvent.buttons() & Qt.LeftButton:
    #         pos = self.mapToParent(QMouseEvent.pos()).x()
    #         pos += 1 # offset correction
    #         self.timeline.move_scrubber(pos)
    #         # self.timeline.time_scrubber.move(pos, 0)
    #         # self.timeline.main_window.player.set_media_time(pos * self.timeline.scale)
    #         if self.timeline.shift_pressed and self.timeline.selector is not None:
    #             self.timeline.move_selector(self.mapToParent(QMouseEvent.pos()))
    #
    #     if QMouseEvent.buttons() & Qt.RightButton:
    #         if self.timeline.selector is not None:
    #             self.timeline.move_selector(self.mapToParent(QMouseEvent.pos()))
    #         else:
    #             pos = self.mapToParent(QMouseEvent.pos()).x()
    #             self.timeline.move_scrubber(pos)