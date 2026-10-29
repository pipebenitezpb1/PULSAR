# PULSAR · tapa protectora: encaja a presión sobre el marco + acrílico + borde de la caja y cubre visera y perillas.
# Dos piezas para imprimir a dos colores (AMS): cuerpo + galón y el nombre PULSAR embutidos a ras (0,8 mm).
# Se imprime boca abajo (la cara del galón sobre la cama): sin soportes.
from pathlib import Path
from build123d import *
import caja_laser as c
from perillas_variantes import VARIANTES
from logo import geometria_tapa

OUT = Path(__file__).parent / "salida_laser"
HOLGURA = 0.25                 # por lado: entra con roce suave (PLA/PETG; subir a 0,35 si queda dura)
PARED, TECHO = 2.0, 2.0
SOLAPE = 4.0                   # cuánto baja la falda sobre el borde de la caja, bajo el acrílico
AIRE = 1.0                     # sobre lo más alto (visera o la perilla más alta)
INLAY = 0.8

alto_perilla = max(f().bounding_box().size.Z for f in VARIANTES.values())        # la más alta de todas las variantes
z_max = max(c.marco.bounding_box().max.Z, c.z_perilla + alto_perilla)
z_falda, z_techo = c.z_acr - SOLAPE, z_max + AIRE
cx, cy = c.W / 2, c.D / 2

def contorno(margen, z0, h):
    return Pos(cx, cy, z0) * extrude(RectangleRounded(c.W + 2 * margen, c.D + 2 * margen, c.R_V + margen), h)

tapa = contorno(HOLGURA + PARED, z_falda, z_techo + TECHO - z_falda)
tapa = fillet(tapa.edges().group_by(Axis.Z)[-1], 2.0)                             # canto superior redondeado
tapa -= contorno(HOLGURA, z_falda - 1, z_techo - z_falda + 1)

# Paso para el zócalo y la funda del USB-C en la cara trasera
fb = c.funda.bounding_box()
xu = (fb.min.X + fb.max.X) / 2
tapa -= Pos(xu, c.D, z_falda - 1) * Box(22.0 + 2 * 0.6, 20, max(fb.max.Z, c.z_acr) + 0.6 - z_falda + 1,
                                       align=(Align.CENTER, Align.CENTER, Align.MIN))
# Muescas para el pulgar a los costados (para sacarla)
for x in (0, c.W):
    tapa -= Pos(x, cy, z_falda) * Rot(0, 90, 0) * Cylinder(9.0, 2 * (PARED + HOLGURA) + 4)

# Galón + nombre PULSAR, embutidos en la cara superior
zt = z_techo + TECHO
def galon(ancho, y_punta, y_ala, grueso):
    a = ancho / 2
    return Polygon((0, y_punta), (a, y_ala), (a, y_ala + grueso), (0, y_punta + grueso * 1.4),
                   (-a, y_ala + grueso), (-a, y_ala), align=None)
dibujo = Pos(cx, cy + 14) * (galon(46, -10, 3, 5) + galon(32, 1, 10, 3.6))
relieves = [extrude(Plane.XY.offset(zt - INLAY) * dibujo, INLAY + 1)]
relieves += [Pos(cx, cy - 16, zt - INLAY) * extrude(parte, INLAY + 1) for parte in geometria_tapa(9.0)]   # logo PULSAR
relieves = [r.fix() for r in relieves]                   # el texto de la fuente trae contornos que OCCT debe reparar
acento = Compound([tapa & r for r in relieves])          # cada relieve por separado: unir texto con otras piezas falla en OCCT
for r in relieves:
    try:
        tapa -= r
    except ValueError:                                    # si una letra no se deja restar, se resta letra por letra
        for sol in r.solids():
            tapa -= sol

if __name__ == "__main__":
    obstaculos = c.cuerpo + c.acrilico + c.marco + c.funda
    choque = (tapa & obstaculos).volume
    for k in c.perillas_mont:                                                   # perillas en todo su recorrido
        for dy in (-c.SLIDER_RECORRIDO / 2 - 10, 0, c.SLIDER_RECORRIDO / 2 - 10):
            choque += (tapa & Pos(0, dy, 0) * k).volume
    bb = tapa.bounding_box()
    print(f"tapa {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm | aire sobre la visera {z_techo - c.marco.bounding_box().max.Z:.1f} mm"
          f" | perilla más alta {alto_perilla:.1f} mm | choque {choque:.2f} mm3 | válida {tapa.is_valid and acento.is_valid}")
    imprimir = lambda s: Pos(0, 0, zt) * Rot(180, 0, 0) * s                      # boca abajo, el galón sobre la cama
    for nombre, s in (("cuerpo", tapa), ("acento", acento)):
        export_stl(imprimir(s), str(OUT / f"CTRL-04L_9_tapa_{nombre}.stl"), tolerance=0.02, angular_tolerance=0.15)
        export_stl(s, str(OUT / f"_tapa_montada_{nombre}.stl"), tolerance=0.02, angular_tolerance=0.15)
    export_step(Compound([imprimir(tapa), imprimir(acento)]), str(OUT / "CTRL-04L_9_tapa.step"))
