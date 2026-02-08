from flask import Flask, Response # Importa modulele necesare pentru a face un server web
import cv2 # Importa biblioteca OpenCV pentru procesare de imagini si controlul camerei
from threading import Thread # Importa Threading pentru a rula camera in paralel cu site-ul
import time # Importa modulul de timp pentru pauze si masuratori
import numpy as np # Importa Numpy pentru calcule matematice pe matrici (imagini)

class ThreadedCamera: # Defineste o clasa noua pentru a gestiona camera separat
    def __init__(self, src=0): # Functia de initializare care porneste cand cream obiectul
        self.capture = cv2.VideoCapture(src, cv2.CAP_V4L2) # Deschide camera folosind driverul V4L2 (specific Linux/Raspberry Pi)
    
        self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G')) # Seteaza formatul video la MJPG pentru viteza maxima
        
        self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640) # Seteaza latimea imaginii la 640 pixeli
        self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480) # Seteaza inaltimea imaginii la 480 pixeli
        
        self.capture.set(cv2.CAP_PROP_FPS, 30) # Cere camerei sa mearga la 30 de cadre pe secunda

        self.status, self.frame = self.capture.read() # Citeste primul cadru pentru a verifica daca merge
        self.thread = Thread(target=self.update, args=()) # Pregateste un fir de executie separat care va rula functia 'update'
        self.thread.daemon = True # Seteaza firul ca 'daemon' (se inchide automat cand programul principal se inchide)
        self.stopped = False # Variabila de control pentru a sti cand sa oprim camera


    def start(self): # Functie care porneste efectiv citirea paralela
        self.thread.start() # Da startul firului de executie creat mai sus
        return self # Returneaza obiectul curent pentru a putea fi folosit usor

    def update(self): # Functia care ruleaza continuu in fundal
        while not self.stopped: # Cat timp nu am primit comanda de stop
            if self.capture.isOpened(): # Verificam daca camera este inca conectata si deschisa
                (self.status, self.frame) = self.capture.read() # Citim fizic urmatorul cadru din camera
            else:
                time.sleep(0.1) # Daca camera e inchisa, asteptam putin sa nu blocam procesorul

    def read(self): # Functia prin care cerem ultima imagine disponibila
        return self.frame # Returneaza ultimul cadru salvat in memorie (fara sa astepte camera)

    def stop(self): # Functie pentru a opri totul curat
        self.stopped = True # Semnalizeaza buclei while sa se opreasca
        self.capture.release() # Elibereaza camera pentru a putea fi folosita de alte programe

stream = ThreadedCamera(0).start() # Initializam camera si pornim citirea in fundal imediat

app = Flask(__name__) # Cream aplicatia serverului web Flask
stop_cascade = cv2.CascadeClassifier('classifiers/stop_sign_classifier_2.xml')


def generate_frames(): # Functia care genereaza fluxul video pentru browser
    while True: # Bucla infinita care trimite poze catre browser
        frame = stream.read() # Cere ultima imagine de la clasa ThreadedCamera
        
        if frame is None: # Daca din vreun motiv nu avem imagine
            continue # Sarim peste acest pas si incercam din nou
            
        frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # Adaugam Grayscale camerei video
        found = stop_cascade.detectMultiScale(frame_gray, minSize=(20, 20))

        for (x, y, w, h) in found:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 5)

        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 50] # Setam calitatea compresiei JPEG la 50% pentru viteza pe WiFi
        ret, buffer = cv2.imencode('.jpg', frame, encode_param) # Comprimam imaginea bruta in format JPG
        frame_bytes = buffer.tobytes() # Convertim imaginea JPG in biti simpli pentru a fi trimisi pe net

        # Trimitem bucata curenta (imaginea) catre browser intr-un format special (multipart)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video') # Definim adresa web /video
def video_feed(): # Functia care raspunde cand cineva acceseaza /video
    # Returneaza fluxul continuu de imagini generate mai sus
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/') # Definim pagina principala (radacina site-ului)
def index(): # Functia care raspunde cand intri pe IP-ul Raspberry Pi
    # Returneaza un cod HTML simplu care contine titlul si imaginea video
    return "<h1>Camera Masina Autonoma</h1><img src='/video' width='640'>"

if __name__ == '__main__': # Verificam daca rulam acest fisier direct (nu importat)
    try:
        # Pornim serverul web pe toate interfetele (0.0.0.0), portul 5000, fara debug ca sa nu blocheze thread-urile
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt: # Daca apasam Ctrl+C in terminal
        stream.stop() # Oprim camera si eliberam resursele inainte de a iesi