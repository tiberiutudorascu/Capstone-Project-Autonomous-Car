import cv2
import numpy as np
import csv
import os
import time
from datetime import datetime

focal_length = 544
stop_sign_height = 7.5
stop_sign_width = 7.5
distance_list = ["Departe", "Medie", "Aproape"]

stop_cascade = cv2.CascadeClassifier('classifiers/stop_sign_classifier.xml')
one_way_cascade = cv2.CascadeClassifier('classifiers/one_way_sign_classifier.xml')

print(f"Stop cascade gol: {stop_cascade.empty()}")
print(f"One way cascade gol: {one_way_cascade.empty()}")

# ---------------------------------------------------------------------------
# Telemetrie globala — scrisa de detect_lanes(), citita de Flask prin API
# ---------------------------------------------------------------------------
telemetry = {
    "error": 0,
    "directie": "NECUNOSCUT",
    "intensitate": "NECUNOSCUT",
    "slope": 0.0,
    "semn": "—",
    "viteza_recomandata": 100,   # % din viteza maxima (trimis catre STM32 via UART)
    "timestamp": 0.0,
}

# ---------------------------------------------------------------------------
# Logging CSV
# ---------------------------------------------------------------------------
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
_log_filename = os.path.join(LOG_DIR, f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
_log_file = open(_log_filename, "w", newline="")
_csv_writer = csv.writer(_log_file)
_csv_writer.writerow(["timestamp", "error", "directie", "intensitate", "slope", "semn", "viteza_recomandata"])


def _log_row():
    """Scrie un rand in CSV cu valorile curente din telemetry."""
    t = telemetry
    _csv_writer.writerow([
        round(t["timestamp"], 3),
        t["error"],
        t["directie"],
        t["intensitate"],
        t["slope"],
        t["semn"],
        t["viteza_recomandata"],
    ])
    _log_file.flush()


# ---------------------------------------------------------------------------
# Detectie semne
# ---------------------------------------------------------------------------
def draw_detection(frame, x, y, w, h, label):
    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 5)
    distance = calculate_distance(focal_length, 7.5, h)
    if distance > 50:
        dist_text = distance_list[0]
    elif 20 < distance <= 50:
        dist_text = distance_list[1]
    else:
        dist_text = distance_list[2]
    text = f"{label}: {dist_text}"
    cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    # Actualizeaza telemetria cu semnul detectat
    telemetry["semn"] = label


def calculate_distance(focal_length, real_height, image_height):
    return (real_height * focal_length) // image_height


# ---------------------------------------------------------------------------
# Lane detection — utilitare
# ---------------------------------------------------------------------------
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
        theta=np.pi / 180,
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


# ---------------------------------------------------------------------------
# Detectie curba
# ---------------------------------------------------------------------------
def detect_curve(left_line, right_line):
    """
    Calculeaza directia si intensitatea curburii din cele doua linii de banda.
    Panta = (x2 - x1) / (y2 - y1) — cat de mult se deplaseaza X pe verticala.
      ~0        → drum drept
      pozitiv   → curba la dreapta
      negativ   → curba la stanga
    Returneaza: (directie, intensitate, slope_mediu)
    """
    slopes = []

    for line in [left_line, right_line]:
        if line is None:
            continue
        x1, y1, x2, y2 = line
        dy = y2 - y1
        if dy == 0:
            continue
        slopes.append((x2 - x1) / dy)

    if len(slopes) == 0:
        return "NECUNOSCUT", "NECUNOSCUT", 0.0

    avg_slope = float(np.mean(slopes))
    abs_slope = abs(avg_slope)

    # Clasificare intensitate
    if abs_slope < 0.05:
        intensitate = "DREPT"
    elif abs_slope < 0.15:
        intensitate = "CURBA_USOARA"
    else:
        intensitate = "CURBA_STRANSA"

    # Clasificare directie
    if avg_slope > 0.05:
        directie = "DREAPTA"
    elif avg_slope < -0.05:
        directie = "STANGA"
    else:
        directie = "DREPT"

    return directie, intensitate, round(avg_slope, 3)


# ---------------------------------------------------------------------------
# Viteza adaptiva
# ---------------------------------------------------------------------------
def compute_speed(intensitate, semn):
    """
    Returneaza viteza recomandata (0-100%) in functie de curba si semnele detectate.
    Aceasta valoare poate fi trimisa catre STM32 via UART alaturi de error.
    """
    if semn == "STOP":
        return 0       # Oprire completa
    if intensitate == "CURBA_STRANSA":
        return 40      # Incetinire semnificativa
    if intensitate == "CURBA_USOARA":
        return 70      # Incetinire moderata
    return 100         # Drum drept — viteza maxima


# ---------------------------------------------------------------------------
# Desenare linii + calcul eroare + curba
# ---------------------------------------------------------------------------

# Filtru spike pentru error (ignora salturi bruste > 80px)
_last_error = 0


def draw_lanes_and_get_error(frame, left_lines, right_lines, width, height):
    global _last_error

    left_line = make_average_line(left_lines, height)
    right_line = make_average_line(right_lines, height)

    error = None
    directie = "NECUNOSCUT"
    intensitate = "NECUNOSCUT"
    slope_val = 0.0

    if left_line is not None and right_line is not None:
        lx1, ly1, lx2, ly2 = left_line
        rx1, ry1, rx2, ry2 = right_line

        cv2.line(frame, (lx1, ly1), (lx2, ly2), (0, 255, 0), 6)
        cv2.line(frame, (rx1, ry1), (rx2, ry2), (0, 255, 0), 6)

        center_lanes_bottom = (lx1 + rx1) // 2
        center_image_bottom = width // 2

        raw_error = center_lanes_bottom - center_image_bottom

        # Filtru spike: ignora erori care sar brusc cu mai mult de 80px
        if abs(raw_error - _last_error) > 80:
            error = _last_error
        else:
            error = raw_error
            _last_error = raw_error

        cv2.line(frame, (center_image_bottom, height),
                 (center_lanes_bottom, int(height * 0.7)), (0, 0, 255), 4)

        # Detectie curba
        directie, intensitate, slope_val = detect_curve(left_line, right_line)

        # Overlay pe frame
        cv2.putText(frame, f"Curba: {directie} / {intensitate}", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(frame, f"Slope: {slope_val}", (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 0), 2)
        cv2.putText(frame, f"Eroare: {error}px", (10, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

    return frame, error, directie, intensitate, slope_val


# ---------------------------------------------------------------------------
# Punct de intrare principal — apelat din app.py
# ---------------------------------------------------------------------------
def detect_lanes(frame, frame_gray):
    """
    Ruleaza pipeline-ul complet de lane detection.
    Actualizeaza telemetry global si scrie un rand in CSV.
    Returneaza: (frame_adnotat, error)  — acelasi API ca inainte.
    """
    roi, height, width = get_edges(frame_gray)
    lines = get_lines(roi)
    left_lines, right_lines = split_lines(lines)
    frame, error, directie, intensitate, slope_val = draw_lanes_and_get_error(
        frame, left_lines, right_lines, width, height
    )

    # Viteza adaptiva
    viteza = compute_speed(intensitate, telemetry["semn"])

    # Actualizeaza telemetria globala
    telemetry["error"] = error if error is not None else 0
    telemetry["directie"] = directie
    telemetry["intensitate"] = intensitate
    telemetry["slope"] = slope_val
    telemetry["viteza_recomandata"] = viteza
    telemetry["timestamp"] = round(time.time(), 3)

    # Scrie in CSV
    _log_row()

    # Reseteaza semnul dupa fiecare frame (va fi setat din nou daca e detectat)
    telemetry["semn"] = "—"

    return frame, error
