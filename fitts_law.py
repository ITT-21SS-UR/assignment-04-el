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


DistanceToTarget = collections.namedtuple('DistanceToTarget', ['target', 'distance_x', 'distance_y', 'total_distance'])


class ApplicationState(Enum):
    EXPLANATION = 1
    EXPERIMENT = 2
    FINISHED = 3


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
    CSV_HEADER = ['user_id', 'timestamp', 'num_clicks', 'time_taken_in_ms', 'click_x', 'click_y', 'target_width',
                  'num_circles', 'screen_width', 'screen_height', 'helper_enabled']

    user_id = 0
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
    distance_between_circles = 0

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

            self.user_id = data['userId']
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
            self.target_coords\
                .append((circle.center[0] + self.circle_width / 2, circle.center[1] + self.circle_width / 2))

    def refresh(self):
        self.circle_coords.clear()
        self.target_coords.clear()
        self.circles.clear()
        self.init_circles()

    def handle_click(self, x, y):
        for coord in self.target_coords:
            distance = math.sqrt((x - coord[0]) ** 2 + (y - coord[1]) ** 2)

            if distance <= self.circle_width / 2:
                return True

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
            'user_id': self.user_id,
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
        self.df.to_csv(sys.stdout, index=False, header=(self.user_id == 1))  # print header only for first user


class FittsLawExperiment(QtWidgets.QWidget):
    DEFAULT_STYLE = "background-color: gray"
    painter = Qt.QPainter()

    def __init__(self, model):
        super().__init__()
        self.application_state = ApplicationState.EXPLANATION
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
        self.show()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        if self.application_state == ApplicationState.EXPLANATION:
            painter.setPen(QtCore.Qt.black)
            painter.setFont(Qt.QFont('Decorative', 36))
            painter.drawText(event.rect(), QtCore.Qt.AlignCenter,
                             "Get ready to move your mouse\nand click the red circle!\n\n\n"
                             "Left Click when you are ready to start!")
            return

        if self.application_state == ApplicationState.FINISHED:
            painter.setPen(QtCore.Qt.black)
            painter.setFont(Qt.QFont('Decorative', 36))
            painter.drawText(event.rect(), QtCore.Qt.AlignCenter,
                             "The experiment is finished!\nThank you for participating\n\n\n"
                             "Click anywhere in the window to\ncontinue with the next participant.")
            return

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
            QtGui.QCursor.setPos(self.mapToGlobal(QtCore.QPoint(self.start_pos[0], self.start_pos[1])))
            self.repaint()
            return

        if self.application_state == ApplicationState.FINISHED:
            self.application_state = ApplicationState.EXPLANATION
            self.repaint()
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
            self.application_state = ApplicationState.FINISHED
            self.reset_experiment()

    def reset_experiment(self):
        self.model.user_id += 1
        self.current_repetition = 0

    def mouseMoveEvent(self, ev):
        if self.application_state == ApplicationState.EXPLANATION:
            return

        if (abs(ev.x() - self.start_pos[0]) > 5) or (abs(ev.y() - self.start_pos[1]) > 5):
            self.model.start_timer()
            self.update()


class FittsLawWithHelper(FittsLawExperiment):

    def __init__(self, model):
        super().__init__(model)

    def mouseMoveEvent(self, ev):
        super().mouseMoveEvent(ev)
        distance_to_target = self.get_nearest_target(ev)

        # anti-solution
        # if distance_to_target.total_distance < self.model.circle_width + 50:
        #     QtGui.QCursor.setPos(self.mapToGlobal(QtCore.QPoint(ev.pos().x() - (distance_to_target.distance_x / 10),
        #                                                         ev.pos().x() - (distance_to_target.distance_x / 10))))

        if distance_to_target.total_distance < self.model.circle_width + 50:  # TODO replace "50" with config value
            QtGui.QCursor.setPos(self.mapToGlobal(
                QtCore.QPoint(ev.pos().x() + (distance_to_target.distance_x / 10) + 0.5,
                              ev.pos().y() + (distance_to_target.distance_y / 10) + 0.5)))


    def get_nearest_target(self, ev):
        nearest_target = None
        nearest_target_distance = 0
        for coord in self.model.target_coords:
            distance = abs((coord[0] - ev.x()) + (coord[1] - ev.y()))

            if nearest_target is None:
                nearest_target = coord
                nearest_target_distance = distance
            else:
                if distance < nearest_target_distance:
                    nearest_target = coord
                    nearest_target_distance = distance

            return DistanceToTarget(nearest_target, coord[0] - ev.x(), coord[1] - ev.y(), nearest_target_distance)


def main():
    app = QtWidgets.QApplication(sys.argv)
    model = FittsLawModel()
    if model.helper_enabled:
        experiment = FittsLawWithHelper(model)
    else:
        experiment = FittsLawExperiment(model)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
