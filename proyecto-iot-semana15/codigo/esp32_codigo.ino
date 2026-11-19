/*
 * PROYECTO: Sistema IoT para el control de entradas y salidas en aulas de clase
 * Grupo B192 - UTS - Kevin Aljuri / Diana Beltran
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <DHT.h>
#include "config.h"   // WIFI_SSID, WIFI_PASS, AIO_USERNAME, AIO_KEY

// ===================== CONFIGURACION =====================
const int MAX_PERSONAS = 5;      // Aforo maximo del aula
const float TEMP_MAX = 35.0;     // Temperatura maxima de referencia (C)
const float HUM_MIN = 40.0;      // Humedad minima de referencia (%)

// ===================== MQTT ADAFRUIT IO =====================
const char* MQTT_SERVER = "io.adafruit.com";
const int MQTT_PORT = 1883;
const char* CLIENT_ID = "ESP32_B192_Kevin_Final";

#define BASE "KevinAlj/feeds"

// Topics de cada feed en Adafruit IO
const char* T_PERSONAS = BASE "/personas";
const char* T_TEMP = BASE "/temperatura";
const char* T_HUM = BASE "/humedad";
const char* T_LUZ = BASE "/luminosidad";
const char* T_LED_ROJO = BASE "/led-rojo";
const char* T_BUZZER = BASE "/buzzer";

// ===================== PINES =====================
#define IR_A_PIN 17        // Sensor IR de entrada
#define IR_B_PIN 18        // Sensor IR de salida
#define IR_ACTIVO LOW      // Los sensores IR dan LOW al detectar
#define DHT_PIN 16
#define DHT_TYPE DHT11
#define LDR_PIN 32         // Entrada analogica (ADC)
#define LED_VERDE 19
#define LED_ROJO 21
#define BUZZER_PIN 22

// ===================== TIEMPOS =====================
const unsigned long INTERVALO_SENSORES = 15000;  // Publicar ambiente cada 15 s
const unsigned long TIMEOUT_CRUCE = 1500;        // Tiempo maximo para completar un cruce

// ===================== OBJETOS Y VARIABLES =====================
DHT dht(DHT_PIN, DHT_TYPE);
WiFiClient espClient;
PubSubClient client(espClient);

int personas = 0;
enum EstadoCruce { LIBRE, A_PRIMERO, B_PRIMERO, ESPERA_LIBRE };
EstadoCruce estadoCruce = LIBRE;

unsigned long tCruce = 0;      // Marca de tiempo del cruce actual
unsigned long tSensores = 0;   // Ultima publicacion de sensores
unsigned long tMqtt = 0;       // Ultimo intento de conexion MQTT
unsigned long tWifi = 0;       // Ultimo intento de reconexion WiFi

bool buzzerManual = false;     // Orden desde el dashboard
bool ledRojoManual = false;    // Orden desde el dashboard
bool estadoBuzzer = false;     // Estado actual para no repetir mensajes

// ===================== WIFI =====================
// Conecta al WiFi al arrancar y espera hasta lograrlo
void conectarWifiInicial() {
  Serial.print("[WiFi] Conectando...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[WiFi] Conectado!");
}

// ===================== BUZZER =====================
// Suena si el aforo se excede o si se activa desde el dashboard
void actualizarBuzzer() {
  bool aforoExcedido = (personas > MAX_PERSONAS);
  bool encender = aforoExcedido || buzzerManual;

  digitalWrite(BUZZER_PIN, encender ? HIGH : LOW);

  // Solo imprime cuando el estado cambia
  if (encender != estadoBuzzer) {
    estadoBuzzer = encender;

    if (encender) {
      if (aforoExcedido) Serial.println("[ALERTA] AFORO EXCEDIDO - BUZZER ON");
      else Serial.println("[BUZZER] Encendido manualmente");
    } else {
      Serial.println("[BUZZER] Apagado");
    }
  }
}

// ===================== LEDS =====================
// Verde si hay cupo; rojo si el aforo se excede o se activa manualmente
void actualizarLeds() {
  bool lleno = (personas > MAX_PERSONAS);
  digitalWrite(LED_VERDE, lleno ? LOW : HIGH);
  digitalWrite(LED_ROJO, (lleno || ledRojoManual) ? HIGH : LOW);
}

// ===================== CALLBACK MQTT =====================
// Recibe las ordenes de los interruptores del dashboard ("1" = encender)
void callbackMQTT(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  msg.trim();

  Serial.print("[MQTT] Comando recibido: ");
  Serial.println(msg);

  if (String(topic) == T_LED_ROJO) {
    ledRojoManual = (msg == "1");
    actualizarLeds();
    Serial.println("[MQTT] LED rojo actualizado");
  }
  else if (String(topic) == T_BUZZER) {
    buzzerManual = (msg == "1");
    actualizarBuzzer();
    Serial.println("[MQTT] Buzzer actualizado");
  }
}

// ===================== PUBLICAR PERSONAS =====================
// Envia el conteo actual al feed "personas"
void publicarPersonas() {
  if (client.connected()) {
    bool enviado = client.publish(T_PERSONAS, String(personas).c_str());

    if (enviado) {
      Serial.print("[MQTT] Personas enviadas: ");
      Serial.println(personas);
    } else {
      Serial.println("[MQTT] Error enviando personas");
    }
  }
}

// ===================== CONEXION MQTT =====================
// Reconecta a Adafruit IO sin bloquear el programa (reintenta cada 5 s)
void vigilarMQTT() {
  if (WiFi.status() != WL_CONNECTED || client.connected()) return;
  if (millis() - tMqtt < 5000) return;
  tMqtt = millis();

  Serial.print("[MQTT] Conectando a Adafruit IO...");

  if (client.connect(CLIENT_ID, AIO_USERNAME, AIO_KEY)) {
    Serial.println("OK");
    client.subscribe(T_LED_ROJO);   // Escucha los interruptores
    client.subscribe(T_BUZZER);
    publicarPersonas();
  } else {
    Serial.print("[MQTT] Error de conexion: ");
    Serial.println(client.state());
  }
}

// ===================== SENSORES IR =====================
// Maquina de estados: A y luego B = ENTRADA; B y luego A = SALIDA
void leerIR() {
  bool a = (digitalRead(IR_A_PIN) == IR_ACTIVO);
  bool b = (digitalRead(IR_B_PIN) == IR_ACTIVO);
  unsigned long ahora = millis();

  switch (estadoCruce) {
    case LIBRE:
      if (a && b) {
        estadoCruce = ESPERA_LIBRE;
        tCruce = ahora;
      }
      else if (a) {            // Se activo primero A
        estadoCruce = A_PRIMERO;
        tCruce = ahora;
      }
      else if (b) {            // Se activo primero B
        estadoCruce = B_PRIMERO;
        tCruce = ahora;
      }
      break;

    case A_PRIMERO:
      if (b) {                 // Cruzo A -> B: entrada
        personas++;
        Serial.print("[IR] ENTRADA -> Personas: ");
        Serial.println(personas);

        estadoCruce = ESPERA_LIBRE;
        tCruce = ahora;
        actualizarLeds();
        actualizarBuzzer();
        publicarPersonas();
      }
      else if (ahora - tCruce > TIMEOUT_CRUCE) {   // Cruce incompleto
        estadoCruce = ESPERA_LIBRE;
        tCruce = ahora;
      }
      break;

    case B_PRIMERO:
      if (a) {                 // Cruzo B -> A: salida
        if (personas > 0) personas--;

        Serial.print("[IR] SALIDA -> Personas: ");
        Serial.println(personas);

        estadoCruce = ESPERA_LIBRE;
        tCruce = ahora;
        actualizarLeds();
        actualizarBuzzer();
        publicarPersonas();
      }
      else if (ahora - tCruce > TIMEOUT_CRUCE) {   // Cruce incompleto
        estadoCruce = ESPERA_LIBRE;
        tCruce = ahora;
      }
      break;

    case ESPERA_LIBRE:
      // Espera a que ambos sensores se liberen antes de aceptar otro cruce
      if (!a && !b && ahora - tCruce > 200) {
        estadoCruce = LIBRE;
      }
      break;
  }
}

// ===================== SENSORES AMBIENTALES =====================
// Lee LDR y DHT11 y los publica en sus feeds
void leerYPublicarAmbiente() {
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  int luz = analogRead(LDR_PIN);     // 0 (oscuro) a 4095 (mucha luz)

  Serial.print("[LDR] Luminosidad: ");
  Serial.println(luz);

  if (client.connected()) {
    bool enviadoLuz = client.publish(T_LUZ, String(luz).c_str());

    if (enviadoLuz) Serial.println("[MQTT] Luminosidad enviada");
    else Serial.println("[MQTT] Error enviando luminosidad");

    delay(500);   // Pausa corta para no superar el limite de Adafruit IO

    if (!isnan(temp) && !isnan(hum)) {
      client.publish(T_TEMP, String(temp, 1).c_str());
      delay(500);
      client.publish(T_HUM, String(hum, 1).c_str());

      Serial.print("[DHT11] Temperatura: ");
      Serial.print(temp);
      Serial.print(" C | Humedad: ");
      Serial.print(hum);
      Serial.println(" %");
    } else {
      Serial.println("[DHT11] Error de lectura");
    }
  } else {
    Serial.println("[MQTT] Sin conexion");
  }
}

// ===================== SETUP =====================
void setup() {
  Serial.begin(115200);

  Serial.println("\n====================================");
  Serial.println(" SISTEMA IoT CONTROL DE AULA - B192");
  Serial.println("====================================");

  pinMode(IR_A_PIN, INPUT);
  pinMode(IR_B_PIN, INPUT);
  pinMode(LDR_PIN, INPUT);
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_ROJO, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(BUZZER_PIN, LOW);
  dht.begin();

  actualizarLeds();
  actualizarBuzzer();
  conectarWifiInicial();

  client.setServer(MQTT_SERVER, MQTT_PORT);
  client.setCallback(callbackMQTT);
}

// ===================== LOOP =====================
void loop() {
  // Reconexion WiFi sin bloquear
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - tWifi >= 5000) {
      tWifi = millis();
      Serial.println("[WiFi] Reconectando...");
      WiFi.disconnect();
      WiFi.begin(WIFI_SSID, WIFI_PASS);
    }
  }

  vigilarMQTT();
  if (client.connected()) client.loop();   // Atiende mensajes entrantes

  leerIR();
  actualizarLeds();
  actualizarBuzzer();

  // Publica luminosidad, temperatura y humedad cada 15 s
  if (millis() - tSensores >= INTERVALO_SENSORES) {
    tSensores = millis();
    leerYPublicarAmbiente();
  }
}
