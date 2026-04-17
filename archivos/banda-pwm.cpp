#include "Arduino.h"
/*
 * Prueba de Control de Potencia/Velocidad con TIP120
 */
// Definimos el pin de control.
const int pinControl = 10;

void setup() { pinMode(pinControl, OUTPUT); }

void loop() {
  // --- 1: ACELERACION ---
  // El ciclo va desde 0 (0% de energia) hasta 255 (100% de energia)
  for (int velocidad = 0; velocidad <= 255; velocidad++) {

    // analogWrite genera los pulsos PWM
    // la banda arranca desde cero y va ganando velocidad
    analogWrite(pinControl, velocidad);
    delay(15);
  }

  // --- 2: VELOCIDAD FINAL ---
  // Mantenemos la maxima potencia (255) durante 2 segundos
  delay(2000);

  // --- 3: FRENADO SUAVE ---
  // El ciclo ahora va en reversa, bajando de 255 a 0
  for (int velocidad = 255; velocidad >= 0; velocidad--) {
    analogWrite(pinControl, velocidad);
    delay(15);
  }

  // --- 4: ESPERA ---
  // Se envia un 0 para asegurar que se haya detenido y esperamos 2 segundos
  analogWrite(pinControl, 0);
  delay(2000);
}
