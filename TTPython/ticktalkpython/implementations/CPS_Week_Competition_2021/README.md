# TickTalk Python, CPS Week Competition - Networked Computing at the Edge

This directory contains a set of files used for a particular application of TTPython on Smart, Signal-Free Intersections of 1/10th Scale Connected Autonomous Vehicles. 

For this competition, we introduced several essential abstractions for TTPython to that existing application developed at Arizona State University. Those abstractions for making communication implicit (by encapsulating values with Tags into Tokens and arbitrating cross-SQ communication through a generic interface within the ProcessManager) and by making real-time and concurrency the basis for synchronizing input values (via WaitingMatching). 

The code for the intersection application resides within the [examples](./examples/') directory, and we used separate files representing the RSU, CAVs, and Camera (infrastructure sensor). These programs were not based on the TTPython programming language, but still on the fundamental components within, such as the SQ abstraction. 

This application is considered an early implementation of the TTPython runtime, which is primarily represented by the [Network](Network.py) and [ProcessManager](ProcessManager.py) classes. These handle the more distributed elements of the program, with the exception of clock-synchronization, for which we set up a local NTP subnet for our four-device network. Clock synchronization is necessary for synchronizing inputs at the global-fusion stage of the application.


