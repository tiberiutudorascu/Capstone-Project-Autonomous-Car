from flask import Flask, Response
import cv2

app = Flask(__name__)
cap = cv2.VideoCapture(0) # Camera ta
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

def generate_frames():
    while True:
        success, frame = cap.read()
        if not success: break
        
      
        
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return "<h1>Camera Masinii</h1><img src='/video' width='640'>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)