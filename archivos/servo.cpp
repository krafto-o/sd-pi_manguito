#include <Arduino.h>
#include <Servo.h>

Servo miServo;

// Definicion de los angulos
const int ANGULO_RUTA_A = 0;  // Posicion base
const int ANGULO_RUTA_B = 60; // Desviacion

// Pin donde conectamos el cable de señal Naranja
const int pinServo = 9;

// Variable para guardar el estado actual
int estadoActual = ANGULO_RUTA_A;

// Funcion para mover el servo solo si es necesario
void moverA(int nuevoAngulo) {
  if (nuevoAngulo != estadoActual) {
    miServo.write(nuevoAngulo);
    estadoActual = nuevoAngulo;
    Serial.print("Moviendo servo a: ");
    Serial.println(nuevoAngulo);
  } else {
    Serial.println("Servo ya esta en posicion.");
  }
}

void setup() {
  Serial.begin(9600);

  miServo.attach(pinServo);

  // Posicion inicial de seguridad
  miServo.write(ANGULO_RUTA_A);
  Serial.println("Sistema de clasificado iniciado. Ruta A activa.");
}

void loop() {
  // --- SIMULACION ---

  Serial.println("Simulando: Deteccion de MANGO MADURO...");
  moverA(ANGULO_RUTA_B);
  delay(1000); // Esperamos a que pase el mango

  Serial.println("Simulando: Deteccion de MANGO VERDE. Regresando...");
  moverA(ANGULO_RUTA_A);
  delay(1000);
}
