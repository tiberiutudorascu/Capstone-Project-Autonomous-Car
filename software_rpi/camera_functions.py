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


def calculate_distance(focal_length,real_height,image_height):
    return (real_height * focal_length) // image_height
