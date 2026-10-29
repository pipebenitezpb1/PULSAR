# CTRL-04L · perillas inspiradas en Buzz Lightyear (verde limón + morado índigo + blanco)
# Cada perilla tiene dos piezas para imprimir a dos colores con el AMS: cuerpo + acento embutido a ras (0,8 mm).
from pathlib import Path
from build123d import *
import caja_laser as c
from perillas_variantes import encastre, seccion

OUT = Path(__file__).parent / "salida_laser" / "perillas_buzz"
OUT.mkdir(parents=True, exist_ok=True)
ALTO = c.RANURA_PERILLA + 1.6          # mínimo para que la palanca no asome arriba
INLAY = 0.8                             # profundidad del acento


def cuello(hasta):
    return loft([seccion(0, 7.0, 6.5), seccion(hasta, 7.6, 6.8)], ruled=True)


def chevron(ancho, y_punta, y_ala, grueso):
    """Galón de Star Command apuntando hacia el usuario (-y)."""
    a = ancho / 2
    return Polygon((0, y_punta), (a, y_ala), (a, y_ala + grueso), (0, y_punta + grueso * 1.4),
                   (-a, y_ala + grueso), (-a, y_ala), align=None)


def separar(cuerpo, acento):
    acento = cuerpo & acento
    return encastre(cuerpo - acento), acento


def ala():
    """Las alas del jetpack: cabeza en flecha con las puntas barridas hacia atrás + galón embutido arriba."""
    alto_ala = 4.5
    planta = Polygon((0, -4.5), (7.5, 2.0), (7.5, 4.5), (0, 3.0), (-7.5, 4.5), (-7.5, 2.0), align=None)
    cuerpo = cuello(ALTO - alto_ala + 0.01) + extrude(Plane.XY.offset(ALTO - alto_ala) * planta, alto_ala)
    cuerpo = fillet(cuerpo.edges().group_by(Axis.Z)[-1], 0.7)
    acento = extrude(Plane.XY.offset(ALTO - INLAY) * chevron(12.4, -3.0, 2.1, 1.3), INLAY + 0.5)
    return separar(cuerpo, acento)


def casco():
    """El casco: cúpula abombada con la franja del visor alrededor."""
    cuerpo = loft([seccion(0, 7.0, 6.5), seccion(3.0, 7.4, 6.8), seccion(5.5, 11.6, 9.6),
                   seccion(8.5, 12.4, 10.2), seccion(ALTO, 9.0, 7.4)])
    franja = Pos(0, 0, 6.2) * Box(20, 20, 1.6, align=(Align.CENTER, Align.CENTER, Align.MIN))
    acento = franja - scale(cuerpo, by=(0.86, 0.84, 1.0))
    return separar(cuerpo, acento)


def cohete():
    """Aleta de cohete inclinada hacia atrás, con ojo de buey a cada lado."""
    alto, grosor = 13.0, 7.0
    def sec(z, dy, w, l, r=None):
        return Plane.XY.offset(z) * Pos(0, dy) * RectangleRounded(w, l, r if r is not None else min(w, l) / 2 - 0.6)
    cuerpo = loft([sec(0, 0, 7.0, 6.5), sec(3.0, 0, 7.6, 6.6), sec(6.5, 0.3, 13.0, grosor, 1.6), sec(alto, 1.2, 11.0, grosor, 1.6)], ruled=True)
    cuerpo = fillet(cuerpo.edges().group_by(Axis.Z)[-1], 1.2)
    z0, yc = 9.5, 0.3 + 0.9 * (9.5 - 6.5) / 6.5
    acento = Part()
    for s in (-1, 1):
        acento += Pos(0, yc + s * grosor / 2, z0) * Rot(90, 0, 0) * Cylinder(2.6, 2 * INLAY)
    return separar(cuerpo, acento)


def insignia():
    """Tapa de fader DJ con el galón de Star Command en relieve embutido."""
    cuerpo = loft([seccion(0, 7.0, 6.5), seccion(ALTO - 5.5, 7.6, 6.8), seccion(ALTO - 3.5, 13.0, 8.5, 1.5),
                   seccion(ALTO, 13.0, 8.5, 1.5)], ruled=True)
    cuerpo = fillet(cuerpo.edges().group_by(Axis.Z)[-1], 0.8)
    acento = extrude(Plane.XY.offset(ALTO - INLAY) * chevron(10.0, -3.0, 1.2, 1.4), INLAY + 0.5)
    return separar(cuerpo, acento)


# nombre: (función, color cuerpo, color acento) para las vistas
VARIANTES = {"H_ala": (ala, "indigo", "lima"), "I_casco": (casco, "blanco", "indigo"),
             "J_cohete": (cohete, "blanco", "lima"), "K_insignia": (insignia, "indigo", "lima")}

if __name__ == "__main__":
    obstaculos = c.marco + c.acrilico
    for nombre, (f, _, _) in VARIANTES.items():
        cuerpo, acento = f()
        k = cuerpo + acento
        bb = k.bounding_box()
        choque = 0.0
        for sx in c.SLIDERS:
            for dy in (-c.SLIDER_RECORRIDO / 2, 0, c.SLIDER_RECORRIDO / 2):
                x, y = c.G(sx, c.SLIDER_BY)
                choque += (Pos(x, y + dy, c.z_perilla) * k & obstaculos).volume
        for parte, sol in (("cuerpo", cuerpo), ("acento", acento)):
            export_stl(Pos(-10, 0, 0) * sol + Pos(10, 0, 0) * sol, str(OUT / f"perilla_{nombre}_{parte}_x2.stl"),
                       tolerance=0.02, angular_tolerance=0.15)
            mont = Compound([Pos(*c.G(sx, c.SLIDER_BY), 0) * Pos(0, 10, c.z_perilla) * sol for sx in c.SLIDERS])
            export_stl(mont, str(OUT / f"_mont_{nombre}_{parte}.stl"), tolerance=0.02, angular_tolerance=0.15)
        export_step(Compound([Pos(-10, 0, 0) * k, Pos(10, 0, 0) * k]), str(OUT / f"perilla_{nombre}_x2.step"))
        print(f"{nombre:12s} {bb.size.X:5.1f} x {bb.size.Y:5.1f} x {bb.size.Z:5.1f} mm | acento {acento.volume:5.1f} mm3 "
              f"| válida {cuerpo.is_valid and acento.is_valid} | choque {choque:.2f} mm3")
