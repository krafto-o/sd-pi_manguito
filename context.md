# Contexto del Proyecto: Seleccionador de Mangos v2.0 (Dual Mode)

## Descripción General

Este proyecto es un sistema mecatrónico híbrido diseñado para automatizar la clasificación de mangos (Verdes y Maduros) mediante Visión Artificial. El sistema integra una arquitectura orientada a eventos, combinando una interfaz de control en Python (Software) con un microcontrolador Arduino (Hardware) bajo el principio de "Única Fuente de la Verdad" (Single Source of Truth) para mantener los estados sincronizados.

[cite_start]El proyecto cumple con los lineamientos del Proyecto Integrador de 3er semestre de Ingeniería y Desarrollo de Tecnologías de Software[cite: 7, 8].

---

## 1. Arquitectura del Sistema

El proyecto está dividido en tres capas principales que se comunican de forma asíncrona:

1. **Capa de Visión (OpenCV):** Monitorea el flujo de video en tiempo real, aplica máscaras de color HSV y toma decisiones de clasificación.
2. **Capa de Interfaz (Tkinter):** Proporciona un panel de control interactivo para el operador, visualizando el estado del sistema, el monitor de producción y permitiendo el control manual.
3. **Capa de Control Embebido (Arduino):** Actúa como el cerebro principal (Máquina de Estados Finitos). Recibe comandos por Serial y lee botones físicos, controlando directamente la potencia de los motores y la posición del servo.

---

## 2. Hardware y Electrónica

El panel de control físico y los actuadores operan bajo una lógica de optimización de pines y tierras comunes.

### Actuadores y Potencia

* **Fuente de Alimentación:** 24V DC.
* **Master Switch:** Ubicado en la línea positiva (VCC) de 24V antes de la bifurcación a los módulos (Operación restringida a estados de "ESPERA" para evitar arcos eléctricos).
* **Motor de Banda:** Controlado por PWM mediante un transistor TIP120 en el **Pin 9**.
* **Servo Clasificador (MG995):** Conectado en el **Pin 10**.
  * Ruta A (Verde / Reposo): 110 grados.
  * Ruta B (Maduro / Desvío): 70 grados.

### Botonera Física (Pull-Up y Anti-rebote)

Se utiliza una topología de "Daisy Chain" para la Tierra (GND).

* **Pin 2 - Paro de Emergencia:** Botón Push-Push (Enclavamiento). Corta la energía a nivel de hardware y bloquea lógicamente cualquier intento de arranque hasta ser liberado.
* **Pin 3 - Toggle Banda:** Botón de pulso momentáneo. Alterna entre `INICIAR` y `FRENAR` evaluando el estado actual.
* **Pin 4 - Toggle Clasificador:** Botón de pulso momentáneo. Alterna entre la posición `VERDE` y `MADURO`.
* **Retroalimentación Visual (LEDs):** Conectados por hardware puro en paralelo a los botones de pulso (Tirando a tierra la línea de 5V) para brillar instantáneamente al presionar, sin consumir recursos lógicos del Arduino.

---

## 3. Software y Control (Python)

### `control_maquina.py` (Script Principal)

* **Gestión de Hilos:** Utiliza un daemon thread para separar el bucle de captura de video de OpenCV del bucle principal de eventos de la GUI (Tkinter), evitando congelamientos.
* **Gestión de Recursos (Cámara):** El hilo de visión solo toma el control de `/dev/video` cuando el sistema pasa al estado `OPERANDO`. Al detener la banda, la cámara se libera (`cap.release()`).
* **Filtro "Anti-Spam":** Mantiene una variable (`ultimo_comando_vision`) para enviar caracteres por el puerto Serial ('V' o 'M') únicamente cuando hay un cambio real en la detección, evitando la saturación del buffer.

### `calibrador.py` (Módulo Independiente)

* Herramienta de calibración de rangos HSV en tiempo real.
* Sistema de pestañas operado por teclado (`'v'` para calibrar Verde, `'m'` para calibrar Maduro).
* Genera y estructura un archivo `config_hsv.json` para persistencia de datos.

---

## 4. Lógica de Detección (OpenCV)

El sistema utiliza un enfoque de **Doble Máscara (Dual Masking)**:

1. Convierte el frame BGR a HSV.
2. Genera simultáneamente una máscara para el rango "Verde" y otra para el rango "Maduro" basadas en el `config_hsv.json`.
3. Aplica operaciones morfológicas (Erosión y Dilatación) para limpiar ruido eléctrico o sombras.
4. Calcula los contornos. Si el área supera los `5000` píxeles, dibuja el Bounding Box, etiqueta el frame y dispara el evento hacia el Arduino.
5. Prioriza la detección del color verde; si no lo encuentra, evalúa la máscara amarilla/madura. Si la banda está vacía, no hace nada (mantiene el último estado).

---

## 5. Estado Actual del Proyecto (Mayo 2026)

### ✅ Completado y Validado

* [x] Comunicación Serial bidireccional limpia y sin lag.
* [x] Máquina de estados en Arduino funcional (`ESPERANDO`, `ACELERANDO`, `OPERANDO`, `FRENANDO`).
* [x] Calibración independiente mediante JSON sin variables globales conflictivas.
* [x] Fusión de hardware y software: Los botones físicos sincronizan la interfaz gráfica de Python al instante mediante etiquetas `SYNC`.
* [x] Clasificación inteligente (Doble Máscara) validada.
* [x] Sistemas de seguridad (Paro de emergencia físico y lógico, verificación de candados).

### ⏳ Pendiente (Requerimientos de Rúbrica UNACH)

* [ ] **Software (Contadores):** Implementar variables de conteo en `control_maquina.py` para sumar los mangos procesados y mostrar la métrica en un nuevo recuadro de la interfaz gráfica.
* [ ] **Mecánica (Bandeja y Embudo):** Construir la estructura física inclinada requerida para alinear los mangos antes de caer a la banda, evitando atascos.
* [ ] **Montaje Final:** Integrar la electrónica en el panel de control físico, conectar el Switch General y realizar pruebas de flujo continuo.
