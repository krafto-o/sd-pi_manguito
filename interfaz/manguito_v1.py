import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import messagebox

# --- CONFIGURACION SERIAL Y DE ESTADO ---
arduino = None
estado_sistema = "DESCONECTADO"


def actualizar_interfaz():
    """Logica para control estricto de estados."""
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
                arduino = serial.Serial(p.device, 9600, timeout=1)
                estado_sistema = "ESPERANDO"
                actualizar_interfaz()
                return
            except Exception as e:
                print(f"Error: {e}")

    messagebox.showerror("Error", "No se encontró el Arduino.")


def enviar_comando(letra, nuevo_estado=None):
    global estado_sistema
    if arduino and arduino.is_open:
        arduino.write(letra.encode())
        if nuevo_estado:
            estado_sistema = nuevo_estado
            actualizar_interfaz()


def disparar_emergencia():
    global estado_sistema
    if estado_sistema == "OPERANDO":
        enviar_comando("E")
        estado_sistema = "BLOQUEADO"
        actualizar_interfaz()
        messagebox.showerror("EMERGENCIA", "¡Sistema detenido!")
        verificar_seguridad()


def verificar_seguridad():
    global estado_sistema
    if messagebox.askyesno("Seguridad", "¿Es seguro restablecer?"):
        estado_sistema = "ESPERANDO"
        actualizar_interfaz()
    else:
        estado_sistema = "BLOQUEADO"
        actualizar_interfaz()


# --- Interfaz ---
ventana = tk.Tk()
ventana.title("Panel de Control v2.1")
ventana.geometry("450x500")

lbl_estado = tk.Label(ventana, text="---", font=("Arial", 14, "bold"))
lbl_estado.pack(pady=15)

btn_conectar = tk.Button(ventana, text="🔌 Conectar Arduino", command=conectar_arduino)
btn_conectar.pack(pady=5)

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
frame_servo = tk.LabelFrame(ventana, text=" Clasificación ", padx=10, pady=10)
frame_servo.pack(pady=10)
btn_maduro = tk.Button(
    frame_servo,
    text="🥭 MADURO",
    bg="#ffeeba",
    width=12,
    command=lambda: enviar_comando("M"),
)
btn_maduro.grid(row=0, column=0, padx=5)
btn_verde = tk.Button(
    frame_servo,
    text="🍏 VERDE",
    bg="#c3e6cb",
    width=12,
    command=lambda: enviar_comando("V"),
)
btn_verde.grid(row=0, column=1, padx=5)

# Emergencia
btn_emergencia = tk.Button(
    ventana,
    text="⚠️ PARO DE EMERGENCIA",
    bg="#f8d7da",
    fg="red",
    font=("Arial", 12, "bold"),
    height=2,
    width=30,
    command=disparar_emergencia,
)
btn_emergencia.pack(pady=20)

btn_restablecer = tk.Button(ventana, text="🔄 Restablecer", command=verificar_seguridad)
btn_restablecer.pack()

actualizar_interfaz()
ventana.mainloop()
