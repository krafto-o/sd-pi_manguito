#include <Arduino.h>
#include <Servo.h>

Servo miServo;

const int pinServo = 9;
int anguloActual = 90; // Empezamos en el punto medio
const int paso = 10;   // Incrementos de 1 grado

void setup() {
  Serial.begin(9600);
  miServo.attach(pinServo);

  miServo.write(anguloActual);

  Serial.println("--- Modo Calibración de Servo ---");
  Serial.println("Instrucciones:");
  Serial.println("- Escribe un numero (0-180) para ir a un angulo exacto.");
  Serial.println("- Envia '+' para aumentar 1 grado.");
  Serial.println("- Envia '-' para disminuir 1 grado.");
  Serial.print("Posicion actual: ");
  Serial.println(anguloActual);
}

void loop() {
  if (Serial.available() > 0) {
    // Leemos la entrada como string para manejar numeros y caracteres
    String entrada = Serial.readStringUntil('\n');
    entrada.trim(); // Limpiar espacios o saltos de linea

    if (entrada == "+") {
      anguloActual = constrain(anguloActual + paso, 0, 180);
    } else if (entrada == "-") {
      anguloActual = constrain(anguloActual - paso, 0, 180);
    } else if (entrada.length() > 0 && isDigit(entrada[0])) {
      // Si la entrada es un número, lo convertimos
      int nuevoAngulo = entrada.toInt();
      anguloActual = constrain(nuevoAngulo, 0, 180);
    }

    miServo.write(anguloActual);
    Serial.print("Angulo actual: ");
    Serial.println(anguloActual);
  }
}
