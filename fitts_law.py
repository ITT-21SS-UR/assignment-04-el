import os
import random
import sys
import json
import time
import collections
import math

from PyQt5 import QtWidgets
from super_spreader import spread
from enum import Enum
from PyQt5 import uic, Qt, QtCore, QtGui
from datetime import datetime
import pandas as pd


class ApplicationState(Enum):
    EXPLANATION = 1
    EXPERIMENT = 2

class MyCircle:
    def __init__(self, model, center, is_target):
        self.model = model
        self.is_target = is_target
        self.center = center
        self.x_coord = center[0]
        self.y_coord = center[1]

    def set_is_target(self, is_target):
        self.is_target = is_target


class FittsLawModel:
    CSV_HEADER = ['timestamp', 'num_clicks', 'time_taken_in_ms', 'click_x', 'click_y', 'target_width', 'num_circles',
                  'screen_width', 'screen_height', 'helper_enabled']

    circle_width = 0
    num_circles = 0
    helper_enabled = False
    background_distraction_enabled = False
    num_targets = 0
    screen_width = 0
    screen_height = 0
    circle_coords = []
    circles = []
    target_coords = []
    max_repetitions = 0

    def __init__(self):
        self.parse_setup(sys.argv[1])
        self.init_circles()
        self.init_circle_coords()
        self.timer = QtCore.QTime()
        self.mouse_moving = False
        self.df = pd.DataFrame(columns=self.CSV_HEADER)

    def parse_setup(self, filename):
        with open(filename) as file:
            data = json.load(file)['experiment']

            self.circle_width = data['circleWidth']
            self.num_circles = data['numberCircles']
            self.helper_enabled = data['helperEnabled']
            self.background_distraction_enabled = data['backgroundDistractionEnabled']
            self.num_targets = data['numberValidTargets']
            self.screen_width = data['screenWidth']
            self.screen_height = data['screenHeight']
            self.max_repetitions = data['repetitions']
            self.distance_between_circles = data['distanceBetweenCircles']

    def init_circles(self):
        self.init_circle_coords()
        self.init_circle_list()

    def init_circle_coords(self):
        self.circle_coords = spread(self.num_circles, self.screen_width - self.circle_width,
                                    self.screen_height - self.circle_width, self.circle_width,
                                    self.distance_between_circles)

    def init_circle_list(self):
        for center in self.circle_coords:
            self.circles.append(MyCircle(self, center, False))
            # self.target_coords.append(center)

        for x in range(self.num_targets):
            unique_timeout = 0
            circle = random.choice(self.circles)
            while circle.is_target:
                unique_timeout += 1
                circle = random.choice(self.circles)
                if unique_timeout > 1000:
                    break

            circle.set_is_target(True)
            self.target_coords.append(circle.center)

    def refresh(self):
        self.circle_coords.clear()
        self.circles.clear()
        self.init_circles()

    def handle_click(self, x, y):
        for coord in self.target_coords:
            distance = math.sqrt((x - coord[0]) ** 2 + (y - coord[1]) ** 2)

            if distance <= self.circle_width:
                return True

            # if coord[0] - self.circle_width < x < coord[0] + self.circle_width:
            #     if coord[1] - self.circle_width < y < coord[1] + self.circle_width:
            #         return True

        return False

    def start_timer(self):
        if not self.mouse_moving:
            self.mouse_moving = True
            self.timer.start()

    def stop_timer(self):
        if self.mouse_moving:
            self.mouse_moving = False
            return self.timer.elapsed()

    def add_log_row(self, click_counter, time_taken, mouse_press_event):
        self.df = self.df.append({
            'timestamp': datetime.now(),
            'num_clicks': click_counter,
            'time_taken_in_ms': time_taken,
            'click_x': mouse_press_event.x(),
            'click_y': mouse_press_event.y(),
            'target_width': self.circle_width,
            'num_circles': self.num_circles,
            'screen_width': self.screen_width,
            'screen_height': self.screen_height,
            'helper_enabled': self.helper_enabled
        }, ignore_index=True)

    def print_log_to_stdout(self):
        self.df.to_csv(sys.stdout)


class FittsLawExperiment(QtWidgets.QWidget):
    DEFAULT_STYLE = "background-color: gray"
    painter = Qt.QPainter()

    def __init__(self, model):
        super().__init__()
        self.application_state = ApplicationState.EXPLANATION
        self.ui = uic.loadUi("fitts_law_ui.ui", self)
        self.model = model
        self.circles_drawn = False
        self.start_pos = (int(self.model.screen_width / 2), int(self.model.screen_height / 2))
        self.init_ui()
        self.current_click_counter = 0
        self.current_repetition = 1
        self.setCursor(QtCore.Qt.ArrowCursor)

    def init_ui(self):
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setStyleSheet(self.DEFAULT_STYLE)
        self.resize(self.model.screen_width, self.model.screen_height)
        self.setMouseTracking(True)
        self.show_explanation()
        self.show()

    def show_explanation(self):
        self.ui.hintText.mousePressEvent = self.mousePressEvent
        self.ui.hintText.setAlignment(QtCore.Qt.AlignCenter)
        self.ui.hintText.setVisible(True)
        self.ui.hintText.viewport().setCursor(QtCore.Qt.ArrowCursor)
        self.ui.hintText.setText("Get ready to move your mouse and click the red circle!\n\n\n"
                                 "Left Click when you are ready to start!")

    def paintEvent(self, event):
        if self.application_state == ApplicationState.EXPLANATION:
            return

        painter = QtGui.QPainter(self)
        painter.setPen(Qt.QPen(QtCore.Qt.black, 2, QtCore.Qt.SolidLine))

        for circle in self.model.circles:
            if circle.is_target:
                painter.setBrush(Qt.QBrush(QtCore.Qt.red, QtCore.Qt.SolidPattern))
            else:
                painter.setBrush(Qt.QBrush(QtCore.Qt.gray))

            painter.drawEllipse(int(circle.x_coord), int(circle.y_coord),
                                int(self.model.circle_width), int(self.model.circle_width))

    def keyPressEvent(self, ev):
        pass

    def mousePressEvent(self, ev):
        if self.application_state == ApplicationState.EXPLANATION:
            self.application_state = ApplicationState.EXPERIMENT
            self.ui.hintText.setVisible(False)
            self.ui.hintText.setEnabled(False)
            QtGui.QCursor.setPos(self.mapToGlobal(QtCore.QPoint(self.start_pos[0], self.start_pos[1])))
            return

        if ev.button() == QtCore.Qt.LeftButton:
            self.current_click_counter += 1
            hit = self.model.handle_click(ev.x(), ev.y())
            if hit:
                self.handle_hit(ev)

    def handle_hit(self, mouse_press_event):
        self.model.refresh()
        self.update()
        QtGui.QCursor.setPos(self.mapToGlobal(QtCore.QPoint(self.start_pos[0], self.start_pos[1])))
        time_taken = self.model.stop_timer()
        self.model.add_log_row(self.current_click_counter, time_taken, mouse_press_event)
        self.current_click_counter = 0
        self.current_repetition += 1

        if self.current_repetition > self.model.max_repetitions:
            self.model.print_log_to_stdout()
            self.close()

    def mouseMoveEvent(self, ev):
        if self.application_state == ApplicationState.EXPLANATION:
            return

        if (abs(ev.x() - self.start_pos[0]) > 5) or (abs(ev.y() - self.start_pos[1]) > 5):
            self.model.start_timer()
            self.update()


def main():
    app = QtWidgets.QApplication(sys.argv)
    model = FittsLawModel()
    experiment = FittsLawExperiment(model)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
