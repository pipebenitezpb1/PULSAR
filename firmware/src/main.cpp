// CTRL-04L · prueba de hardware · Taller de Interfaces UAI · Luis-Felipe Benitez
// Cada slider llena su mitad de la tira desde abajo, con fundido suave entre LED;
// cada pulsación del botón blanco pasa al siguiente modo (colores fijos y efectos). La OLED muestra niveles y modo. El serial manda una línea JSON cada 50 ms (115200)
// para el dashboard web: {"izq":0-100,"der":0-100,"mv":[mV,mV],"bot":[r,a,b,y],"modo":"..."}.
// Combinaciones: rojo + azul = siguiente animación · amarillo + blanco = pantalla de prueba · rojo + amarillo = juegos
// (Pong, Simón dice, Alunizaje) · azul + amarillo = modo exhibición · azul + blanco = brillo · rojo + blanco = pulso
// a golpes (mantener 1,5 s lo apaga) · los 4 juntos = reinicio. OJO: la variable izq es A1 = deslizante físico DERECHO
// (y la mitad 0 de la tira, que está a su lado); der es A2 = el físico IZQUIERDO.
// Récords (Simón, Asteroides, racha de Alunizaje) en la memoria flash: sobreviven al desenchufar.
// "o1" activa el espejo de la OLED: la caja manda "o" + 1024 bytes en base64 (~12 por s) mientras lleguen "o1" cada <3 s.
// El dashboard manda líneas: "n" = siguiente modo; "e" + 32 hex = espectro del audio (16 bandas 0-255) que se dibuja en la OLED.
#include <Arduino.h>
#include <Wire.h>
#include <U8g2lib.h>
#include <Adafruit_NeoPixel.h>
#include <Preferences.h>

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
const uint8_t BRILLOS[3] = {80, 20, 170};
const char *NOMBRE_BRILLO[3] = {"BRILLO NORMAL", "BRILLO BAJO", "BRILLO ALTO"};
int brilloSel = 0;
bool pulso = false;                       // pulso a golpes (rojo + blanco)
unsigned long periodoPulso = 500, tPulso = 0;
unsigned long tDestello[2] = {0, 0};      // destello de una mitad de la tira (juegos)
uint32_t colorDestello[2];

float envolventePulso() {                 // 1 en cada golpe, cae rápido
  if (!pulso) return 0;
  unsigned long fase = (millis() - tPulso) % periodoPulso;
  return expf(-fase / 120.0f);
}
void destello(int lado, uint32_t c) { tDestello[lado] = millis(); colorDestello[lado] = c; }

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
    if (pulso) f *= 0.3f + 0.7f * envolventePulso();                             // late con el pulso
    uint32_t c = colorModo(pos, lado, t);
    tiras.setPixelColor(led, millis() - tDestello[lado] < 160 ? colorDestello[lado] : escalar(c, f));
  }
}

// Espectro que llega del dashboard (audio del navegador) → barras en la OLED
const int BANDAS = 16;
uint8_t espectro[BANDAS], pico[BANDAS];
unsigned long tEspectro = 0;
bool espejo = false;
unsigned long tEspejo = 0;
char linea[48];
int largo = 0;

int hex(char c) { return c <= '9' ? c - '0' : (c | 0x20) - 'a' + 10; }

void leerSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c != '\n') { if (largo < (int)sizeof(linea) - 1) linea[largo++] = c; continue; }
    linea[largo] = 0;
    if (largo == 1 && linea[0] == 'n') modo = (modo + 1) % N_MODOS;
    if (largo == 2 && linea[0] == 'o') { espejo = linea[1] == '1'; tEspejo = millis(); }
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
enum { A_CUBO, A_ESTRELLAS, A_COHETE, A_PLANETA, A_INFINITO, A_RADAR, A_ASTEROIDES, A_GALAXIA,
       A_AGUJERO, A_FUGACES, A_TIERRA, A_ESPECTRO, A_TUNEL, A_ONDA, A_OCTAEDRO, N_ANIM };
const char *NOMBRE_ANIM[N_ANIM] = {"CUBO 3D", "HIPERESPACIO", "COHETE", "PLANETA", "AL INFINITO", "RADAR",
                                   "ASTEROIDES", "GALAXIA", "AGUJERO NEGRO", "FUGACES", "TIERRA",
                                   "ESPECTRO", "TUNEL", "ONDA", "OCTAEDRO"};
Preferences memoria;
int recSimon = 0, recAsteroides = 0, recLuna = 0, rachaLuna = 0;
bool nuevoRecord(const char *clave, int &record, int valor) {      // guarda solo si se superó
  if (valor <= record) return false;
  record = valor; memoria.putInt(clave, valor);
  return true;
}
char avisoTxt[22] = "";
unsigned long tAviso = 0;
void aviso(const char *txt) { strncpy(avisoTxt, txt, sizeof avisoTxt - 1); tAviso = millis(); }
int anim = A_CUBO;
bool pantallaPrueba = false, exhibicion = false;
unsigned long tExhibicion = 0;
float angX = 0, angY = 0, angZ = 0;

float graves() {                                       // energía de graves del audio (0..1); 0 si no llega audio
  if (millis() - tEspectro > 400) return envolventePulso() * 0.8f;   // sin audio: late con el pulso a golpes
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

// ---------- Animaciones espaciales (inspiradas en Buzz Lightyear) ----------
const int N_FONDO = 28;
float fondo[N_FONDO][3];                                // estrellas de fondo: x, y, velocidad
void estrellasFondo(float vel) {                        // campo de estrellas que cae (o queda quieto con vel 0)
  static bool listo = false;
  if (!listo) { for (auto &e : fondo) { e[0] = random(128); e[1] = random(64); e[2] = random(3, 10) / 10.0f; } listo = true; }
  for (auto &e : fondo) {
    e[1] += e[2] * vel;
    if (e[1] > 63) { e[1] = 0; e[0] = random(128); }
    oled.drawPixel(e[0], e[1]);
    if (e[2] > 0.8f && vel > 2) oled.drawPixel(e[0], e[1] - 1);   // las rápidas dejan estela
  }
}

void dibujarCohete(int izq, int der, float g) {          // izq = velocidad · der = lado a lado
  static float x = 64;
  x += ((10 + der * 1.08f) - x) * 0.15f;                // se inclina hacia donde lo llevas
  float vel = 0.5f + izq * 0.06f + g * 4;
  estrellasFondo(vel);
  int cx = x, cy = 30 + 3 * sinf(millis() / 300.0f);
  int llama = 6 + random(4) + vel * 1.5f;                // fuego del motor, titila
  oled.drawTriangle(cx - 3, cy + 9, cx + 3, cy + 9, cx, cy + 9 + llama);
  oled.setDrawColor(0); oled.drawTriangle(cx - 1, cy + 9, cx + 1, cy + 9, cx, cy + 9 + llama / 2); oled.setDrawColor(1);
  oled.drawBox(cx - 3, cy - 6, 7, 15);                   // cuerpo
  oled.drawTriangle(cx - 3, cy - 6, cx + 3, cy - 6, cx, cy - 14);   // nariz
  oled.drawTriangle(cx - 3, cy + 2, cx - 3, cy + 9, cx - 8, cy + 10);   // aletas
  oled.drawTriangle(cx + 3, cy + 2, cx + 3, cy + 9, cx + 8, cy + 10);
  oled.setDrawColor(0); oled.drawDisc(cx, cy - 1, 1); oled.setDrawColor(1);   // ventanilla
}

void dibujarPlaneta(int izq, int der, float g) {         // izq = órbita de la luna · der = tamaño
  static float a = 0;
  a += 0.02f + izq * 0.0012f;
  estrellasFondo(0);
  int r = 9 + der * 0.08f + g * 4, rx = r * 2, ry = r * 0.45f;
  int lx = 64 + (r + 14) * cosf(a), ly = 32 + (r + 14) * 0.35f * sinf(a);
  bool lunaDelante = sinf(a) > 0;
  if (!lunaDelante) oled.drawDisc(lx, ly, 2);
  oled.drawEllipse(64, 32, rx, ry, U8G2_DRAW_UPPER_LEFT | U8G2_DRAW_UPPER_RIGHT);   // anillo de atrás
  oled.setDrawColor(0); oled.drawDisc(64, 32, r); oled.setDrawColor(1);
  oled.drawCircle(64, 32, r);
  for (int k = -1; k <= 1; k++) {                        // franjas del planeta
    int y = 32 + k * r / 2.6f, w = sqrtf(max(0, r * r - (y - 32) * (y - 32))) - 1;
    oled.drawHLine(64 - w, y, 2 * w);
  }
  oled.drawEllipse(64, 32, rx, ry, U8G2_DRAW_LOWER_LEFT | U8G2_DRAW_LOWER_RIGHT);   // anillo de adelante
  oled.drawEllipse(64, 32, rx - 3, ry - 1, U8G2_DRAW_LOWER_LEFT | U8G2_DRAW_LOWER_RIGHT);
  if (lunaDelante) { oled.setDrawColor(0); oled.drawDisc(lx, ly, 3); oled.setDrawColor(1); oled.drawDisc(lx, ly, 2); }
}

void dibujarInfinito(int izq, int der, float g) {        // "¡Al infinito y más allá!": cometa sobre el símbolo ∞
  static float t = 0, texto = 128;
  t += 0.04f + izq * 0.0012f + g * 0.08f;
  float a = 30 + der * 0.22f;
  estrellasFondo(0);
  for (int i = 0; i < 64; i++) {                         // el símbolo, punteado
    float u = i * TWO_PI / 64, d = 1 + sinf(u) * sinf(u);
    oled.drawPixel(64 + a * cosf(u) / d, 26 + a * sinf(u) * cosf(u) / d);
  }
  for (int k = 0; k < 10; k++) {                         // cometa con cola
    float u = t - k * 0.09f, d = 1 + sinf(u) * sinf(u);
    int x = 64 + a * cosf(u) / d, y = 26 + a * sinf(u) * cosf(u) / d;
    if (k == 0) oled.drawDisc(x, y, 3); else if (k < 4) oled.drawDisc(x, y, 1); else oled.drawPixel(x, y);
  }
  const char *frase = "AL INFINITO Y MAS ALLA!";
  texto -= 1.2f;
  if (texto < -6.0f * strlen(frase)) texto = 128;
  oled.setFont(u8g2_font_6x12_tf);
  oled.drawStr(texto, 63, frase);
}

void dibujarRadar(int izq, int der, float g) {           // el comunicador de muñeca: barrido y blips de Zurg
  static float ang = 0;
  static float blip[6][3];                               // ángulo, distancia (0..1), edad
  static bool listo = false;
  if (!listo) { for (auto &b : blip) { b[0] = random(628) / 100.0f; b[1] = random(25, 95) / 100.0f; b[2] = 99; } listo = true; }
  float antes = ang;
  ang += 0.04f + izq * 0.0015f;
  if (ang > TWO_PI) ang -= TWO_PI;
  const int cx = 64, cy = 32, R = 30;
  float zoom = 0.6f + der * 0.008f;
  oled.drawCircle(cx, cy, R); oled.drawCircle(cx, cy, R * 2 / 3); oled.drawCircle(cx, cy, R / 3);
  oled.drawHLine(cx - R, cy, 2 * R + 1); oled.drawVLine(cx, cy - R, 2 * R + 1);
  for (int k = 0; k < 6; k++)                            // barrido con estela
    oled.drawLine(cx, cy, cx + R * cosf(ang - k * 0.05f), cy + R * sinf(ang - k * 0.05f));
  for (auto &b : blip) {
    bool cruzo = antes < ang ? (b[0] > antes && b[0] <= ang) : (b[0] > antes || b[0] <= ang);
    if (cruzo) b[2] = 0;
    if (b[2] < 45) {
      int x = cx + R * b[1] * zoom * cosf(b[0]), y = cy + R * b[1] * zoom * sinf(b[0]);
      oled.drawDisc(x, y, b[2] < 15 ? 2 + g * 2 : 1);
    }
    b[2]++;
    if (b[2] == 200) { b[0] = random(628) / 100.0f; b[1] = random(25, 95) / 100.0f; }   // el blip se mueve
  }
  oled.setFont(u8g2_font_5x7_tf);
  oled.drawStr(0, 7, "SECTOR"); oled.drawStr(0, 15, "12");
  oled.drawStr(103, 63, "ZURG?");
}

void dibujarAsteroides(int izq, int der, float g) {      // la nave dispara sola · izq = velocidad · der = posición
  struct Roca { float x, y, v; int r; };
  static Roca roca[6];
  static float bala[6][2];
  static float chispa[24][4];                            // x, y, vx, vy
  static int vida[24], puntos = 0, cuadro = 0;
  static bool listo = false;
  if (!listo) {
    for (auto &r : roca) r = {(float)random(8, 120), (float)-random(64), random(3, 8) / 10.0f, (int)random(2, 6)};
    for (auto &b : bala) b[1] = -1;
    listo = true;
  }
  estrellasFondo(0.4f);
  int nx = 8 + der * 1.12f;
  float vel = 0.4f + izq * 0.02f + g;
  if (++cuadro % 7 == 0)                                 // dispara
    for (auto &b : bala) if (b[1] < 0) { b[0] = nx; b[1] = 54; break; }
  for (auto &b : bala) if (b[1] >= 0) { b[1] -= 4; oled.drawVLine(b[0], b[1], 3); }
  for (auto &r : roca) {
    r.y += r.v * vel;
    if (r.y > 70) r = {(float)random(8, 120), -8, random(3, 8) / 10.0f, (int)random(2, 6)};
    if (r.y > 52 && r.y < 62 && fabsf(r.x - nx) < r.r + 4) {     // la roca chocó con la nave
      if (nuevoRecord("ast", recAsteroides, puntos)) aviso("NUEVO RECORD!");
      destello(0, 0xFF0000); destello(1, 0xFF0000);
      puntos = 0;
      r = {(float)random(8, 120), -8, random(3, 8) / 10.0f, (int)random(2, 6)};
    }
    for (auto &b : bala)
      if (b[1] >= 0 && fabsf(b[0] - r.x) <= r.r + 1 && fabsf(b[1] - r.y) <= r.r + 1) {   // impacto
        for (int k = 0, n = 0; k < 24 && n < 6; k++)
          if (vida[k] <= 0) { chispa[k][0] = r.x; chispa[k][1] = r.y; chispa[k][2] = random(-20, 21) / 10.0f; chispa[k][3] = random(-20, 21) / 10.0f; vida[k] = 12; n++; }
        b[1] = -1; puntos++;
        r = {(float)random(8, 120), -8, random(3, 8) / 10.0f, (int)random(2, 6)};
      }
    oled.drawCircle(r.x, r.y, r.r);
  }
  for (int k = 0; k < 24; k++)
    if (vida[k] > 0) { chispa[k][0] += chispa[k][2]; chispa[k][1] += chispa[k][3]; oled.drawPixel(chispa[k][0], chispa[k][1]); vida[k]--; }
  oled.drawTriangle(nx - 5, 62, nx + 5, 62, nx, 54);    // nave
  char txt[16]; snprintf(txt, sizeof txt, "%d", puntos);
  oled.setFont(u8g2_font_5x7_tf);
  oled.drawStr(127 - 5 * strlen(txt), 7, txt);
  snprintf(txt, sizeof txt, "REC %d", max(recAsteroides, puntos));
  oled.drawStr(0, 7, txt);
}

void dibujarGalaxia(int izq, int der, float g) {         // espiral de dos brazos · izq = giro · der = tamaño
  static float rot = 0;
  rot += 0.01f + izq * 0.0006f;
  float tam = 0.6f + der * 0.006f + g * 0.3f;
  for (int brazo = 0; brazo < 2; brazo++)
    for (int i = 0; i < 70; i++) {
      float rr = i * 0.55f * tam, a = rot + brazo * PI + i * 0.11f;
      float dx = (i * 37 % 7 - 3) * 0.5f, dy = (i * 53 % 5 - 2) * 0.4f;   // dispersión fija
      int x = 64 + (rr * cosf(a) + dx), y = 32 + (rr * sinf(a) + dy) * 0.55f;
      if (x >= 0 && x < 128 && y >= 0 && y < 64) oled.drawPixel(x, y);
    }
  oled.drawDisc(64, 32, 3 + g * 3);
  estrellasFondo(0);
}

void dibujarAgujero(int izq, int der, float g) {         // partículas que caen en espiral · izq = velocidad · der = tamaño
  static float p[44][2];                                 // radio, ángulo
  static bool listo = false;
  if (!listo) { for (auto &q : p) { q[0] = random(6, 70); q[1] = random(628) / 100.0f; } listo = true; }
  float vel = 0.15f + izq * 0.01f + g;
  float esc = 0.6f + der * 0.006f;
  for (auto &q : p) {
    q[1] += 2.2f / q[0];
    q[0] -= vel * (1 + 12 / q[0]);
    if (q[0] < 4) { q[0] = random(50, 75); q[1] = random(628) / 100.0f; }
    oled.drawPixel(64 + q[0] * esc * cosf(q[1]), 32 + q[0] * esc * 0.5f * sinf(q[1]));
  }
  oled.drawEllipse(64, 32, 16 * esc, 4 * esc);           // disco de acreción
  oled.setDrawColor(0); oled.drawDisc(64, 32, 5 * esc + 1); oled.setDrawColor(1);
  oled.drawCircle(64, 32, 5 * esc + 2);
}

void dibujarFugaces(int izq, int der, float g) {         // constelación que se va uniendo + estrellas fugaces
  static const uint8_t c[8][2] = {{14, 40}, {30, 28}, {46, 33}, {62, 20}, {80, 26}, {96, 14}, {104, 34}, {88, 46}};
  static float f[3][3];                                  // x, y, vida
  estrellasFondo(0);
  int n = (millis() / (900 - izq * 7)) % 10;             // cuántos tramos están dibujados
  for (int i = 0; i < 8; i++) oled.drawDisc(c[i][0], c[i][1], i < n + 1 ? 2 : 1);
  for (int i = 0; i < min(n, 7); i++) oled.drawLine(c[i][0], c[i][1], c[i + 1][0], c[i + 1][1]);
  for (auto &e : f) {
    if (e[2] <= 0) { if (random(100) < 2 + der / 10 + g * 20) { e[0] = random(20, 128); e[1] = random(0, 20); e[2] = 18; } continue; }
    e[0] -= 4; e[1] += 2; e[2]--;
    oled.drawLine(e[0], e[1], e[0] + 10, e[1] - 5);
    oled.drawDisc(e[0], e[1], 1);
  }
}

void dibujarTierra(int izq, int der, float g) {          // globo que gira con un satélite en órbita
  static float giro = 0, orb = 0;
  giro += 0.02f + izq * 0.0006f;
  orb += 0.03f + der * 0.0008f;
  estrellasFondo(0);
  int r = 15 + g * 3;
  int sx = 64 + 36 * cosf(orb), sy = 33 + 11 * sinf(orb) - 6 * cosf(orb);
  bool delante = sinf(orb) > 0;
  auto satelite = [&]() {
    oled.setDrawColor(0); oled.drawBox(sx - 2, sy - 2, 5, 5); oled.setDrawColor(1);
    oled.drawFrame(sx - 1, sy - 1, 3, 3);
    oled.drawHLine(sx - 7, sy, 5); oled.drawHLine(sx + 3, sy, 5);
    oled.drawFrame(sx - 8, sy - 2, 3, 5); oled.drawFrame(sx + 6, sy - 2, 3, 5);
  };
  if (!delante) satelite();
  oled.setDrawColor(0); oled.drawDisc(64, 33, r); oled.setDrawColor(1);
  oled.drawCircle(64, 33, r);
  for (int k = 0; k < 4; k++) {                          // meridianos que giran
    float a = giro + k * PI / 4;
    int rx = fabsf(r * cosf(a));
    if (rx > 1) oled.drawEllipse(64, 33, rx, r, cosf(a) > 0 ? U8G2_DRAW_UPPER_RIGHT | U8G2_DRAW_LOWER_RIGHT : U8G2_DRAW_UPPER_LEFT | U8G2_DRAW_LOWER_LEFT);
  }
  oled.drawHLine(64 - r, 33, 2 * r);
  oled.drawEllipse(64, 33, r, r / 3, U8G2_DRAW_LOWER_LEFT | U8G2_DRAW_LOWER_RIGHT);
  if (delante) satelite();
  oled.drawDisc(112, 10, 4); oled.setDrawColor(0); oled.drawDisc(114, 9, 3); oled.setDrawColor(1);   // luna creciente
}

// ---------- Juegos (rojo + amarillo abre el menú; rojo + amarillo de nuevo sale) ----------
enum { J_NADA = -1, J_MENU, J_PONG, J_SIMON, J_LUNA };
const char *NOMBRE_JUEGO[3] = {"PONG", "SIMON DICE", "ALUNIZAJE"};
int juego = J_NADA, menuSel = 0;

// Pong: el deslizante izquierdo mueve la paleta izquierda (variable der) y el derecho la derecha (variable izq)
const int PALETA = 14;
float bx, by, vx, vy;
int puntos[2];
bool pongFin = false;
void pongSaque() { bx = 64; by = 32; vx = random(2) ? 1.7f : -1.7f; vy = random(-12, 13) / 10.0f; }
void pongIniciar() { puntos[0] = puntos[1] = 0; pongFin = false; pongSaque(); }
void dibujarPong(int izq, int der) {
  int yi = (100 - der) * (64 - PALETA) / 100, yd = (100 - izq) * (64 - PALETA) / 100;
  if (!pongFin) {
    bx += vx; by += vy;
    if (by < 1 || by > 62) { vy = -vy; by = constrain(by, 1.0f, 62.0f); }
    if (vx < 0 && bx <= 5 && bx >= 1 && by >= yi - 2 && by <= yi + PALETA + 2) { vx = fabsf(vx) * 1.07f; vy += (by - (yi + PALETA / 2)) * 0.12f; }
    if (vx > 0 && bx >= 122 && bx <= 126 && by >= yd - 2 && by <= yd + PALETA + 2) { vx = -fabsf(vx) * 1.07f; vy += (by - (yd + PALETA / 2)) * 0.12f; }
    vx = constrain(vx, -4.5f, 4.5f); vy = constrain(vy, -3.0f, 3.0f);
    if (bx < -2) { puntos[1]++; destello(0, 0x00FF60); pongSaque(); }    // anota el de la derecha: se iluminan sus luces
    if (bx > 129) { puntos[0]++; destello(1, 0x00FF60); pongSaque(); }
    if (puntos[0] == 5 || puntos[1] == 5) pongFin = true;
  }
  for (int y = 0; y < 64; y += 6) oled.drawVLine(64, y, 3);
  oled.drawBox(1, yi, 3, PALETA); oled.drawBox(124, yd, 3, PALETA);
  oled.drawBox(bx - 1, by - 1, 3, 3);
  oled.setFont(u8g2_font_6x12_tf);
  char t[8]; snprintf(t, sizeof t, "%d  %d", puntos[0], puntos[1]);
  oled.drawStr(64 - 3 * strlen(t), 10, t);
  if (pongFin) {
    oled.setDrawColor(0); oled.drawBox(14, 22, 100, 24); oled.setDrawColor(1); oled.drawFrame(14, 22, 100, 24);
    oled.drawStr(20, 33, puntos[0] == 5 ? "GANA IZQUIERDA" : "GANA DERECHA");
    oled.drawStr(26, 43, "boton = otra");
  }
}

// Simón dice: la caja muestra colores en las luces y se repiten con los botones
const uint32_t COLOR_SIMON[4] = {0xFF0000, 0x0040FF, 0xFFFFFF, 0xFFB000};
uint8_t secuencia[40];
int nivel = 1, idxSimon = 0, faseSimon = 0, luzSimon = -1;       // fase 0 muestra, 1 espera, 2 perdió
unsigned long tSimon = 0, tLuzBoton = 0;
void simonIniciar() { for (auto &x : secuencia) x = random(4); nivel = 1; faseSimon = 0; tSimon = millis() + 600; }
void simonBoton(int i) {
  if (faseSimon == 2) { if (millis() - tSimon > 800) simonIniciar(); return; }
  if (faseSimon != 1) return;
  luzSimon = i; tLuzBoton = millis();
  if (i != secuencia[idxSimon]) {
    faseSimon = 2; tSimon = millis();
    if (nuevoRecord("simon", recSimon, nivel - 1)) aviso("NUEVO RECORD!");
    return;
  }
  if (++idxSimon == nivel) { nivel = min(nivel + 1, 40); faseSimon = 0; tSimon = millis() + 700; }
}
void dibujarSimon() {
  oled.setFont(u8g2_font_6x12_tf);
  oled.drawStr(0, 10, "SIMON DICE");
  char t[20]; snprintf(t, sizeof t, "NIVEL %d", nivel);
  oled.drawStr(128 - 6 * strlen(t), 10, t);
  if (faseSimon == 0) {
    long dt = (long)(millis() - tSimon);
    int k = dt < 0 ? -1 : dt / 600;
    luzSimon = (dt >= 0 && k < nivel && dt % 600 < 420) ? secuencia[k] : -1;
    if (dt >= 0 && k >= nivel) { faseSimon = 1; idxSimon = 0; luzSimon = -1; }
    oled.setFont(u8g2_font_logisoso16_tr);
    oled.drawStr(4, 44, luzSimon >= 0 ? NOMBRE_BOTON[luzSimon] : "MIRA...");
  } else if (faseSimon == 1) {
    if (millis() - tLuzBoton > 250) luzSimon = -1;
    oled.setFont(u8g2_font_logisoso16_tr);
    oled.drawStr(4, 44, "TU TURNO");
    for (int i = 0; i < nivel && i < 21; i++) (i < idxSimon ? oled.drawDisc(4 + i * 6, 58, 2) : oled.drawCircle(4 + i * 6, 58, 2));
  } else {
    luzSimon = (millis() / 200) % 2 ? 0 : -1;
    oled.setFont(u8g2_font_logisoso16_tr);
    oled.drawStr(4, 40, "PERDISTE");
    oled.setFont(u8g2_font_6x12_tf);
    snprintf(t, sizeof t, "nivel %d  rec %d", nivel - 1, recSimon);
    oled.drawStr(4, 58, t);
  }
}

// Alunizaje: el deslizante derecho es el motor (variable izq) y el izquierdo inclina la nave (variable der)
float lx, ly, lvx, lvy, combustible;
int estadoLuna = 0, plataforma;                          // 0 volando, 1 alunizó, 2 chocó
uint8_t suelo[9];
void lunaIniciar() {
  lx = random(20, 108); ly = 4; lvx = random(-5, 6) / 10.0f; lvy = 0; combustible = 100; estadoLuna = 0;
  for (auto &h : suelo) h = random(48, 61);
  plataforma = random(1, 7); suelo[plataforma + 1] = suelo[plataforma];
}
int alturaSuelo(float x) { int k = constrain((int)(x / 16), 0, 7); float u = (x - k * 16) / 16; return suelo[k] + (suelo[k + 1] - suelo[k]) * u; }
void dibujarLuna(int izq, int der) {
  float motor = combustible > 0 ? izq / 100.0f : 0;
  if (estadoLuna == 0) {
    lvy += 0.03f - motor * 0.075f;
    lvx += ((der - 50) / 60.0f - lvx) * 0.04f;
    combustible = max(0.0f, combustible - motor * 0.45f);
    lx = constrain(lx + lvx, 4.0f, 124.0f); ly += lvy;
    if (ly + 4 >= alturaSuelo(lx)) {
      bool enPlataforma = lx >= plataforma * 16 + 3 && lx <= (plataforma + 1) * 16 - 3;
      estadoLuna = enPlataforma && lvy < 0.8f && fabsf(lvx) < 0.6f ? 1 : 2;
      rachaLuna = estadoLuna == 1 ? rachaLuna + 1 : 0;
      if (nuevoRecord("luna", recLuna, rachaLuna)) aviso("NUEVO RECORD!");
      destello(0, estadoLuna == 1 ? 0x00FF60 : 0xFF0000); destello(1, estadoLuna == 1 ? 0x00FF60 : 0xFF0000);
      ly = alturaSuelo(lx) - 4;
    }
  }
  for (int k = 0; k < 8; k++) oled.drawLine(k * 16, suelo[k], k * 16 + 16, suelo[k + 1]);
  oled.drawBox(plataforma * 16 + 2, suelo[plataforma] - 1, 12, 2);
  int x = lx, y = ly;
  oled.drawTriangle(x - 3, y + 1, x + 3, y + 1, x, y - 5);
  oled.drawLine(x - 3, y + 1, x - 5, y + 4); oled.drawLine(x + 3, y + 1, x + 5, y + 4);
  if (motor > 0.05f && estadoLuna == 0) oled.drawTriangle(x - 2, y + 2, x + 2, y + 2, x, y + 3 + motor * 6 + random(3));
  oled.setFont(u8g2_font_5x7_tf);
  oled.drawFrame(0, 0, 42, 6); oled.drawBox(1, 1, combustible * 0.4f, 4);
  char t[16]; snprintf(t, sizeof t, "V %.1f", lvy);
  oled.drawStr(90, 6, t);
  snprintf(t, sizeof t, "x%d rec %d", rachaLuna, recLuna);
  oled.drawStr(46, 6, t);
  if (estadoLuna) {
    oled.setFont(u8g2_font_6x12_tf);
    oled.setDrawColor(0); oled.drawBox(18, 16, 92, 24); oled.setDrawColor(1); oled.drawFrame(18, 16, 92, 24);
    oled.drawStr(24, 27, estadoLuna == 1 ? "ALUNIZASTE!" : "TE ESTRELLASTE");
    oled.drawStr(30, 37, "boton = otra");
  }
}

void dibujarMenuJuegos() {
  oled.setFont(u8g2_font_6x12_tf);
  oled.drawStr(0, 10, "JUEGOS");
  for (int i = 0; i < 3; i++) {
    if (i == menuSel) { oled.drawBox(0, 15 + i * 13, 128, 12); oled.setDrawColor(0); }
    oled.drawStr(6, 25 + i * 13, NOMBRE_JUEGO[i]);
    oled.setDrawColor(1);
  }
  oled.setFont(u8g2_font_5x7_tf);
  char t[12];
  int rec[3] = {-1, recSimon, recLuna};
  for (int i = 1; i < 3; i++) {
    snprintf(t, sizeof t, "rec %d", rec[i]);
    if (i == menuSel) oled.setDrawColor(0);
    oled.drawStr(92, 23 + i * 13, t);
    oled.setDrawColor(1);
  }
  oled.drawStr(0, 63, "blanco elige  amarillo juega");
}
void juegoBoton(int i) {                                  // botón suelto dentro de los juegos
  if (juego == J_MENU) {
    if (i == 2 || i == 1) menuSel = (menuSel + 1) % 3;
    if (i == 0) menuSel = (menuSel + 2) % 3;
    if (i == 3) {
      juego = J_PONG + menuSel;
      if (juego == J_PONG) pongIniciar(); else if (juego == J_SIMON) simonIniciar(); else lunaIniciar();
    }
  } else if (juego == J_PONG) { if (pongFin) pongIniciar(); }
  else if (juego == J_SIMON) simonBoton(i);
  else if (juego == J_LUNA) { if (estadoLuna) lunaIniciar(); }
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

void mandarEspejo() {                                    // la pantalla, tal cual, en base64 (1024 bytes → 1368 caracteres)
  static unsigned long ultimo = 0;
  if (!espejo || millis() - tEspejo > 3000 || millis() - ultimo < 80) return;
  ultimo = millis();
  static const char B64[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  static char out[1 + 1368 + 2];
  const uint8_t *b = oled.getBufferPtr();
  int n = 0;
  out[n++] = 'o';
  for (int i = 0; i < 1024; i += 3) {                     // 342 grupos: el último solo trae el byte 1023
    uint32_t v = (b[i] << 16) | (i + 1 < 1024 ? b[i + 1] << 8 : 0) | (i + 2 < 1024 ? b[i + 2] : 0);
    out[n++] = B64[v >> 18 & 63]; out[n++] = B64[v >> 12 & 63]; out[n++] = B64[v >> 6 & 63]; out[n++] = B64[v & 63];
  }
  out[n++] = '\n';
  Serial.write((const uint8_t *)out, n);
}

void dibujarPantalla(int izq, int der, int apretado) {
  oled.clearBuffer();
  if (juego == J_MENU) dibujarMenuJuegos();
  else if (juego == J_PONG) dibujarPong(izq, der);
  else if (juego == J_SIMON) dibujarSimon();
  else if (juego == J_LUNA) dibujarLuna(izq, der);
  else if (pantallaPrueba) dibujarPrueba(izq, der, apretado);
  else {
    float g = graves();
    switch (anim) {
      case A_CUBO:      dibujarCubo(izq, der, g); break;
      case A_ESTRELLAS: dibujarEstrellas(izq, der, g); break;
      case A_ESPECTRO:  dibujarEspectro(izq, der); break;
      case A_TUNEL:     dibujarTunel(izq, der, g); break;
      case A_ONDA:      dibujarOnda(izq, der, g); break;
      case A_OCTAEDRO:  dibujarOctaedro(izq, der, g); break;
      case A_COHETE:    dibujarCohete(izq, der, g); break;
      case A_PLANETA:   dibujarPlaneta(izq, der, g); break;
      case A_INFINITO:  dibujarInfinito(izq, der, g); break;
      case A_RADAR:     dibujarRadar(izq, der, g); break;
      case A_ASTEROIDES:dibujarAsteroides(izq, der, g); break;
      case A_GALAXIA:   dibujarGalaxia(izq, der, g); break;
      case A_AGUJERO:   dibujarAgujero(izq, der, g); break;
      case A_FUGACES:   dibujarFugaces(izq, der, g); break;
      case A_TIERRA:    dibujarTierra(izq, der, g); break;
    }
  }
  if (millis() - tAviso < 1500) {                        // aviso arriba a la izquierda (animación, brillo, etc.)
    oled.setFont(u8g2_font_6x12_tf);
    int w = 6 * strlen(avisoTxt) + 6;
    oled.setDrawColor(0); oled.drawBox(0, 0, w, 13); oled.setDrawColor(1);
    oled.drawFrame(0, 0, w, 13);
    oled.drawStr(3, 10, avisoTxt);
  }
  oled.sendBuffer();
  mandarEspejo();
}

void galon(int cx, int cy, int a) {                       // galón de Star Command (chevron)
  oled.drawTriangle(cx - a, cy - a / 2, cx, cy + a / 2, cx, cy + a / 2 - 5);
  oled.drawTriangle(cx - a, cy - a / 2, cx - a, cy - a / 2 + 6, cx, cy + a / 2);
  oled.drawTriangle(cx + a, cy - a / 2, cx, cy + a / 2, cx, cy + a / 2 - 5);
  oled.drawTriangle(cx + a, cy - a / 2, cx + a, cy - a / 2 + 6, cx, cy + a / 2);
}
void arranque() {
  randomSeed(esp_random());                             // NO usar analogRead(A0): es el pin del botón blanco y le quita el pull-up
  for (int f = 0; f < 22; f++) {                         // el galón aparece creciendo
    oled.clearBuffer(); galon(64, 24, min(f * 2, 26));
    oled.setFont(u8g2_font_6x12_tf);
    if (f > 12) oled.drawStr(28, 60, "STAR COMMAND");
    oled.sendBuffer(); delay(35);
  }
  delay(500);
  for (int n = 3; n >= 1; n--) {                         // 3, 2, 1 con las luces subiendo
    for (int k = 0; k < 2 * LEDS_POR_TIRA; k++) tiras.setPixelColor(k, (k % LEDS_POR_TIRA) < 4 - n ? 0x00FF60 : 0);
    tiras.show();
    oled.clearBuffer(); oled.setFont(u8g2_font_logisoso32_tn);
    char t[2] = {(char)('0' + n), 0}; oled.drawStr(56, 48, t);
    oled.sendBuffer(); delay(450);
  }
  for (int y = 70; y > -30; y -= 3) {                    // despegue
    for (int k = 0; k < 2 * LEDS_POR_TIRA; k++) tiras.setPixelColor(k, random(2) ? 0xFF6000 : 0xFFD000);
    tiras.show();
    oled.clearBuffer(); estrellasFondo(3);
    oled.drawBox(61, y - 6, 7, 15); oled.drawTriangle(61, y - 6, 67, y - 6, 64, y - 14);
    oled.drawTriangle(61, y + 2, 61, y + 9, 56, y + 10); oled.drawTriangle(67, y + 2, 67, y + 9, 72, y + 10);
    oled.drawTriangle(61, y + 9, 67, y + 9, 64, y + 18 + random(5));
    oled.setFont(u8g2_font_6x12_tf); oled.drawStr(36, 63, "DESPEGUE!");
    oled.sendBuffer(); delay(20);
  }
  tiras.clear(); tiras.show();
  aviso(NOMBRE_ANIM[anim]);
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 4; i++) pinMode(PIN_BOTON[i], INPUT_PULLUP);
  analogReadResolution(12);
  oled.setBusClock(400000);                         // I2C rápido: animaciones fluidas
  oled.begin();
  tiras.begin();
  tiras.setBrightness(BRILLOS[0]);
  tiras.show();
  memoria.begin("ctrl04l", false);
  recSimon = memoria.getInt("simon", 0); recAsteroides = memoria.getInt("ast", 0); recLuna = memoria.getInt("luna", 0);
  arranque();
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
  static int modoPrevio = 0;
  static unsigned long tBlanco = 0, tRB = 0, golpes[4] = {0, 0, 0, 0};
  int combo = 0;                                                      // máscara de los dos botones de la combinación
  if (ahora[0] && ahora[1] && ahora[2] && ahora[3]) {
    if (flanco[0] || flanco[1] || flanco[2] || flanco[3]) {           // los 4 juntos = reinicio
      if (millis() - tBlanco < 600) modo = modoPrevio;
      modo = 0; anim = 0; brilloSel = 0; tiras.setBrightness(BRILLOS[0]); pulso = false; exhibicion = false;
      juego = J_NADA; pantallaPrueba = false; aviso("REINICIO");
    }
  } else
    for (int i = 0; i < 4 && !combo; i++)
      if (flanco[i]) for (int j = 0; j < 4; j++) if (j != i && ahora[j]) { combo = (1 << i) | (1 << j); break; }

  if (combo) {
    if ((combo & 4) && millis() - tBlanco < 600 && juego == J_NADA) modo = modoPrevio;   // deshace el blanco suelto
    if (combo == 0b1001) {                                            // rojo + amarillo = juegos
      juego = juego == J_NADA ? J_MENU : J_NADA;
      aviso(juego == J_NADA ? "FIN DEL JUEGO" : "JUEGOS");
    } else if (juego == J_NADA) {
      if (combo == 0b0011) { anim = (anim + 1) % N_ANIM; pantallaPrueba = false; aviso(NOMBRE_ANIM[anim]); }   // rojo + azul
      if (combo == 0b1100) pantallaPrueba = !pantallaPrueba;                                                  // amarillo + blanco
      if (combo == 0b1010) { exhibicion = !exhibicion; tExhibicion = millis(); aviso(exhibicion ? "EXHIBICION ON" : "EXHIBICION OFF"); }
      if (combo == 0b0110) { brilloSel = (brilloSel + 1) % 3; tiras.setBrightness(BRILLOS[brilloSel]); aviso(NOMBRE_BRILLO[brilloSel]); }
      if (combo == 0b0101) {                                          // rojo + blanco = un golpe del pulso
        tRB = millis();
        for (int k = 3; k > 0; k--) golpes[k] = golpes[k - 1];
        golpes[0] = millis();
        if (golpes[1] && golpes[0] - golpes[1] < 1500) {
          unsigned long suma = 0; int n = 0;
          for (int k = 0; k < 3 && golpes[k + 1] && golpes[k] - golpes[k + 1] < 1500; k++) { suma += golpes[k] - golpes[k + 1]; n++; }
          periodoPulso = suma / n; tPulso = millis(); pulso = true;
          char t[22]; snprintf(t, sizeof t, "PULSO %d BPM", (int)(60000 / periodoPulso)); aviso(t);
        }
      }
    }
  } else
    for (int i = 0; i < 4; i++) {
      if (!flanco[i]) continue;
      if (juego != J_NADA) juegoBoton(i);
      else if (i == 2) { modoPrevio = modo; modo = (modo + 1) % N_MODOS; tBlanco = millis(); }   // blanco solo = luces
    }
  static unsigned long tCuatro = 0;                                   // mantener los 4 juntos 3 s = borrar récords
  if (ahora[0] && ahora[1] && ahora[2] && ahora[3]) {
    if (!tCuatro) tCuatro = millis();
    else if (millis() - tCuatro > 3000) {
      memoria.clear(); recSimon = recAsteroides = recLuna = 0; aviso("RECORDS BORRADOS"); tCuatro = ~0UL;
    }
  } else tCuatro = 0;
  if (pulso && ahora[0] && ahora[2] && tRB && millis() - tRB > 1500) { pulso = false; tRB = 0; aviso("PULSO OFF"); }   // mantener rojo + blanco
  if (!(ahora[0] && ahora[2])) tRB = 0;
  if (exhibicion && juego == J_NADA && !pantallaPrueba && millis() - tExhibicion > 10000) {   // exhibición: cambia sola
    anim = (anim + 1) % N_ANIM; tExhibicion = millis(); aviso(NOMBRE_ANIM[anim]);
  }

  unsigned long t = millis();
  pintarTira(0, izq, IZQ_INVERTIDA, t);
  pintarTira(1, der, DER_INVERTIDA, t);
  if (juego == J_SIMON)                                    // en Simón las luces muestran el color que toca
    for (int k = 0; k < 2 * LEDS_POR_TIRA; k++) tiras.setPixelColor(k, luzSimon >= 0 ? COLOR_SIMON[luzSimon] : 0);
  tiras.show();

  leerSerial();
  dibujarPantalla(izq, der, apretado);

  static unsigned long ultimo = 0;
  if (millis() - ultimo > 50) {
    ultimo = millis();
    int b[4];
    for (int i = 0; i < 4; i++) b[i] = digitalRead(PIN_BOTON[i]) == LOW;
    Serial.printf("{\"izq\":%d,\"der\":%d,\"mv\":[%d,%d],\"bot\":[%d,%d,%d,%d],\"modo\":\"%s\",\"anim\":\"%s\",\"jg\":\"%s\",\"rec\":[%d,%d,%d]}\n",
                  izq, der, mvCrudo[0], mvCrudo[1], b[0], b[1], b[2], b[3], NOMBRE_MODO[modo],
                  pantallaPrueba ? "PRUEBA" : NOMBRE_ANIM[anim],
                  juego == J_NADA ? "" : juego == J_MENU ? "MENU" : NOMBRE_JUEGO[juego - J_PONG],
                  recSimon, recAsteroides, recLuna);
  }
  delay(15);
}
