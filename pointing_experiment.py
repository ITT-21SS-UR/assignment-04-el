import random
import sys
import json
import math

from PyQt5 import QtWidgets
from super_spreader import spread
from enum import Enum
from PyQt5 import Qt, QtCore, QtGui
from datetime import datetime
import pandas as pd
from pointing_technique import CursorHelper


LATIN_SQUARE_FULL = [[1, 3, 4, 2],
                     [4, 1, 2, 3],
                     [2, 4, 3, 1],
                     [3, 2, 1, 4]]

LATIN_SQUARE_SINGLE = [[1, 2],
                       [2, 1]]

TEST_TYPE_FULL = "full"
TEST_TYPE_SINGLE = "single"


class ApplicationState(Enum):
    EXPLANATION = 1
    EXPERIMENT = 2
    FINISHED = 3


class Condition(Enum):
    Circle = 1
    Square = 2
    CircleHelper = 3
    SquareHelper = 4


class MyShape:
    def __init__(self, model, center, is_target):
        self.model = model
        self.is_target = is_target
        self.center = center
        self.x_coord = center[0]
        self.y_coord = center[1]

    def set_is_target(self, is_target):
        self.is_target = is_target


class FittsLawModel:
    CSV_HEADER = ['user_id', 'timestamp', 'condition', 'num_clicks', 'time_taken_in_ms', 'click_x', 'click_y',
                  'target_width', 'num_circles', 'screen_width', 'screen_height', 'helper_enabled']
    MIN_SCREEN_WIDTH = 850
    MIN_SCREEN_HEIGHT = 650

    user_id = 0                                     # current participant id
    shape_width = 0                                 # width of the shapes on screen
    num_shapes = 0                                  # maximum number of shapes on screen
    helper_enabled = False                          # toggle for the pointing helper
    num_targets = 0                                 # number of valid clickable targets
    screen_width = 0                                # width of the widget
    screen_height = 0                               # height of the widget
    shape_coords = []                               # list of tuples containing the x and y coordinates of all shapes
    shapes = []                                     # list containing the shape objects (see class 'MyShape')
    target_coords = []                              # list of tuples containing the x and y coordinates of target shapes
    max_repetitions = 0                             # repetitions per condition
    distance_between_shapes = 0                     # minimum distance in pixels between the shapes
    test_type = ""                                  # either "full" or "single", determines the conditions
    helper_gravity_distance = 0                     # distance threshold for magnetic pointer helper activation

    def __init__(self):
        self.helper = ()
        self.parse_setup(sys.argv[1])
        self.init_shapes()
        self.init_shape_coords()
        self.timer = QtCore.QTime()
        self.mouse_moving = False
        self.current_participant_repetitions = 1    # counts how many conditions the participant has already completed
        self.latin_square = LATIN_SQUARE_FULL if self.test_type == TEST_TYPE_FULL else LATIN_SQUARE_SINGLE
        self.current_latin_square_row = self.calculate_row_for_id()
        self.current_condition_index = 0
        self.current_condition = self.latin_square[self.current_latin_square_row][self.current_condition_index]
        self.set_helper()
        self.df = pd.DataFrame(columns=self.CSV_HEADER)

    def parse_setup(self, filename):
        """
        Read config from config.json
        See config.json for comments on the settings
        """
        with open(filename) as file:
            data = json.load(file)['experiment']

            self.user_id = data['userId']
            self.shape_width = data['shapeWidth']
            self.num_shapes = data['numberShapes']
            self.helper_enabled = data['helperEnabled']
            self.num_targets = data['numberValidTargets']
            self.screen_width = \
                data['screenWidth'] if data['screenWidth'] >= self.MIN_SCREEN_WIDTH else self.MIN_SCREEN_WIDTH
            self.screen_height = \
                data['screenHeight'] if data['screenWidth'] >= self.MIN_SCREEN_HEIGHT else self.MIN_SCREEN_HEIGHT
            self.max_repetitions = data['repetitions']
            self.distance_between_shapes = data['distanceBetweenShapes']
            self.test_type = data['testType']
            self.helper_gravity_distance = data['helperGravityDistance']

    def calculate_row_for_id(self):
        """
        Calculates which row of the Latin Square to use for a given user ID
        :return: the **index** of the Latin Square row that should be used
        """
        if self.user_id <= len(self.latin_square):
            return self.user_id - 1

        else:
            to_subtract = int(self.user_id / len(self.latin_square))
            normalized_id = self.user_id - to_subtract * len(self.latin_square)
            return normalized_id - 1

    def init_shapes(self):
        self.init_shape_coords()
        self.init_shape_list()
        self.helper = CursorHelper(self.target_coords, self.shape_width, self.helper_gravity_distance)

    def init_shape_coords(self):
        self.shape_coords = spread(self.num_shapes, self.screen_width - self.shape_width,
                                   self.screen_height - self.shape_width, self.shape_width,
                                   self.distance_between_shapes)
        self.remove_shapes_from_text_area()

    def init_shape_list(self):
        """
        Initializes the list of shapes
        Then sets a defined number of shapes as valid target.
        The targets are chosen randomly and the operation may time out if the script is unable to find enough
        valid shapes (this means that less targets than specified will be set)
        """
        for center in self.shape_coords:
            self.shapes.append(MyShape(self, center, False))

        for x in range(self.num_targets):
            unique_timeout = 0
            shape = random.choice(self.shapes)
            while shape.is_target:                      # try to randomly find a shape that is not yet set as target
                unique_timeout += 1
                shape = random.choice(self.shapes)
                if unique_timeout > 1000:               # stop randomly picking shapes after a certain amount of tries
                    break

            shape.set_is_target(True)
            self.target_coords\
                .append((shape.center[0] + self.shape_width / 2, shape.center[1] + self.shape_width / 2))

    def get_next_condition(self):
        self.current_condition_index += 1
        self.current_condition = self.latin_square[self.current_latin_square_row][self.current_condition_index]
        self.set_helper()

    def set_helper(self):
        """
        This function can be used to add / remove the helper depending on Condition.
        Only enabled for test type "full", e.g. an experiment that includes tests with both enabled and disabled helper
        for the same participant
        """
        if self.test_type == TEST_TYPE_SINGLE:
            return

        if Condition(self.current_condition) == Condition.CircleHelper \
                or Condition(self.current_condition) == Condition.SquareHelper:
            self.helper_enabled = True

        else:
            self.helper_enabled = False

    def refresh(self):
        """ Refreshes the displayed shapes, by clearing the arrays and initializing new, random shapes """
        self.shape_coords.clear()
        self.target_coords.clear()
        self.shapes.clear()
        self.init_shapes()

    def refresh_participant(self):
        """ Resets all values concerning the participant """
        self.user_id += 1
        self.current_latin_square_row = self.calculate_row_for_id()
        self.current_condition_index = 0
        self.current_condition = self.latin_square[self.current_latin_square_row][self.current_condition_index]
        self.current_participant_repetitions = 1
        self.set_helper()

    def handle_click(self, x, y):
        """
        Checks if a mouse click hit a valid target.
        Returns True on hit.
        """
        for coord in self.target_coords:
            if Condition(self.current_condition) == Condition.Circle or \
                    Condition(self.current_condition) == Condition.CircleHelper:
                distance = math.sqrt((x - coord[0]) ** 2 + (y - coord[1]) ** 2)

                if distance <= self.shape_width / 2:
                    return True

            elif Condition(self.current_condition) == Condition.Square or \
                    Condition(self.current_condition) == Condition.SquareHelper:
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
            'num_circles': self.num_shapes,
            'screen_width': self.screen_width,
            'screen_height': self.screen_height,
            'helper_enabled': self.helper_enabled
        }, ignore_index=True)

    def print_log_to_stdout(self):
        self.df.to_csv(sys.stdout, index=False)

    def remove_shapes_from_text_area(self):
        """
        The upper area is reserved only for the ui text, no shapes should be drawn there
        Removes all elements that have a y-coordinate < 50 from the list of shape coordinates
        """
        for shape in self.shape_coords[:]:
            if shape[1] <= 50:
                self.shape_coords.remove(shape)


class FittsLawExperiment(QtWidgets.QWidget):
    DEFAULT_STYLE = "background-color: gray"
    painter = Qt.QPainter()

    def __init__(self, model):
        super().__init__()
        self.application_state = ApplicationState.EXPLANATION
        self.model = model
        self.circles_drawn = False
        self.start_pos = (int(self.model.screen_width / 2), int(self.model.screen_height / 2))
        self.progress_bar = Qt.QProgressBar(self)
        self.init_ui()
        self.current_click_counter = 0
        self.current_repetition = 1
        self.setCursor(QtCore.Qt.ArrowCursor)

    def init_ui(self):
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setStyleSheet(self.DEFAULT_STYLE)
        self.resize(self.model.screen_width, self.model.screen_height)
        self.setMouseTracking(True)
        progress_bar_area = Qt.QRect(self.model.screen_width / 2, 5, self.model.screen_width / 2 - 50, 25)
        self.progress_bar.setGeometry(progress_bar_area)
        self.progress_bar.setMaximum(self.model.max_repetitions * len(self.model.latin_square))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFormat('Progress: %v of %m (%p %)')
        self.show()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        if self.application_state == ApplicationState.EXPLANATION:
            painter.setPen(QtCore.Qt.black)
            painter.setFont(Qt.QFont('Decorative', 36))
            painter.drawText(event.rect(), QtCore.Qt.AlignCenter,
                             "Get ready to move your mouse\nand click the red shape!\n\n\n"
                             "Left Click when you are ready to start!")
            return

        if self.application_state == ApplicationState.FINISHED:
            painter.setPen(QtCore.Qt.black)
            painter.setFont(Qt.QFont('Decorative', 36))
            painter.drawText(event.rect(), QtCore.Qt.AlignCenter,
                             "The experiment is finished!\nThank you for participating\n\n\n"
                             "Click anywhere in the window to\ncontinue with the next participant.")
            return

        self.draw_task_hint(painter)

        painter.setPen(Qt.QPen(QtCore.Qt.black, 2, QtCore.Qt.SolidLine))
        for shape in self.model.shapes:
            if shape.is_target:  # targets should be filled with a red color
                painter.setBrush(Qt.QBrush(QtCore.Qt.red, QtCore.Qt.SolidPattern))
            else:
                painter.setBrush(Qt.QBrush(QtCore.Qt.gray))

            # draw different shapes based on condition
            if Condition(self.model.current_condition) == Condition.Circle or \
                    Condition(self.model.current_condition) == Condition.CircleHelper:
                painter.drawEllipse(int(shape.x_coord), int(shape.y_coord),
                                    int(self.model.shape_width), int(self.model.shape_width))

            elif Condition(self.model.current_condition) == Condition.Square or \
                    Condition(self.model.current_condition) == Condition.SquareHelper:
                painter.drawRect(int(shape.x_coord), int(shape.y_coord),
                                 int(self.model.shape_width), int(self.model.shape_width))

    def draw_task_hint(self, painter):
        painter.setPen(QtCore.Qt.black)
        painter.setFont(Qt.QFont('Decorative', 24))
        textarea = QtCore.QRect(5, 5, self.model.screen_width, 50)
        painter.drawText(textarea, QtCore.Qt.AlignLeft,
                         "Click on the red shape!")

    def keyPressEvent(self, ev):
        if ev.key() == QtCore.Qt.Key_H and ev.modifiers() & QtCore.Qt.ControlModifier:
            self.model.helper_enabled = not self.model.helper_enabled

    def mousePressEvent(self, ev):
        if self.application_state == ApplicationState.EXPLANATION:
            self.application_state = ApplicationState.EXPERIMENT
            self.progress_bar.setVisible(True)
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
        QtGui.QCursor.setPos(self.mapToGlobal(QtCore.QPoint(self.start_pos[0], self.start_pos[1])))
        time_taken = self.model.stop_timer()
        self.model.add_log_row(self.current_click_counter, time_taken, mouse_press_event)
        self.current_click_counter = 0
        self.current_repetition += 1
        self.progress_bar.setValue(self.progress_bar.value() + 1)

        # trigger the next condition, or finish the experiment if all conditions are completed
        if self.current_repetition > self.model.max_repetitions:
            if self.model.current_participant_repetitions >= len(self.model.latin_square):
                self.application_state = ApplicationState.FINISHED
                self.progress_bar.setVisible(False)
                self.reset_experiment()
            else:
                self.model.current_participant_repetitions += 1
                self.current_repetition = 1
                self.model.get_next_condition()

        self.repaint()

    def reset_experiment(self):
        self.current_repetition = 1
        self.model.refresh_participant()
        self.progress_bar.setValue(0)

    def mouseMoveEvent(self, ev):
        if self.application_state == ApplicationState.EXPLANATION or \
                self.application_state == ApplicationState.FINISHED:
            return

        if (abs(ev.x() - self.start_pos[0]) > 5) or (abs(ev.y() - self.start_pos[1]) > 5):
            self.model.start_timer()
            self.update()

        if self.model.helper_enabled:
            new_coords = self.model.helper.filter(ev)

            if new_coords is not None:
                QtGui.QCursor.setPos(self.mapToGlobal(self.model.helper.filter(ev)))

    def closeEvent(self, event):
        # print the logged data to stdout before closing
        self.model.print_log_to_stdout()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    model = FittsLawModel()
    experiment = FittsLawExperiment(model)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
