import cv2
import numpy as np
import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import messagebox
import threading
import json
import time
import calibrador  # Importamos tu nuevo archivo modular


# --- CONFIGURACION DE COLORES Y AREA DE OPEN VISION ---
# Función para extraer los arreglos Numpy desde el JSON
def cargar_limites_hsv():
    try:
        with open("config_hsv.json", "r") as f:
            c = json.load(f)
            return (
                np.array([c["h_min"], c["s_min"], c["v_min"]]),
                np.array([c["h_max"], c["s_max"], c["v_max"]]),
            )
    # Valores de seguridad si el archivo no existe
    except Exception as e:
        print(f"Error: {e}")
        return np.array([35, 40, 40]), np.array([85, 255, 255])


VERDE_BAJO = np.array([35, 40, 40])  # TODO: Definir valores para el color verde
VERDE_ALTO = np.array([85, 255, 255])  # TODO: Definir valores para el color amarillo
AREA_MINIMA = 5000

# --- ESTADO GLOBAL ---
arduino = None
estado_sistema = "DESCONECTADO"
programa_corriendo = True  # Controla el ciclo de vida del programa y los hilos
ultimo_comando_vision = None  # Limpieza del puerto serial


def actualizar_interfaz():
    if estado_sistema == "DESCONECTADO":
        btn_conectar.config(state=tk.NORMAL)
        btn_inicio.config(state=tk.DISABLED)
        btn_freno.config(state=tk.DISABLED)
        btn_maduro.config(state=tk.DISABLED)
        btn_verde.config(state=tk.DISABLED)
        btn_emergencia.config(state=tk.DISABLED)
        btn_restablecer.config(state=tk.DISABLED)
        lbl_estado.config(text="Desconectado", fg="red")

    elif estado_sistema == "ESPERANDO":
        btn_conectar.config(state=tk.DISABLED)
        btn_inicio.config(state=tk.NORMAL)
        btn_freno.config(state=tk.DISABLED)
        btn_maduro.config(state=tk.DISABLED)
        btn_verde.config(state=tk.DISABLED)
        btn_emergencia.config(state=tk.DISABLED)
        btn_restablecer.config(state=tk.DISABLED)
        lbl_estado.config(text="Conectado - En Espera", fg="blue")

    elif estado_sistema == "OPERANDO":
        btn_conectar.config(state=tk.DISABLED)
        btn_inicio.config(state=tk.DISABLED)
        btn_freno.config(state=tk.NORMAL)
        btn_maduro.config(state=tk.NORMAL)
        btn_verde.config(state=tk.NORMAL)
        btn_emergencia.config(state=tk.NORMAL)
        btn_restablecer.config(state=tk.DISABLED)
        lbl_estado.config(text="SISTEMA OPERANDO", fg="green")

    elif estado_sistema == "BLOQUEADO":
        btn_conectar.config(state=tk.DISABLED)
        btn_inicio.config(state=tk.DISABLED)
        btn_freno.config(state=tk.DISABLED)
        btn_maduro.config(state=tk.DISABLED)
        btn_verde.config(state=tk.DISABLED)
        btn_emergencia.config(state=tk.DISABLED)
        btn_restablecer.config(state=tk.NORMAL)
        lbl_estado.config(text="EMERGENCIA - BLOQUEADO", fg="red")


def conectar_arduino():
    global arduino, estado_sistema
    if estado_sistema == "BLOQUEADO":
        return

    puertos = list(serial.tools.list_ports.comports())
    for p in puertos:
        if "ttyACM" in p.device or "ttyUSB" in p.device:
            try:
                arduino = serial.Serial(p.device, 9600, timeout=0.05)
                estado_sistema = "ESPERANDO"
                actualizar_interfaz()

                # Inicia la escucha constante del Arduino
                escuchar_arduino()
                return
            except Exception as e:
                print(f"Error: {e}")

    messagebox.showerror("Error", "No se encontro el Arduino.")


def enviar_comando(letra, nuevo_estado=None):
    global estado_sistema
    if arduino and arduino.is_open:
        arduino.write(letra.encode())
        print(f"> Enviado a Arduino: {letra}")
        if nuevo_estado:
            estado_sistema = nuevo_estado
            actualizar_interfaz()


# --- COMUNICACION BIDIRECCIONAL, CONEXION CON ARDUINO ---
def escuchar_arduino():
    """Lee el puerto serial sin bloquear la interfaz de tkinter, se llama a si misma cada 100ms."""
    global estado_sistema
    if arduino and arduino.is_open and programa_corriendo:
        try:
            if arduino.in_waiting > 0:
                mensaje = arduino.readline().decode("utf-8").strip()
                if mensaje:
                    print(f"< Arduino dice: {mensaje}")

                    if "EMERGENCIA_HW" in mensaje and estado_sistema != "BLOQUEADO":
                        estado_sistema = "BLOQUEADO"
                        actualizar_interfaz()
                        messagebox.showerror(
                            "EMERGENCIA FÍSICA",
                            "Alerta del Hardware:\n\nSe presionó el botón físico de paro. El sistema se ha bloqueado.",
                        )
                        verificar_seguridad()
        except Exception as e:
            pass  # TODO: Agregar excepcion y manejador de errores

        # Repetimos el ciclo cada 100 milisegundos
        ventana.after(100, escuchar_arduino)


# --- OPEN CV EN UN HILO SEPARADO ---
def bucle_vision():
    global ultimo_comando_vision

    while programa_corriendo:
        if estado_sistema == "OPERANDO":
            # 1. Cargamos la config fresca justo al arrancar la banda
            VERDE_BAJO, VERDE_ALTO = cargar_limites_hsv()

            # 2. Tomamos control de la cámara
            cap = cv2.VideoCapture(2)

            while estado_sistema == "OPERANDO" and programa_corriendo:
                ret, frame = cap.read()
                if not ret:
                    continue

                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                mask = cv2.inRange(hsv, VERDE_BAJO, VERDE_ALTO)
                mask = cv2.erode(mask, None, iterations=2)
                mask = cv2.dilate(mask, None, iterations=2)

                contornos, _ = cv2.findContours(
                    mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                detectado_verde = False
                for c in contornos:
                    if cv2.contourArea(c) > 5000:
                        x, y, w, h = cv2.boundingRect(c)
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        detectado_verde = True
                        break

                if detectado_verde:
                    if ultimo_comando_vision != "V":
                        enviar_comando("V")
                        ultimo_comando_vision = "V"

                cv2.imshow("Monitor de Produccion", frame)
                cv2.waitKey(1)

            # 3. Al detener la banda, SOLTAMOS la cámara y cerramos la ventana
            cap.release()
            cv2.destroyWindow("Monitor de Produccion")

        else:
            # Si no estamos operando, el hilo duerme un poco para no quemar CPU
            time.sleep(0.2)


def disparar_emergencia():
    global estado_sistema
    if estado_sistema == "OPERANDO":
        enviar_comando("E")
        estado_sistema = "BLOQUEADO"
        actualizar_interfaz()
        messagebox.showerror("EMERGENCIA", "¡Sistema detenido por software!")
        verificar_seguridad()


def verificar_seguridad():
    global estado_sistema
    if messagebox.askyesno("Seguridad", "¿Es seguro restablecer la maquina?"):
        estado_sistema = "ESPERANDO"
        actualizar_interfaz()
    else:
        estado_sistema = "BLOQUEADO"
        actualizar_interfaz()


# --- CIERRE SEGURO ---
def cerrar_programa():
    """Detenemos la maquina por seguridad, apaga la camara y cierra la interfaz."""
    global programa_corriendo
    if messagebox.askokcancel("Salir", "¿Detener todo y cerrar el panel de control?"):
        programa_corriendo = False  # Rompemos el ciclo del hilo de OpenCV

        if arduino and arduino.is_open:
            arduino.write(b"E")  # Frenado total al cerrar
            arduino.close()

        ventana.destroy()


def abrir_herramienta_calibracion():
    if estado_sistema in ["OPERANDO", "BLOQUEADO"]:
        messagebox.showwarning(
            "Atención", "Detén la banda para poder usar la cámara en modo calibración."
        )
        return
    # Esto abrirá las ventanas de OpenCV del otro archivo
    calibrador.ejecutar_calibracion(camara_id=2)
    messagebox.showinfo(
        "Calibración",
        "Se han actualizado los rangos de color. Surtirán efecto en el próximo arranque de la banda.",
    )


# --- Interfaz ---
ventana = tk.Tk()
ventana.title("Manguito v2")
ventana.geometry("450x550")

ventana.protocol("WM_DELETE_WINDOW", cerrar_programa)

lbl_estado = tk.Label(ventana, text="---", font=("Arial", 14, "bold"))
lbl_estado.pack(pady=15)

btn_conectar = tk.Button(ventana, text="🔌 Conectar Arduino", command=conectar_arduino)
btn_conectar.pack(pady=5)

# --- Agregar a la GUI (debajo de btn_conectar) ---
btn_calibrar = tk.Button(
    ventana,
    text="⚙️ Calibrar Cámara (HSV)",
    bg="#e2e3e5",
    command=abrir_herramienta_calibracion,
)
btn_calibrar.pack(pady=5)

# Controles de Banda
frame_banda = tk.LabelFrame(ventana, text=" Banda Transportadora ", padx=10, pady=10)
frame_banda.pack(pady=10)
btn_inicio = tk.Button(
    frame_banda,
    text="▶ INICIAR",
    bg="#d4edda",
    width=12,
    command=lambda: enviar_comando("I", "OPERANDO"),
)
btn_inicio.grid(row=0, column=0, padx=5)
btn_freno = tk.Button(
    frame_banda,
    text="⏹ FRENAR",
    bg="#fff3cd",
    width=12,
    command=lambda: enviar_comando("F", "ESPERANDO"),
)
btn_freno.grid(row=0, column=1, padx=5)

# Controles de Servo
frame_servo = tk.LabelFrame(ventana, text=" Clasificacion Manual 🥭", padx=10, pady=10)
frame_servo.pack(pady=10)
btn_maduro = tk.Button(
    frame_servo,
    text="MADURO",
    bg="#ffeeba",
    width=12,
    command=lambda: enviar_comando("M"),
)
btn_maduro.grid(row=0, column=0, padx=5)
btn_verde = tk.Button(
    frame_servo,
    text="VERDE",
    bg="#c3e6cb",
    width=12,
    command=lambda: enviar_comando("V"),
)
btn_verde.grid(row=0, column=1, padx=5)

# Emergencia y Salida
btn_emergencia = tk.Button(
    ventana,
    text="PARADA DE EMERGENCIA",
    bg="#f8d7da",
    fg="red",
    font=("Arial", 12, "bold"),
    height=2,
    width=30,
    command=disparar_emergencia,
)
btn_emergencia.pack(pady=15)

btn_restablecer = tk.Button(ventana, text="🔄 Restablecer", command=verificar_seguridad)
btn_restablecer.pack(pady=5)

btn_salir = tk.Button(
    ventana, text="❌ Terminar conexion y salir", bg="#e2e3e5", command=cerrar_programa
)
btn_salir.pack(pady=15)

# Iniciamos el hilo de la camara en segundo plano al iniciar
threading.Thread(target=bucle_vision, daemon=True).start()
# TODO:: Agregar manejador de errores por si se ejecuta la interfaz sin la camara conectada
actualizar_interfaz()
ventana.mainloop()
