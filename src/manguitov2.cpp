#include <Arduino.h>
#include <Servo.h>

// --- HARDWARE ---
Servo miServo;
const int pinMotor = 9;           // PIN para el TIP120
const int pinServo = 10;          // PIN del servo MG995
const int pinBotonEmergencia = 2; // Pin de interrupcion fisica

// NUEVOS PINES: Botones Físicos Unificados (Pulsadores Momentáneos)
const int pinBtnToggleBanda = 3;
const int pinBtnToggleFruta = 4;

// --- CONSTANTES DEL SERVO ---
const int ANGULO_RUTA_A = 110; // Verde
const int ANGULO_RUTA_B = 70;  // Maduro
int estadoServo = ANGULO_RUTA_A;

// --- ESTADOS DEL SISTEMA ---
enum Estado { ESPERANDO, ACELERANDO, OPERANDO, FRENANDO };
volatile Estado estadoActual = ESPERANDO;

int velocidadMotor = 0;
unsigned long tiempoUltimoPaso = 0;

// Bandera para comunicar la interrupcion al loop principal
volatile bool emergenciaActivada = false;

// --- VARIABLES DE DEBOUNCE (ANTIRREBOTE) ---
bool estadoToggleBandaAnt = HIGH;
bool estadoToggleFrutaAnt = HIGH;
unsigned long tiempoDebounce = 0;
const int RETARDO_DEBOUNCE = 200; // 50ms para ignorar ruido eléctrico

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

  // Pin de interrupción (Botón de enclavamiento)
  pinMode(pinBotonEmergencia, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(pinBotonEmergencia), paroDeEmergencia,
                  FALLING);

  // Configuración de los 2 botones de pulso
  pinMode(pinBtnToggleBanda, INPUT_PULLUP);
  pinMode(pinBtnToggleFruta, INPUT_PULLUP);

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

    // Limpiar el buffer serial
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
  // Opción B: Comandos desde Botones Físicos de Pulso
  else {
    bool toggleBandaAct = digitalRead(pinBtnToggleBanda);
    bool toggleFrutaAct = digitalRead(pinBtnToggleFruta);

    // Lógica de detección de "Borde de bajada"
    if (millis() - tiempoDebounce > RETARDO_DEBOUNCE) {

      // BOTÓN 1: INICIO / PARO BANDA
      if (toggleBandaAct == LOW && estadoToggleBandaAnt == HIGH) {
        if (estadoActual == ESPERANDO || estadoActual == FRENANDO) {
          comando = 'I';
          Serial.println("SYNC_I");
        } else {
          comando = 'F';
          Serial.println("SYNC_F");
        }
        tiempoDebounce = millis();
      }

      // BOTÓN 2: CLASIFICACIÓN VERDE / MADURO
      else if (toggleFrutaAct == LOW && estadoToggleFrutaAnt == HIGH) {
        if (estadoServo == ANGULO_RUTA_A) {
          comando = 'M';
          Serial.println("SYNC_M");
        } else {
          comando = 'V';
          Serial.println("SYNC_V");
        }
        tiempoDebounce = millis();
      }
    }

    // Guardamos el estado actual para la siguiente vuelta
    estadoToggleBandaAnt = toggleBandaAct;
    estadoToggleFrutaAnt = toggleFrutaAct;
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
    }

    // --- LÓGICA DE ARRANQUE CON CANDADO DE SEGURIDAD ---
    else if (estadoActual == ESPERANDO && comando == 'I') {
      // Validamos si el botón físico de emergencia sigue sumido (LOW)
      if (digitalRead(pinBotonEmergencia) == LOW) {
        Serial.println("BLOQUEO: Boton de emergencia fisico enclavado. Gire "
                       "para liberar.");
      } else {
        estadoActual = ACELERANDO;
        Serial.println("Arrancando banda...");
      }
    }
    // ---------------------------------------------------

    else if (estadoActual == OPERANDO && comando == 'F') {
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
