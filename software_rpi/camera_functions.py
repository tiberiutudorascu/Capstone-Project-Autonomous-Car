from flask import Flask, Response # Importa modulele necesare pentru a face un server web
import cv2 # Importa biblioteca OpenCV pentru procesare de imagini si controlul camerei
from threading import Thread # Importa Threading pentru a rula camera in paralel cu site-ul
import time # Importa modulul de timp pentru pauze si masuratori
import numpy as np # Importa Numpy pentru calcule matematice pe matrici (imagini)
import serial as ser 

focal_length = 544 # px
stop_sign_height = 7.5 # cm
stop_sign_width = 7.5 # cm
distance_list = ["Departe","Medie","Aproape"]

stop_cascade = cv2.CascadeClassifier('classifiers/stop_sign_classifier_2.xml')
one_way_cascade = cv2.CascadeClassifier('classifiers/classifiers')


def draw_detection(frame, x, y, w, h, label):
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 5)
    distance = calculate_distance(focal_length, 7.5, h)
    if distance > 50:
        text = f"{label}: {distance_list[0]}"
    elif 20 < distance <= 50:
        text = f"{label}: {distance_list[1]}"
    else:
        text = f"{label}: {distance_list[2]}"
    cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

def calculate_distance(focal_length,real_height,image_height):
    return (real_height * focal_length) // image_height

def apply_roi(edges, height, width):
    mask = np.zeros_like(edges)
    trapez = np.array([[
        (0, height),
        (width, height),
        (int(width * 0.6), int(height * 0.6)),
        (int(width * 0.4), int(height * 0.6))
    ]], dtype=np.int32)
    cv2.fillPoly(mask, trapez, 255)
    return cv2.bitwise_and(edges, mask)

def get_edges(frame_gray):
    height, width = frame_gray.shape
    blur = cv2.GaussianBlur(frame_gray, (5, 5), 0)
    edges = cv2.Canny(blur, 50, 150)
    roi = apply_roi(edges, height, width)
    return roi, height, width

def get_lines(roi):
    lines = cv2.HoughLinesP(
        roi,
        rho=1,
        theta=np.pi/180,
        threshold=50,
        minLineLength=50,
        maxLineGap=150
    )
    return lines

def split_lines(lines):
    left_lines = []
    right_lines = []
    
    if lines is None:
        return left_lines, right_lines
    
    for line in lines:
        x1, y1, x2, y2 = line[0]
        
        if x2 - x1 == 0:
            continue
            
        slope = (y2 - y1) / (x2 - x1)
        
        if abs(slope) < 0.5:
            continue
        
        if slope < 0:
            left_lines.append(line[0])
        else:
            right_lines.append(line[0])
    
    return left_lines, right_lines

def make_average_line(lines):
    if len(lines) == 0:
        return None
    
    x1 = int(np.mean([l[0] for l in lines]))
    y1 = int(np.mean([l[1] for l in lines]))
    x2 = int(np.mean([l[2] for l in lines]))
    y2 = int(np.mean([l[3] for l in lines]))
    
    return (x1, y1, x2, y2)

def draw_lanes_and_get_error(frame, left_lines, right_lines, width):
    left_line = make_average_line(left_lines)
    right_line = make_average_line(right_lines)
    
    error = None
    
    if left_line is not None:
        cv2.line(frame, (left_line[0], left_line[1]), (left_line[2], left_line[3]), (0, 255, 0), 5)
    
    if right_line is not None:
        cv2.line(frame, (right_line[0], right_line[1]), (right_line[2], right_line[3]), (0, 255, 0), 5)
    
    if left_line is not None and right_line is not None:
        center_lanes = (left_line[0] + right_line[0]) // 2
        center_image = width // 2
        error = center_lanes - center_image
        
        cv2.line(frame, (center_image, frame.shape[0]), (center_lanes, frame.shape[0] - 50), (0, 0, 255), 2)
    
    return frame, error

def detect_lanes(frame, frame_gray):
    roi, height, width = get_edges(frame_gray)
    lines = get_lines(roi)
    left_lines, right_lines = split_lines(lines)
    frame, error = draw_lanes_and_get_error(frame, left_lines, right_lines, width)
    return frame, error