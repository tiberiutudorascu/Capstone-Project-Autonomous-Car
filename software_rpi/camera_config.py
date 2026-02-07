from flask import Flask, Response
import cv2

app = Flask(__name__)
cap = cv2.VideoCapture(0) # Camera ta
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

def generate_frames():
    while True:
        success, frame = cap.read()
        if not success: break
        
        # Aici îți faci procesarea OpenCV (linii, semne etc.)
        # ...pip
        
        # Convertim imaginea în jpg pentru a o trimite pe web
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        
        # Trimitem frame-ul ca un flux continuu
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return "<h1>Camera Masinii</h1><img src='/video' width='640'>"

if __name__ == '__main__':
    # Rulam pe toate interfetele (0.0.0.0) pe portul 5000
    app.run(host='0.0.0.0', port=5000, debug=False)