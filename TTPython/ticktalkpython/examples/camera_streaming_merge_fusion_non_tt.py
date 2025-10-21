# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import matplotlib.pyplot as plt
import linecache

import math
import numpy as np
import matplotlib.pyplot as plt
from sklearn.neighbors import BallTree
from shapely.geometry import Polygon
from shapely.geometry import box
from shapely.affinity import rotate, translate
import bisect


max_id = 10000

match_and_kalman = None
count = -99


''' Kalman filter prediction equasion '''
def kalman_prediction(X_hat_t_1, P_t_1, F_t, B_t, U_t, Q_t):
    X_hat_t = F_t.dot(X_hat_t_1) + (B_t.dot(U_t).reshape(B_t.shape[0], -1))
    P_t = F_t.dot(P_t_1).dot(F_t.transpose()) + Q_t
    return X_hat_t, P_t

''' Kalman filter update equasion '''
def kalman_update(X_hat_t, P_t, Z_t, R_t, H_t):
    K_prime = P_t.dot(H_t.transpose()).dot(kalman_inverse(H_t.dot(P_t).dot(H_t.transpose()) + R_t))
    X_t = X_hat_t + K_prime.dot(Z_t - H_t.dot(X_hat_t))
    P_t = P_t - K_prime.dot(H_t).dot(P_t)
    return X_t, P_t

''' Inverse function that is better than the default numpy one '''
def kalman_inverse(m):
    a, b = m.shape
    if a != b:
        raise ValueError("Only square matrices are invertible.")
    i = np.eye(a, a)
    return np.linalg.lstsq(m, i, rcond=None)[0]

def binarySearch(a, x):
    'Locate the leftmost value exactly equal to x'
    i = bisect.bisect_left(a, x)
    if i != len(a) and a[i] == x:
        return i
    return -1

def ellipsify(covariance, num_std_deviations = 3.0):
    # Eigenvalue and eigenvector computations
    vals, vecs = np.linalg.eigh(covariance)
    order = vals.argsort()[::-1]
    vals = vals[order]
    vecs = vecs[:, order]

    # Use the eigenvalue to figure out which direction is larger
    phi = np.arctan2(*vecs[:, 0][::-1])

    # A and B are radii
    if not np.any(np.isnan(vals)) and np.all(np.isfinite(vals)):
        a, b = num_std_deviations * np.sqrt(vals)
    elif not np.isnan(vals[0]) and np.isfinite(vals[0]):
        a = num_std_deviations * np.sqrt(vals[0])
        b = 0.0
    elif not np.isnan(vals[1]) and np.isfinite(vals[1]):
        b = num_std_deviations * np.sqrt(vals[1])
        a = 0.0
    else:
        a = 0.0
        b = 0.0

    return a, b, phi

# This function turns elipses into rectanges so that an IO calculation can be done for 
# ball tree matching
def computeDistanceEllipseBox(a, b):
    cx = a[0]
    cy = a[1]
    w = a[2]
    h = a[3]
    angle = a[4]
    c = box(-w/2.0, -h/2.0, w/2.0, h/2.0)
    rc = rotate(c, angle)
    contour_a = translate(rc, cx, cy)

    cx = b[0]
    cy = b[1]
    w = b[2]
    h = b[3]
    angle = a[4]
    c = box(-w/2.0, -h/2.0, w/2.0, h/2.0)
    rc = rotate(c, angle)
    contour_b = translate(rc, cx, cy)

    iou = contour_a.intersection(contour_b).area / contour_a.union(contour_b).area

    # Modify to invert the IOU so that it works with the BallTree class
    if iou <= 0:
        distance = 1
    else:
        distance = 1 - iou

    return distance


class MatchClass:
    def __init__(self, id, x, y, covariance, dx, dy, d_confidence, object_type, time):
        self.x = x
        self.y = y
        self.covariance = covariance
        self.dx = dx
        self.dy = dy
        self.velocity_confidence = d_confidence
        self.type = object_type
        self.last_tracked = time
        self.id = id


class ResizableKalman:
    def __init__(self, time, x, y):
        # This list will take 
        self.localTrackersTimeAliveList = []
        self.localTrackersHList = []
        self.localTrackersMeasurementList = []
        self.localTrackersCovarainceList = []
        self.localTrackersIDList = []

        # Init the covariance to some value
        self.error_covariance = np.array([[1.0, 0.0], [0.0, 1.0]], dtype = 'float')
        self.d_covariance = np.array([[2.0, 0.0], [0.0, 2.0]], dtype = 'float')

        # Store the first value for matching purposes
        self.x = x
        self.y = y

        # Arbitrary to start with, updated each iteration
        self.elapsed = 0.125

        # Arbitrary min tracking size so we are not too small to match to
        self.min_size = .75

        # Process varaition guess
        process_variation = 1

        # Track the time of the last track
        self.lastTracked = time

        # Track the number of times this Kalman filter has been used
        self.idx = 0

        # The amount of time before a tracker is removed from the list
        self.time_until_removal = .5

        # Set up the Kalman filter
        self.F_t_len = 4
        # Setup for x_hat = x + dx,  y_hat = y + dy
        # Initial State cov
        self.P_t = np.identity(4)
        self.P_t[2][2] = 0.0
        self.P_t[3][3] = 0.0
        self.P_hat_t = self.P_t
        # Process cov
        four = process_variation * (.125*.125*.125*.125)/4.0
        three = process_variation * (.125*.125*.125)/2.0
        two = process_variation * (.125*.125)
        self.Q_t = np.array([[four, 0, three, 0],
                            [0, four, 0, three],
                            [three, 0, two, 0],
                            [0, three, 0, two]], dtype = 'float')
        # Control matrix
        self.B_t = np.array([[0], [0], [0], [0]], dtype = 'float')
        # Control vector
        self.U_t = 0

    def addFrames(self, measurement_list):
        # try:
        # Rebuild the lists every time because measurements come and go
        self.localTrackersCovarainceList = []
        self.localTrackersMeasurementList = []
        self.localTrackersHList= []
        # Check if there are more sensors in the area that have not been added
        for match in measurement_list:
            measurment_index = binarySearch(self.localTrackersIDList, match.id)
            if measurment_index < 0:
                # This is not in the tracked list, needs to be added
                self.addTracker(match.id)
            
            # All should be in the tracked list now, continue building the lists
            # Add the current covariance to the R matrix
            cov = match.covariance
            self.localTrackersCovarainceList.append(cov)

            # Add the current measurments to the measurement matrix
            self.localTrackersMeasurementList.append(np.array([match.x, match.y]))#, match.dx, match.dy]))

            # The H matrix is different for radar (type 1), the rest are type 0
            self.localTrackersHList.append(0)

            # Mark this measurements as having been used recently
            self.localTrackersTimeAliveList.append(self.lastTracked)

    def addTracker(self, id):
        # Make sure we have something, if not create the array here
        # Start off with measuring only 1 sensor x and y, this will be dynamically built
        self.localTrackersIDList.append(id)
        self.localTrackersTimeAliveList.append(self.lastTracked)

    def removeOldTrackers(self):
        # REmove any trackers that have not been used for a while
        # Do this in reverse so we can delete the entire time
        for position, trackerAlive in enumerate(reversed(self.localTrackersTimeAliveList)):
            if (self.lastTracked - trackerAlive) > self.time_until_removal:
                # Time to remove this track
                if len(self.localTrackersIDList) <= 1:
                    # Removing the last track from a filter, this should not
                    # occur normally as we delete the entire tracker sooner
                    self.localTrackersIDList = []
                    self.localTrackersTimeAliveList = []
                    self.localTrackersCovarainceList = []
                    self.localTrackersMeasurementList = []
                    self.localTrackersHList = []
                else:
                    # Remove from the list and list searcher
                    self.localTrackersIDList.pop(position)
                    self.localTrackersTimeAliveList.pop(position)
                    self.localTrackersCovarainceList.pop(position)
                    self.localTrackersMeasurementList.pop(position)
                    self.localTrackersHList.pop(position)

    def h_t(self, h_t_type):
        if h_t_type == 0:
            return np.array([[1, 0., 0., 0.],
                            [0., 1, 0., 0.]], dtype = 'float')
        else:
            # TODO: radar type
            return np.array([[1, 0., 1., 0.],
                            [0., 1, 0., 1.]], dtype = 'float')

    def averageMeasurementsFirstFrame(self):
        if len(self.localTrackersCovarainceList) == 1:
            return self.localTrackersMeasurementList[0], self.localTrackersCovarainceList[0]

        for idx, cov in enumerate(self.localTrackersCovarainceList):
            if idx == 0:
                temporary_c = cov.transpose()
            else:
                temporary_c = np.add(temporary_c, cov.transpose())
        temporary_c = temporary_c.transpose()

        for idx, (pos, cov) in enumerate(zip(self.localTrackersMeasurementList, self.localTrackersCovarainceList)):
            if idx == 0:
                temprorary_mu = np.matmul(cov.transpose(), pos)
            else:
                temprorary_mu = np.add(temprorary_mu, np.matmul(cov.transpose(), pos))
        temprorary_mu = np.matmul(temporary_c, temprorary_mu)

        return temprorary_mu, temporary_c

    def fusion(self, measurement_list):
        # Set the kalman variables and resize the arrays dynalically (if needed
        self.addFrames(measurement_list)
        # Do the kalman thing!
        if self.idx == 0:
            # We have no prior detection so we need to just output what we have but store for later
            # Do a Naive average to get the starting position
            pos, cov= self.averageMeasurementsFirstFrame()

            # Store so that next fusion is better
            self.prev_time = self.lastTracked
            self.x = pos[0]
            self.y = pos[1]
            self.error_covariance = cov
            self.idx += 1

            # Store so that next fusion is better
            self.X_hat_t = np.array(
                [[self.x], [self.y], [0], [0]], dtype = 'float')
            
            # Seed the covariance values directly from the measurement
            self.P_t[0][0] = self.error_covariance[0][0]
            self.P_t[0][1] = self.error_covariance[0][1]
            self.P_t[1][0] = self.error_covariance[1][0]
            self.P_t[1][1] = self.error_covariance[1][1]
            self.P_hat_t = self.P_t
            self.prev_time = self.lastTracked
            self.x = self.x
            self.y = self.y
            self.dx = 0.0
            self.dy = 0.0
            self.idx += 1
        else:
            try:
                # We have valid data
                # Transition matrix
                elapsed = self.lastTracked - self.prev_time

                self.F_t = np.array([[1, 0, elapsed, 0],
                                    [0, 1, 0, elapsed],
                                    [0, 0, 1, 0],
                                    [0, 0, 0, 1]], dtype = 'float')

                self.X_hat_t, self.P_hat_t = kalman_prediction(self.X_hat_t, self.P_t, self.F_t, self.B_t, self.U_t, self.Q_t)

                if len(self.localTrackersMeasurementList) == 0:
                    nothing_cov = np.array([[1.0, 0.],
                                            [0., 1.0]], dtype = 'float')
                    measure = np.array([.0, .0], dtype = 'float')
                    nothing_Ht = np.array([[0, 0., 0., 0.],
                                            [0., 0, 0., 0.]], dtype = 'float')

                    Z_t = Z_t.reshape(Z_t.shape[0], -1)
                    X_t, self.P_t = kalman_update(self.X_hat_t, self.P_hat_t, Z_t, nothing_cov, nothing_Ht)
                    self.X_hat_t = X_t
                    self.P_hat_t = self.P_t
                else:
                    for mu, cov, h_t_type in zip(self.localTrackersMeasurementList, self.localTrackersCovarainceList, self.localTrackersHList):
                        Z_t = (mu).transpose()
                        Z_t = Z_t.reshape(Z_t.shape[0], -1)
                        X_t, self.P_t = kalman_update(self.X_hat_t, self.P_hat_t, Z_t, cov, self.h_t(h_t_type))
                        self.X_hat_t = X_t
                        self.P_hat_t = self.P_t

                self.prev_time = self.lastTracked
                self.x = X_t[0][0]
                self.y = X_t[1][0]
                self.dx = X_t[2][0]
                self.dy = X_t[3][0]
                self.idx += 1
                if self.P_t[0][0] != 0.0 or self.P_t[0][1] != 0.0:
                    self.error_covariance = np.array([[self.P_t[0][0], self.P_t[0][1]], [self.P_t[1][0], self.P_t[1][1]]], dtype = 'float')
                    self.d_covariance = np.array([[self.P_t[2][2], self.P_t[2][3]], [self.P_t[3][2], self.P_t[3][3]]], dtype = 'float')
                else:
                    self.error_covariance = np.array([[1.0, 0.0], [0.0, 1.0]], dtype = 'float')
                    self.d_covariance = np.array([[2.0, 0.0], [0.0, 2.0]], dtype = 'float')

                #print ( elapsed, self.x, self.y, self.dx, self.dy, math.degrees(math.hypot(self.dx, self.dy)))
                # Post fusion, lets clear old trackers now
                self.removeOldTrackers()

            except Exception as e:
                print ( " Exception: " + str(e) )

    def getKalmanPred(self, time):
        # Prediction based mathcing methods seems to be making this fail so we are using no prediction :/
        # Enforce a min size of a vehicle so that a detection has some area overlap to check
        a, b, phi = ellipsify(self.error_covariance, 3.0)
        return self.x, self.y, self.min_size + a, self.min_size + b, phi


class GlobalTracked:
    # This object tracks a single object that has been detected in a video frame.
    # We use this primarily to match objects seen between frames and included in here
    # is a function for kalman filter to smooth the x and y values as well as a
    # function for prediction where the next bounding box will be based on prior movement.
    def __init__(self, sensed_id, x, y, covariance, dx, dy, dcovariance, object_type, time, id):
        self.x = x
        self.y = y
        self.dx = 0
        self.dy = 0
        self.error_covariance = np.array([[1.0, 0.0], [0.0, 1.0]], dtype = 'float')
        self.typeArray = [0, 0, 0, 0]
        self.typeArray[object_type] += 1
        self.type = self.typeArray.index(max(self.typeArray))
        self.lastTracked = time
        self.id = id
        self.idx = 0
        self.min_size = 0.75
        self.track_count = 0
        self.d_covariance = np.array([[2.0, 0.0], [0.0, 2.0]], dtype = 'float')
        self.match_list = []
        self.fusion_steps = 0

        # Add this first match
        new_match = MatchClass(sensed_id, x, y, covariance, dx, dy, dcovariance, object_type, time)
        self.match_list.append(new_match)

        # Kalman stuff
        self.kalman = ResizableKalman(time, x, y)

    # Update adds another detection to this track
    def update(self, other, time):
        new_match = MatchClass(other[0], other[1], other[2], other[3], other[4], other[5], other[6], other[7], time)
        self.match_list.append(new_match)

        self.lastTracked = time

        self.track_count += 1

    # Gets our position in an array form so we can use it in the BallTree
    def getPosition(self):
        return [
            [self.x, self.y, self.min_size, self.min_size, math.radians(0)]
        ]

    def getPositionPredicted(self, timestamp):
        # If this kalman fitler has never been run, we can't use it for prediction!
        return [
            [self.x, self.y, self.min_size, self.min_size, math.radians(0)]
        ]

    def fusion(self):
        self.kalman.fusion(self.match_list)
        self.x = self.kalman.x
        self.y = self.kalman.y
        self.error_covariance = self.kalman.error_covariance
        self.dx = self.kalman.dx
        self.dy = self.kalman.dy
        self.d_covariance = self.kalman.d_covariance
        self.fusion_steps += 1

    def clearLastFrame(self):
        self.match_list = []


class LocalFUSION:
    # Fusion is a special class for matching and fusing detections for a variety of sources.
    # The inpus is scalable and therefore must be generated before being fed into this class.
    # A unique list of detections is required from each individual sensor or pre-fused device
    # output or it will not be matched. Detections too close to each other may be combined.
    # This is a modified version of the frame-by-frame tracker seen in:
    # https://github.com/eandert/Jetson_Nano_Camera_Vehicle_Tracker
    def __init__(self):
        # Set other parameters for the class
        self.trackedList = []
        self.id = 0
        self.prev_time = -99.0
        self.min_size = 0.75
        self.trackShowThreshold = 5

    def fuseDetectionFrame(self):
        # Time to go through each track list and fuse!
        result = []
        for track in self.trackedList:
            track.fusion()
            if track.fusion_steps >= self.trackShowThreshold:
                result.append([track.id, track.x, track.y, track.error_covariance.tolist(), track.dx, track.dy, track.d_covariance.tolist()])
            # Clear the previous detection list
            track.clearLastFrame()
            # Clean up the tracks for next time
            self.cleanDetections()

        return result

    def processDetectionFrame(self, sensor_id, timestamp, observations, cleanupTime):
        # We need to generate and add the detections from this detector
        detections_position_list = []
        detections_list = []
        for det in observations:
            detections_position_list.append([det[0], det[1], self.min_size, self.min_size, math.radians(0)])
            detections_list.append([0, det[0], det[1], np.array(det[2]), 0.0, 0.0, np.array(det[5]), sensor_id])

        # Call the matching function to modify our detections in trackedList
        self.matchDetections(detections_position_list, detections_list, timestamp, cleanupTime)

    def matchDetections(self, detections_list_positions, detection_list, timestamp, cleanupTime):
        matches = []
        if len(detections_list_positions) > 0:
            if len(self.trackedList) > 0:
                numpy_formatted = np.array(detections_list_positions).reshape(len(detections_list_positions), 5)
                thisFrameTrackTree = BallTree(numpy_formatted, metric=computeDistanceEllipseBox)

                # Need to check the tree size here in order to figure out if we can even do this
                length = len(numpy_formatted)
                if length > 0:
                    for trackedListIdx, track in enumerate(self.trackedList):
                        tuple = thisFrameTrackTree.query(np.array(track.getPositionPredicted(timestamp)), k=length,
                                                         return_distance=True)
                        first = True
                        for IOUVsDetection, detectionIdx in zip(tuple[0][0], tuple[1][0]):
                            if .99 >= IOUVsDetection >= 0:
                                # Only grab the first match
                                # Before determining if this is a match check if this detection has been matched already
                                if first:
                                    try:
                                        index = [i[0] for i in matches].index(detectionIdx)
                                        # We have found the detection index, lets see which track is a better match
                                        if matches[index][2] > IOUVsDetection:
                                            # We are better so add ourselves
                                            matches.append([detectionIdx, trackedListIdx, IOUVsDetection])
                                            # Now unmatch the other one because we are better
                                            # This essentiall eliminates double matching
                                            matches[index][2] = 1
                                            matches[index][1] = -99
                                            # Now break the loop
                                            first = False
                                    except:
                                        # No matches in the list, go ahead and add
                                        matches.append([detectionIdx, trackedListIdx, IOUVsDetection])
                                        first = False
                                else:
                                    # The other matches need to be marked so they arent made into a new track
                                    # Set distance to 1 so we know this wasn't the main match
                                    if detectionIdx not in [i[0] for i in matches]:
                                        # No matches in the list, go ahead and add
                                        matches.append([detectionIdx, -99, 1])

                # update the tracks that made it through
                for match in matches:
                    if match[1] != -99:
                        # Now append to the correct track
                        self.trackedList[match[1]].relations.append([match[0], match[2]])

                # Old way
                for track in self.trackedList:
                    if len(track.relations) == 1:
                        # Single match, go ahead and update the location
                        track.update(detection_list[track.relations[0][0]], timestamp)
                    elif len(track.relations) > 1:
                        # if we have multiple matches, pick the best one
                        max = 0
                        idx = -99
                        for rel in track.relations:
                            if rel[1] < max:
                                max = rel[1]
                                idx = rel[0]

                        if idx != -99:
                            track.update(detection_list[idx], timestamp)

                if len(matches):
                    missing = sorted(set(range(0, len(detections_list_positions))) - set([i[0] for i in matches]))
                else:
                    missing = list(range(0, len(detections_list_positions)))

                added = []
                for add in missing:
                    # Before we add anything, let's check back against the list to make sure there is no IOU match over .5 with this new item and another new item
                    tuple = thisFrameTrackTree.query((np.array([detections_list_positions[add]])), k=length,
                                                     return_distance=True)
                    add_this = False
                    for IOUsDetection, detectionIdx in zip(tuple[0][0], tuple[1][0]):
                        # Check to make sure thie IOU match is low with existing added
                        if .99 <= IOUsDetection:
                            # Make sure this is not ourself
                            if add != detectionIdx:
                                # If this is not ourself, add ourself only if none of our matches has been added yet
                                if detectionIdx not in added:
                                    add_this = True
                                    break

                    # We are the best according to arbitrarily broken tie and can be added
                    if add_this:
                        added.append(add)
                        new = GlobalTracked(detection_list[add][0], detection_list[add][1], detection_list[add][2],
                                      detection_list[add][3], detection_list[add][4], detection_list[add][5],
                                      detection_list[add][6], detection_list[add][7], timestamp, self.id)
                        if self.id < max_id:
                            self.id += 1
                        else:
                            self.id = 0
                        self.trackedList.append(new)

            else:
                for dl in detection_list:
                    new = GlobalTracked(dl[0], dl[1], dl[2], dl[3], dl[4], dl[5], dl[6], dl[7], timestamp, self.id)
                    if self.id < max_id:
                        self.id += 1
                    else:
                        self.id = 0
                    self.trackedList.append(new)

        remove = []
        for idx, track in enumerate(self.trackedList):
            track.relations = []
            if track.lastTracked < ( timestamp - cleanupTime ):
                remove.append(idx)

        for delete in reversed(remove):
            self.trackedList.pop(delete)

    def cleanDetections(self):
        detections_position_list = []
        detections_position_list_id = []
        for track in self.trackedList:
            detections_position_list.append([track.x, track.y, self.min_size, self.min_size, math.radians(0)])
            detections_position_list_id.append(track.id)
        matches = []
        remove = []
        if len(detections_position_list) > 0:
            if len(self.trackedList) > 0:
                numpy_formatted = np.array(detections_position_list).reshape(len(detections_position_list), 5)
                thisFrameTrackTree = BallTree(numpy_formatted, metric=computeDistanceEllipseBox)

                # Need to check the tree size here in order to figure out if we can even do this
                length = len(numpy_formatted)
                if length > 0:
                    for trackedListIdx, track in enumerate(self.trackedList):
                        tuple = thisFrameTrackTree.query(np.array(track.getPositionPredicted(self.prev_time)), k=length,
                                                         return_distance=True)
                        first = True
                        for IOUVsDetection, detectionIdx in zip(tuple[0][0], tuple[1][0]):
                            # 100% match is ourself! Look for IOU > .75 for now to delete
                            if .50 >= IOUVsDetection > 0.001:
                                # Only grab the first match
                                # Before determining if this is a match check if this detection has been matched already
                                if first:
                                    try:
                                        index = [i[0] for i in matches].index(detectionIdx)
                                        # We have found the detection index, lets see which track is a better match
                                        if matches[index][2] > IOUVsDetection:
                                            # We are better so add ourselves
                                            matches.append([detectionIdx, trackedListIdx, IOUVsDetection])
                                            # Now unmatch the other one because we are better
                                            # This essentiall eliminates double matching
                                            matches[index][2] = 1
                                            matches[index][1] = -99
                                            # Now break the loop
                                            first = False
                                    except:
                                        # No matches in the list, go ahead and add
                                        matches.append([detectionIdx, trackedListIdx, IOUVsDetection])
                                        first = False
                                else:
                                    # The other matches need to be marked so they arent made into a new track
                                    # Set distance to 1 so we know this wasn't the main match
                                    if detectionIdx not in [i[0] for i in matches]:
                                        # No matches in the list, go ahead and add
                                        matches.append([detectionIdx, -99, 1])

                # update the tracks that made it through
                for match in matches:
                    if match[1] != -99:
                        if match[0] != match[1]:
                            if match[1] not in remove and match[0] not in remove:
                                # Check which track is older and keep that one
                                check0 = self.trackedList[match[0]].lastTracked
                                check1 = self.trackedList[match[1]].lastTracked
                                # Arbitrary tie break towards earlier in the list
                                if check0 > check1:
                                    if self.trackedList[match[0]].fusion_steps >= self.trackShowThreshold:
                                        bisect.insort(remove, match[1])
                                elif check0 < check1:
                                    if self.trackedList[match[1]].fusion_steps >= self.trackShowThreshold:
                                        bisect.insort(remove, match[0])
                                else:
                                    check0 = self.trackedList[match[0]].fusion_steps
                                    check1 = self.trackedList[match[1]].fusion_steps  
                                    if check0 >= check1:
                                        if check0 >= self.trackShowThreshold:
                                            bisect.insort(remove, match[1])
                                    else:
                                        if check1 >= self.trackShowThreshold:
                                            bisect.insort(remove, match[0])
                      
        for delete in reversed(remove):
            print( "Cleaning track ", delete)
            self.trackedList.pop(delete)


def camera_sampler(c_time, c_file):
    # extracting the nth line
    if c_file == 0:
        filename = "data_0.txt"
    else:
        filename = "data_1.txt"
    particular_line = linecache.getline(c_file, c_time)
    split = particular_line.split(',')
    detections = []
    x = 0.0
    y = 0.0
    if particular_line != '':
        for idx in range(len(split)):
            if idx == 0:
                continue
            elif idx == 1:
                continue
            elif idx == 2:
                x = float(split[idx])
            elif idx == 3:
                y = float(split[idx])
            else:
                if idx % 2 == 1:
                    detections.append([float(split[idx-1]), float(split[idx])])

    return detections, [x, y]

def localFusion(input1, input2, self1, self2, time1, time2):
    ourself_list = []
    ourself_list.append(self1)
    ourself_list.append(self2)

    global match_and_kalman
    global count
    if count == -99:
        match_and_kalman = LocalFUSION()
        count = 0

    count = count + 1

    input_set_1 = []
    for each in input1:
        #sq_state['current_list'].append(each)
        new_match = [each[0], each[1], np.array([[0.2, 0.0], [0.0, 0.2]], dtype = 'float'), 0.0, 0.0, 0.0]
        input_set_1.append(new_match)
    match_and_kalman.processDetectionFrame(0, time1, input_set_1, .25)

    input_set_2 = []
    for each in input2:
        #sq_state['current_list'].append(each)
        new_match = [each[0], each[1], np.array([[0.2, 0.0], [0.0, 0.2]], dtype = 'float'), 0.0, 0.0, 0.0]
        input_set_2.append(new_match)
    match_and_kalman.processDetectionFrame(1, time2, input_set_2, .25)

    return match_and_kalman.fuseDetectionFrame(), ourself_list
    

def streamify_test(trigger):
    file_1 = "data_0.txt"
    file_2 = "data_1.txt"

    current_time = 0
    output_observations = []
    output_self = []
    for count in range(900):
        # collect a timestamp from a clock; needs a trigger whose arrival will make the timestamp be taken. This is for setting the start-tick of the STREAMify's periodic firing rule
        start_time = current_time

        # do the sampling with streamify'd SQs. Only one of the inputs needs the special sampling time interval (but it wouldn't hurt if all did) because the other const values have infinite timestamps
        sensor_1, self_1 = camera_sampler(count+1, file_1) 
        sensor_2, self_2 = camera_sampler(count+1, file_2) 

        # do some operations on the streams at runtime. Multiple streams will have their values synchronized by searching for intersections/overlaps in their time-intervals
        observations, self_pos = localFusion(sensor_1, sensor_2, self_1, self_2, current_time, current_time)
        output_observations.append(observations)
        output_self.append(self_pos)

        current_time += 0.125

    x_val = []
    y_val = []
    for timestep in output_observations:
        for observation in timestep:
            x_val.append(observation[0])
            y_val.append(observation[1])

    self_x_val = []
    self_y_val = []
    for timestep in output_self:
        for observation in timestep:
            self_x_val.append(observation[0])
            self_y_val.append(observation[1])

    plt.plot(self_x_val,self_y_val,'ob')
    plt.plot(x_val,y_val,'xr')
    plt.show()

streamify_test(0)