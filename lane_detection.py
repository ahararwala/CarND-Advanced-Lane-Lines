from perspective_transform import PerspectiveTransform
from processing import *

import numpy as np
import cv2


class Line:
    POLYNOMIAL_COEFFICIENT = 719

    def __init__(self, n_images=1, x=None, y=None):
        self.n_images = n_images  # history to keep
        self.x_recent = []  # most recent x
        self.pixels = []  # # pixels added per image
        self.x_average = None  # average of x over the last n
        self.best_fit = None  # average polynomial coefficients
        self.current_coefficient = None  # current polynomial coefficients
        self.current_fit_coefficient_poly = None  # polynomial for the current fit
        self.best_fit_poly = None  # average of the last n polynomial
        self.xs = None  # x values for found line pixels
        self.ys = None
        self.update(x, y)

    def update(self, x, y):
        self.xs = x
        self.ys = y

        self.pixels.append(len(self.xs))
        self.x_recent.extend(self.xs)

        if len(self.pixels) > self.n_images:
            n_x_to_remove = self.pixels.pop(0)
            self.x_recent = self.x_recent[n_x_to_remove:]

        self.x_average = np.mean(self.x_recent)

        self.current_coefficient = np.polyfit(self.xs, self.ys, 2)

        if self.best_fit is None:
            self.best_fit = self.current_coefficient
        else:
            self.best_fit = (self.best_fit * (self.n_images - 1) + self.current_coefficient) / self.n_images

        self.current_fit_coefficient_poly = np.poly1d(self.current_coefficient)
        self.best_fit_poly = np.poly1d(self.best_fit)

    def is_current_fit_parallel(self, candidate_line, threshold=(0, 0)):
        first_coefficient_delta = np.abs(self.current_coefficient[0] - candidate_line.current_coefficient[0])
        second_coefficient_delta = np.abs(self.current_coefficient[1] - candidate_line.current_coefficient[1])
        is_parallel = first_coefficient_delta < threshold[0] and second_coefficient_delta < threshold[1]

        return is_parallel

    def get_current_fit_distance(self, other_line):
        return np.abs(self.current_fit_coefficient_poly(self.POLYNOMIAL_COEFFICIENT)
                      - other_line.current_fit_coefficient_poly(self.POLYNOMIAL_COEFFICIENT))

    def get_best_fit_distance(self, candidate_line):
        return np.abs(
            self.best_fit_poly(self.POLYNOMIAL_COEFFICIENT) - candidate_line.best_fit_poly(self.POLYNOMIAL_COEFFICIENT))


class LaneDetector:
    ARROW_TIP_LENGTH = 0.5
    VERTICAL_OFFSET = 400
    HISTOGRAM_WINDOW = 7
    POLYNOMIAL_COEFFICIENT = 719
    LINE_SEGMENTS = 10

    def __init__(self, src, dst, n_images=1, calibration=None, line_segments=LINE_SEGMENTS, offset=0):
        self.n_images = n_images
        self.camera_calibration = calibration
        self.line_segments = line_segments
        self.image_offset = offset
        self.left_line = None
        self.right_line = None
        self.center_poly = None
        self.curvature = 0.0
        self.offset = 0.0
        self.perspective = PerspectiveTransform(src, dst)
        self.distances = []

    @staticmethod
    def _acceptable_lanes(left, right):
        if len(left[0]) < 3 or len(right[0]) < 3:
            return False
        else:
            new_left = Line(y=left[0], x=left[1])
            new_right = Line(y=right[0], x=right[1])
            return acceptable_lanes(new_left, new_right)

    def _check_lines(self, left_x, left_y, right_x, right_y):
        left_found, right_found = False, False

        if self._acceptable_lanes((left_x, left_y), (right_x, right_y)):
            left_found, right_found = True, True
        elif self.left_line and self.right_line:
            if self._acceptable_lanes((left_x, left_y), (self.left_line.ys, self.left_line.xs)):
                left_found = True
            if self._acceptable_lanes((right_x, right_y), (self.right_line.ys, self.right_line.xs)):
                right_found = True

        return left_found, right_found

    def _draw_info(self, image):
        font = cv2.FONT_HERSHEY_SIMPLEX
        text_curvature = 'Curvature: {}'.format(self.curvature)
        cv2.putText(image, text_curvature, (50, 50), font, 1, (255, 255, 255), 2)
        text_position = '{}m {} of center'.format(abs(self.offset), 'left' if self.offset < 0 else 'right')
        cv2.putText(image, text_position, (50, 100), font, 1, (255, 255, 255), 2)

    def _draw_overlay(self, image):
        overlay = np.zeros([*image.shape])
        mask = np.zeros([image.shape[0], image.shape[1]])
        lane_area = calculate_lane_area((self.left_line, self.right_line), image.shape[0], 20)
        mask = cv2.fillPoly(mask, np.int32([lane_area]), 1)
        mask = self.perspective.inverse_transform(mask)
        overlay[mask == 1] = (255, 128, 0)
        selection = (overlay != 0)
        image[selection] = image[selection] * 0.3 + overlay[selection] * 0.7
        mask[:] = 0
        mask = draw_polynomial(mask, self.center_poly, 20, 255, 5, True, self.ARROW_TIP_LENGTH)
        mask = self.perspective.inverse_transform(mask)
        image[mask == 255] = (255, 75, 2)
        mask[:] = 0
        mask = draw_polynomial(mask, self.left_line.best_fit_poly, 5, 255)
        mask = draw_polynomial(mask, self.right_line.best_fit_poly, 5, 255)
        mask = self.perspective.inverse_transform(mask)
        image[mask == 255] = (255, 200, 2)

    def _process_history(self, image, left_found, right_found, left_x, left_y, right_x, right_y):
        if self.left_line and self.right_line:
            left_x, left_y = lane_detection_history(image, self.left_line.best_fit_poly, self.line_segments)
            right_x, right_y = lane_detection_history(image, self.right_line.best_fit_poly, self.line_segments)

            left_found, right_found = self._check_lines(left_x, left_y, right_x, right_y)
        return left_found, right_found, left_x, left_y, right_x, right_y

    def _process_histogram(self, image, left_found, right_found, left_x, left_y, right_x, right_y):
        if not left_found:
            left_x, left_y = lane_detection_histogram(image, self.line_segments,
                                                      (self.image_offset, image.shape[1] // 2),
                                                      h_window=self.HISTOGRAM_WINDOW)
            left_x, left_y = remove_outliers(left_x, left_y)
        if not right_found:
            right_x, right_y = lane_detection_histogram(image, self.line_segments,
                                                        (image.shape[1] // 2, image.shape[1] - self.image_offset),
                                                        h_window=self.HISTOGRAM_WINDOW)
            right_x, right_y = remove_outliers(right_x, right_y)

        if not left_found or not right_found:
            left_found, right_found = self._check_lines(left_x, left_y, right_x, right_y)

        return left_found, right_found, left_x, left_y, right_x, right_y

    def _draw(self, image, original_image):
        if self.left_line and self.right_line:
            self.distances.append(self.left_line.get_best_fit_distance(self.right_line))
            self.center_poly = (self.left_line.best_fit_poly + self.right_line.best_fit_poly) / 2
            self.curvature = curvature(self.center_poly)
            self.offset = (image.shape[1] / 2 - self.center_poly(self.POLYNOMIAL_COEFFICIENT)) * 3.7 / 700
            self._draw_overlay(original_image)
            self._draw_info(original_image)

    def _update_lane_left(self, found, x, y):
        if found:
            if self.left_line:
                self.left_line.update(y=x, x=y)
            else:
                self.left_line = Line(self.n_images, y, x)

    def _update_lane_right(self, found, x, y):
        if found:
            if self.right_line:
                self.right_line.update(y=x, x=y)
            else:
                self.right_line = Line(self.n_images, y, x)

    def process_image(self, image):
        original_image = np.copy(image)

        image = self.camera_calibration.undistort(image)
        image = lane_mask(image, self.VERTICAL_OFFSET)
        image = self.perspective.transform(image)

        left_found = right_found = False
        left_x = left_y = right_x = right_y = []

        left_found, right_found, left_x, left_y, right_x, right_y = \
            self._process_history(image, left_found, right_found, left_x, left_y, right_x, right_y)
        left_found, right_found, left_x, left_y, right_x, right_y = \
            self._process_histogram(image, left_found, right_found, left_x, left_y, right_x, right_y)

        self._update_lane_left(left_found, left_x, left_y)
        self._update_lane_right(right_found, right_x, right_y)
        self._draw(image, original_image)

        return original_image
