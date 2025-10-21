# Copyright 2021 Carnegie Mellon University
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

# Program to represent the application that the team is working on for the CPS Week Competition
# Constructed on 3/4/21 in the TT Weekly Meeting

from tt.Instructions import CONST
from tt.SQ import GRAPHify
from tt.Clock import TTClock
from tt.StreamResampler import TTResample

from cav import communication
from cav import lidar_recognition
from cav import camera_recognition
from cav import planning_control
from cav import motors

from rsu import global_fusion

@SQify
def camera_settings(trigger):
    # Setup our various settings, we sue these for both camera and Yolo inits
    settings = camera_recognition.Settings()
    settings.darknetPath = '../darknet/'
    camSpecs = camera_recognition.CameraSpecifications()
    camSpecs.cameraHeight = .2
    camSpecs.cameraAdjustmentAngle = 0.0

    return (settings, camSpecs)

@SQify
def lidar_settings(trigger):
    # For now we are hard coding these pipe names, this is a bad practice
    # TODO: find a more elegant solution than hard coding
    pipeFromC= "/home/jetson/Projects/slamware/fifo_queues/fifopipefromc"
    pipeToC= "/home/jetson/Projects/slamware/fifo_queues/fifopipetoc"

    return (pipeFromC, pipeToC)

@SQify
def generate_map(trigger):
    # Setup the mapspecs
    mapObject = mapGenerator.MapSpecs()
    map = dict(
        route_x=self.mapSpecs.xCoordinates,
        route_y=self.mapSpecs.yCoordinates,
        route_TFL=self.mapSpecs.vCoordinates,
    )
    return map

@STREAMify
def LIDAR_source(trigger, sticky_lidar_settings):
    global sq_state

    if not sq_state:
        # Make sure the dict has been created. TODO: Do we need this?
        sq_state = {}

    if not sq_state['lidar_stream']:
        # Start the connection with the LIDAR through pipes
        # Init the lIDAR and store the object - this may take a while!
        sq_state['lidar_stream'] = communication.connectLIDAR(sticky_lidar_settings[0], sticky_lidar_settings[1])

    # This will block until data is available
    # Should block around 125ms unless this is the frist time starting
    # May block around 1000ms the first time due to the C++ code
    sq_state['lidar_stream'].checkFromC()

    # Blocking is over, data should now be available
    return sq_state['lidar_stream'].parseFromC()

@STREAMify
def camera_source(interval_token, sticky_cam_setting):
    global sq_state

    if not sq_state:
        # Make sure the dict has been created. TODO: Do we need this?
        sq_state = {}

    if not sq_state['camera_stream']:
        # If it is not already started, we need to init the camera
        sq_state['camera_stream'] = camera_recognition.Camera(sticky_cam_setting[0], sticky_cam_setting[1])

    # Take the actual camera frame
    frame, camtimestamp = sq_state['camera_stream'].takeCameraFrame()

    return (frame, camtimestamp)

@SQify
def LIDAR_DB_scan(point_cloud):
    global sq_state

    if not sq_state:
        # Make sure the dict has been created. TODO: Do we need this?
        sq_state = {}

    if not sq_state['lidar_recognition']:
        # If it is not already started, we need to init the LIDAR recogntion
        sq_state['lidar_recognition'] = lidar_recognition.LIDAR(point_cloud.time)

    # Now run the recognition
    lidarcoordinates, lidartimestamp = lidarRecognition.processLidarFrame(point_cloud, point_cloud.time)

    return (lidarcoordinates, timestamp)

@SQify
def YOLO(image, settings):
    global sq_state

    if not sq_state:
        # Make sure the dict has been created. TODO: Do we need this?
        sq_state = {}

    if not sq_state['yolo']:
        # Setup YOLO
        sq_state['yolo'] = YOLO()
        sq_state['yolo'].init(settings[0].frame_width, settings[0].frame_height, time.time(), settings[0], settings[1])

    coordinates, timestamp = sq_state['yolo'].readFrame(frame_read, time.time())

    return (coordinates, timestamp)

@SQify
def plan(RSU_response, localization, sticky_vehicle_id, sticky_route):
    global sq_state

    if not sq_state:
        # Make sure the dict has been created. TODO: Do we need this?
        sq_state = {}

    if not sq_state['planner']:
        # Init everything
        sq_state['planner'] = planning_control.Planner()
        sq_state['planner'].initialVehicleAtPosition(localization[0], localization[1], localization[2], sticky_route["route_x"], sticky_route["route_y"], sticky_route["route_TFL"], sticky_vehicle_id, False)

    # Update our various pieces
    sq_state['planner'].targetVelocityGeneral = float(RSU_response["v_t"])
    sq_state['planner'].update_localization([localization[0], localization[1], lidarDevice[2]])
    sq_state['planner'].recieve_coordinate_group_commands(RSU_response["tfl_state"])
    sq_state['planner'].pure_pursuit_control()

    # Now update our current PID with respect to other vehicles
    sq_state['planner'].check_positions_of_other_vehicles_adjust_velocity(RSU_response["veh_locations"], sticky_vehicle_id)

    # We can't update the PID controls until after all positions are known
    sq_state['planner'].update_pid()

    # Finally, issue the commands to the motors
    steering_ppm, motor_pid = sq_state['planner'].return_command_package()

    return (steering_ppm, motor_pid)

@SQify
def motors(PID_controls):
    global sq_state

    if not sq_state:
        # Make sure the dict has been created. TODO: Do we need this?
        sq_state = {}

    if not sq_state['ego_vehicle']:
    # The first thing we should always do is initialize the control module
    # This is important to make sure a rogue signal doesn't drive us away
        sq_state['ego_vehicle'] = motors.Motors()

    # Check for a deadline failure, inputs will be None if so
    if PID_controls == None:
        sq_state['ego_vehicle'].emergencyStop()
    else:
        sq_state['ego_vehicle'].setControlMotors(PID_controls[0], PID_controls[1])

@GRAPHify
def rc_cars(init_trigger):

    # Define clock tree
    with TTClock.root() as ROOT:
        with TTClock("Fusion clock", ROOT, 100000, 0) as RSU_clock:
            with TTClock("LIDAR clock", ROOT, 125000, 0) as LIDAR_clock:
                pass
            with TTClock("Cam clock", ROOT, 16667, 0) as Cam_clock:
                pass

    # Init
    sticky_route = generate_map(init_trigger)
    sticky_vehicle_id_cav1 = 0
    sticky_cam_setting_cav1 = camera_settings(init_trigger)
    sticky_vehicle_id_cav2 = 1
    sticky_cam_setting_cav2 = camera_settings(init_trigger)
    sticky_vehicle_id_cam = 2
    sticky_cam_setting_cam = camera_settings(init_trigger)
    sticky_cam_position = TUPLE_3(-.75,.75,-.7854)

    with CAV1:
        # Sensing section
        # Lidar, run for 5 minutes
        point_clouds_cav1 = LIDAR_source(TTTime(LIDAR_clock, 0, 2400))
        lidar_locations_cav1 = LIDAR_DB_scan(point_clouds_cav1)
        lidar_localization_cav1 = LIDAR_SLAM(point_clouds_cav1)
        # Camera, run for 5 minutes
        images_cav1 = camera_source(TTTime(Cam_clock, 0, 2400), sticky_cam_setting_cav1)
        images_decimated_cav1 = TTResample(Fusion_clock, images_cav1)
        cam_locations_cav1 = YOLO(images_decimated_cav1, sticky_cam_setting_cav1)
        # Fusion
        detection_package_cav_1 = TUPLE_3(lidar_locations_cav1, lidar_localization_cav1, cam_locations_cav1)

    with CAV2:
        # Sensing section
        # Lidar, run for 5 minutes
        point_clouds_cav2 = LIDAR_source(TTTime(LIDAR_clock, 0, 2400))
        lidar_locations_cav2 = LIDAR_DB_scan(point_clouds_cav2)
        lidar_localization_cav2 = LIDAR_SLAM(point_clouds_cav2)
        # Camera, run for 5 minutes
        images_cav2 = camera_source(TTTime(Cam_clock, 0, 2400), sticky_cam_setting_cav2)
        images_decimated_cav2 = TTResample(Fusion_clock, images_cav2)
        cam_locations_cav2 = YOLO(images_decimated_cav2, sticky_cam_setting_cav2)
        # Fusion
        detection_package_cav_2 = TUPLE_3(lidar_locations_cav2, lidar_localization_cav2, cam_locations_cav2)

    with CAM:
        # Sensing section
        # Camera, run for 5 minutes
        images_cam = camera_source(TTTime(Cam_clock, 0, 2400), sticky_cam_setting_cam)
        images_decimated_cam = TTResample(Fusion_clock, images_cam)
        cam_locations_cam = YOLO(images_decimated_cam, sticky_cam_setting_cam)
        # Fusion, mostly a placeholder here but it translates coordinates
        detection_package_cam = TUPLE_3(None, sticky_cam_position, cam_locations_cam)

    with RSU:
        # Fusion
        resampled_locations_cav1 = TTResample(RSU_Clock, detection_package_cav_1) # there are 3 of these streams? but kind of not really. 1 camera stream, 2 fused cam+lidar
        resampled_locations_cav2 = TTResample(RSU_Clock, detection_package_cav_2)
        resampled_locations_cam = TTResample(RSU_Clock, detection_package_cam)
        error_att_cav1 = error_attribution_fusion(resampled_locations_cav1)
        error_att_cav2 = error_attribution_fusion(resampled_locations_cav2)
        error_att_cam = error_attribution_fusion(resampled_locations_cam)
        with TTDeadline(delay_ticks=100000, clock=ROOT, trigger=EARLIEST, failure_mode=NONE_MODE, deadline_start_sources=(point_clouds_cav1,point_clouds_cav2,images_cam)): # 100ms after the lidar source was supposed to fire
            # Tokens not present wil be set to none by default and sensor fusion function will handle that
            global_fusion = location_KF(error_att_cav1, error_att_cav2, error_att_cam)
        RSU_response = calculate_traffic_light_state(global_fusion)

    with CAV1:
        # Actuation
        PID_controls = plan(RSU_response, localization, sticky_vehicle_id_cav1, sticky_route)
        with TTDeadline(deadline_start_sources=point_clouds_cav1, clock=LIDAR_clock, delay_ticks=1, failure_mode=NONE_MODE): # 1 tick of the lidar clock, implicitly assuming deadlines starts with each token along point cloud arc
            # Tokens not present wil be set to none by default and PID controls will check for none and if so run a stop
            Motors(PID_controls)

    with CAV2:
        # Actuation
        PID_controls = plan(RSU_response, localization, sticky_vehicle_id_cav2, sticky_route)
        with TTDeadline(deadline_start_sources=point_clouds_cav2, clock=LIDAR_clock, delay_ticks=1, failure_mode=NONE_MODE): # 1 tick of the lidar clock, implicitly assuming deadlines starts with each token along point cloud arc
            # Tokens not present wil be set to none by default and PID controls will check for none and if so run a stop
            Motors(PID_controls)








# TT Deadline options for later
        # # Removed plan B handles in favor of if else aka select merge
        # with TTDeadline(point_clouds, 1): # 1 tick of the lidar clock, implicitly assuming deadlines starts with each token along point cloud arc
        #     if TTDeadline.fail:
        #         PID_controls = TUPLE_2(0.0, 0.0) #Emergency stop
        #     else:
        #         PID_controls = plan(RSU_response, localization, sticky_vehicle_id_cav1, sticky_route)
        #     Motors(PID_controls)

        # with TTDeadline(RSU_clock, 100000, NONE_MODE): # 100ms after the lidar source was supposed to fire
        #     try:
        #         global_fusion = location_KF(error_att_cav1, error_att_cav2, error_att_cam)
        #     except deadline_failure:
        #         # Tokens not present wil be set to none by default and sensor fusion function will handle that
        #         global_fusion = location_KF(error_att_cav1, error_att_cav2, error_att_cam)


# def planB_handler(exception_type, exception_value, traceback, ego_vehicle):
#     print(f"Entered the PlanB handler for Exception: {exception_value}")
#     ego_vehicle.emergencyStop()
#     # Returning True will allow execution to continue; False causes a fatal exception
#     return False

# @SQify
# def cav1_init(trigger, sticky_vehicle_id, sticky_route)
#     # Init the lidar
#     sticky_lidar_settings = lidar_settings(trigger)
#     point_clouds_init = LIDAR_source(TTTime(LIDAR_clock, 0, 1), sticky_lidar_settings)
#     lidar_locations_init = LIDAR_DB_scan(point_clouds_init)

#     # Init the camera
#     sticky_cam_setting = camera_settings(trigger)
#     cam_object = camera_source(TTTime(Cam_clock, 0, 1), sticky_cam_setting):

#     # Initialize the planner using the route and lidar, the result will be ignored as we should default to stop
#     pid_controls = plan(RSU_response, lidar_locations_init[0], sticky_vehicle_id, sticky_route):

#     # Start the motors in the off position
#     motors(0.0, 0.0)

#     return True

# @SQify
# def cav1_detection(trigger)
#     with TTClock("Fusion clock", ROOT, 100000, 0): as Fusion_clock:
#         # Lidar
#         with TTClock("LIDAR clock cav1", ROOT, 125000, 0) as LIDAR_clock:
#             point_clouds = LIDAR_source(TTTime(LIDAR_clock, 0, 1000), LIDAR_object)
#             lidar_locations = LIDAR_DB_scan(point_clouds)
#             lidar_localization = LIDAR_SLAM(point_clouds)
#         # Camera
#         with TTClock("Cam Clock cav1", ROOT, 16667, 0) as Cam_clock:
#             images = camera_source(TTTime(Cam_clock, 0, 1000), cam_object)
#             images_decimated = TTResample(Fusion_clock, images)
#             cam_locations = YOLO(images_decimated, yoloObject)
#     return (cam_locations, lidar_locations, lidar_localization)

# @SQify
# def cav1_actuation(trigger, RSU_response, localization)
#     with TTClock("Fusion clock", ROOT, 100000, 0): as Fusion_clock:
#         with TTClock("LIDAR clock cav1", ROOT, 125000, 0) as LIDAR_clock:
#             with TTPlanB(planB_handler):            # will catch deadline errors
#                 with TTDeadline(point_clouds.time, 12500):          # Plan B Handler need to trigger if we wait more than 125 milliseconds
#                     if TTDeadline.fail:
#                         PID_controls = (0.0, 0.0) #Emergency stop
#                     else:
#                         PID_controls = plan(RSU_response, localization, None, None)
#                     Motors(PID_controls[0], PID_controls[1])
