from __future__ import division

import time
import picamera
import numpy as np
import socket
import sys

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler

motion_dtype = np.dtype([
    ('x', 'i1'),
    ('y', 'i1'),
    ('sad', 'u2'),
    ])

livesplit = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
livesplit.settimeout(3)
livesplit.connect(("stream.lan", 16834))

last_motion = time.time() + 5
mode = 0

class FinishLineDetector(object):
    def __init__(self, camera):
        width, height = camera.resolution
        self.cols = (width + 15) // 16
        self.cols += 1 # there's always an extra column
        self.rows = (height + 15) // 16

    def write(self, s):
        global last_motion
        global mode
        global livesplit
        # Load the motion data from the string to a numpy array
        data = np.fromstring(s, dtype=motion_dtype)
        # Re-shape it and calculate the magnitude of each vector
        data = data.reshape((self.rows, self.cols))
        data = np.sqrt(
            np.square(data['x'].astype(np.float)) +
            np.square(data['y'].astype(np.float))
            ).clip(0, 255).astype(np.uint8)
        # If there're more than 10 vectors with a magnitude greater
        # than 60, then say we've detected motion
        if (data > 90).sum() > 10:
            current_time = time.time()
            if (last_motion <= current_time):
                cmd = "split"
                if (mode == 0):
                    cmd = "starttimer";
                    mode = 1
                livesplit.send(cmd + "\r\n")
                print("\n[" + str(round(current_time, 3)) + "] -> " + cmd)
                last_motion = current_time + 5
        # Pretend we wrote all the bytes of s
        return len(s)

class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        request_path = self.path

        if (request_path == "/reset"):
            global mode
            mode = 0
        # self.wfile.write('hello')
        print "GET: " + request_path
        self.send_response(200)

with picamera.PiCamera() as camera:
    camera.resolution = (1280, 720)
    camera.framerate = 30
    camera.capture('test.jpg')
    camera.start_recording(
        # Throw away the video data, but make sure we're using H.264
        '/dev/null', format='h264',
        # Record motion data to our custom output object
        motion_output=FinishLineDetector(camera)
    )

    port = 8080
    print('Listening on localhost:%s' % port)
    server = HTTPServer(('', port), RequestHandler)
    server.serve_forever()
Raw
