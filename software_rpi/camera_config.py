from flask import Flask, Response
import cv2
from threading import Thread
import time
import numpy as np

class ThreadedCamera:
    def __init__(self, src=0):
        self.capture = cv2.VideoCapture(src, cv2.CAP_V4L2)
    
        self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
        
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.capture.set(cv2.CAP_PROP_FPS, 30)

        self.status, self.frame = self.capture.read()
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True
        self.stopped = False


    def start(self):
        self.thread.start()
        return self

    def update(self):
        while not self.stopped:
            if self.capture.isOpened():
                (self.status, self.frame) = self.capture.read()
            else:
                time.sleep(0.1)

    def read(self):
        return self.frame

    def stop(self):
        self.stopped = True
        self.capture.release()

stream = ThreadedCamera(0).start()

app = Flask(__name__)

def generate_frames():
    while True:
        frame = stream.read()
        
        if frame is None:
            continue
        
        cv2.line(frame, (0,0), (frame.shape[1]//2, frame.shape[0]//2),(255,255,255))
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 50]
        ret, buffer = cv2.imencode('.jpg', frame, encode_param)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return "<h1>Camera Masina Autonoma</h1><img src='/video' width='640'>"

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        stream.stop()