from flask import Flask, Response
import cv2
from threading import Thread
import time
import numpy as np

focal_length = 544
stop_sign_height = 7.5
stop_sign_width = 7.5
distance_list = ["Departe","Medie","Aproape"]

stop_cascade = cv2.CascadeClassifier('classifiers/stop_sign_classifier.xml')
one_way_cascade = cv2.CascadeClassifier('classifiers/one_way_sign_classifier.xml')

print(f"Stop cascade gol: {stop_cascade.empty()}")
print(f"One way cascade gol: {one_way_cascade.empty()}")


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

def calculate_distance(focal_length, real_height, image_height):
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

def make_average_line(lines, height):
    if len(lines) == 0:
        return None
    
    slopes = []
    intercepts = []
    
    for line in lines:
        x1, y1, x2, y2 = line
        if x1 == x2:
            continue
        
        slope = (y2 - y1) / (x2 - x1)
        intercept = y1 - slope * x1
        slopes.append(slope)
        intercepts.append(intercept)
        
    if len(slopes) == 0:
        return None
        
    avg_slope = np.mean(slopes)
    avg_intercept = np.mean(intercepts)
    
    y1 = height
    y2 = int(height * 0.6)
    
    x1 = int((y1 - avg_intercept) / avg_slope)
    x2 = int((y2 - avg_intercept) / avg_slope)
    
    return (x1, y1, x2, y2)

def draw_lanes_and_get_error(frame, left_lines, right_lines, width, height):
    left_line = make_average_line(left_lines, height)
    right_line = make_average_line(right_lines, height)
    
    error = None
    
    if left_line is not None and right_line is not None:
        lx1, ly1, lx2, ly2 = left_line
        rx1, ry1, rx2, ry2 = right_line
        
        cv2.line(frame, (lx1, ly1), (lx2, ly2), (0, 255, 0), 6)
        cv2.line(frame, (rx1, ry1), (rx2, ry2), (0, 255, 0), 6)
        
        center_lanes_bottom = (lx1 + rx1) // 2
        center_image_bottom = width // 2
        
        error = center_lanes_bottom - center_image_bottom
        
        cv2.line(frame, (center_image_bottom, height), (center_lanes_bottom, int(height * 0.7)), (0, 0, 255), 4)
        
    return frame, error

def detect_lanes(frame, frame_gray):
    roi, height, width = get_edges(frame_gray)
    lines = get_lines(roi)
    left_lines, right_lines = split_lines(lines)
    frame, error = draw_lanes_and_get_error(frame, left_lines, right_lines, width, height)
    return frame, error