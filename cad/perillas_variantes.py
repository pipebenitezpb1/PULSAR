# CTRL-04L · variantes de perilla para los sliders (todas calzan a presión en la misma palanca de 1,2 x 4 mm)
# Usa las medidas de caja_laser.py y revisa que ninguna choque con el marco, la visera ni el acrílico en todo el recorrido.
import math
from pathlib import Path
from build123d import *
import caja_laser as c

OUT = Path(__file__).parent / "salida_laser" / "perillas"
OUT.mkdir(parents=True, exist_ok=True)
H = c.PERILLA_H


def encastre(k):
    """Ranura a presión para la palanca (igual en todas)."""
    return k - Pos(0, 0, -0.01) * Box(c.PALANCA[0] + 0.1, c.PALANCA[1] + 0.1, c.RANURA_PERILLA + 0.01,
                                      align=(Align.CENTER, Align.CENTER, Align.MIN))


def seccion(z, w, l, r=None):
    return Plane.XY.offset(z) * RectangleRounded(w, l, r if r is not None else min(w, l) / 2 - 0.6)


def tulipan():
    """La actual: cuello que se abre en curva, corona redondeada y cuenco."""
    return c.perilla()


def dj():
    """Tapa de fader de mesa DJ: cabeza ancha y plana con estrías cruzadas al recorrido (alto mínimo: la palanca entra 9 mm)."""
    alto = c.RANURA_PERILLA + 1.6
    k = loft([seccion(0, 7.0, 6.5), seccion(alto - 5.5, 7.6, 6.8), seccion(alto - 3.5, 13.0, 8.5, 1.5), seccion(alto, 13.0, 8.5, 1.5)], ruled=True)
    k = fillet(k.edges().group_by(Axis.Z)[-1], 0.8)
    for i in (-1, 0, 1):                                   # tres estrías a lo ancho
        k -= Pos(0, i * 2.4, alto + 0.35) * Rot(0, 90, 0) * Cylinder(0.7, 14)
    return encastre(k)


def cilindro():
    """Cilindro moleteado con tapa abombada."""
    r, alto = 5.5, 11.0
    k = Cylinder(3.4, 3.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    k += loft([Plane.XY.offset(2.5) * Circle(3.4), Plane.XY.offset(4.5) * Circle(r)])
    k += Pos(0, 0, 4.5) * Cylinder(r, alto - 4.5, align=(Align.CENTER, Align.CENTER, Align.MIN))
    k = fillet(k.edges().group_by(Axis.Z)[-1], 1.6)
    for i in range(18):                                    # moleteado
        a = math.radians(i * 20)
        k -= Pos(r * math.cos(a), r * math.sin(a), 5.5) * Cylinder(0.45, alto - 7.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return encastre(k)


def hongo():
    """Cuello delgado y sombrero en domo, se empuja con la yema."""
    k = loft([seccion(0, 6.5, 6.0), seccion(5.0, 5.5, 5.0, 2.2), seccion(6.0, 7.0, 6.5)])
    domo = Pos(0, 0, 6.0) * (Sphere(7.0) & Pos(0, 0, 0) * Box(20, 20, 20, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    domo = Pos(0, 0, -2.0) * (domo & Pos(0, 0, 8.0) * Box(20, 20, 20, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    k += domo
    return encastre(k)


def aleta():
    """Aleta delgada tipo consola: ancha cruzada al recorrido, con un hoyuelo para el dedo en cada cara."""
    alto, ancho, grosor = 13.0, 13.0, 5.5
    k = loft([seccion(0, 7.0, 6.5), seccion(3.0, 7.6, 6.0), seccion(6.5, ancho, grosor, 1.5), seccion(alto, ancho, grosor, 1.5)], ruled=True)
    k = fillet(k.edges().group_by(Axis.Z)[-1], 1.2)
    for s_ in (-1, 1):                                     # hoyuelo cóncavo a cada lado del recorrido
        k -= Pos(0, s_ * (9.0 + grosor / 2 - 0.9), 9.8) * Sphere(9.0)
    return encastre(k)


def hexagono():
    """Prisma hexagonal facetado con chaflán arriba."""
    alto = 11.0
    k = loft([seccion(0, 7.0, 6.5), Plane.XY.offset(4.0) * RegularPolygon(6.2, 6)])
    k += extrude(Plane.XY.offset(4.0) * RegularPolygon(6.2, 6), alto - 4.0)
    k = chamfer(k.edges().group_by(Axis.Z)[-1], 1.2)
    k -= Pos(0, 0, alto + 6.0 - 0.7) * Sphere(6.0)                             # leve cuenco
    return encastre(k)


def escalonada():
    """Tres escalones tipo pagoda, más ancha arriba."""
    k = Box(7.0, 6.5, 4.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    k += Pos(0, 0, 4.0) * Box(10.0, 8.0, 3.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    k += Pos(0, 0, 7.0) * Box(12.5, 9.5, 4.0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    k = fillet(k.edges().filter_by(Axis.Z), 1.0)
    k = fillet(k.edges().group_by(Axis.Z)[-1], 1.0)
    return encastre(k)


VARIANTES = {"A_tulipan": tulipan, "B_dj": dj, "C_cilindro": cilindro, "D_hongo": hongo,
             "E_aleta": aleta, "F_hexagono": hexagono, "G_escalonada": escalonada}

if __name__ == "__main__":
    obstaculos = c.marco + c.acrilico
    for nombre, f in VARIANTES.items():
        k = f()
        bb = k.bounding_box()
        choque = 0.0
        for sx in c.SLIDERS:                               # extremos y centro del recorrido
            for dy in (-c.SLIDER_RECORRIDO / 2, 0, c.SLIDER_RECORRIDO / 2):
                x, y = c.G(sx, c.SLIDER_BY)
                choque += (Pos(x, y + dy, c.z_perilla) * k & obstaculos).volume
        par = Pos(-9, 0, 0) * k + Pos(9, 0, 0) * k
        export_stl(par, str(OUT / f"perilla_{nombre}_x2.stl"), tolerance=0.02, angular_tolerance=0.15)
        export_step(par, str(OUT / f"perilla_{nombre}_x2.step"))
        export_stl(k, str(OUT / f"_{nombre}.stl"), tolerance=0.02, angular_tolerance=0.15)
        print(f"{nombre:14s} {bb.size.X:5.1f} x {bb.size.Y:5.1f} x {bb.size.Z:5.1f} mm | choque {choque:.2f} mm3")
