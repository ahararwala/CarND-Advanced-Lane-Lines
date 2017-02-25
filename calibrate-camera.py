# coding: utf-8

# ## Advanced Lane Finding Project
# 
# The goals / steps of this project are the following:
# 
# * Compute the camera calibration matrix and distortion coefficients given a set of chessboard images.
# * Apply a distortion correction to raw images.
# * Use color transforms, gradients, etc., to create a thresholded binary image.
# * Apply a perspective transform to rectify binary image ("birds-eye view").
# * Detect lane pixels and fit to find the lane boundary.
# * Determine the curvature of the lane and vehicle position with respect to center.
# * Warp the detected lane boundaries back onto the original image.
# * Output visual display of the lane boundaries and numerical estimation of lane curvature and vehicle position.
# 
# ---
# ## First, I'll compute the camera calibration using chessboard images

# In[11]:
import pickle as pickle_module
import os
import numpy as np
import glob
import cv2
from scipy.misc import imread, imresize
import matplotlib.pyplot as plt

# %matplotlib qt

# prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
objp = np.zeros((6 * 9, 3), np.float32)
objp[:, :2] = np.mgrid[0:9, 0:6].T.reshape(-1, 2)

# Arrays to store object points and image points from all the images.
objpoints = []  # 3d points in real world space
imgpoints = []  # 2d points in image plane.


def display_camera_images():
    # Make a list of calibration images
    calibration_images = glob.glob('camera_cal/calibration*.jpg')
    # Step through the list and search for chessboard corners
    for fname in calibration_images:
        img = cv2.imread(fname)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Find the chessboard corners
        ret, corners = cv2.findChessboardCorners(gray, (9, 6), None)

        # If found, add object points, image points
        if ret:
            objpoints.append(objp)
            imgpoints.append(corners)

            # Draw and display the corners
            img = cv2.drawChessboardCorners(img, (9, 6), corners, ret)
            cv2.imshow('img', img)
            cv2.waitKey(500)
    cv2.destroyAllWindows()


display_camera_images()

# ## Camera calibration class

# In[12]:

# get_ipython().magic('matplotlib inline')

IMAGE_SIZE = (1280, 720)
CALIBRATION_IMAGE_SIZE = (720, 1280, 3)
CALIBRATION_PICKLE_FILE = 'camera_calibration.pkl'
IMAGES_PATH = 'camera_cal/calibration*.jpg'
CHESSBOARD_ROWS = 6
CHESSBOARD_COLS = 9


class CameraCalibration:
    def __init__(self, image_size=IMAGE_SIZE, calibration_file=CALIBRATION_PICKLE_FILE):
        # Get camera calibration
        points_object, points_image = (unpickle(calibration_file) if os.path.exists(calibration_file)
                                       else self._calibrate())
        # Get mtx and dist to undistorted new images
        _, self.mtx, self.dist, _, _ = cv2.calibrateCamera(points_object, points_image, image_size, None, None)

    def undistort(self, image):
        return cv2.undistort(image, self.mtx, self.dist, None, self.mtx)

    @staticmethod
    def _calibrate(images_path=IMAGES_PATH, chessboard_rows=CHESSBOARD_ROWS, chessboard_cols=CHESSBOARD_COLS,
                   image_size=CALIBRATION_IMAGE_SIZE, calibration_pickle_file=CALIBRATION_PICKLE_FILE):
        obj = np.zeros((chessboard_rows * chessboard_cols, 3), np.float32)
        obj[:, :2] = np.mgrid[:chessboard_cols, :chessboard_rows].T.reshape(-1, 2)

        object_points = []
        image_points = []

        images = glob.glob(images_path)

        for image in images:
            image_array = imread(image)
            if image_array.shape != image_size:
                image_array = imresize(image_array, image_size)
            gray = cv2.cvtColor(image_array, cv2.COLOR_RGB2GRAY)
            ret, corners = cv2.findChessboardCorners(gray, (chessboard_cols, chessboard_rows), None)

            if ret:
                object_points.append(obj)
                image_points.append(corners)

        calibration = (object_points, image_points)
        pickle(calibration, calibration_pickle_file)
        return calibration


def unpickle(file_path):
    with open(file_path, 'rb') as file_handle:
        pickled_object = pickle_module.load(file_handle)
        return pickled_object


def pickle(object_to_pickle, file_path):
    with open(file_path, 'wb') as file_handle:
        pickle_module.dump(object_to_pickle, file_handle)


        # In[13]:


CameraCalibration()


# In[ ]:
