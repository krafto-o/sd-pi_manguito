#include <Arduino.h>
#include <Servo.h>

// --- HARDWARE ---
Servo miServo;
const int pinMotor = 9;           // PIN para el TIP120
const int pinServo = 10;          // PIN del servo MG995
const int pinBotonEmergencia = 2; // Pin de interrupcion fisica

// NUEVOS PINES: Botones Físicos de Control
const int pinBtnInicio = 3;
const int pinBtnFreno = 4;
const int pinBtnMaduro = 5;
const int pinBtnVerde = 6;

// --- CONSTANTES DEL SERVO ---
const int ANGULO_RUTA_A = 0;  // Verde
const int ANGULO_RUTA_B = 60; // Maduro
int estadoServo = ANGULO_RUTA_A;

// --- ESTADOS DEL SISTEMA ---
enum Estado { ESPERANDO, ACELERANDO, OPERANDO, FRENANDO };
volatile Estado estadoActual = ESPERANDO;

int velocidadMotor = 0;
unsigned long tiempoUltimoPaso = 0;

// Bandera para comunicar la interrupcion al loop principal
volatile bool emergenciaActivada = false;

// --- VARIABLES DE DEBOUNCE (ANTIRREBOTE) ---
bool estadoInicioAnt = HIGH;
bool estadoFrenoAnt = HIGH;
bool estadoMaduroAnt = HIGH;
bool estadoVerdeAnt = HIGH;
unsigned long tiempoDebounce = 0;
const int RETARDO_DEBOUNCE = 50; // 50ms para ignorar ruido eléctrico

// --- RUTINA DE INTERRUPCION ---
void paroDeEmergencia() {
  analogWrite(pinMotor, 0);
  velocidadMotor = 0;
  estadoActual = ESPERANDO;
  emergenciaActivada = true;
  Serial.println("EMERGENCIA_HW");
}

void setup() {
  Serial.begin(9600);
  pinMode(pinMotor, OUTPUT);

  // Pin de interrupción
  pinMode(pinBotonEmergencia, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(pinBotonEmergencia), paroDeEmergencia,
                  FALLING);

  // Configuración de botones físicos de control
  pinMode(pinBtnInicio, INPUT_PULLUP);
  pinMode(pinBtnFreno, INPUT_PULLUP);
  pinMode(pinBtnMaduro, INPUT_PULLUP);
  pinMode(pinBtnVerde, INPUT_PULLUP);

  miServo.attach(pinServo);
  miServo.write(ANGULO_RUTA_A);
  analogWrite(pinMotor, 0);

  Serial.println("SISTEMA LISTO. En espera de comando...");
}

void loop() {
  // 0. GESTIÓN DE EMERGENCIA FÍSICA
  if (emergenciaActivada) {
    Serial.println("!!! EMERGENCIA FISICA !!! Boton presionado.");
    miServo.write(ANGULO_RUTA_A);
    estadoServo = ANGULO_RUTA_A;

    while (Serial.available() > 0) {
      Serial.read();
    }
    emergenciaActivada = false;
  }

  // 1. CAPTURA DE COMANDOS (Fusión de Serial y Hardware)
  char comando = '\0';

  // Opción A: Comando desde Python/OpenCV (Prioridad principal)
  if (Serial.available() > 0) {
    comando = Serial.read();
  }
  // Opción B: Comandos desde Botones Físicos
  else {
    bool inicioAct = digitalRead(pinBtnInicio);
    bool frenoAct = digitalRead(pinBtnFreno);
    bool maduroAct = digitalRead(pinBtnMaduro);
    bool verdeAct = digitalRead(pinBtnVerde);

    // Lógica de detección de "Borde de bajada" (Presión del botón)
    if (millis() - tiempoDebounce > RETARDO_DEBOUNCE) {
      if (inicioAct == LOW && estadoInicioAnt == HIGH) {
        comando = 'I';
        Serial.println("SYNC_I"); // Notifica a Python del cambio
        tiempoDebounce = millis();
      } else if (frenoAct == LOW && estadoFrenoAnt == HIGH) {
        comando = 'F';
        Serial.println("SYNC_F");
        tiempoDebounce = millis();
      } else if (maduroAct == LOW && estadoMaduroAnt == HIGH) {
        comando = 'M';
        Serial.println("SYNC_M");
        tiempoDebounce = millis();
      } else if (verdeAct == LOW && estadoVerdeAnt == HIGH) {
        comando = 'V';
        Serial.println("SYNC_V");
        tiempoDebounce = millis();
      }
    }

    // Guardamos el estado actual para la siguiente vuelta
    estadoInicioAnt = inicioAct;
    estadoFrenoAnt = frenoAct;
    estadoMaduroAnt = maduroAct;
    estadoVerdeAnt = verdeAct;
  }

  // 2. PROCESAMIENTO CENTRAL DE COMANDOS
  if (comando != '\0') {
    if (comando == 'E') {
      estadoActual = ESPERANDO;
      velocidadMotor = 0;
      analogWrite(pinMotor, 0);
      miServo.write(ANGULO_RUTA_A);
      estadoServo = ANGULO_RUTA_A;
      Serial.println("!!! BOTON DE EMERGENCIA PRESIONADO (SOFTWARE) !!!");
    } else if (estadoActual == ESPERANDO && comando == 'I') {
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

  // 3. EJECUTAR LA ACELERACIÓN O FRENADO NO BLOQUEANTE
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
