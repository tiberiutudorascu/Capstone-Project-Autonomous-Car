import cv2
import os
import yt_dlp

if not os.path.exists('n'):
    os.makedirs('n')

video_url = 'https://www.youtube.com/watch?v=aIeiInlP6Jw'

ydl_opts = {
    'format': 'best[height<=480]',
    'noplaylist': True,
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(video_url, download=False)
    stream_url = info['url'] 

cap = cv2.VideoCapture(stream_url)

count = 0
frame_id = 10938

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    if count % 60 == 0:
        frame_resized = cv2.resize(frame, (640, 480))
        gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
        
        filename = f"n/neg_{frame_id}.jpg"
        cv2.imwrite(filename, gray)
        print(f"Salvat: {filename}")
        frame_id += 1
        
    count += 1    

cap.release()
print(f"Gata! Ai extras {frame_id} poze negative direct de pe YouTube.")
