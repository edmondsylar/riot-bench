from rsu_folder import vehicle
import math
import time


def rotate(origin, point, angle):
    """
    Rotate a point counterclockwise by a given angle around a given origin.

    The angle should be given in radians.
    """
    ox, oy = origin
    px, py = point

    qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
    qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
    return qx, qy

class RSU():
    def __init__(self, mapSpecs, vehicles, sensors, trafficLightArray, isSimulation):
        self.mapSpecs = mapSpecs
        self.vehicles = vehicles
        self.sensors = sensors
        self.trafficLightArray = trafficLightArray

        self.lightTime = time.time()
        self.lightTimePeriod = 5.0
        self.checkLightState()

        # Lets create some simulation vehicles, this would be done automatically as vehicles are added if this is not a simulation
        if isSimulation:
            newvehicle1 = vehicle.Vehicle()
            newvehicle1.initialVehicleAtPosition(
                (- (mapSpecs.intersectionWidth * mapSpecs.meters_to_print_scale / 2) - 50) / mapSpecs.meters_to_print_scale, 0,
                math.radians(0),
                mapSpecs.xCoordinates, mapSpecs.yCoordinates, mapSpecs.vCoordinates, 0, False)

            # newvehicle2 = vehicle.Vehicle()
            # newvehicle2.initialVehicleAtPosition(0, (
            #         (mapSpecs.intersectionWidth * mapSpecs.meters_to_print_scale / 2) + 50) / mapSpecs.meters_to_print_scale,
            #                                      270,
            #                                      mapSpecs.xCoordinates, mapSpecs.yCoordinates, mapSpecs.vCoordinates, len(self.vehicles),
            #                                      False)

            newvehicle2 = vehicle.Vehicle()
            newvehicle2.initialVehicleAtPosition(
                2.0 * (- (mapSpecs.intersectionWidth * mapSpecs.meters_to_print_scale / 2) - 50) / mapSpecs.meters_to_print_scale, 0,
                math.radians(0),
                mapSpecs.xCoordinates, mapSpecs.yCoordinates, mapSpecs.vCoordinates, 1, False)

            newSensor = vehicle.Vehicle()
            newSensor.initialVehicleAtPosition(
                (- (mapSpecs.intersectionWidth * mapSpecs.meters_to_print_scale / 2) - 50) / mapSpecs.meters_to_print_scale, (
                    (mapSpecs.intersectionWidth * mapSpecs.meters_to_print_scale / 2) + 50) / mapSpecs.meters_to_print_scale,
                math.radians(-45),
                mapSpecs.xCoordinates, mapSpecs.yCoordinates, mapSpecs.vCoordinates, 2, True)

            self.vehicles[0] = newvehicle1
            self.vehicles[1] = newvehicle2
            self.sensors[0] = newSensor

            print("Pos veh 0: ", (- (
                        mapSpecs.intersectionWidth * mapSpecs.meters_to_print_scale / 2) - 50) / mapSpecs.meters_to_print_scale,
                  0, 0)
            print("Pos veh 1: ", 2*(- (
                        mapSpecs.intersectionWidth * mapSpecs.meters_to_print_scale / 2) - 50) / mapSpecs.meters_to_print_scale,
                  0, 0)
            print("Pos sens 0: ", (- (mapSpecs.intersectionWidth * mapSpecs.meters_to_print_scale / 2) - 50) / mapSpecs.meters_to_print_scale, (
                    (mapSpecs.intersectionWidth * mapSpecs.meters_to_print_scale / 2) + 50) / mapSpecs.meters_to_print_scale,
                -45)

    def recieveMessage(self, request_data):
        try:
            if request_data:
                key = request_data['key']
                id = int(request_data['id'])
                type = int(request_data['type'])
                register = bool(request_data['register'])
                timestamp = float(request_data['timestamp'])
                x = float(request_data['x'])
                y = float(request_data['y'])
                z = float(request_data['z'])
                roll = float(request_data['roll'])
                pitch = float(request_data['pitch'])
                yaw = float(request_data['yaw'])
                detections = request_data['detections']

                if register:
                    print ( '    registering ' + str(type) + ' ' + str(id) + ' ' + str(time.time()))
                    return self.register(key, id, type, timestamp, x, y, z, roll, pitch, yaw)
                else:
                    print ( '    checkin ' + str(type) + ' ' + str(id) + ' ' + str(time.time()), self.vehicles[id].targetVelocityGeneral)
                    return self.checkinResponse(key, id, type, timestamp, x, y, z, roll, pitch, yaw, detections)

        except Exception as e:
            print ( " Exception occured in recieveMessage ", str(e) )

    def register(self, key, id, type, timestamp, x, y, z, roll, pitch, yaw):
        try:
            if type == 0:
                # Check if this vehicle ID is taken or not
                if id in self.vehicles:
                    print ( " Warning: Vehicle ID already in use!")

                # This is the init funciton that arbitrarily locates the vehicles at positions
                # and if the vehicle is not at the correct location this will not work
                init_x = self.vehicles[id].positionX_offset
                init_y = self.vehicles[id].positionY_offset
                init_yaw = self.vehicles[id].theta_offset

                # TODO: Improve this to add the cars dynamically

                # Set the key so we have some security
                self.vehicles[id].key = key

                # Now init the vehicle at a location
                self.vehicles[id].update_localization(x, y, yaw, 0.0)
                self.vehicles[id].recieve_coordinate_group_commands(self.trafficLightArray)

                # We update this just for the visualizer
                self.vehicles[id].pure_pursuit_control()

                # Get the last known location of all other vehicles
                vehicleList = []
                for idx, vehicle in self.vehicles.items():
                    vehicleList.append(vehicle.get_location())

                # Now update our current PID with respect to other vehicles
                self.vehicles[id].check_positions_of_other_vehicles_adjust_velocity(vehicleList, id)

                # We can't update the PID controls until after all positions are known
                # We still do this here just for debugging as it should match the PID controls
                # on the actual car and then it will be displayed on the UI
                self.vehicles[id].update_pid()

                # Finally we can create the return messages
                registerResponse = dict(
                    v_t=self.vehicles[id].targetVelocityGeneral,
                    t_x=init_x,
                    t_y=init_y,
                    t_z="0.0",
                    t_roll="0.0",
                    t_pitch="0.0",
                    t_yaw=init_yaw,
                    route_x=self.mapSpecs.xCoordinates,
                    route_y=self.mapSpecs.yCoordinates,
                    route_TFL=self.mapSpecs.vCoordinates,
                    tfl_state=self.trafficLightArray,
                    veh_locations=vehicleList,
                    timestep=time.time()
                )

                return registerResponse

            elif type == 1:
                # Check if this vehicle ID is taken or not
                if id in self.sensors:
                    print(" Warning: Sensor ID already in use!")

                # This is the init funciton that arbitrarily locates the vehicles at positions
                # and if the vehicle is not at the correct location this will not work
                init_x = self.sensors[id].positionX_offset
                init_y = self.sensors[id].positionY_offset
                init_yaw = self.sensors[id].theta_offset

                # TODO: Improve this to add the cars dynamically

                # Set the key so we have some security
                self.sensors[id].key = key

                # Now init the vehicle at a location
                self.sensors[id].update_localization(x, y, yaw, 0.0)

                # Finally we can create the return messages
                registerResponse = dict(
                    t_x=init_x,
                    t_y=init_y,
                    t_z="0.0",
                    t_roll="0.0",
                    t_pitch="0.0",
                    t_yaw=init_yaw,
                    route_x=self.mapSpecs.xCoordinates,
                    route_y=self.mapSpecs.yCoordinates,
                    route_TFL=self.mapSpecs.vCoordinates,
                    tfl_state=self.trafficLightArray,
                    timestep=time.time()
                )

                return registerResponse

        except Exception as e:
            print ( "Exception in register! " + str(e) )


    def checkinResponse(self, key, id, type, timestamp, x, y, z, roll, pitch, yaw, detections):
        try:
            if type == 0:
                # Double check our security, this is pretty naive at this point
                if self.vehicles[id].key == key:
                    # TODO: possibly do these calculation after responding to increase response time

                    # Calculate our velocity using our last position
                    velocity = self.calc_velocity(self.vehicles[id].localizationPositionX, self.vehicles[id].localizationPositionY, x, y, yaw)

                    # Update ourself
                    self.vehicles[id].update_localization(x, y, yaw, velocity)
                    #self.vehicles[vehicle_id].recieve_coordinate_group_commands(trafficLightArray)

                    # Get the last known location of all other vehicles
                    vehicleList = []
                    for idx, vehicle in self.vehicles.items():
                        vehicleList.append(vehicle.get_location())

                    # Do some processing
                    # We do these calculation after responding to increase response time
                    self.vehicles[id].recieve_coordinate_group_commands(self.trafficLightArray)

                    # We update this just for the visualizer
                    self.vehicles[id].pure_pursuit_control()

                    # print ( "detections: ", detections["lidar_obj"] )
                    pos = [x + self.vehicles[id].positionX_offset, y + self.vehicles[id].positionY_offset, yaw + self.vehicles[id].theta_offset]

                    self.vehicles[id].cameraDetections = []
                    self.vehicles[id].lidarDetections = []

                    # Lets add the detections to the vehicle class
                    for each in detections:
                        new = rotate((0, 0), (float(each[1]), float(each[2])), pos[2])
                        sensed_x = new[0] + pos[0]
                        sensed_y = new[1] + pos[1]
                        if each[5] == "L":
                            self.vehicles[id].lidarDetections.append([sensed_x,sensed_y])
                        else:
                            self.vehicles[id].cameraDetections.append([sensed_x,sensed_y])
                    # for each in detections["lidar_obj"]:
                    #     new = rotate((0, 0), (float(each[1]), float(each[2])), pos[2])
                    #     sensed_x = new[0] + pos[0]
                    #     sensed_y = new[1] + pos[1]
                    #     self.vehicles[id].lidarDetections.append([sensed_x,sensed_y])
                    #vehicles[id].cameraDetections = detections["cam_obj"]
                    #vehicles[id].lidarDetections = detections["lidar_obj"]

                    # Get the last known location of all other vehicles
                    vehicleList = []
                    for idx, vehicle in self.vehicles.items():
                        vehicleList.append(vehicle.get_location())

                    # Now update our current PID with respect to other vehicles
                    self.vehicles[id].check_positions_of_other_vehicles_adjust_velocity(vehicleList, id)

                    # We can't update the PID controls until after all positions are known
                    # We still do this here just for debugging as it should match the PID controls
                    # on the actual car and then it will be displayed on the UI
                    self.vehicles[id].update_pid()

                    # Finally we can create the return messages
                    registerResponse = dict(
                        v_t=self.vehicles[id].targetVelocityGeneral,
                        tfl_state=self.trafficLightArray,
                        veh_locations=vehicleList,
                        timestep=time.time()
                    )

                    # Finally we can create the return message
                    return registerResponse

            elif type == 1:
                # Double check our security, this is pretty naive at this point
                if self.sensors[id].key == key:
                    # save the data
                    # print ( "detections: ", detections["lidar_obj"] )
                    pos = [x + self.sensors[id].positionX_offset, y + self.sensors[id].positionY_offset, yaw + self.sensors[id].theta_offset]

                    self.sensors[id].cameraDetections = []
                    self.sensors[id].lidarDetections = []

                    # Lets add the detections to the vehicle class
                    for each in detections:
                        new = rotate((0, 0), (float(each[1]), float(each[2])), pos[2])
                        sensed_x = new[0] + pos[0]
                        sensed_y = new[1] + pos[1]
                        if each[5] == "L":
                            self.sensors[id].lidarDetections.append([sensed_x,sensed_y])
                        else:
                            self.sensors[id].cameraDetections.append([sensed_x,sensed_y])

                    # Create the return messages and send
                    registerResponse = dict(
                        t_x=self.vehicles[id].positionX_offset,
                        t_y=self.sensors[id].positionY_offset,
                        t_z="0.0",
                        t_roll="0.0",
                        t_pitch="0.0",
                        t_yaw=self.sensors[id].theta_offset,
                        tfl_state=self.trafficLightArray,
                        timestep=time.time()
                    )

                    # Finally we can create the return message
                    return registerResponse
        except Exception as e:
            print ( "Exception in checkin! " + str(e) )

    def calc_velocity(self, x1, y1, x2, y2, theta):
        velocity = math.hypot(x2 - x1, y2 - y1) * (1/8)
        expected_theta = math.atan2(y2 - y1, x2 - x1)
        if not (theta < (expected_theta + math.radians(45)) and theta > (expected_theta - math.radians(45))):
            # We are traveling backwards so adjust the velocity accordingly
            velocity = -velocity
        return velocity

    def checkLightState(self):
        #print ( "tfl " + str((time.time() - self.lightTime)) )
        if (time.time() - self.lightTime) > self.lightTimePeriod:
            self.lightTime = time.time()
            if self.trafficLightArray[1] == 2:
                self.trafficLightArray[1] = 1
                self.trafficLightArray[2] = 0
                self.lightTimePeriod = 3.0
            elif self.trafficLightArray[2] == 2:
                self.trafficLightArray[1] = 0
                self.trafficLightArray[2] = 1
                self.lightTimePeriod = 3.0
            elif self.trafficLightArray[1] == 1:
                self.trafficLightArray[1] = 0
                self.trafficLightArray[2] = 2
                self.lightTimePeriod = 5.0
            elif self.trafficLightArray[2] == 1:
                self.trafficLightArray[1] = 2
                self.trafficLightArray[2] = 0
                self.lightTimePeriod = 5.0

                detections = []

        # # Offsets for map starting positions
        # cav1_x_off = .75
        # cav1_y_off = 0
        # cav1_yaw_off = 0
        # cav2_x_off = .75*2
        # cav2_y_off = 0
        # cav2_yaw_off = 0
        # cam1_x_off = 0
        # cam1_y_off = 0
        # cam1_yaw_off = math.radians(-90)

        # # Rotate our positions
        # cam = (cam[0] + cam1_x_off, cam[1] + cam1_y_off, cam[2] + cam1_yaw_off)
        # cav1 = (cav1_pos[0] + cav1_x_off, cav1_pos[1] + cav1_y_off, cav1_pos[2] + cav1_yaw_off)
        # cav2 = (cav2_pos[0] + cav1_x_off, cav2_pos[1] + cav1_y_off, cav2_pos[2] + cav1_yaw_off)

        # # Accumulate the observations
        # for each in cav1_obs:
        #     new = rotate((0, 0), (each[1], each[2]), cav1_pos[2])
        #     sensed_x = new[0] + cav1_pos[0]
        #     sensed_y = new[1] + cav1_pos[1]
        #     detections.append([sensed_x,sensed_y])

        # for each in cav2_obs:
        #     new = rotate((0, 0), (each[1], each[2]), cav2_pos[2])
        #     sensed_x = new[0] + cav2_pos[0]
        #     sensed_y = new[1] + cav2_pos[1]
        #     detections.append([sensed_x,sensed_y])

        # for each in cam_obs:
        #     new = rotate((0, 0), (each[1], each[2]), cam_pos[2])
        #     sensed_x = new[0] + cam_pos[0]
        #     sensed_y = new[1] + cam_pos[1]
        #     detections.append([sensed_x,sensed_y])
            
        # print ( detections )