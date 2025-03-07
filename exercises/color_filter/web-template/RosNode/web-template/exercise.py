#!/usr/bin/env python

from __future__ import print_function

from websocket_server import WebsocketServer
import logging
import time
import threading
import sys
from datetime import datetime
import re
import traceback
import imp
import signal
import cv2
import os
from gui import GUI, ThreadGUI
import subprocess
import console

class Template:
    # Initialize class variables
    # self.time_cycle to run an execution for atleast 1 second
    # self.process for the current running process
    def __init__(self):
        self.thread = None
        self.reload = False

        # Time variables
        self.time_cycle = 80
        self.ideal_cycle = 80
        self.iteration_counter = 0

        self.server = None
        self.client = None
        self.host = sys.argv[1]

        # Initialize the GUI, WEBRTC and Console behind the scenes
        self.console = console.Console()
        self.exercice = subprocess.Popen(["python", "consumer.py"], stdout=subprocess.PIPE, preexec_fn=os.setsid)

        self.gui = GUI(self.host, self.console)

    # Function for saving
    def save_code(self, source_code):
        with open('code/academy.py', 'w') as code_file:
            code_file.write(source_code)

    # Function for loading
    def load_code(self):
        with open('code/academy.py', 'r') as code_file:
            source_code = code_file.read()

        return source_code

    # Function to parse the code
    # A few assumptions:
    # 1. The user always passes sequential and iterative codes
    # 2. Only a single infinite loop
    def parse_code(self, source_code):
        # Check for save/load
        if(source_code[:5] == "#save"):
            source_code = source_code[5:]
            self.save_code(source_code)

            return "", "", 1

        elif(source_code[:5] == "#load"):
            source_code = source_code + self.load_code()
            self.server.send_message(self.client, source_code)

            return "", "", 1

        else:
            # Get the frequency of operation, convert to time_cycle and strip
            try:
        		# Get the debug level and strip the debug part
                debug_level = int(source_code[5])
                source_code = source_code[12:]
            except:
                debug_level = 1
                source_code = ""

                source_code = self.debug_parse(source_code, debug_level)

            sequential_code, iterative_code = self.seperate_seq_iter(source_code)
            return iterative_code, sequential_code, debug_level


    # Function to parse code according to the debugging level
    def debug_parse(self, source_code, debug_level):
        if(debug_level == 1):
            # If debug level is 0, then all the GUI operations should not be called
            source_code = re.sub(r'GUI\..*', '', source_code)

        return source_code

    # Function to seperate the iterative and sequential code
    def seperate_seq_iter(self, source_code):
        if source_code == "":
            return "", ""

        # Search for an instance of while True
        infinite_loop = re.search(r'[^ \t]while\(True\):|[^ \t]while True:', source_code)

        # Seperate the content inside while True and the other
        # (Seperating the sequential and iterative part!)
        try:
            start_index = infinite_loop.start()
            iterative_code = source_code[start_index:]
            sequential_code = source_code[:start_index]

            # Remove while True: syntax from the code
            # And remove the the 4 spaces indentation before each command
            iterative_code = re.sub(r'[^ ]while\(True\):|[^ ]while True:', '', iterative_code)
            iterative_code = re.sub(r'^[ ]{4}', '', iterative_code, flags=re.M)

        except:
            sequential_code = source_code
            iterative_code = ""

        return sequential_code, iterative_code


    # The process function
    def process_code(self, source_code):
        # Reference Environment for the exec() function
        reference_environment = {'console': self.console, 'print': print_function}
        iterative_code, sequential_code, debug_level = self.parse_code(source_code)

        # print("The debug level is " + str(debug_level)
        # print(sequential_code)
        # print(iterative_code)


        try:
            # The Python exec function
            # Run the sequential part
            gui_module = self.generate_modules()
            exec(sequential_code, {"GUI": gui_module, "time": time}, reference_environment)

            # Run the iterative part inside template
            # and keep the check for flag
            while self.reload == False:
                start_time = datetime.now()

                # Execute the iterative portion
                exec(iterative_code, reference_environment)

                # Template specifics to run!
                finish_time = datetime.now()
                dt = finish_time - start_time
                ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0

                # Keep updating the iteration counter
                if(iterative_code == ""):
                    self.iteration_counter = 0
                else:
                    self.iteration_counter = self.iteration_counter + 1

                # The code should be run for atleast the target time step
                # If it's less put to sleep
                if(ms < self.time_cycle):
                    time.sleep((self.time_cycle - ms) / 1000.0)

            print("Current Thread Joined!")

        # To print the errors that the user submitted through the Javascript editor (ACE)
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.console.print(str(exc_value))

    # Function to generate the modules for use in ACE Editor
    def generate_modules(self):
        # Define GUI module
        gui_module = imp.new_module("GUI")
        gui_module.GUI = imp.new_module("GUI")

        # Add GUI functions
        gui_module.GUI.showImage = self.gui.showImage
        gui_module.GUI.getImage = self.gui.getImage

        # Adding modules to system
        # Protip: The names should be different from
        # other modules, otherwise some errors
        sys.modules["GUI"] = gui_module

        return gui_module
    # Function to measure the frequency of iterations
    def measure_frequency(self):
        previous_time = datetime.now()
        # An infinite loop
        while self.reload == False:
            # Sleep for 2 seconds
            time.sleep(2)

            # Measure the current time and subtract from the previous time to get real time interval
            current_time = datetime.now()
            dt = current_time - previous_time
            ms = (dt.days * 24 * 60 * 60 + dt.seconds) * 1000 + dt.microseconds / 1000.0
            previous_time = current_time

            # Get the time period
            try:
                # Division by zero
                self.ideal_cycle = ms / self.iteration_counter
            except:
                self.ideal_cycle = 0

            # Reset the counter
            self.iteration_counter = 0

            # Send to client
            try:
                self.server.send_message(self.client, "#freq" + str(round(1000 / self.ideal_cycle, 1)))
            except ZeroDivisionError:
                self.server.send_message(self.client, "#freq" + str(0))

    # Function to maintain thread execution
    def execute_thread(self, source_code):
        # Keep checking until the thread is alive
        # The thread will die when the coming iteration reads the flag
        if(self.thread != None):
            while self.thread.is_alive() or self.measure_thread.is_alive():
                pass

        # Turn the flag down, the iteration has successfully stopped!
        self.reload = False
        # New thread execution
        self.measure_thread = threading.Thread(target=self.measure_frequency)
        self.thread = threading.Thread(target=self.process_code, args=[source_code])
        self.thread.start()
        self.measure_thread.start()
        print("New Thread Started!")

    # The websocket function
    # Gets called when there is an incoming message from the client
    def handle(self, client, server, message):
        if(message[:5] == "#freq"):
            frequency = float(message[5:])
            self.time_cycle = 1000.0 / frequency
            self.server.send_message(self.client, "#ping")
            return

        try:
            # Once received turn the reload flag up and send it to execute_thread function
            code = message
            # print(repr(code))
            self.reload = True
            self.execute_thread(code)
        except:
            pass

    # Function that gets called when the server is connected
    def connected(self, client, server):
        self.client = client
        # Start the GUI update thread
        t = ThreadGUI(self.gui)
        t.start()

        # Initialize the ping message
        self.server.send_message(self.client, "#ping")

        print(client, 'connected')

    # Function that gets called when the connected closes
    def handle_close(self, client, server):
        os.killpg(os.getpgid(self.exercice.pid), signal.SIGKILL)
        print(client, 'closed')

    def run_server(self):
        self.server = WebsocketServer(port=1905, host=self.host)
        self.server.set_fn_new_client(self.connected)
        self.server.set_fn_client_left(self.handle_close)
        self.server.set_fn_message_received(self.handle)
        self.server.run_forever()


# Execute!
if __name__ == "__main__":
    server = Template()
    server.run_server()
