# Patas de TPU para los 4 rebajes del piso: CTRL-04L y CTRL-03 compacta (Ø10 x 1), CTRL-02 (Ø12 x 1)
from pathlib import Path
from build123d import *

OUT = Path(__file__).parent / "salida_laser"
REBAJE_H, PIE_H = 1.0, 2.0
CONTROLADORES = {"CTRL-04L_8": 10.0, "CTRL-03c": 10.0, "CTRL-02": 12.0}   # diámetro del rebaje de cada base


def pata(rebaje_d):
    """Se imprime con la cara de apoyo (la ancha) sobre la cama."""
    TAPON_D = rebaje_d - 0.2        # entra justo en el rebaje (el TPU cede)
    PIE_D = rebaje_d + 2.0          # lo que queda afuera: un poco más ancho que el rebaje, tapa el borde
    pie = Cylinder(PIE_D / 2, PIE_H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    pie = fillet(pie.edges().group_by(Axis.Z)[0], 0.8)                 # canto redondeado hacia la mesa
    tapon = Pos(0, 0, PIE_H - 0.01) * Cylinder(TAPON_D / 2, REBAJE_H + 0.01, align=(Align.CENTER, Align.CENTER, Align.MIN))
    tapon = chamfer(tapon.edges().group_by(Axis.Z)[-1], 0.3)           # entra fácil
    return pie + tapon


if __name__ == "__main__":
    for nombre, d in CONTROLADORES.items():
        p = pata(d)
        paso = d + 5
        juego = Compound([Pos(x * paso, y * paso, 0) * p for x in range(3) for y in range(2)])   # 4 + 2 de repuesto
        export_stl(juego, str(OUT / f"{nombre}_patas_tpu_x6.stl"), tolerance=0.01, angular_tolerance=0.1)
        export_step(juego, str(OUT / f"{nombre}_patas_tpu_x6.step"))
        bb = p.bounding_box().size
        print(f"{nombre}: pata Ø{bb.X:.1f} x {bb.Z:.1f} mm | válida {p.is_valid}")
