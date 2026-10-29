"""
CTRL-04L · edición avanzada en 3 capas · Taller de Interfaces UAI · Luis-Felipe Benitez
  1. CAJA impresa: piso + paredes + 4 columnas en las esquinas; la placa 7x9 se atornilla aparte sobre 4 separadores (M3 x 8).
  2. ACRÍLICO cortado a láser: apoya sobre el lomo de los deslizantes; ranuras, agujeros de botones y paso de cables de la OLED.
  3. MARCO impreso arriba: borde perimetral + visera con la OLED 0,96" inclinada 15° hacia el usuario
     (la OLED queda atrapada entre la visera y una CUÑA impresa que apoya en el acrílico).
  4. TIRAS NEOPIXEL en las CARAS LATERALES (una por deslizante): la tira va parada, pegada a una costilla de la caja,
     mirando a una ventana de la pared lateral tapada por una LÁMINA difusora impresa que baja por una ranura.
Marco y acrílico se atornillan a las 4 columnas de la caja, FUERA de la placa: 4 tornillos M3 x 12 cabeza redonda (botón)
    marco → acrílico → columna de la caja (rosca en el plástico).  El acrílico además apoya en las fundas de los deslizantes.
Salidas en salida_laser/: caja y marco (STL/STEP), cuña de la OLED, láminas difusoras y fundas (STL), acrílico (DXF/SVG con capas CORTE y GRABADO, y STEP).
Ejes: X ancho, Y fondo (frente=0), Z alto.  Coordenadas de la placa (bx, by): bx desde la izquierda, by desde el borde del USB.
"""
from pathlib import Path
from build123d import *
from build123d.exporters import ColorIndex
import math

OUT = Path(__file__).parent / "salida_laser"
OUT.mkdir(exist_ok=True)

# ---------- Placa y componentes (mismos datos que caja_avanzada.py) ----------
PL_W, PL_D, PL_T = 70.0, 90.0, 1.6
PASO = 2.54
GX0 = (PL_W - 25 * PASO) / 2
GY0 = (PL_D - 30 * PASO) / 2

def col(i):
    return GX0 + i * PASO

def fila(j):
    return GY0 + j * PASO

PL_AGUJEROS = [(2.45, 3.0), (67.55, 3.0), (2.45, 87.0), (67.55, 87.0)]   # M3; medido en foto: 65,1 de ancho (68 era borde a borde) y 84 de largo entre centros
SLIDERS = [6.9, PL_W - 6.9]                       # eje medido en foto cenital; simétrico *
SLIDER_BY, SLIDER_RECORRIDO = PL_D / 2, 60.0      # plano: recorrido 60 ± 0,5; * centro
SLIDER_CUERPO = (9.0, 75.0, 7.0)                  # plano: 9 x 75, alto 7 ± 0,5 → el acrílico apoya aquí
BOTONES = [(col(9), fila(19.5)), (col(16), fila(19.5)), (col(9), fila(27.5)), (col(16), fila(27.5))]  # contados
TAPA_BOTON_D, TAPA_BOTON_ALTO = 11.5, 12.3        # plano: tapa Ø11,5 (pestaña Ø12,8), tope a 12,3 de la placa
XIAO_X, USB_ALTO = col(13), 5.1                  # medido en foto: pines en columnas J y P (desde A), USB a 36,3 de la izquierda

# OLED 0,96" I2C 4 pines, apoyada sobre el acrílico dentro de la isla del marco (pines hacia los botones)
OLED_X, OLED_BORDE_PINES = 34.5, 42.5             # 5 mm más atrás que antes: espacio para los cables delante de los pines
OLED_FRENTE = 4.0                                  # aire delante del borde de los pines (soldaduras y curva de los cables)
OLED_PASO_CABLES = (16.0, OLED_FRENTE + 5.0)       # paso por la cuña y el acrílico: desde el aire delantero hasta 5 mm detrás del borde
OLED_PCB = (27.3, 27.8, 1.6)                      # ancho, largo, espesor
OLED_VIDRIO_ALTO, OLED_REVERSO = 1.5, 1.0         # vidrio sobre el PCB; componentes del reverso
OLED_VENTANA = (24.0, 12.4, 11.5)                 # foto IMG_1971: con 9,4 se veían los pines y faltaban ~14 filas abajo; centro real ≈ 11,5
OLED_VENTANA_ANT = (24.0, 12.6, 10.7)                 # zona visible 22 x 11 (ficha); centro a 10,7 del borde de los pines (vidrio desde ~4,2)
OLED_INCL, CUNA_MIN = 15.0, 1.0                   # inclinación hacia el usuario; espesor mínimo de la cuña (adelante)

# Tiras NeoPixel en las caras laterales (paradas, mirando hacia afuera)
LED_ANCHO, LED_ALTO = 12.0, 3.0                   # tira 144 LED/m (12 mm) o 60 LED/m (10 mm); espesor con LED
LED_LARGO = SLIDER_RECORRIDO + 10.0               # canal de 70 mm a lo largo del recorrido
LED_AIRE = 3.0                                    # aire entre los LED y la lámina (difumina los puntos)
COSTILLA = 1.6                                    # costilla donde se pega la tira
VENT_ALTO = 10.0                                  # alto de la ventana en la pared lateral
LAMINA_T = 1.0                                    # lámina difusora impresa (PLA/PETG blanco o natural)

# ---------- Capas ----------
ACRILICO = 3.0
T, HOLG, ATRAS, FRENTE = 2.5, 8.5, 0.3, 1.5   # costados 8,5 mm: aire + tira + costilla (ahí caen las columnas); atrás 0,3: el USB-C entra en la pared
COL_R = 3.5                    # columnas de las esquinas (marco + acrílico)
BAJO, TB = 6.0, 2.5            # espacio bajo la placa y espesor del piso
ALZA = 1.0                     # funda sobre cada deslizante (la que funcionó en la prueba): 1 mm entre lomo y acrílico
ALZAS_PRUEBA = (1.0,)          # se exporta la funda elegida
GAP = SLIDER_CUERPO[2] + ALZA  # placa → acrílico: el acrílico apoya sobre los alzadores
PIEL = 1.0                     # plástico sobre el vidrio de la OLED
R_V, R_T = 6.0, 1.5

W = PL_W + 2 * HOLG + 2 * T
D = PL_D + ATRAS + FRENTE + 2 * T
z_pl = TB + BAJO
z_top_pl = z_pl + PL_T
z_acr = z_top_pl + GAP                    # cara inferior del acrílico = borde de la caja
z_marco = z_acr + ACRILICO                # cara inferior del marco
OLED_HUECO = OLED_REVERSO + OLED_PCB[2] + OLED_VIDRIO_ALTO + 0.2
H_MARCO = 2.4                  # marco delgado: solo una pestaña sobre las paredes (la visera de la OLED sube aparte)
PESTANA = 1.0                  # cuánto entra el marco por dentro de las paredes
H = z_marco + H_MARCO
BX0, BY_USB = T + HOLG, D - T - ATRAS

COLUMNAS = [(T + COL_R, T + COL_R), (W - T - COL_R, T + COL_R), (T + COL_R, D - T - COL_R), (W - T - COL_R, D - T - COL_R)]

def G(bx, by):
    return BX0 + bx, BY_USB - by

def C(r, h, x, y, z):
    return Pos(x, y, z) * Cylinder(r, h, align=(Align.CENTER, Align.CENTER, Align.MIN))

def P(cx, cy, z0, w, d, h, r=0.0):
    b = Box(w, d, h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    if r > 0:
        b = fillet(b.edges().filter_by(Axis.Z), r)
    return Pos(cx, cy, z0) * b

def caja(w, d, h, r, x=0, y=0, z=0):
    b = Box(w, d, h, align=(Align.MIN, Align.MIN, Align.MIN))
    return Pos(x, y, z) * fillet(b.edges().filter_by(Axis.Z), r)

def rrect(cx, cy, w, h, r):
    return Pos(cx, cy) * RectangleRounded(w, h, r)

# ---------- 1. Caja ----------
cuerpo = caja(W, D, z_acr, R_V)
cuerpo = fillet(cuerpo.edges().group_by(Axis.Z)[0], R_T)
cuerpo -= caja(W - 2 * T, D - 2 * T, z_acr, R_V - T, T, T, TB)
for bx, by in PL_AGUJEROS:                      # separadores bajo la placa, agujero ciego para M3 autorroscante
    x, y = G(bx, by)
    cuerpo += C(2.6, BAJO, x, y, TB)
    cuerpo -= C(1.25, BAJO + TB - 0.8, x, y, 0.8)
for bx in (-0.3 - 1.0, PL_W + 0.3 + 1.0):        # guías laterales: la placa calza entre ellas (0,3 por lado), no baila
    for by in (20.0, PL_D - 20.0):
        x, y = G(bx, by)
        cuerpo += P(x, y, TB - 0.01, 2.0, 6.0, z_top_pl - TB + 0.01)   # 2 mm: no tocan la tira LED
x, _ = G(XIAO_X, 0)                             # USB-C: escotadura abierta arriba (la placa entra desde arriba)
z_usb = z_top_pl + USB_ALTO
# Funda del alargador USB-C macho-hembra (sobresale 26 mm de la cara de la XIAO): pieza aparte tipo calcetín.
# Se pasa por el alargador desde el lado macho; la boca hembra queda empotrada en un túnel justo. La funda baja
# desde arriba por la ranura de la pared (abierta arriba) con dos lengüetas en ranuras verticales: no sale ni entra.
ALARGADOR = 26.0                                  # medido: boca hembra a 26 mm de la cara del USB de la XIAO
FU_ZOCALO = 3.0                                   # refuerzo exterior de la pared donde calza la funda
FU_PASO = (9.8, 4.4)                              # interior por donde pasa el alargador
FU_TUNEL, FU_TUNEL_L = (9.5, 3.8), 5.0            # túnel de la boca: USB-C 8,94 x 3,26 + ~0,28 por lado (9,15 x 3,45 quedó extremo justo)
FU_ENCHUFE = (11.6, FU_PASO[1] + 1.2)             # parte que entra en la pared
FU_RANURA = 12.0
LENG = (1.0, 1.5)                                 # lengüeta: sobresale x espesor
FU_ACORTE = 10.0                                  # manga 1 cm más corta (pedido tras la prueba)
y_boca = BY_USB + ALARGADOR - 0.5 - FU_ACORTE     # cara de la boca de la manga
y_zoc = D + FU_ZOCALO
y_leng = D + (FU_ZOCALO - T) / 2                  # centro del espesor pared + zócalo
zocalo = Pos(x, D - 0.5 + (FU_ZOCALO + 0.5) / 2, 0) * Box(22.0, FU_ZOCALO + 0.5, z_acr, align=(Align.CENTER, Align.CENTER, Align.MIN))
cuerpo += fillet(zocalo.edges().filter_by(Axis.Z).group_by(Axis.Y)[-1], 1.5)
cuerpo -= Pos(x, D, z_top_pl + 0.3) * Box(FU_RANURA, 2 * (FU_ZOCALO + T) + 2, z_acr, align=(Align.CENTER, Align.CENTER, Align.MIN))
for sx in (-1, 1):                                # ranuras verticales para las lengüetas
    cuerpo -= Pos(x + sx * (FU_RANURA / 2 + (LENG[0] + 0.2) / 2 - 0.01), y_leng, z_top_pl + 0.3) * Box(
        LENG[0] + 0.2, LENG[1] + 0.3, z_acr, align=(Align.CENTER, Align.CENTER, Align.MIN))

def seccion(y, w, h, r):
    return Plane(origin=(x, y, z_usb), x_dir=(1, 0, 0), z_dir=(0, 1, 0)) * RectangleRounded(w, h, r)

funda = loft([seccion(y_zoc, 18.0, 11.0, 3.0), seccion(y_zoc + 0.45 * (y_boca - y_zoc), 14.2, 8.4, 2.6), seccion(y_boca, 12.6, 6.6, 2.2)])
funda += Pos(x, D - T + 0.1 + (y_zoc - D + T - 0.1) / 2, z_usb) * Box(FU_ENCHUFE[0], y_zoc - D + T - 0.1 + 0.01, FU_ENCHUFE[1])
for sx in (-1, 1):
    funda += Pos(x + sx * (FU_ENCHUFE[0] / 2 + LENG[0] / 2 - 0.01), y_leng, z_usb) * Box(LENG[0] + 0.02, LENG[1], FU_ENCHUFE[1])
funda -= Pos(x, (D - T - 1 + y_boca - FU_TUNEL_L) / 2, z_usb) * Box(FU_PASO[0], y_boca - FU_TUNEL_L - D + T + 1.01, FU_PASO[1])
funda -= extrude(seccion(y_boca - FU_TUNEL_L - 0.01, FU_TUNEL[0], FU_TUNEL[1], FU_TUNEL[1] / 2 - 0.01), FU_TUNEL_L + 1)
for x, y in [(20, 28), (W - 20, 28), (20, D - 28), (W - 20, D - 28)]:   # rebajes para patas de goma
    cuerpo -= C(5.0, 1.0, x, y, -0.01)
for x, y in COLUMNAS:                           # columnas de las esquinas, unidas a las dos paredes, hasta el acrílico
    sx, sy = (1 if x < W / 2 else -1), (1 if y < D / 2 else -1)
    cuerpo += C(COL_R, z_acr - TB, x, y, TB)
    cuerpo += P(x - sx * COL_R / 2, y, TB, COL_R, 2 * COL_R, z_acr - TB)
    cuerpo += P(x, y - sy * COL_R / 2, TB, 2 * COL_R, COL_R, z_acr - TB)
    cuerpo -= C(1.25, 12.0, x, y, z_acr - 12.0)                 # M3 autorroscante desde arriba

# Tiras NeoPixel laterales: ventana en la pared + ranura vertical (abierta arriba) para la lámina + costilla para la tira
RANURA = LAMINA_T + 0.3                            # la ranura se come parte de la pared por dentro
TOPE = 1.0                                         # espesor de los topes que cierran la ranura por dentro
z_led = (TB + z_acr) / 2                          # centro en alto de la tira y la ventana
_, y_led = G(0, SLIDER_BY)
LADOS = [(-1, T), (1, W - T)]                      # (hacia afuera, x de la cara interior de la pared)
for sx, xw in LADOS:
    cuerpo -= P(xw + sx * T / 2, y_led, z_led - VENT_ALTO / 2, T + 0.2, LED_LARGO - 2, VENT_ALTO, r=0)         # ventana
    cuerpo -= P(xw + sx * RANURA / 2 - sx * 0.01, y_led, z_led - VENT_ALTO / 2 - 1.5, RANURA, LED_LARGO + 2.0,
                z_acr - (z_led - VENT_ALTO / 2 - 1.5) + 0.1)                                                     # ranura
    # topes por dentro (fuera de la ventana): encierran la lámina para que no se doble hacia la tira
    z_fondo = z_led - VENT_ALTO / 2 - 1.5
    x_tope = xw - sx * TOPE / 2
    y_vent, y_ran = (LED_LARGO - 2) / 2, (LED_LARGO + 2) / 2          # medio largo de la ventana y de la ranura
    for sy in (-1, 1):                                                                                           # extremos
        cuerpo += P(x_tope, y_led + sy * (y_vent + 0.3 + y_ran + 2.0) / 2, TB - 0.5,
                    TOPE, y_ran + 2.0 - y_vent - 0.3, z_acr - TB + 0.5)                     # tope (llega al piso)
        cuerpo += P(xw - sx * (TOPE - 0.5) / 2, y_led + sy * (y_ran + 1.0), TB - 0.5,
                    TOPE + 0.5, 2.0, z_acr - TB + 0.5)                                       # anclaje dentro de la pared
    cuerpo += P(xw - sx * (TOPE - 0.5) / 2, y_led, TB - 0.5, TOPE + 0.5, 2 * y_ran, z_fondo - TB + 0.49)        # base bajo la ranura
    cuerpo += P(x_tope, y_led, z_fondo - 0.02, TOPE, 2 * y_ran, 1.42)                                            # borde de abajo
    x_cost = xw - sx * (LED_AIRE + LED_ALTO + COSTILLA / 2)
    cuerpo += P(x_cost, y_led, TB, COSTILLA, LED_LARGO + 4, z_led + LED_ANCHO / 2 + 1.0 - TB)                     # costilla
    cuerpo += P(x_cost - sx * COSTILLA, y_led, TB, COSTILLA, LED_LARGO + 4, 3.0)                                 # pie de la costilla

FALDON, HOLG_FUNDA, PARED_FUNDA = 2.5, 0.15, 1.0     # funda: baja 2,5 mm por los costados del cuerpo

def alzador(h):
    """Funda ("calcetín") que calza sobre el cuerpo del deslizante: tapa de alto h + faldón alrededor.
    Origen en el lomo del deslizante (z=0); el faldón queda bajo z=0. Ranura para la palanca y agujeros M2 a 71 mm."""
    iw, il = SLIDER_CUERPO[0] + 2 * HOLG_FUNDA, SLIDER_CUERPO[1] + 2 * HOLG_FUNDA
    a = Pos(0, 0, -FALDON) * Box(iw + 2 * PARED_FUNDA, il + 2 * PARED_FUNDA, FALDON + h, align=(Align.CENTER, Align.CENTER, Align.MIN))
    a = fillet(a.edges().filter_by(Axis.Z), 1.0)
    a -= Pos(0, 0, -FALDON - 0.01) * Box(iw, il, FALDON + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    a -= Pos(0, 0, -FALDON) * extrude(SlotOverall(SLIDER_RECORRIDO + 6, 3.2, rotation=90), FALDON + h)
    for s in (-1, 1):
        a -= C(1.2, FALDON + h, 0, s * 35.5, -FALDON)
    return a

for h in ALZAS_PRUEBA:                          # dos por altura (uno por deslizante), separados para imprimir juntos
    par = Rot(180, 0, 0) * (Pos(-8, 0, 0) * alzador(h) + Pos(8, 0, 0) * alzador(h))   # tapa sobre la cama
    export_stl(par, str(OUT / f"CTRL-04L_alzador_deslizante_{h:g}mm_x2.stl"), tolerance=0.02, angular_tolerance=0.15)

# ---------- 2. Acrílico (2D) ----------
oled_c = G(OLED_X, OLED_BORDE_PINES - OLED_PCB[1] / 2)
contorno = Pos(W / 2, D / 2) * RectangleRounded(W, D, R_V)
cortes = [Pos(x, y) * Circle(1.7) for x, y in COLUMNAS]
for sx in SLIDERS:
    x, y = G(sx, SLIDER_BY)
    cortes.append(Pos(x, y) * SlotOverall(SLIDER_RECORRIDO + 6, 3.2, rotation=90))
for bx, by in BOTONES:
    cortes.append(Pos(*G(bx, by)) * Circle(TAPA_BOTON_D / 2 + 0.15))   # Ø11,8: con el corte del láser queda ~0,25 mm por lado
cortes.append(rrect(*G(OLED_X, OLED_BORDE_PINES - (5.0 - OLED_FRENTE) / 2), *OLED_PASO_CABLES, 2.0))   # paso de los cables de la OLED (bajo los pines)

grabado = []
for i, sx in enumerate(SLIDERS):
    x, y = G(sx, SLIDER_BY)
    lado = 1 if i == 0 else -1
    for k in range(11):
        largo = 4.0 if k % 5 == 0 else 2.5
        grabado.append(Pos(x + lado * (4.0 + largo / 2), y - 30 + k * 6) * Rectangle(largo, 0.6))

tapa_2d = contorno
for c in cortes:
    tapa_2d -= c
acrilico = Pos(0, 0, z_acr) * extrude(tapa_2d, ACRILICO)

def exportar_laser(e, ruta, capas):
    for nombre, estilo in capas:
        e.add_layer(nombre, **estilo)
    e.add_shape([contorno] + cortes, layer="CORTE")
    e.add_shape(grabado, layer="GRABADO")
    e.write(str(ruta))

nombre_acr = f"CTRL-04L_acrilico_{ACRILICO:g}mm"
exportar_laser(ExportDXF(unit=Unit.MM), OUT / f"{nombre_acr}.dxf",
               [("CORTE", {"color": ColorIndex.RED}), ("GRABADO", {"color": ColorIndex.BLUE})])
exportar_laser(ExportSVG(unit=Unit.MM, fill_color=None), OUT / f"{nombre_acr}.svg",
               [("CORTE", {"line_color": "red", "fill_color": None}),
                ("GRABADO", {"line_color": "blue", "fill_color": None})])

# ---------- 3. Marco superior con visera inclinada para la OLED (se imprime de pie; soporte solo dentro del hueco) ----------
ESQ_R = 4.6                                      # refuerzo alrededor de cada tornillo
abertura = rrect(W / 2, D / 2, W - 2 * (T + PESTANA), D - 2 * (T + PESTANA), R_V - T - PESTANA)   # deja ver todo el acrílico
for x, y in COLUMNAS:
    abertura -= Pos(x, y) * Circle(ESQ_R)
isla_w, isla_frente = OLED_PCB[0] + 0.6 + 2 * 1.6, OLED_BORDE_PINES + OLED_FRENTE + 1.6
isla = Pos(G(OLED_X, 0)[0], G(0, isla_frente)[1]) * Rectangle(isla_w, isla_frente + 2, align=(Align.CENTER, Align.MIN))
isla = fillet(isla.vertices().sort_by(Axis.Y)[:2], 3.0)
abertura -= isla
marco = extrude(contorno - abertura, H_MARCO)
try:                                                                  # borde superior del marco redondeado (transición)
    marco = fillet(marco.edges().group_by(Axis.Z)[-1], 1.0)
except Exception as e:
    print("aviso: no se pudo redondear el marco:", e)

# Sistema local de la OLED: origen en el borde de los pines, a CUNA_MIN sobre el acrílico; y' hacia atrás y arriba
si, co = math.sin(math.radians(OLED_INCL)), math.cos(math.radians(OLED_INCL))
y_pines = G(0, OLED_BORDE_PINES)[1]
PL_OLED = Plane(origin=(G(OLED_X, 0)[0], y_pines, CUNA_MIN), x_dir=(1, 0, 0), z_dir=(0, -si, co))
OL_W, OL_L = OLED_PCB[0], OLED_PCB[1]

def inclinada(x0, x1, y0, y1, z0, z1):
    return PL_OLED * Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(x1 - x0, y1 - y0, z1 - z0)

sobre_acrilico = Pos(W / 2, D / 2, 0) * Box(2 * W, 2 * D, 60, align=(Align.CENTER, Align.CENTER, Align.MIN))
# Visera con transición: nace ancha desde el marco y se angosta hacia arriba (costados y trasera en talud);
# el frente sigue la inclinación de la pantalla (no puede crecer hacia los botones)
VIS_TALUD = 4.0                                    # cuánto más ancha es la visera en la base que arriba (por lado)
vx0 = G(OLED_X, 0)[0]
y_atras = y_pines + (OL_L + 1.9) * co + 2.0
a_top = OL_W / 2 + 0.3 + 1.4
z_top = CUNA_MIN + (OL_L + 1.9) * si + (OLED_HUECO + PIEL) * co + 1.0
y_fr = y_pines - OLED_FRENTE - 8
base = Plane.XY * Pos(vx0, (y_fr + y_atras + VIS_TALUD) / 2) * RectangleRounded(2 * (a_top + VIS_TALUD), y_atras + VIS_TALUD - y_fr, 4.0)
tope = Plane.XY.offset(z_top) * Pos(vx0, (y_fr + y_atras) / 2) * RectangleRounded(2 * a_top, y_atras - y_fr, 2.5)
visera = loft([base, tope])
visera &= inclinada(-60, 60, -(OLED_FRENTE + 1.6), OL_L + 30, -60, OLED_HUECO + PIEL) & sobre_acrilico
try:                                                                  # visera con aristas superiores redondeadas
    visera = fillet(visera.faces().sort_by(Axis.Z)[-1].edges(), 1.5)       # arista superior redondeada
except Exception as e:
    print("aviso: no se pudo redondear la visera:", e)
marco += visera
hueco = inclinada(-(OL_W / 2 + 0.3), OL_W / 2 + 0.3, -OLED_FRENTE, OL_L + 0.3, -60, OLED_HUECO) & Pos(0, 0, -0.01) * sobre_acrilico
marco -= hueco
yv = OLED_VENTANA[2]
marco -= inclinada(-OLED_VENTANA[0] / 2, OLED_VENTANA[0] / 2, yv - OLED_VENTANA[1] / 2, yv + OLED_VENTANA[1] / 2,
                   OLED_HUECO - 0.2, OLED_HUECO + PIEL + 1.0)                                  # ventana

# Cuña que empuja la OLED contra la visera (apoya en el acrílico), con paso para los 4 cables junto a los pines
cuna = inclinada(-(OL_W / 2 + 0.1), OL_W / 2 + 0.1, -0.1, OL_L + 0.1, -60, 0) & sobre_acrilico
cuna -= P(G(OLED_X, 0)[0], y_pines + (5.0 - OLED_FRENTE) / 2, -1, OLED_PASO_CABLES[0], OLED_PASO_CABLES[1], 30)   # mismo paso que el acrílico
for sx in (-1, 1):                     # topes delanteros a los lados del paso de cables: la OLED no se corre hacia adelante
    x0, x1 = sorted((sx * (OLED_PASO_CABLES[0] / 2 + 0.6), sx * (OL_W / 2 - 0.5)))
    tope = inclinada(x0, x1, -OLED_FRENTE + 0.3, -0.1, -60,
                     OLED_REVERSO + OLED_PCB[2] + 0.6)
    cuna += tope & sobre_acrilico

# Lámina difusora: placa que baja por la ranura de la pared lateral (se imprime acostada)
LAM_ALTO = z_acr - (z_led - VENT_ALTO / 2 - 1.5) - 0.2
lamina = P(0, 0, 0, LAM_ALTO, LED_LARGO + 1.6, LAMINA_T)

for x, y in COLUMNAS:                             # tornillo M3 cabeza redonda, apoyada sobre el marco
    marco -= C(1.7, H_MARCO + 0.2, x, y, -0.1)

# ---------- 5. Perillas de los deslizantes (a presión en la palanca de 1,2 x 4 mm) ----------
PALANCA = (1.2, 4.0, 15.0)                        # plano: espesor, ancho, alto sobre el lomo del deslizante
PERILLA_W, PERILLA_L, PERILLA_H = 12.0, 9.0, 11.5 # ancho (cruzado al recorrido), largo (en el recorrido), alto
PERILLA_LUZ = 1.5                                 # aire entre la perilla y el acrílico
z_perilla = z_marco + PERILLA_LUZ                 # cara inferior de la perilla
z_palanca = z_top_pl + SLIDER_CUERPO[2] + PALANCA[2]
RANURA_PERILLA = z_palanca - z_perilla - 0.5      # la palanca no toca el fondo

def perilla():
    """Perilla tipo fader: cuello angosto en la palanca que se abre en curva hasta la cabeza, corona redondeada y cuenco."""
    secciones = [(0.0, 7.0, 6.5), (2.5, 7.6, 6.9), (5.5, 10.0, 7.9), (8.0, PERILLA_W, PERILLA_L),
                 (PERILLA_H - 1.0, PERILLA_W, PERILLA_L), (PERILLA_H, PERILLA_W - 1.6, PERILLA_L - 1.6)]
    perfiles = [Plane.XY.offset(z) * RectangleRounded(w, l, min(w, l) / 2 - 0.6) for z, w, l in secciones]
    k = loft(perfiles)                                                                       # transición suave
    k -= Pos(0, 0, PERILLA_H + 18.0 - 0.9) * Rot(0, 90, 0) * Cylinder(18.0, PERILLA_W + 2)    # cuenco para el dedo
    k -= Pos(0, 0, -0.01) * Box(PALANCA[0] + 0.1, PALANCA[1] + 0.1, RANURA_PERILLA + 0.01,
                                align=(Align.CENTER, Align.CENTER, Align.MIN))             # a presión
    return k
marco = Pos(0, 0, z_marco) * marco

# ---------- Referencia de componentes (solo vista previa y verificación) ----------
ref = Pos(BX0, BY_USB - PL_D, z_pl) * Box(PL_W, PL_D, PL_T, align=(Align.MIN, Align.MIN, Align.MIN))
for sx in SLIDERS:
    x, y = G(sx, SLIDER_BY)
    ref += P(x, y, z_top_pl, *SLIDER_CUERPO)
    ref += P(x, y + 10, z_top_pl + SLIDER_CUERPO[2], 1.2, 4.0, 15.0)
perillas_mont = [Pos(*G(sx, SLIDER_BY), 0) * Pos(0, 10, z_perilla) * perilla() for sx in SLIDERS]
tapas = []                                       # tapas de los botones (aparte, para pintarlas en la vista)
for bx, by in BOTONES:
    x, y = G(bx, by)
    ref += P(x, y, z_top_pl, 12, 12, 3.6)
    tapas.append(C(TAPA_BOTON_D / 2, 8.5, x, y, z_top_pl + TAPA_BOTON_ALTO - 8.5)
                 + C(6.4, 1.3, x, y, z_top_pl + TAPA_BOTON_ALTO - 8.5))
ref_oled = inclinada(-7, 7, OL_L / 2 - 5, OL_L / 2 + 5, 0, OLED_REVERSO)
ref_oled += inclinada(-OL_W / 2, OL_W / 2, 0, OL_L, OLED_REVERSO, OLED_REVERSO + OLED_PCB[2])
ref_oled += inclinada(-13.0, 13.0, 3.85, 3.85 + 16.6, OLED_REVERSO + OLED_PCB[2], OLED_REVERSO + OLED_PCB[2] + OLED_VIDRIO_ALTO)
ref += Pos(0, 0, z_marco) * ref_oled
for sx, xw in LADOS:
    ref += P(xw - sx * (LED_AIRE + LED_ALTO / 2), y_led, z_led - LED_ANCHO / 2, LED_ALTO, LED_LARGO - 4, LED_ANCHO)
x, y = G(XIAO_X, 10.5)
ref += P(x, y, z_top_pl + 2.5, 17.5, 21.0, 1.0)
ref += P(x, G(0, 2.2)[1], z_top_pl + 3.5, 9.0, 7.4, 3.2)
ref += P(x, G(0, -ALARGADOR / 2)[1], z_usb - 1.6, 9.2, ALARGADOR, 3.2)   # alargador
for sx in SLIDERS:
    ref += Pos(*G(sx, SLIDER_BY), z_top_pl + SLIDER_CUERPO[2]) * alzador(ALZA)

for nombre, pieza, step in [("CTRL-04L_1_caja", cuerpo, True), 
                            ("CTRL-04L_3_marco_oled", marco, True), (nombre_acr, acrilico, True),
                            ("CTRL-04L_4_cuna_oled", cuna, True),
                            ("CTRL-04L_7_funda_usb", Pos(0, 0, y_boca) * Rot(-90, 0, 0) * Pos(-x, 0, -z_usb) * funda, True),
                            ("_funda_usb_montada", funda, False),
                            ("CTRL-04L_5_lamina_difusora_x2", Pos(-9, 0, 0) * lamina + Pos(9, 0, 0) * lamina, False),
                            ("CTRL-04L_6_perilla_x2", Pos(-8, 0, 0) * perilla() + Pos(8, 0, 0) * perilla(), True),
                            ("_perillas_montadas", Compound(perillas_mont), False),
                            ("_referencia_componentes", ref, False),
                            *[(f"_tapa_boton_{i}", t, False) for i, t in enumerate(tapas)],
                            ("_laminas_montadas", Compound([Pos(xw + sx * RANURA / 2, y_led, z_acr - LAM_ALTO - 0.1 + LAM_ALTO / 2)
                                                             * Rot(0, 90, 0) * Pos(0, 0, -LAMINA_T / 2) * lamina for sx, xw in LADOS]), False)]:
    export_stl(pieza, str(OUT / f"{nombre}.stl"), tolerance=0.02, angular_tolerance=0.15)
    if step:
        export_step(pieza, str(OUT / f"{nombre}.step"))
    bb = pieza.bounding_box()
    print(nombre, f"{bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f}", f"vol {pieza.volume / 1000:.1f} cm3")

ref_total = ref + Compound(tapas)
for nombre, pieza in [("caja", cuerpo), ("acrílico", acrilico), ("marco", marco), ("cuña", Pos(0, 0, z_marco) * cuna)]:
    print(f"choque {nombre}-componentes mm3:", round((pieza & ref_total).volume, 2))
print("tapa del botón sobre el acrílico (mm):", round(TAPA_BOTON_ALTO - GAP - ACRILICO, 2))
x_b, y_b = G(*BOTONES[0])
print("holgura isla OLED ↔ tapa de botón (mm):", round(BOTONES[0][1] - TAPA_BOTON_D / 2 - isla_frente, 2))
laminas_mont = [Pos(xw + sx * RANURA / 2, y_led, z_acr - LAM_ALTO - 0.1 + LAM_ALTO / 2) * Rot(0, 90, 0) * Pos(0, 0, -LAMINA_T / 2) * lamina
                for sx, xw in LADOS]
print("choque láminas-caja mm3:", round(sum((l & cuerpo).volume for l in laminas_mont), 3))
x_u, _ = G(XIAO_X, 0)
print("USB-C: boca del conector a", round(D - (BY_USB + 1.6), 2), "mm de la cara exterior | columnas traseras x hasta",
      round(T + 2 * COL_R, 1), "vs placa desde x", BX0)
print("choque perillas-marco/acrílico mm3:", round(sum((k & marco).volume + (k & acrilico).volume for k in perillas_mont), 3),
      "| palanca dentro de la perilla:", round(RANURA_PERILLA, 1), "mm")
print("choque cuña-marco mm3:", round((Pos(0, 0, z_marco) * cuna & marco).volume, 2))
print("visera: alto sobre el acrílico adelante/atrás (mm):", round(CUNA_MIN - 1.9 * si + (OLED_HUECO + PIEL) * co, 1), "/",
      round(CUNA_MIN + (OL_L + 1.9) * si + (OLED_HUECO + PIEL) * co, 1))
print("tiras laterales: ventana", LED_LARGO - 2, "x", VENT_ALTO, "mm | aire LED→lámina", LED_AIRE, "mm | lámina", round(LAM_ALTO, 1), "x", LED_LARGO + 1.6, "x", LAMINA_T)
print("alto total (borde del marco):", round(H, 1), "mm | tornillo bajo la cabeza:", round(H_MARCO + ACRILICO, 1), "mm + rosca en la columna (M3 x 12)")
print("caja:", round(W, 1), "x", round(D, 1), "mm")
