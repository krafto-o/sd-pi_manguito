import cv2
import numpy as np
import json
import os

ARCHIVO_CONFIG = "config_hsv.json"


def nada(x):
    pass


def cargar_configuracion_previa():
    """Carga valores anteriores o usa unos por defecto si es la primera vez."""
    if os.path.exists(ARCHIVO_CONFIG):
        with open(ARCHIVO_CONFIG, "r") as f:
            return json.load(f)
    return {
        "h_min": 15,
        "s_min": 60,
        "v_min": 100,
        "h_max": 40,
        "s_max": 255,
        "v_max": 255,
    }


def ejecutar_calibracion(camara_id=2):
    """Abre la interfaz de calibración y bloquea hasta que el usuario presione 'q'."""

    config = cargar_configuracion_previa()

    cv2.namedWindow("Controles HSV")
    cv2.createTrackbar("H Min", "Controles HSV", config["h_min"], 179, nada)
    cv2.createTrackbar("S Min", "Controles HSV", config["s_min"], 255, nada)
    cv2.createTrackbar("V Min", "Controles HSV", config["v_min"], 255, nada)
    cv2.createTrackbar("H Max", "Controles HSV", config["h_max"], 179, nada)
    cv2.createTrackbar("S Max", "Controles HSV", config["s_max"], 255, nada)
    cv2.createTrackbar("V Max", "Controles HSV", config["v_max"], 255, nada)

    cap = cv2.VideoCapture(camara_id)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: No se pudo leer la cámara.")
            break

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Leemos los valores en tiempo real
        h_min = cv2.getTrackbarPos("H Min", "Controles HSV")
        s_min = cv2.getTrackbarPos("S Min", "Controles HSV")
        v_min = cv2.getTrackbarPos("V Min", "Controles HSV")
        h_max = cv2.getTrackbarPos("H Max", "Controles HSV")
        s_max = cv2.getTrackbarPos("S Max", "Controles HSV")
        v_max = cv2.getTrackbarPos("V Max", "Controles HSV")

        bajo = np.array([h_min, s_min, v_min])
        alto = np.array([h_max, s_max, v_max])
        mask = cv2.inRange(hsv, bajo, alto)

        cv2.imshow("Calibracion - Original", frame)
        cv2.imshow("Calibracion - Mascara Binaria", mask)

        # Al presionar 'q', guardamos en JSON y salimos
        if cv2.waitKey(1) & 0xFF == ord("q"):
            nueva_config = {
                "h_min": h_min,
                "s_min": s_min,
                "v_min": v_min,
                "h_max": h_max,
                "s_max": s_max,
                "v_max": v_max,
            }
            with open(ARCHIVO_CONFIG, "w") as f:
                json.dump(nueva_config, f)
            print("Configuración guardada en config_hsv.json")
            break

    cap.release()
    cv2.destroyAllWindows()
