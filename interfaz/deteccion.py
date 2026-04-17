import cv2
import numpy as np
import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import messagebox
import threading

VERDE_BAJO = np.array([35, 40, 40])
VERDE_ALTO = np.array([85, 255, 255])
AREA_MINIMA = 5000

arduino = None
estado_sistema = "DESCONECTADO"
corriendo_deteccion = False


def conectar_arduino():
    global arduino, estado_sistema
    puertos = list(serial.tools.list_ports.comports())
    for p in puertos:
        if "ttyACM" in p.device or "ttyUSB" in p.device:
            try:
                arduino = serial.Serial(p.device, 9600, timeout=0.1)
                estado_sistema = "ESPERANDO"
                actualizar_interfaz()
                return
            except Exception as e:
                print(f"Error: {e}")
    messagebox.showerror("Error", "Arduino no detectado.")


def enviar_comando(letra):
    if arduino and arduino.is_open:
        arduino.write(letra.encode())


def bucle_vision():
    global corriendo_deteccion
    cap = cv2.VideoCapture(2)

    while corriendo_deteccion:
        ret, frame = cap.read()
        if not ret:
            break

        # 1. Procesamiento de imagen
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, VERDE_BAJO, VERDE_ALTO)

        # Limpieza de ruido (Erosión y Dilatación)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        # 2. Detección de Contornos
        contornos, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        detectado_verde = False
        for c in contornos:
            area = cv2.contourArea(c)
            if area > AREA_MINIMA:
                # Dibujar rectángulo en pantalla para feedback visual
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                detectado_verde = True
                break

        # 3. Lógica de Control
        if estado_sistema == "OPERANDO":
            if detectado_verde:
                enviar_comando("V")  # Manda señal de Verde (Ruta A)
            else:
                pass

        cv2.imshow("Monitor de Clasificacion", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


def toggle_banda():
    global estado_sistema, corriendo_deteccion
    if estado_sistema == "ESPERANDO":
        enviar_comando("I")
        estado_sistema = "OPERANDO"
        corriendo_deteccion = True
        # Iniciamos el hilo de la cámara
        threading.Thread(target=bucle_vision, daemon=True).start()
    elif estado_sistema == "OPERANDO":
        enviar_comando("F")
        estado_sistema = "ESPERANDO"
        corriendo_deteccion = False
    actualizar_interfaz()


def disparar_emergencia():
    global estado_sistema, corriendo_deteccion
    enviar_comando("E")
    corriendo_deteccion = False
    estado_sistema = "BLOQUEADO"
    actualizar_interfaz()
    messagebox.showerror("!!! EMERGENCIA !!!", "Sistema detenido por completo.")


root = tk.Tk()
root.title("Cerebro Clasificador v3.0")
root.geometry("400x400")

lbl_info = tk.Label(root, text="Estado: Desconectado", font=("Arial", 12))
lbl_info.pack(pady=20)

btn_conectar = tk.Button(root, text="Conectar", command=conectar_arduino)
btn_conectar.pack()

btn_accion = tk.Button(
    root, text="INICIAR BANDA", state=tk.DISABLED, command=toggle_banda
)
btn_accion.pack(pady=10)

btn_stop = tk.Button(
    root, text="PARO EMERGENCIA", bg="red", fg="white", command=disparar_emergencia
)
btn_stop.pack(pady=20)


def actualizar_interfaz():
    lbl_info.config(text=f"Estado: {estado_sistema}")
    if estado_sistema == "ESPERANDO":
        btn_accion.config(text="INICIAR BANDA", state=tk.NORMAL, bg="lightgreen")
    elif estado_sistema == "OPERANDO":
        btn_accion.config(text="DETENER BANDA", state=tk.NORMAL, bg="orange")
    elif estado_sistema == "BLOQUEADO":
        btn_accion.config(state=tk.DISABLED)


root.mainloop()
