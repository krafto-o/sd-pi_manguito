#include <Arduino.h>
#include <Servo.h>

// --- HARDWARE ---
Servo miServo;
const int pinMotor = 9;           // PIN para el TIP120
const int pinServo = 10;          // PIN del servo MG995
const int pinBotonEmergencia = 2; // Pin de interrupcion fisica

// --- CONSTANTES DEL SERVO ---
const int ANGULO_RUTA_A = 0;  // Verde
const int ANGULO_RUTA_B = 60; // Maduro
int estadoServo = ANGULO_RUTA_A;

// --- ESTADOS DEL SISTEMA ---
enum Estado { ESPERANDO, ACELERANDO, OPERANDO, FRENANDO };
// Nota: volatile le dice al compilador que la variable
// puede cambiar en cualquier momento, declararla asi
// previene que la variable quede inaccesible en Runtime
volatile Estado estadoActual = ESPERANDO;

int velocidadMotor = 0;
unsigned long tiempoUltimoPaso = 0;

// Bandera para comunicar la interrupcion al loop principal
volatile bool emergenciaActivada = false;

// --- RUTINA DE INTERRUPCION ---
// Esta funcion se ejecuta al presionar el boton fisico
void paroDeEmergencia() {
  // 1. Cortamos la energia del motor a nivel de hardware
  analogWrite(pinMotor, 0);
  velocidadMotor = 0;

  // 2. Cambiamos el estado y levantamos la bandera
  estadoActual = ESPERANDO;
  emergenciaActivada = true;
  // 3. Avisamos por serial que ocurio un paro de emergencia
  Serial.println("EMERGENCIA_HW");
}

void setup() {
  Serial.begin(9600);
  pinMode(pinMotor, OUTPUT);

  // Configuramos el Pin 2 con su resistencia interna (PULLUP)
  pinMode(pinBotonEmergencia, INPUT_PULLUP);

  // Adjuntamos la interrupcion. FALLING detecta cuando el voltaje
  // cae de 5V a 0V, que seria cuando presionas el boton fisico
  attachInterrupt(digitalPinToInterrupt(pinBotonEmergencia), paroDeEmergencia,
                  FALLING);

  miServo.attach(pinServo);
  miServo.write(ANGULO_RUTA_A);

  analogWrite(pinMotor, 0);
  Serial.println("SISTEMA LISTO. En espera de señal 'I'.");
}

void loop() {
  // 0. GESTIÓN DE LA BANDERA DE EMERGENCIA FÍSICA
  if (emergenciaActivada) {
    Serial.println("!!! EMERGENCIA FISICA !!! Boton presionado.");
    miServo.write(ANGULO_RUTA_A); // Regresamos el servo a la posicion inicial
    estadoServo = ANGULO_RUTA_A;

    // Vaciamos el bufer serial por si la interfaz
    // mando comandos mientras la banda frenaba
    while (Serial.available() > 0) {
      Serial.read();
    }

    emergenciaActivada = false; // Apagamos la bandera para poder reiniciar
  }

  // 1. ESCUCHAR LA CONEXION CON LA INTERFAZ
  if (Serial.available() > 0) {
    char comando = Serial.read();

    // Paro de Emergencia por Software ('E')
    if (comando == 'E') {
      estadoActual = ESPERANDO;
      velocidadMotor = 0;
      analogWrite(pinMotor, 0);
      miServo.write(ANGULO_RUTA_A);
      estadoServo = ANGULO_RUTA_A;
      Serial.println("!!! BOTON DE EMERGENCIA PRESIONADO (SOFTWARE) !!!");
    }
    // Secuencia normal
    else if (estadoActual == ESPERANDO && comando == 'I') {
      estadoActual = ACELERANDO;
      Serial.println("Arrancando banda...");
    } else if (estadoActual == OPERANDO && comando == 'F') {
      estadoActual = FRENANDO;
      Serial.println("Frenando banda...");
    } else if (estadoActual == OPERANDO) {
      if (comando == 'M' && estadoServo != ANGULO_RUTA_B) {
        miServo.write(ANGULO_RUTA_B);
        estadoServo = ANGULO_RUTA_B;
        Serial.println("Clasificando: MADURO");
      } else if (comando == 'V' && estadoServo != ANGULO_RUTA_A) {
        miServo.write(ANGULO_RUTA_A);
        estadoServo = ANGULO_RUTA_A;
        Serial.println("Clasificando: VERDE");
      }
    }
  }

  // 2. EJECUTAR LA ACELERACIÓN O FRENADO
  if (millis() - tiempoUltimoPaso > 10) {
    tiempoUltimoPaso = millis();

    if (estadoActual == ACELERANDO) {
      if (velocidadMotor < 255) {
        velocidadMotor++;
        analogWrite(pinMotor, velocidadMotor);
      } else {
        estadoActual = OPERANDO;
        Serial.println("Velocidad máxima. SISTEMA OPERANDO.");
      }
    } else if (estadoActual == FRENANDO) {
      if (velocidadMotor > 0) {
        velocidadMotor--;
        analogWrite(pinMotor, velocidadMotor);
      } else {
        estadoActual = ESPERANDO;
        Serial.println("Banda detenida. En ESPERA.");
      }
    }
  }
}
