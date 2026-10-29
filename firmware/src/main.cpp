// CTRL-04L · prueba de hardware · Taller de Interfaces UAI · Luis-Felipe Benitez
// Cada slider llena su mitad de la tira desde abajo, con fundido suave entre LED;
// cada pulsación del botón blanco pasa al siguiente modo (colores fijos y efectos). La OLED muestra niveles y modo. El serial manda una línea JSON cada 50 ms (115200)
// para el dashboard web: {"izq":0-100,"der":0-100,"mv":[mV,mV],"bot":[r,a,b,y],"modo":"..."}.
// Combinaciones: amarillo + blanco = pantalla de prueba (on/off) · rojo + azul = siguiente animación de la OLED.
// El dashboard manda líneas: "n" = siguiente modo; "e" + 32 hex = espectro del audio (16 bandas 0-255) que se dibuja en la OLED.
#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>
#include <Adafruit_NeoPixel.h>

// Pines XIAO ESP32-C3 (A0/GPIO2 y A3/GPIO5 no sirven para los sliders: arranque y ADC2)
const int PIN_SLIDER_IZQ = A1;   // GPIO3
const int PIN_SLIDER_DER = A2;   // GPIO4
const int PIN_BOTON[4] = {D6, D3, D0, D7};          // rojo, azul, blanco, amarillo (a GND) · cableado real
const char *NOMBRE_BOTON[4] = {"ROJO", "AZUL", "BLANCO", "AMARILLO"};
const int PIN_TIRAS = D10;       // GPIO10, por una resistencia de ~330 Ω (D1 NO: es A1, el slider izquierdo)
const int LEDS_POR_TIRA = 4;     // una sola tira de 8: LED 0-3 = slider izquierdo, LED 4-7 = slider derecho
const int BRILLO = 80;           // ~30 %
const bool IZQ_INVERTIDA = true;  // LED 0 de cada mitad queda arriba: crecer desde abajo (botones)
const bool DER_INVERTIDA = false;

U8G2_SSD1306_128X64_NONAME_F_HW_I2C oled(U8G2_R2, U8X8_PIN_NONE);   // SDA D4, SCL D5 · R2: en la caja los pines quedan hacia los botones
Adafruit_NeoPixel tiras(2 * LEDS_POR_TIRA, PIN_TIRAS, NEO_GRB + NEO_KHZ800);

// Lectura en milivoltios calibrados (analogReadMilliVolts) + promedio + suavizado exponencial.
// MV_MIN / MV_MAX: voltaje real en cada punta del recorrido (ajustar con lo que imprime el serial).
const int MV_MIN = 60, MV_MAX = 2830;   // medido: el ADC satura en 2870 mV
const bool SLIDER_INVERTIDO = true;   // cableados con 3V3 en la punta de abajo: abajo = 2870 mV
float suave[2] = {0, 0};
int mvCrudo[2] = {0, 0};

int leerSlider(int pin, int canal) {      // 0..100 %
  long suma = 0;
  for (int i = 0; i < 16; i++) suma += analogReadMilliVolts(pin);
  mvCrudo[canal] = suma / 16;
  suave[canal] += 0.35f * (mvCrudo[canal] - suave[canal]);
  int pct = constrain(map((int)suave[canal], MV_MIN, MV_MAX, 0, 100), 0, 100);
  return SLIDER_INVERTIDO ? 100 - pct : pct;
}

// Modos que recorre el botón blanco: primero los colores fijos, después los efectos
const int N_COLORES = 9;
const uint32_t COLOR_FIJO[N_COLORES] = {0x00FF60, 0xFF0000, 0x0040FF, 0x00C8FF, 0x8A2BE2,
                                        0xFFB000, 0xFF4000, 0xFF3080, 0xFFFFFF};
enum { E_VUMETRO = N_COLORES, E_ARCOIRIS, E_RESPIRA, E_FUEGO, E_LASER, N_MODOS };
const char *NOMBRE_MODO[N_MODOS] = {"VERDE", "ROJO", "AZUL", "CIAN", "MORADO", "AMARILLO", "NARANJO",
                                    "ROSADO", "BLANCO", "VUMETRO", "ARCOIRIS", "RESPIRA", "FUEGO", "LASER"};
int modo = 0;
float mostrado[2] = {0, 0};               // LED encendidos (con decimales), persigue al slider con inercia

// Color de un LED según el modo; pos = 0 abajo .. LEDS_POR_TIRA-1 arriba
uint32_t colorModo(int pos, int lado, unsigned long t) {
  switch (modo) {
    case E_VUMETRO:  return tiras.ColorHSV(21845 - pos * 21845 / (LEDS_POR_TIRA - 1));   // verde abajo → rojo arriba
    case E_ARCOIRIS: return tiras.ColorHSV(t * 20 + pos * 9000 + lado * 32768);         // gira en el tiempo
    case E_RESPIRA:  return tiras.ColorHSV(32000, 255, 70 + 185 * (0.5f + 0.5f * sinf(t / 600.0f)));
    case E_FUEGO:    return tiras.ColorHSV(1200 + random(2500), 255, 140 + random(116));  // parpadeo naranjo
    default:         return COLOR_FIJO[modo];
  }
}

uint32_t escalar(uint32_t c, float f) {   // f 0..1 con corrección de brillo (gamma) para un fundido parejo
  uint8_t k = tiras.gamma8((uint8_t)(f * 255));
  return tiras.Color((uint8_t)(c >> 16) * k / 255, (uint8_t)(c >> 8) * k / 255, (uint8_t)c * k / 255);
}

// Láser: disparos que suben desde abajo hasta donde está el slider, con estela, y destello al llegar
const float LASER_MS_POR_LED = 55.0f;     // velocidad del disparo
const float LASER_PAUSA = 2.5f;           // espacio entre disparos, en "LED" de recorrido
const uint32_t LASER_COLOR = 0xFF0010, LASER_IMPACTO = 0xFFD0C0;

uint32_t colorLaser(int pos, int lado, float alcance, unsigned long t) {
  if (alcance < 0.25f) return 0;
  float ciclo = alcance + LASER_PAUSA;
  float h = fmodf(t / LASER_MS_POR_LED + lado * ciclo / 2, ciclo) - 0.5f;   // lados alternados: pew-pew
  float f = 0;
  if (h <= alcance) {                                   // proyectil en vuelo: cabeza + estela que se apaga
    float d = h - pos;
    if (d > -1.0f && d < 0) f = 1.0f + d;               // cabeza entrando al LED
    else if (d >= 0) f = expf(-d * 1.6f);               // estela
    f *= constrain(alcance - pos, 0.0f, 1.0f);          // nunca pasa del slider
    return escalar(LASER_COLOR, f);
  }
  int tope = constrain((int)ceilf(alcance) - 1, 0, LEDS_POR_TIRA - 1);
  float g = 1.0f - (h - alcance) / 1.2f;                // destello en el punto de impacto
  return pos == tope && g > 0 ? escalar(LASER_IMPACTO, g) : 0;
}

void pintarTira(int lado, int nivel, bool invertida, unsigned long t) {
  mostrado[lado] += 0.18f * (nivel * LEDS_POR_TIRA / 100.0f - mostrado[lado]);    // deslizamiento suave
  for (int pos = 0; pos < LEDS_POR_TIRA; pos++) {
    int led = lado * LEDS_POR_TIRA + (invertida ? LEDS_POR_TIRA - 1 - pos : pos);
    if (modo == E_LASER) { tiras.setPixelColor(led, colorLaser(pos, lado, mostrado[lado], t)); continue; }
    float f = constrain(mostrado[lado] - pos, 0.0f, 1.0f);                         // el LED del borde a medias
    uint32_t c = colorModo(pos, lado, t);
    tiras.setPixelColor(led, escalar(c, f));
  }
}

// Espectro que llega del dashboard (audio del navegador) → barras en la OLED
const int BANDAS = 16;
uint8_t espectro[BANDAS], pico[BANDAS];
unsigned long tEspectro = 0;
char linea[48];
int largo = 0;

int hex(char c) { return c <= '9' ? c - '0' : (c | 0x20) - 'a' + 10; }

void leerSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c != '\n') { if (largo < (int)sizeof(linea) - 1) linea[largo++] = c; continue; }
    linea[largo] = 0;
    if (largo == 1 && linea[0] == 'n') modo = (modo + 1) % N_MODOS;
    if (largo == 1 + 2 * BANDAS && linea[0] == 'e') {
      for (int i = 0; i < BANDAS; i++) espectro[i] = hex(linea[1 + 2 * i]) * 16 + hex(linea[2 + 2 * i]);
      tEspectro = millis();
    }
    largo = 0;
  }
}

void dibujarEspectro(int izq, int der) {
  oled.setFont(u8g2_font_6x12_tf);
  if (millis() - tEspectro > 400) {                     // sin audio: el espectro decae solo
    for (int i = 0; i < BANDAS; i++) espectro[i] = espectro[i] * 0.85f;
    oled.drawStr(0, 9, "SIN AUDIO");
  } else oled.drawStr(0, 9, "AUDIO");
  oled.drawStr(128 - 6 * strlen(NOMBRE_MODO[modo]), 9, NOMBRE_MODO[modo]);
  for (int i = 0; i < BANDAS; i++) {
    int h = espectro[i] * 44 / 255;                                      // barras de 44 px máx.
    if (h >= pico[i]) pico[i] = h; else if (pico[i] > 0) pico[i]--;     // puntito que cae lento
    oled.drawBox(i * 8 + 1, 57 - h, 6, h);
    if (pico[i] > h + 1) oled.drawHLine(i * 8 + 1, 57 - pico[i], 6);
  }
  oled.drawBox(0, 61, izq * 63 / 100, 3);                                // abajo: los dos faders
  oled.drawBox(65, 61, der * 63 / 100, 3);
}

// ---------- Animaciones de la OLED (rojo + azul cambia entre ellas) ----------
enum { A_CUBO, A_ESTRELLAS, A_ESPECTRO, A_TUNEL, A_ONDA, A_OCTAEDRO, N_ANIM };
const char *NOMBRE_ANIM[N_ANIM] = {"CUBO 3D", "HIPERESPACIO", "ESPECTRO", "TUNEL", "ONDA", "OCTAEDRO"};
int anim = A_CUBO;
bool pantallaPrueba = false;
unsigned long tCambioAnim = 0;
float angX = 0, angY = 0, angZ = 0;

float graves() {                                       // energía de graves del audio (0..1); 0 si no llega audio
  if (millis() - tEspectro > 400) return 0;
  return (espectro[0] + espectro[1] + espectro[2] + espectro[3]) / (4 * 255.0f);
}

// Proyecta un punto 3D rotado a la pantalla (centro 64,32) con perspectiva
void proyectar(float x, float y, float z, float escala, int &px, int &py) {
  float y1 = y * cosf(angX) - z * sinf(angX), z1 = y * sinf(angX) + z * cosf(angX);
  float x2 = x * cosf(angY) + z1 * sinf(angY), z2 = -x * sinf(angY) + z1 * cosf(angY);
  float x3 = x2 * cosf(angZ) - y1 * sinf(angZ), y3 = x2 * sinf(angZ) + y1 * cosf(angZ);
  float p = 3.2f / (3.2f + z2);
  px = 64 + x3 * escala * p;
  py = 32 + y3 * escala * p;
}

void solido(const float v[][3], int nv, const uint8_t a[][2], int na, float escala) {
  int px[12], py[12];
  for (int i = 0; i < nv; i++) proyectar(v[i][0], v[i][1], v[i][2], escala, px[i], py[i]);
  for (int i = 0; i < na; i++) oled.drawLine(px[a[i][0]], py[a[i][0]], px[a[i][1]], py[a[i][1]]);
  for (int i = 0; i < nv; i++) oled.drawDisc(px[i], py[i], 1);
}

const float CUBO_V[8][3] = {{-1,-1,-1},{1,-1,-1},{1,1,-1},{-1,1,-1},{-1,-1,1},{1,-1,1},{1,1,1},{-1,1,1}};
const uint8_t CUBO_A[12][2] = {{0,1},{1,2},{2,3},{3,0},{4,5},{5,6},{6,7},{7,4},{0,4},{1,5},{2,6},{3,7}};
const float OCTA_V[6][3] = {{1,0,0},{-1,0,0},{0,1,0},{0,-1,0},{0,0,1},{0,0,-1}};
const uint8_t OCTA_A[12][2] = {{0,2},{0,3},{0,4},{0,5},{1,2},{1,3},{1,4},{1,5},{2,4},{4,3},{3,5},{5,2}};

void dibujarCubo(int izq, int der, float g) {           // fader izq = velocidad de giro · der = tamaño · graves = latido
  float v = 0.01f + izq * 0.0012f;
  angX += v; angY += v * 1.3f; angZ += v * 0.4f;
  float e = 10 + der * 0.16f + g * 10;
  solido(CUBO_V, 8, CUBO_A, 12, e);
  float ax = angX, ay = angY;                            // cubito interior girando al revés
  angX = -ax * 1.7f; angY = -ay * 1.7f;
  solido(CUBO_V, 8, CUBO_A, 12, e * 0.42f);
  angX = ax; angY = ay;
}

void dibujarOctaedro(int izq, int der, float g) {
  float v = 0.012f + izq * 0.001f;
  angX += v * 0.7f; angY += v; angZ += v * 0.3f;
  solido(OCTA_V, 6, OCTA_A, 12, 14 + der * 0.18f + g * 12);
}

const int N_EST = 48;
float est[N_EST][3];
void dibujarEstrellas(int izq, int der, float g) {      // izq = velocidad (warp) · der = largo de la estela
  static bool listo = false;
  if (!listo) { for (auto &e : est) { e[0] = random(-640, 640) / 10.0f; e[1] = random(-320, 320) / 10.0f; e[2] = random(10, 640) / 10.0f; } listo = true; }
  float vel = 0.4f + izq * 0.04f + g * 3;
  for (auto &e : est) {
    float z0 = e[2];
    e[2] -= vel;
    if (e[2] < 1) { e[0] = random(-640, 640) / 10.0f; e[1] = random(-320, 320) / 10.0f; e[2] = 64; continue; }
    int x = 64 + e[0] * 32 / e[2], y = 32 + e[1] * 32 / e[2];
    float zc = min(64.0f, e[2] + vel * (1 + der * 0.06f));
    int xc = 64 + e[0] * 32 / zc, yc = 32 + e[1] * 32 / zc;
    if (x < 0 || x > 127 || y < 0 || y > 63) { e[2] = 0; continue; }
    oled.drawLine(xc, yc, x, y);
    if (z0 < 12) oled.drawPixel(x + 1, y);
  }
}

void dibujarTunel(int izq, int der, float g) {          // izq = velocidad · der = giro
  static float fase = 0, giro = 0;
  fase += 0.02f + izq * 0.0008f + g * 0.05f;
  giro += (der - 50) * 0.0008f;
  for (int k = 0; k < 7; k++) {
    float z = fmodf(fase + k / 7.0f, 1.0f);
    float r = 4 + z * z * 70;
    float a = giro + z * 1.6f;
    int px[4], py[4];
    for (int i = 0; i < 4; i++) {
      px[i] = 64 + r * cosf(a + i * HALF_PI);
      py[i] = 32 + r * 0.6f * sinf(a + i * HALF_PI);
    }
    for (int i = 0; i < 4; i++) oled.drawLine(px[i], py[i], px[(i + 1) % 4], py[(i + 1) % 4]);
  }
}

void dibujarOnda(int izq, int der, float g) {           // izq = frecuencia · der = amplitud · graves = sacudida
  static float fase = 0;
  fase += 0.15f;
  float f = 0.04f + izq * 0.0025f, amp = 4 + der * 0.22f + g * 10;
  int y0 = 32, y1 = 32;
  for (int x = 0; x < 128; x++) {
    int ya = 32 + amp * sinf(x * f + fase);
    int yb = 32 + amp * 0.5f * sinf(x * f * 2.1f - fase * 1.3f);
    if (x) { oled.drawLine(x - 1, y0, x, ya); if (x % 2) oled.drawLine(x - 1, y1, x, yb); }
    y0 = ya; y1 = yb;
  }
}

void dibujarPrueba(int izq, int der, int apretado) {
  oled.setFont(u8g2_font_6x12_tf);
  oled.drawStr(0, 10, "CTRL-04L prueba");
  oled.drawFrame(0, 18, 128, 12);
  oled.drawBox(1, 19, izq * 126 / 100, 10);
  oled.drawFrame(0, 34, 128, 12);
  oled.drawBox(1, 35, der * 126 / 100, 10);
  oled.drawStr(0, 62, apretado >= 0 ? NOMBRE_BOTON[apretado] : "-");
  oled.drawStr(70, 62, NOMBRE_MODO[modo]);
}

void dibujarPantalla(int izq, int der, int apretado) {
  oled.clearBuffer();
  if (pantallaPrueba) dibujarPrueba(izq, der, apretado);
  else {
    float g = graves();
    switch (anim) {
      case A_CUBO:      dibujarCubo(izq, der, g); break;
      case A_ESTRELLAS: dibujarEstrellas(izq, der, g); break;
      case A_ESPECTRO:  dibujarEspectro(izq, der); break;
      case A_TUNEL:     dibujarTunel(izq, der, g); break;
      case A_ONDA:      dibujarOnda(izq, der, g); break;
      case A_OCTAEDRO:  dibujarOctaedro(izq, der, g); break;
    }
    if (millis() - tCambioAnim < 1500) {                 // nombre de la animación al cambiarla
      oled.setFont(u8g2_font_6x12_tf);
      int w = 6 * strlen(NOMBRE_ANIM[anim]) + 6;
      oled.setDrawColor(0); oled.drawBox(0, 0, w, 13); oled.setDrawColor(1);
      oled.drawFrame(0, 0, w, 13);
      oled.drawStr(3, 10, NOMBRE_ANIM[anim]);
    }
  }
  oled.sendBuffer();
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 4; i++) pinMode(PIN_BOTON[i], INPUT_PULLUP);
  analogReadResolution(12);
  oled.setBusClock(400000);                         // I2C rápido: animaciones fluidas
  oled.begin();
  tiras.begin();
  tiras.setBrightness(BRILLO);
  tiras.show();
}

void loop() {
  int izq = leerSlider(PIN_SLIDER_IZQ, 0);
  int der = leerSlider(PIN_SLIDER_DER, 1);
  int apretado = -1;
  for (int i = 0; i < 4; i++)
    if (digitalRead(PIN_BOTON[i]) == LOW) apretado = i;

  // Flancos con antirrebote; índices: 0 rojo, 1 azul, 2 blanco, 3 amarillo
  static bool antes[4] = {false, false, false, false};
  static unsigned long tFlanco[4] = {0, 0, 0, 0};
  bool ahora[4], flanco[4];
  for (int i = 0; i < 4; i++) {
    ahora[i] = digitalRead(PIN_BOTON[i]) == LOW;
    flanco[i] = ahora[i] && !antes[i] && millis() - tFlanco[i] > 150;
    if (flanco[i]) tFlanco[i] = millis();
    antes[i] = ahora[i];
  }
  if ((flanco[2] && ahora[3]) || (flanco[3] && ahora[2])) {        // amarillo + blanco = pantalla de prueba
    pantallaPrueba = !pantallaPrueba;
    if (flanco[3] && !flanco[2]) modo = (modo + N_MODOS - 1) % N_MODOS;   // el blanco ya había cambiado el modo: se deshace
  } else if (flanco[2]) modo = (modo + 1) % N_MODOS;                // blanco solo = siguiente modo de luces
  if ((flanco[0] && ahora[1]) || (flanco[1] && ahora[0])) {         // rojo + azul = siguiente animación
    anim = (anim + 1) % N_ANIM;
    tCambioAnim = millis();
    pantallaPrueba = false;
  }

  unsigned long t = millis();
  pintarTira(0, izq, IZQ_INVERTIDA, t);
  pintarTira(1, der, DER_INVERTIDA, t);
  tiras.show();

  leerSerial();
  dibujarPantalla(izq, der, apretado);

  static unsigned long ultimo = 0;
  if (millis() - ultimo > 50) {
    ultimo = millis();
    int b[4];
    for (int i = 0; i < 4; i++) b[i] = digitalRead(PIN_BOTON[i]) == LOW;
    Serial.printf("{\"izq\":%d,\"der\":%d,\"mv\":[%d,%d],\"bot\":[%d,%d,%d,%d],\"modo\":\"%s\",\"anim\":\"%s\"}\n",
                  izq, der, mvCrudo[0], mvCrudo[1], b[0], b[1], b[2], b[3], NOMBRE_MODO[modo],
                  pantallaPrueba ? "PRUEBA" : NOMBRE_ANIM[anim]);
  }
  delay(15);
}
