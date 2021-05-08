import collections
from PyQt5 import QtCore

DistanceToTarget = collections.namedtuple('DistanceToTarget', ['target', 'distance_x', 'distance_y', 'total_distance'])


class CursorHelper:

    def __init__(self, target_coords, shape_width):
        super().__init__()
        self.target_coords = target_coords
        self.shape_width = shape_width

    def filter(self, mouse_event):
        distance_to_target = self.get_nearest_target_distance(mouse_event)

        if distance_to_target.total_distance < self.shape_width + 50:  # TODO replace "50" with config value
            return (QtCore.QPoint(mouse_event.pos().x() + (distance_to_target.distance_x / 10),
                    mouse_event.pos().y() + (distance_to_target.distance_y / 10)))

        else:
            return None

    def get_nearest_target_distance(self, ev):
        """
        Gets the distance to the nearest valid target. Is designed to support multiple targets, and returns
        the distance to the nearest one.
        """
        nearest_target = None
        nearest_target_distance = 0
        for coord in self.target_coords:
            distance = abs((coord[0] - ev.x()) + (coord[1] - ev.y()))

            if nearest_target is None:
                nearest_target = coord
                nearest_target_distance = distance
            else:
                if distance < nearest_target_distance:
                    nearest_target = coord
                    nearest_target_distance = distance

            return DistanceToTarget(nearest_target, coord[0] - ev.x(), coord[1] - ev.y(), nearest_target_distance)