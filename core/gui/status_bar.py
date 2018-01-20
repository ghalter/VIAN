from PyQt5 import QtCore
from PyQt5.QtGui import *
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QMainWindow, QTextBrowser, QTextEdit, QSpacerItem, QSizePolicy, QMenu
from PyQt5.QtGui import QColor
class StatusBar(QtWidgets.QWidget):
    def __init__(self,main_window,server):
        super(StatusBar, self).__init__(main_window)

        self.main_window = main_window
        self.server = server
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)

        # self.setSizePolicy(QtWidgets.QSizePolicy.Preferred,QtWidgets.QSizePolicy.Preferred)

        self.label_selection = QtWidgets.QLabel(self)
        self.label_selection.setText("Selection: ")
        self.label_selection.setStyleSheet("QLabel{background: transparent;}")

        self.label_selection_length = QtWidgets.QLabel("0 Items", self)
        self.label_selection_length.setStyleSheet("QLabel{background: transparent;}")
        self.layout.addWidget(self.label_selection)
        self.layout.addWidget(self.label_selection_length)
        self.layout.addItem(QSpacerItem(20,20))

        self.label_server = QtWidgets.QLabel(self)
        self.label_server.setText("ELAN: ")
        self.label_server.setStyleSheet("QLabel{background: transparent;}")
        self.lbl_connection_status = QtWidgets.QLabel(self)
        self.lbl_connection_status.setStyleSheet("QLabel{background: transparent;}")
        self.layout.addWidget(self.label_server)
        self.layout.addWidget(self.lbl_connection_status)
        self.layout.addItem(QSpacerItem(20, 20))

        self.label_corpus = QtWidgets.QLabel(self)
        self.label_corpus.setText("Corpus: ")
        self.label_corpus.setStyleSheet("QLabel{background: transparent;}")
        self.lbl_corpus_status = QtWidgets.QLabel(self)
        self.lbl_corpus_status.setStyleSheet("QLabel{background: transparent;}")
        self.layout.addWidget(self.label_corpus)
        self.layout.addWidget(self.lbl_corpus_status)
        self.layout.addItem(QSpacerItem(20, 20))



        self.update_timer = QtCore.QTimer(self)
        self.update_timer.setInterval(1000)
        self.update_timer.timeout.connect(self.check_server_info)
        self.update_timer.start()
        self.check_server_info()
        # self.label_server.setFixedWidth(130)
        # self.lbl_connection_status.setFixedWidth(110)
        self.label_server.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignVCenter)
        self.show()

    def closeEvent(self, QCloseEvent):
        self.main_window.elan_status = None
        super(StatusBar, self).closeEvent(QCloseEvent)

    def check_server_info(self):
        if self.server.is_connected == True:
            self.lbl_connection_status.setText("Online")
            self.lbl_connection_status.setStyleSheet("QLabel {color : green; background: transparent;}")
        else:
            self.lbl_connection_status.setText("Offline")
            self.lbl_connection_status.setStyleSheet("QLabel {color : red; background: transparent;}")

        if self.main_window.corpus_client.is_connected == True:
            self.lbl_corpus_status.setText("Online")
            self.lbl_corpus_status.setStyleSheet("QLabel {color : green; background: transparent;}")
        else:
            self.lbl_corpus_status.setText("Offline")
            self.lbl_corpus_status.setStyleSheet("QLabel {color : red; background: transparent;}")

    def set_selection(self, selection):
        self.label_selection_length.setText(str(len(selection)) + " Items")

class OutputLine(QtWidgets.QWidget):
    def __init__(self,main_window):
        super(OutputLine, self).__init__(main_window)

        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.main_window = main_window

        self.text_line = QtWidgets.QLabel(self)
        self.text_line.setStyleSheet("QLabel{background: transparent;}")
        self.layout.addWidget(self.text_line)
        self.message_log = []

        self.text_time = QtCore.QTimer(self)
        self.text_time.setInterval(2000)
        self.text_time.timeout.connect(self.on_timeout)
        self.setMinimumWidth(100)

        # self.setFixedWidth(400)
        self.text_line.setMargin(0)
        self.message_queue = []
        self.log_wnd = None
        self.print_message("Ready")


    def print_message(self, msg = "", color = "white"):

        self.message_queue.append([msg, color])
        if self.text_time.remainingTime() < 0:
            self.on_timeout()

    def mouseDoubleClickEvent(self, QMouseEvent):
        log_wnd = MessageLogWindow(self)
        log_wnd.update_log()
        log_wnd.show()
        self.log_wnd = log_wnd



    def on_timeout(self):
        self.text_time.stop()
        if len(self.message_queue) > 0:
            curr_msg = self.message_queue[0]
            self.message_queue.remove(curr_msg)

            color = curr_msg[1]
            msg = curr_msg [0]

            self.text_line.setText(str(msg))
            if color is not "":
                self.setStyleSheet("QLabel{color : " + color + ";}")

            self.message_log.append(curr_msg)
            self.text_time.start()
            if self.log_wnd is not None:
                self.log_wnd.update_log()
        else:
            self.text_line.setText("")

class StatusVideoSource(QtWidgets.QWidget):
    def __init__(self,main_window):
        super(StatusVideoSource, self).__init__(main_window)
        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        lbl = QtWidgets.QLabel("Video Source: ")
        lbl.setStyleSheet("QLabel{background: transparent;}")
        self.layout.addWidget(lbl)
        self.lbl_source = QtWidgets.QLabel("VLC")
        self.lbl_source.setFixedWidth(100)
        self.lbl_source.setStyleSheet("QLabel{background: transparent;}")
        self.layout.addWidget(self.lbl_source)
        self.setStyleSheet("QWiget{background: transparent;}")

    def on_source_changed(self, source):
        if source == "VLC":
            self.lbl_source.setText("VLC")
            self.lbl_source.setStyleSheet("QLabel{color:Orange; background: transparent;}")
        else:
            self.lbl_source.setText("OpenCV")
            self.lbl_source.setStyleSheet("QLabel{color:Green; background: transparent;}")

    def mousePressEvent(self, a0: QMouseEvent):
        menu = QMenu(self)
        a_vlc = menu.addAction("\tAlways VLC")
        a_vlc.setCheckable(True)
        a_opencv = menu.addAction("\tAlways OpenCV")
        a_opencv.setCheckable(True)
        a_scale_depending = menu.addAction("\tTimeline Scale Depending")
        a_scale_depending.setCheckable(True)

        menu.popup(self.mapToGlobal(a0.pos())- QtCore.QPoint())

class StatusProgressBar(QtWidgets.QWidget):
    def __init__(self,main_window):
        super(StatusProgressBar, self).__init__(main_window)

        self.layout = QtWidgets.QHBoxLayout()
        self.setLayout(self.layout)
        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setStyleSheet("QProgressBar{background: transparent;}")
        self.layout.addWidget(self.progress_bar)

        self.hide()

    def set_progress(self, float):
        if self.isVisible() is False:
            self.show()
        self.progress_bar.setValue(float * 100)

    def on_finished(self):
        self.progress_bar.setValue(0)
        self.hide()


class MessageLogWindow(QMainWindow):
    def __init__(self, parent):
        super(MessageLogWindow, self).__init__(parent)
        self.message_bar = parent
        self.view = QTextEdit(self)
        self.setWindowTitle("Message Log")
        self.setCentralWidget(self.view)
        self.main_window = self.message_bar.main_window
        self.resize(600,400)

    def update_log(self):
        self.view.clear()
        self.messages = self.message_bar.message_log
        header = self.main_window.get_version_as_string()
        # for msg in self.messages:
        #     text += "<font color=\"" + msg[1] + "\">"
        #     text += msg[0] + "\n"
        # self.view.setPlainText(text)
        self.view.append(header)
        for i, msg in enumerate(self.messages):
            self.view.setTextColor(QColor(msg[1]))
            self.view.append(str(i) + ".  " + msg[0])




