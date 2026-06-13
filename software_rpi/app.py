from flask import Flask, Response, jsonify
import cv2
from threading import Thread
import time
import numpy as np
import camera_functions as camera

# ---------------------------------------------------------------------------
# Camera cu thread separat
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Generator cadre video
# ---------------------------------------------------------------------------
def generate_frames():
    while True:
        frame = stream.read()

        if frame is None:
            continue

        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detectie semne
        found_stop_sign = camera.stop_cascade.detectMultiScale(frame_gray, minSize=(20, 20))
        found_way_sign = camera.one_way_cascade.detectMultiScale(
            frame_gray, scaleFactor=1.05, minNeighbors=3, minSize=(32, 32)
        )

        for (x, y, w, h) in found_stop_sign:
            camera.draw_detection(frame, x, y, w, h, "STOP")

        for (x, y, w, h) in found_way_sign:
            camera.draw_detection(frame, x, y, w, h, "SENS UNIC")

        # Lane detection (actualizeaza telemetry intern)
        frame, error = camera.detect_lanes(frame, frame_gray)

        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 50]
        ret, buffer = cv2.imencode('.jpg', frame, encode_param)
        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


# ---------------------------------------------------------------------------
# Rute Flask
# ---------------------------------------------------------------------------
@app.route('/video')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/telemetry')
def telemetry_api():
    """Endpoint JSON poll-uit de dashboard la fiecare secunda."""
    return jsonify(camera.telemetry)


@app.route('/')
def index():
    return """<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Masina Autonoma</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap');

    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      font-size: 14px;
      background: #f5f5f5;
      color: #222;
    }
    h1 {
      font-size: 15px;
      font-weight: 500;
      padding: 12px 16px;
      border-bottom: 1px solid #ddd;
      background: #fff;
    }
    .layout {
      display: grid;
      grid-template-columns: 640px 1fr;
      gap: 16px;
      padding: 16px;
      align-items: start;
    }
    img { display: block; width: 640px; border: 1px solid #ddd; }
    .panel { background: #fff; border: 1px solid #ddd; padding: 14px; }
    table { width: 100%; border-collapse: collapse; }
    td { padding: 7px 4px; border-bottom: 1px solid #eee; }
    td:first-child { color: #666; width: 130px; }
    td:last-child { font-weight: 500; }
    .ok    { color: #1a7a3c; }
    .warn  { color: #b35c00; }
    .alert { color: #b30000; }
  </style>
</head>
<body>
<h1>Masina Autonoma</h1>
<div class="layout">
  <img src="/video" alt="Camera live">
  <div class="panel">
    <table>
      <tr><td>Eroare centru</td><td id="t-error">—</td></tr>
      <tr><td>Directie</td><td id="t-dir">—</td></tr>
      <tr><td>Intensitate curba</td><td id="t-int">—</td></tr>
      <tr><td>Slope</td><td id="t-slope">—</td></tr>
      <tr><td>Semn detectat</td><td id="t-semn">—</td></tr>
      <tr><td>Viteza recomandata</td><td id="t-speed">—</td></tr>
    </table>
  </div>
</div>
<script>
  async function poll() {
    try {
      const d = await fetch('/api/telemetry').then(r => r.json());

      const err = d.error;
      const errEl = document.getElementById('t-error');
      errEl.textContent = err + ' px';
      errEl.className = Math.abs(err) > 80 ? 'alert' : Math.abs(err) > 40 ? 'warn' : 'ok';

      document.getElementById('t-dir').textContent   = d.directie;
      document.getElementById('t-slope').textContent = d.slope.toFixed(3);

      const intEl = document.getElementById('t-int');
      intEl.textContent = d.intensitate;
      intEl.className = d.intensitate === 'CURBA_STRANSA' ? 'alert'
                      : d.intensitate === 'CURBA_USOARA'  ? 'warn' : 'ok';

      const semnEl = document.getElementById('t-semn');
      semnEl.textContent = d.semn;
      semnEl.className   = (d.semn && d.semn !== '—') ? 'alert' : '';

      const spdEl = document.getElementById('t-speed');
      spdEl.textContent = d.viteza_recomandata + ' %';
      spdEl.className   = d.viteza_recomandata === 0   ? 'alert'
                        : d.viteza_recomandata < 60    ? 'warn' : 'ok';
    } catch(e) {}
  }
  setInterval(poll, 300);
  poll();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        stream.stop()