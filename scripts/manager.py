#!/usr/bin/env python3
import sys
print(sys.path)

import asyncio
import websockets
import os
import threading
import time
import json


GAZEBO_RESOURCE_PATH = "export GAZEBO_RESOURCE_PATH=/usr/share/gazebo-9:$GAZEBO_RESOURCE_PATH:"
DISPLAY = ":0"
GZCLIENT_EXERCISES = set(["follow_line"])

instructions = {
    "follow_line": {
        "gazebo_path": "/RoboticsAcademy/exercises/follow_line/web-template/launch",
        "instructions_ros": ["/opt/ros/melodic/bin/roslaunch ./RoboticsAcademy/exercises/follow_line/web-template/launch/simple_line_follower_ros_headless.launch"],
        "instructions_host": "python /RoboticsAcademy/exercises/follow_line/web-template/exercise.py 0.0.0.0"
    },
    "obstacle_avoidance": {
        "gazebo_path": "/RoboticsAcademy/exercises/obstacle_avoidance/web-template/launch",
        "instructions_ros": ["/opt/ros/melodic/bin/roslaunch ./RoboticsAcademy/exercises/obstacle_avoidance/web-template/launch/obstacle_avoidance_f1_headless.launch"],
        "instructions_host": "python /RoboticsAcademy/exercises/obstacle_avoidance/web-template/exercise.py 0.0.0.0"
    },
    "vacuum_cleaner": {
        "gazebo_path": "/RoboticsAcademy/exercises/vacuum_cleaner/web-template/launch",
        "instructions_ros": ["/opt/ros/melodic/bin/roslaunch ./RoboticsAcademy/exercises/vacuum_cleaner/web-template/launch/vacuum_cleaner_headless.launch"],
        "instructions_host": "python /RoboticsAcademy/exercises/vacuum_cleaner/web-template/exercise.py 0.0.0.0"
    },
    "vacuum_cleaner_loc": {
        "gazebo_path": "/RoboticsAcademy/exercises/vacuum_cleaner_loc/web-template/launch",
        "instructions_ros": ["/opt/ros/melodic/bin/roslaunch ./RoboticsAcademy/exercises/vacuum_cleaner_loc/web-template/launch/vacuum_cleaner_headless.launch"],
        "instructions_host": "python /RoboticsAcademy/exercises/vacuum_cleaner_loc/web-template/exercise.py 0.0.0.0"
    },
    "color_filter": {
        "instructions_host": "python /RoboticsAcademy/exercises/color_filter/web-template/exercise.py 0.0.0.0"
    },
    "drone_cat_mouse": {
        "gazebo_path": "/RoboticsAcademy/exercises/drone_cat_mouse/web-template/launch",
        "instructions_ros": ["/opt/ros/melodic/bin/roslaunch ./RoboticsAcademy/exercises/drone_cat_mouse/web-template/launch/drone_cat_mouse.launch"],
        "instructions_host": "python /RoboticsAcademy/exercises/drone_cat_mouse/web-template/exercise.py 0.0.0.0"
    },
    "3dreconstruction": {
        "gazebo_path": "/RoboticsAcademy/exercises/3d_reconstruction/web-template/launch",
        "instructions_ros": [
            "/opt/ros/melodic/bin/roslaunch ./RoboticsAcademy/exercises/3d_reconstruction/web-template/launch/3d_reconstruction_ros.launch"],
        "instructions_host": "python /RoboticsAcademy/exercises/3d_reconstruction/web-template/exercise.py 0.0.0.0"
    },
}


def export_gazebo(exercise):
    gazebo_path = GAZEBO_RESOURCE_PATH + instructions[exercise]["gazebo_path"] + ";"
    return gazebo_path


def ros_instructions(exercise):
    roslaunch_cmd = '/bin/sh -c "export PWD="/";chmod +rwx /;export DISPLAY=:0;export OLDPWD=/etc/ros/rosdep;cd /;export LD_LIBRARY_PATH=/opt/ros/melodic/lib:/usr/lib/x86_64-linux-gnu/gazebo-9/plugins;export GAZEBO_MODEL_PATH=/usr/share/gazebo-9/models:$GAZEBO_MODEL_PATH;export GAZEBO_MODEL_DATABASE_URI=http://gazebosim.org/models;export ROS_DISTRO=melodic;export PKG_CONFIG_PATH=/opt/ros/melodic/lib/pkgconfig;export OGRE_RESOURCE_PATH=/usr/lib/x86_64-linux-gnu/OGRE-1.9.0;export SHLVL=1;export GAZEBO_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/gazebo-9/plugins:${GAZEBO_PLUGIN_PATH};export TERM=xterm;export ROS_VERSION=1;export GAZEBO_MASTER_URI=http://localhost:11345;ROS_ETC_DIR=/opt/ros/melodic/etc/ros;export CMAKE_PREFIX_PATH=/opt/ros/melodic;export ROS_PACKAGE_PATH=/opt/ros/melodic/share; chmod +x /opt/ros/melodic/bin/rosmaster;export ' \
                      'PYTHONPATH=/opt/ros/melodic/lib/python2.7/dist-packages; chmod +x /opt/ros/melodic/bin/roslaunch ; cd ' \
                      '/; export ROS_ROOT=/opt/ros/melodic/share/ros;export GAZEBO_RESOURCE_PATH=/usr/share/gazebo-9:$GAZEBO_RESOURCE_PATH; export ' \
                      'ROS_MASTER_URI=http://localhost:11311; export PATH=/opt/ros/melodic/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin;' \
                      'export ROS_PACKAGE_PATH=/opt/ros/melodic/share:/Firmware:/Firmware/Tools/sitl_gazebo;'
    roslaunch_cmd = roslaunch_cmd + export_gazebo(exercise)
    for instruction in instructions[exercise]["instructions_ros"]:
        roslaunch_cmd = roslaunch_cmd + instruction + ";"
    roslaunch_cmd = roslaunch_cmd + '"'
    return roslaunch_cmd


def start_gzclient(exercise, width, height):
    # Configure browser screen width and height for gzclient
    gzclient_config_cmds = ["echo [geometry] > ~/.gazebo/gui.ini;",
                            "echo x=0 >> ~/.gazebo/gui.ini;",
                            "echo y=0 >> ~/.gazebo/gui.ini;",
                            f"echo width={width} >> ~/.gazebo/gui.ini;",
                            f"echo height={height} >> ~/.gazebo/gui.ini;"]

    # Write display config and start gzclient
    gzclient_cmd = (f"export DISPLAY={DISPLAY};" +
                    export_gazebo(exercise) +
                    "".join(gzclient_config_cmds) +
                    "gzclient --verbose")
    gzclient_thread = DockerThread(gzclient_cmd)
    gzclient_thread.start()

def start_vnc():
    # Start VNC server without password, forever running in background
    x11vnc_cmd = f"x11vnc -display {DISPLAY} -nopw -forever -xkb -bg"
    x11vnc_thread = DockerThread(x11vnc_cmd)
    x11vnc_thread.start()

    # Start noVNC with default port 6080 listening to VNC server on 5900
    novnc_cmd = "/noVNC/utils/launch.sh"
    novnc_thread = DockerThread(novnc_cmd)
    novnc_thread.start()



async def kill_simulation():
    cmd_gzweb = "pkill -9 -f exercise.py"
    os.popen(cmd_gzweb)
    cmd_host = "pkill -9 -f node"
    os.popen(cmd_host)
    cmd_host = "pkill -9 -f gzserver"
    os.popen(cmd_host)
    cmd_ros = "pkill -9 -f roslaunch"
    os.popen(cmd_ros)
    cmd_rosout = "pkill -9 -f rosout"
    os.popen(cmd_rosout)
    cmd_mel = "pkill -9 -f melodroot"
    os.popen(cmd_mel)
    cmd_rosout = "pkill -9 -f rosout"
    os.popen(cmd_rosout)
    cmd_x11vnc = "pkill -9 -f x11vnc"
    os.popen(cmd_x11vnc)
    cmd_novnc = "pkill -9 -f launch.sh"
    os.popen(cmd_novnc)
    """cmd_py = "pkill -9 -f python"
    os.popen(cmd_py)"""


class DockerThread(threading.Thread):
    def __init__(self, cmd):
        threading.Thread.__init__(self)
        self.cmd = cmd

    def run(self):
        stream = os.popen(self.cmd)
        out = stream.read()
        print(out)
        

async def hello(websocket, path):
    # name = await websocket.recv()
    print(websocket)
    async for name in websocket:
        print(name)
        data = json.loads(name)
        command = data["command"]
        if command == "open":
            print("> Starting simulation")
            xvfb_cmd = "/usr/bin/Xorg -noreset +extension GLX +extension RANDR +extension RENDER -logfile ./xdummy.log -config ./xorg.conf :0"
            xvfb_thread = DockerThread(xvfb_cmd)
            xvfb_thread.start()

            host_cmd = instructions[data["exercise"]]["instructions_host"]
            host_thread = DockerThread(host_cmd)
            host_thread.start()

            if not ("color_filter" in data["exercise"]):
                roslaunch_cmd = ros_instructions(data["exercise"])
                roslaunch_thread = DockerThread(roslaunch_cmd)
                roslaunch_thread.start()
                time.sleep(5)

                if (data["exercise"] in GZCLIENT_EXERCISES):
                    # Start x11vnc server
                    start_vnc()

                    # Start gazebo client
                    width = data.get("width", 1920)
                    height = data.get("height", 1080)
                    start_gzclient(data["exercise"], width, height)
                else:
                    gzweb_cmd = 'cd /gzweb; npm start -p 8080'
                    gzweb_thread = DockerThread(gzweb_cmd)
                    gzweb_thread.start()
        elif command == "resume":
            print("RESUME SIMULATIOn")
            cmd = "/opt/ros/melodic/bin/rosservice call gazebo/unpause_physics"
            rosservice_thread = DockerThread(cmd)
            rosservice_thread.start()
        elif command == "stop":
            print("STOP SIMULATIOn")
            cmd = "/opt/ros/melodic/bin/rosservice call gazebo/pause_physics"
            rosservice_thread = DockerThread(cmd)
            rosservice_thread.start()
        elif command == "start":
            cmd = "/opt/ros/melodic/bin/rosservice call gazebo/unpause_physics"
            rosservice_thread = DockerThread(cmd)
            rosservice_thread.start()
        elif command == "reset":
            cmd = "/opt/ros/melodic/bin/rosservice call gazebo/reset_simulation"
            rosservice_thread = DockerThread(cmd)
            rosservice_thread.start()
        else:
            print("ALL KILED")
            await kill_simulation()

        greeting = f"Hello {name}!"

        await websocket.send("Done")
        # print(f"> {greeting}")

start_server = websockets.serve(hello, "0.0.0.0", 8765)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
