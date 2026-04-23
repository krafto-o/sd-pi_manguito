import cv2
import numpy as np
import json
import os

ARCHIVO_CONFIG = "config_hsv.json"


def nada(x):
    pass


def cargar_configuracion_previa():
    """Carga valores anteriores de AMBOS colores o crea una plantilla por defecto."""
    config_por_defecto = {
        "verde": {
            "h_min": 22,
            "s_min": 51,
            "v_min": 94,
            "h_max": 80,
            "s_max": 255,
            "v_max": 255,
        },
        "maduro": {
            "h_min": 15,
            "s_min": 120,
            "v_min": 180,
            "h_max": 30,
            "s_max": 255,
            "v_max": 255,
        },
    }

    if os.path.exists(ARCHIVO_CONFIG):
        try:
            with open(ARCHIVO_CONFIG, "r") as f:
                config_cargada = json.load(f)
                # Validamos que tenga el formato nuevo dual
                if "verde" in config_cargada and "maduro" in config_cargada:
                    return config_cargada
        except:
            print("El JSON antiguo no es compatible. Generando nuevo formato dual.")

    return config_por_defecto


def ejecutar_calibracion(camara_id=0):
    config = cargar_configuracion_previa()
    modo_actual = "verde"  # Empezamos calibrando el verde

    cv2.namedWindow("Controles HSV")

    # Creamos las barras iniciando en 0, luego las ajustaremos
    cv2.createTrackbar("H Min", "Controles HSV", 0, 179, nada)
    cv2.createTrackbar("S Min", "Controles HSV", 0, 255, nada)
    cv2.createTrackbar("V Min", "Controles HSV", 0, 255, nada)
    cv2.createTrackbar("H Max", "Controles HSV", 179, 179, nada)
    cv2.createTrackbar("S Max", "Controles HSV", 255, 255, nada)
    cv2.createTrackbar("V Max", "Controles HSV", 255, 255, nada)

    # Función interna para mover las barras físicamente al cambiar de modo
    def actualizar_barras_gui(modo):
        cv2.setTrackbarPos("H Min", "Controles HSV", config[modo]["h_min"])
        cv2.setTrackbarPos("S Min", "Controles HSV", config[modo]["s_min"])
        cv2.setTrackbarPos("V Min", "Controles HSV", config[modo]["v_min"])
        cv2.setTrackbarPos("H Max", "Controles HSV", config[modo]["h_max"])
        cv2.setTrackbarPos("S Max", "Controles HSV", config[modo]["s_max"])
        cv2.setTrackbarPos("V Max", "Controles HSV", config[modo]["v_max"])

    # Cargamos los valores iniciales del verde a la interfaz
    actualizar_barras_gui(modo_actual)

    cap = cv2.VideoCapture(camara_id)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: No se pudo leer la cámara.")
            break

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 1. Leer valores actuales de la interfaz
        h_min = cv2.getTrackbarPos("H Min", "Controles HSV")
        s_min = cv2.getTrackbarPos("S Min", "Controles HSV")
        v_min = cv2.getTrackbarPos("V Min", "Controles HSV")
        h_max = cv2.getTrackbarPos("H Max", "Controles HSV")
        s_max = cv2.getTrackbarPos("S Max", "Controles HSV")
        v_max = cv2.getTrackbarPos("V Max", "Controles HSV")

        # 2. Guardar en tiempo real en nuestro diccionario en memoria
        config[modo_actual] = {
            "h_min": h_min,
            "s_min": s_min,
            "v_min": v_min,
            "h_max": h_max,
            "s_max": s_max,
            "v_max": v_max,
        }

        # 3. Crear máscara para previsualización
        bajo = np.array([h_min, s_min, v_min])
        alto = np.array([h_max, s_max, v_max])
        mask = cv2.inRange(hsv, bajo, alto)

        # 4. Feedback visual de qué estamos haciendo
        color_texto = (0, 255, 0) if modo_actual == "verde" else (0, 255, 255)
        cv2.putText(
            frame,
            f"CALIBRANDO: {modo_actual.upper()}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            color_texto,
            3,
        )
        cv2.putText(
            frame,
            "Presiona 'v' (Verde) | 'm' (Maduro) | 'q' (Guardar y Salir)",
            (20, 80),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
        )

        cv2.imshow("Calibracion - Original", frame)
        cv2.imshow("Calibracion - Mascara Binaria", mask)

        # 5. Gestión de Teclas
        tecla = cv2.waitKey(1) & 0xFF

        if tecla == ord("v") and modo_actual != "verde":
            modo_actual = "verde"
            actualizar_barras_gui(modo_actual)

        elif tecla == ord("m") and modo_actual != "maduro":
            modo_actual = "maduro"
            actualizar_barras_gui(modo_actual)

        elif tecla == ord("q"):
            # Guardamos el diccionario completo con ambos colores
            with open(ARCHIVO_CONFIG, "w") as f:
                json.dump(config, f, indent=4)
            print("Configuración Dual guardada exitosamente en config_hsv.json")
            break

    cap.release()
    cv2.destroyAllWindows()
