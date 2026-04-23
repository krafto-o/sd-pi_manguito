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
AREA_MINIMA = 5000


def cargar_limites_hsv():
    """Carga los límites para AMBOS colores. Usa valores por defecto si falla."""
    try:
        with open("config_hsv.json", "r") as f:
            c = json.load(f)
            # Intentamos leer el nuevo formato anidado
            if "verde" in c and "maduro" in c:
                vb = np.array(
                    [c["verde"]["h_min"], c["verde"]["s_min"], c["verde"]["v_min"]]
                )
                va = np.array(
                    [c["verde"]["h_max"], c["verde"]["s_max"], c["verde"]["v_max"]]
                )
                mb = np.array(
                    [c["maduro"]["h_min"], c["maduro"]["s_min"], c["maduro"]["v_min"]]
                )
                ma = np.array(
                    [c["maduro"]["h_max"], c["maduro"]["s_max"], c["maduro"]["v_max"]]
                )
                return vb, va, mb, ma
            else:
                raise ValueError("El JSON no tiene las claves 'verde' y 'maduro'.")
    except Exception as e:
        print(f"Aviso de Configuración: {e}. Usando valores por defecto.")
        # Valores por defecto (ajustados a tus pruebas previas)
        vb = np.array([22, 51, 94])  # Verde Bajo
        va = np.array([80, 255, 255])  # Verde Alto
        mb = np.array([15, 120, 180])  # Maduro Bajo (Amarillo)
        ma = np.array([30, 255, 255])  # Maduro Alto (Amarillo)
        return vb, va, mb, ma


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
    global estado_sistema, ultimo_comando_vision

    if arduino and arduino.is_open:
        arduino.write(letra.encode())
        print(f"> Enviado a Arduino: {letra}")

        if letra in ["M", "V"]:
            ultimo_comando_vision = letra

        if nuevo_estado:
            estado_sistema = nuevo_estado
            actualizar_interfaz()


# --- COMUNICACION BIDIRECCIONAL ---
def escuchar_arduino():
    global estado_sistema, ultimo_comando_vision
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
                    elif "SYNC_I" in mensaje and estado_sistema == "ESPERANDO":
                        estado_sistema = "OPERANDO"
                        actualizar_interfaz()
                    elif "SYNC_F" in mensaje and estado_sistema == "OPERANDO":
                        estado_sistema = "ESPERANDO"
                        actualizar_interfaz()
                    elif "SYNC_M" in mensaje:
                        ultimo_comando_vision = "M"
                    elif "SYNC_V" in mensaje:
                        ultimo_comando_vision = "V"
        except Exception as e:
            pass  # TODO: Agregar excepcion y manejador de errores

        ventana.after(100, escuchar_arduino)


# --- OPEN CV EN UN HILO SEPARADO ---
def bucle_vision():
    global ultimo_comando_vision

    while programa_corriendo:
        if estado_sistema == "OPERANDO":
            # 1. Cargamos config de AMBOS colores
            V_BAJO, V_ALTO, M_BAJO, M_ALTO = cargar_limites_hsv()

            # 2. Tomamos control de la cámara
            cap = cv2.VideoCapture(0)

            while estado_sistema == "OPERANDO" and programa_corriendo:
                ret, frame = cap.read()
                if not ret:
                    continue

                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

                # --- PROCESAMIENTO MÁSCARA VERDE ---
                mask_v = cv2.inRange(hsv, V_BAJO, V_ALTO)
                mask_v = cv2.erode(mask_v, None, iterations=2)
                mask_v = cv2.dilate(mask_v, None, iterations=2)
                contornos_v, _ = cv2.findContours(
                    mask_v, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                # --- PROCESAMIENTO MÁSCARA MADURO (Amarillo) ---
                mask_m = cv2.inRange(hsv, M_BAJO, M_ALTO)
                mask_m = cv2.erode(mask_m, None, iterations=2)
                mask_m = cv2.dilate(mask_m, None, iterations=2)
                contornos_m, _ = cv2.findContours(
                    mask_m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )

                comando_detectado = None

                # Evaluar primero si hay mangos verdes
                for c in contornos_v:
                    if cv2.contourArea(c) > AREA_MINIMA:
                        x, y, w, h = cv2.boundingRect(c)
                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(
                            frame,
                            "VERDE",
                            (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0, 255, 0),
                            2,
                        )
                        comando_detectado = "V"
                        break

                # Si no vio verdes, buscar maduros
                if not comando_detectado:
                    for c in contornos_m:
                        if cv2.contourArea(c) > AREA_MINIMA:
                            x, y, w, h = cv2.boundingRect(c)
                            cv2.rectangle(
                                frame, (x, y), (x + w, y + h), (0, 255, 255), 2
                            )
                            cv2.putText(
                                frame,
                                "MADURO",
                                (x, y - 10),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.7,
                                (0, 255, 255),
                                2,
                            )
                            comando_detectado = "M"
                            break

                # --- LÓGICA DE CONTROL ---
                if comando_detectado:
                    # Solo enviamos el comando si es distinto al último que mandamos
                    if ultimo_comando_vision != comando_detectado:
                        enviar_comando(comando_detectado)
                        ultimo_comando_vision = comando_detectado

                cv2.imshow("Monitor de Produccion", frame)
                cv2.waitKey(1)

            cap.release()
            cv2.destroyWindow("Monitor de Produccion")

        else:
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


def cerrar_programa():
    global programa_corriendo
    if messagebox.askokcancel("Salir", "¿Detener todo y cerrar el panel de control?"):
        programa_corriendo = False
        if arduino and arduino.is_open:
            arduino.write(b"E")
            arduino.close()
        ventana.destroy()


def abrir_herramienta_calibracion():
    if estado_sistema in ["OPERANDO", "BLOQUEADO"]:
        messagebox.showwarning(
            "Atención", "Detén la banda para poder usar la cámara en modo calibración."
        )
        return
    calibrador.ejecutar_calibracion(camara_id=0)
    messagebox.showinfo(
        "Calibración", "Surtirán efecto en el próximo arranque de la banda."
    )


# --- Interfaz ---
ventana = tk.Tk()
ventana.title("Manguito v2 - Dual Mode")
ventana.geometry("450x550")

ventana.protocol("WM_DELETE_WINDOW", cerrar_programa)

lbl_estado = tk.Label(ventana, text="---", font=("Arial", 14, "bold"))
lbl_estado.pack(pady=15)

btn_conectar = tk.Button(ventana, text="🔌 Conectar Arduino", command=conectar_arduino)
btn_conectar.pack(pady=5)

btn_calibrar = tk.Button(
    ventana,
    text="⚙️ Calibrar Cámara (HSV)",
    bg="#e2e3e5",
    command=abrir_herramienta_calibracion,
)
btn_calibrar.pack(pady=5)

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

threading.Thread(target=bucle_vision, daemon=True).start()
actualizar_interfaz()
ventana.mainloop()
