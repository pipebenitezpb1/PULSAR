# PULSAR · logo: la palabra en Orbitron Black + una línea de pulso con un pico (la señal de un púlsar).
# Genera el PNG del logo, el mapa de bits para la OLED (encabezado C para el firmware) y la geometría para la tapa.
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

AQUI = Path(__file__).parent
FUENTE = AQUI / "fuentes" / "Orbitron-Black.ttf"     # Orbitron, SIL Open Font License
TEXTO = "PULSAR"


def pulso(x0, x1, y, alto):
    """Puntos de la línea de pulso: plana, un pico doble al centro, plana."""
    cx = (x0 + x1) / 2
    return [(x0, y), (cx - 0.11 * alto * 4, y), (cx - 0.06 * alto * 4, y - 0.55 * alto), (cx - 0.01 * alto * 4, y + 0.55 * alto),
            (cx + 0.04 * alto * 4, y - alto), (cx + 0.09 * alto * 4, y), (x1, y)]


def imagen(alto_letra, tinta, acento, fondo=(0, 0, 0, 0), margen=None):
    """Logo en mapa de bits; alto_letra en píxeles."""
    f = ImageFont.truetype(str(FUENTE), int(alto_letra / 0.72))
    esp = alto_letra * 0.1
    cajas = [f.getbbox(ch) for ch in TEXTO]
    ancho = sum(b[2] - b[0] for b in cajas) + esp * (len(TEXTO) - 1)
    m = alto_letra * 0.15 if margen is None else margen
    sup = min(b[1] for b in cajas)
    W, H = int(ancho + 2 * m), int(alto_letra * 2.0 + 2 * m)
    im = Image.new("RGBA", (W, H), fondo)
    d = ImageDraw.Draw(im)
    x = m
    for ch, b in zip(TEXTO, cajas):
        d.text((x - b[0], m - sup), ch, font=f, fill=tinta)
        x += b[2] - b[0] + esp
    y = m + alto_letra * 1.55
    d.line(pulso(m, W - m, y, alto_letra * 0.42), fill=acento, width=max(1, round(alto_letra * 0.07)), joint="curve")
    return im


def xbm_oled(ancho=120):
    """Logo de 1 bit para la OLED (U8g2 drawXBMP), ajustado a `ancho` píxeles."""
    alto_letra = 16
    while True:
        im = imagen(alto_letra, (255, 255, 255, 255), (255, 255, 255, 255), (0, 0, 0, 255), margen=0)
        if im.width >= ancho or alto_letra > 40:
            break
        alto_letra += 1
    im = im.convert("L").point(lambda v: 255 if v > 110 else 0)
    w, h = im.size
    filas = []
    for y in range(h):
        fila = []
        for bx in range(0, w, 8):
            v = 0
            for k in range(8):
                if bx + k < w and im.getpixel((bx + k, y)):
                    v |= 1 << k
            fila.append(f"0x{v:02x}")
        filas.append("  " + ", ".join(fila) + ",")
    return w, h, "\n".join(filas)


def letras_vectoriales(alto_letra, pasos=10):
    """PULSAR como caras de build123d desde los contornos de la fuente (fontTools), con las curvas en tramos rectos."""
    from fontTools.ttLib import TTFont
    from fontTools.pens.basePen import BasePen
    from build123d import Polygon, Pos

    class Contornos(BasePen):
        def __init__(self, glifos):
            super().__init__(glifos); self.lista, self.actual = [], []
        def _moveTo(self, p): self.actual = [p]
        def _lineTo(self, p): self.actual.append(p)
        def _qCurveToOne(self, p1, p2):
            p0 = self.actual[-1]
            for k in range(1, pasos + 1):
                t = k / pasos
                self.actual.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))
        def _curveToOne(self, p1, p2, p3):
            p0 = self.actual[-1]
            for k in range(1, pasos + 1):
                t = k / pasos; u = 1 - t
                self.actual.append((u**3 * p0[0] + 3 * u*u*t * p1[0] + 3 * u*t*t * p2[0] + t**3 * p3[0],
                                    u**3 * p0[1] + 3 * u*u*t * p1[1] + 3 * u*t*t * p2[1] + t**3 * p3[1]))
        def _closePath(self):
            if len(self.actual) > 2: self.lista.append(self.actual)
            self.actual = []
        _endPath = _closePath

    fuente = TTFont(str(FUENTE))
    glifos, cmap, hmtx = fuente.getGlyphSet(), fuente.getBestCmap(), fuente["hmtx"]
    alto_mayus = fuente["OS/2"].sCapHeight or fuente["head"].unitsPerEm * 0.72
    esc = alto_letra / alto_mayus
    resultado, x = None, 0.0
    for ch in TEXTO:
        nombre = cmap[ord(ch)]
        pen = Contornos(glifos); glifos[nombre].draw(pen)
        def area(c): return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(c, c[1:] + c[:1])) / 2
        def cara(c):
            pts = [(x + px * esc, py * esc) for px, py in c]
            pts = [q for i, q in enumerate(pts) if i == 0 or abs(q[0] - pts[i - 1][0]) + abs(q[1] - pts[i - 1][1]) > 1e-4]
            if area(c) < 0: pts = pts[::-1]                   # todas antihorarias: la cara mira hacia +Z al extruir
            return Polygon(*pts, align=None)
        exteriores = [c for c in pen.lista if area(c) < 0]           # TrueType: exterior en sentido horario
        huecos = [c for c in pen.lista if area(c) > 0]
        letra = None
        for c in exteriores: letra = cara(c) if letra is None else letra + cara(c)
        for c in huecos: letra -= cara(c)
        resultado = letra if resultado is None else resultado + letra
        x += (hmtx[nombre][0] + 0.1 * alto_mayus) * esc            # avance + 10 % de espacio extra
    return resultado


def geometria_tapa(alto_letra):
    """Logo como lista de dibujos 2D de build123d (letras, pulso), centrado en el origen."""
    import math
    from build123d import Pos, Rot, Rectangle, Circle
    letras = letras_vectoriales(alto_letra)                # Text() de OCCT deja sólidos inválidos con esta fuente
    bb = letras.bounding_box()
    x0, x1 = bb.min.X, bb.max.X
    y = bb.min.Y - alto_letra * 0.55
    grueso = max(alto_letra * 0.07, 1.0)                  # mínimo 1 mm: imprimible con boquilla 0,4
    pts = pulso(x0, x1, y, alto_letra * 0.42)
    pts = [(px, 2 * y - py) for px, py in pts]            # en CAD el eje Y sube: el pico va hacia arriba
    linea = None
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):          # tramos gruesos con uniones redondas
        largo, ang = math.hypot(bx - ax, by - ay), math.degrees(math.atan2(by - ay, bx - ax))
        tramo = Pos((ax + bx) / 2, (ay + by) / 2) * Rot(0, 0, ang) * Rectangle(largo, grueso)
        tramo += Pos(bx, by) * Circle(grueso / 2)
        linea = tramo if linea is None else linea + tramo
    linea += Pos(*pts[0]) * Circle(grueso / 2)
    xs = (min(bb.min.X, x0), max(bb.max.X, x1)); ys = (min(p[1] for p in pts) - grueso, bb.max.Y)
    centro = Pos(-(xs[0] + xs[1]) / 2, -(ys[0] + ys[1]) / 2)
    return [centro * letras, centro * linea]               # se extruyen por separado (la unión 2D texto+caras falla en OCCT)


if __name__ == "__main__":
    imagen(240, (27, 26, 19, 255), (26, 122, 46, 255)).save(AQUI / "logo_pulsar.png")
    imagen(240, (241, 235, 220, 255), (155, 210, 42, 255)).save(AQUI / "logo_pulsar_claro.png")
    w, h, datos = xbm_oled()
    (AQUI.parent / "firmware_ctrl04" / "src" / "logo_pulsar.h").write_text(
        f"// Logo PULSAR para la OLED (generado por avanzado/logo.py, no editar a mano)\n#pragma once\n"
        f"const int LOGO_W = {w}, LOGO_H = {h};\nstatic const unsigned char LOGO_BITS[] PROGMEM = {{\n{datos}\n}};\n", encoding="utf-8")
    print("logo listo; OLED", w, "x", h)
