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


class Condition(Enum):
    Circle = 1
    Square = 2


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
    CSV_HEADER = ['user_id', 'timestamp', 'condition', 'num_clicks', 'time_taken_in_ms', 'click_x', 'click_y', 'target_width',
                  'num_circles', 'screen_width', 'screen_height', 'helper_enabled']

    user_id = 0
    shape_width = 0
    num_circles = 0
    helper_enabled = False
    background_distraction_enabled = False
    num_targets = 0
    screen_width = 0
    screen_height = 0
    shape_coords = []
    shapes = []
    target_coords = []
    max_repetitions = 0                             # repetitions per condition
    distance_between_shapes = 0

    def __init__(self):
        self.parse_setup(sys.argv[1])
        self.init_shapes()
        self.init_shape_coords()
        self.timer = QtCore.QTime()
        self.mouse_moving = False
        self.current_participant_repetitions = 1    # counts how many conditions the participant has already completed
        self.latin_square = [[1, 2],
                             [2, 1]]
        self.current_latin_square_row = self.calculate_row_for_id()
        self.current_condition_index = 0
        self.current_condition = self.latin_square[self.current_latin_square_row][self.current_condition_index]
        self.df = pd.DataFrame(columns=self.CSV_HEADER)

    def parse_setup(self, filename):
        with open(filename) as file:
            data = json.load(file)['experiment']

            self.user_id = data['userId']
            self.shape_width = data['shapeWidth']
            self.num_circles = data['numberShapes']
            self.helper_enabled = data['helperEnabled']
            self.background_distraction_enabled = data['backgroundDistractionEnabled']
            self.num_targets = data['numberValidTargets']
            self.screen_width = data['screenWidth']
            self.screen_height = data['screenHeight']
            self.max_repetitions = data['repetitions']
            self.distance_between_shapes = data['distanceBetweenShapes']

    def calculate_row_for_id(self):
        if self.user_id <= len(self.latin_square):
            return self.user_id - 1

        else:
            to_subtract = int(self.user_id / len(self.latin_square))
            normalized_id = self.user_id - to_subtract * len(self.latin_square)
            return normalized_id - 1

    def init_shapes(self):
        self.init_shape_coords()
        self.init_shape_list()

    def init_shape_coords(self):
        self.shape_coords = spread(self.num_circles, self.screen_width - self.shape_width,
                                   self.screen_height - self.shape_width, self.shape_width,
                                   self.distance_between_shapes)

    def init_shape_list(self):
        for center in self.shape_coords:
            self.shapes.append(MyCircle(self, center, False))

        for x in range(self.num_targets):
            unique_timeout = 0
            shape = random.choice(self.shapes)
            while shape.is_target:
                unique_timeout += 1
                shape = random.choice(self.shapes)
                if unique_timeout > 1000:
                    break

            shape.set_is_target(True)
            self.target_coords\
                .append((shape.center[0] + self.shape_width / 2, shape.center[1] + self.shape_width / 2))

    def get_next_condition(self):
        self.current_condition_index += 1
        row = self.current_latin_square_row
        index = self.current_condition_index

        if row >= len(self.latin_square):
            row = 0

        if index >= len(self.latin_square[0]):
            index = 0

        self.current_condition = self.latin_square[row][index]

    def refresh(self):
        self.shape_coords.clear()
        self.target_coords.clear()
        self.shapes.clear()
        self.init_shapes()

    def refresh_participant(self):
        self.user_id += 1
        self.current_latin_square_row = self.calculate_row_for_id()
        self.current_condition_index = 0
        self.current_condition = self.latin_square[self.current_latin_square_row][self.current_condition_index]
        self.current_participant_repetitions = 1

    def handle_click(self, x, y):
        for coord in self.target_coords:
            if Condition(self.current_condition) == Condition.Circle:
                distance = math.sqrt((x - coord[0]) ** 2 + (y - coord[1]) ** 2)

                if distance <= self.shape_width / 2:
                    return True

            elif Condition(self.current_condition) == Condition.Square:
                # we adjusted the target coordinates to be at the center of the shape
                # in case of the 'square' target we need to adjust these values back to the top-left corner
                rect_x = coord[0] - self.shape_width / 2
                rect_y = coord[1] - self.shape_width / 2

                if rect_x < x < rect_x + self.shape_width:
                    if rect_y < y < rect_y + self.shape_width:
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
            'condition': Condition(self.current_condition).name,
            'num_clicks': click_counter,
            'time_taken_in_ms': time_taken,
            'click_x': mouse_press_event.x(),
            'click_y': mouse_press_event.y(),
            'target_width': self.shape_width,
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

        for shape in self.model.shapes:
            if shape.is_target:
                painter.setBrush(Qt.QBrush(QtCore.Qt.red, QtCore.Qt.SolidPattern))
            else:
                painter.setBrush(Qt.QBrush(QtCore.Qt.gray))

            if Condition(self.model.current_condition) == Condition.Circle:
                painter.drawEllipse(int(shape.x_coord), int(shape.y_coord),
                                    int(self.model.shape_width), int(self.model.shape_width))

            elif Condition(self.model.current_condition) == Condition.Square:
                painter.drawRect(int(shape.x_coord), int(shape.y_coord),
                                 int(self.model.shape_width), int(self.model.shape_width))

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
            if self.model.current_participant_repetitions >= len(Condition):
                self.model.print_log_to_stdout()
                self.application_state = ApplicationState.FINISHED
                self.reset_experiment()
            else:
                self.model.current_participant_repetitions += 1
                self.current_repetition = 1
                self.model.get_next_condition()

    def reset_experiment(self):
        self.current_repetition = 1
        self.model.refresh_participant()

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

        if distance_to_target.total_distance < self.model.shape_width + 50:  # TODO replace "50" with config value
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
