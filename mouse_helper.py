from fitts_law import FittsLawExperiment
from PyQt5 import Qt, QtCore, QtGui
import math
import collections

DistanceToTarget = collections.namedtuple('DistanceToTarget', ['target', 'distance_x', 'distance_y'])


class FittsLawWithHelper(FittsLawExperiment):

    def __init__(self, model):
        super().__init__(model)

    def mouseMoveEvent(self, ev):
        super().mouseMoveEvent(ev)
        distance_to_target = self.get_nearest_target(ev)

        QtGui.QCursor.setPos(self.mapToGlobal(QtCore.QPoint(
            distance_to_target.target[0] - (distance_to_target.distance_x / 10),
            distance_to_target.target[1] - (distance_to_target.distance_y / 10)
        )))

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

            return DistanceToTarget(nearest_target, coord[0] - ev.x(), coord[1] - ev.y())
