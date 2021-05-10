import collections
import math
from PyQt5 import QtCore

DistanceToTarget = collections.namedtuple('DistanceToTarget', ['target', 'distance_x', 'distance_y', 'total_distance'])


class CursorHelper:
    """
    Helps the user click the target by modifying the position of the mouse cursor.
    This class takes the current cursor position and calculates the coordinates of the nearest target.
    Once the cursor is within a certain distance of that target, the cursor position will be set closer to the position
    of the target. In order to not "teleport" the cursor instantly, only a fraction of the distance is adjusted
    per cycle. This leads to a smooth yet quick magnetic pull towards the target coordinates.
    Once on the target, the cursor can only be moved away again by intentional quick movements. This further prevents
    accidentally "overshooting" the target location.

    :param target_coords: A list of tuples containing the x and y coordinates of valid targets
    :param shape_width: The width of the shapes on screen. This is used as a part of the distance calculation between
    cursor and target center
    :param gravity_distance: when the distance between cursor and target is below this value, the magnetic pull effect
    gets enabled
    """

    # factor by which the magnetic pull should be smoothed. Higher number = smoother and slower cursor adjustment
    MAGNETIC_PULL_SMOOTHING = 10

    def __init__(self, target_coords, shape_width, gravity_distance):
        super().__init__()
        self.target_coords = target_coords
        self.shape_width = shape_width
        self.gravity_distance = gravity_distance

    def filter(self, mouse_event):
        distance_to_target = self.get_nearest_target_distance(mouse_event)

        if distance_to_target.total_distance < self.shape_width / 2 + self.gravity_distance:
            return (QtCore.QPoint(mouse_event.pos().x()
                    + (distance_to_target.distance_x / self.MAGNETIC_PULL_SMOOTHING), mouse_event.pos().y()
                    + (distance_to_target.distance_y / self.MAGNETIC_PULL_SMOOTHING)))

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
            distance = math.hypot(ev.x() - coord[0], ev.y() - coord[1])

            if nearest_target is None:
                nearest_target = coord
                nearest_target_distance = distance
            else:
                if distance < nearest_target_distance:
                    nearest_target = coord
                    nearest_target_distance = distance

        return DistanceToTarget(nearest_target, nearest_target[0] - ev.x(), nearest_target[1] - ev.y(),
                                nearest_target_distance)
