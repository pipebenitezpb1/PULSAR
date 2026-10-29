"""Genera el manual a partir de MANUAL.md (Edge headless), en blanco y negro y como cuadernillo de hoja partida:
- docs/manual_CTRL-04L.pdf: páginas A5 en orden de lectura (para pantalla).
- docs/manual_CTRL-04L_cuadernillo.pdf: las mismas páginas impuestas de a dos en hojas A4 VERTICALES (giradas 90°),
  para que funcione la doble cara normal de cualquier impresora (borde largo), al 100 %; se dobla por la mitad.
La tarjeta rápida queda siempre en la contratapa."""
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright
from pypdf import PdfReader, PdfWriter, PageObject, Transformation

RAIZ = Path(__file__).resolve().parent.parent
md = (RAIZ / "MANUAL.md").read_text(encoding="utf-8")
md = md.split("## Índice", 1)[1].split("---", 1)[1]           # sin el título ni el índice: van en la portada
fuentes = (RAIZ / "dashboard" / "fonts" / "fonts.css").as_uri()

HTML = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<link rel="stylesheet" href="__FUENTES__">
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
<style>
  @page { size: A5; margin: 11mm 11mm 13mm; }
  * { box-sizing: border-box; }
  html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { margin: 0; color: #000; font: 9pt/1.4 'Barlow', Arial, sans-serif; }
  img { filter: grayscale(1) contrast(1.1); max-width: 100%; }
  h1, h2, h3 { font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif; text-transform: uppercase; letter-spacing: .02em; break-after: avoid; }
  h2 { font-size: 15pt; margin: 14pt 0 6pt; padding: 3pt 0 4pt; border-top: 3pt solid #000; border-bottom: 1pt solid #000; }
  h3 { font-size: 11pt; margin: 10pt 0 3pt; }
  p, li { margin: 3pt 0; }
  ul, ol { padding-left: 13pt; }
  table { width: 100%; border-collapse: collapse; margin: 5pt 0 8pt; break-inside: avoid; font-size: 8pt; }
  th, td { border: .8pt solid #000; padding: 2pt 4pt; text-align: left; vertical-align: top; }
  th { background: #e6e6e6; font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif; font-size: 8.5pt; text-transform: uppercase; }
  blockquote { margin: 8pt 0; padding: 5pt 10pt; border-left: 3pt solid #000; background: #f0f0f0; }
  blockquote p { margin: 0; }
  code { font-family: 'Space Mono', Consolas, monospace; font-size: 7.5pt; }
  pre { border: 1pt solid #000; padding: 6pt 8pt; background: #f0f0f0; break-inside: avoid; }
  hr { display: none; }
  .junto { break-inside: avoid; }
  a { color: #000; text-decoration: none; }
  /* portada */
  .portada { height: 184mm; display: flex; flex-direction: column; break-after: page; }
  .portada .marca { font: 400 7pt 'Space Mono', monospace; letter-spacing: .14em; border-bottom: 2pt solid #000; padding-bottom: 4pt; }
  .portada h1 { font-size: 40pt; line-height: .9; margin: 10mm 0 3mm; }
  .portada .sub { font: 600 12pt 'Barlow Condensed', sans-serif; text-transform: uppercase; }
  .portada img { margin: 4mm auto 0; width: 100mm; }
  .portada .indice { margin-top: auto; columns: 2; font-size: 8pt; border-top: 2pt solid #000; padding-top: 6pt; }
  .portada .indice div { break-inside: avoid; padding: 1.5pt 0; }
  .portada .pie { font: 7.5pt 'Space Mono', monospace; margin-top: 6pt; }
  /* la tarjeta rápida: página propia, recortable */
  .tarjeta { break-before: page; }
  .tarjeta table { border: 2pt solid #000; font-size: 10pt; }
  .tarjeta td { padding: 5pt 8pt; }
  .tarjeta .tijera { font: 7pt 'Space Mono', monospace; margin-top: 6pt; }
</style></head><body>
<div class="portada">
  <div class="marca">TALLER DE INTERFACES UAI · LUIS-FELIPE BENITEZ · 2026</div>
  <h1>CTRL-04L<br>Manual de uso</h1>
  <div class="sub">Controlador físico con pantalla, luces, juegos y sintetizador web</div>
  <img src="__IMAGEN__">
  <div class="indice" id="indice"></div>
  <div class="pie">github.com/pipebenitezpb1/CTRL-04L</div>
</div>
<main id="m"></main>
<script>
  const md = __MD__;
  const m = document.getElementById("m");
  m.innerHTML = marked.parse(md);
  m.querySelectorAll("img").forEach(i => i.remove());           // la foto ya está en la portada
  m.querySelectorAll("thead").forEach(t => { if (!t.textContent.trim()) t.remove(); });   // tablas sin encabezado
  m.querySelectorAll("h2, h3").forEach(h => {                   // el título no queda solo al final de una página
    const g = document.createElement("div"); g.className = "junto";
    h.before(g); g.appendChild(h);
    for (let k = 0; k < 2 && g.nextElementSibling && !/^H[23]$/.test(g.nextElementSibling.tagName); k++) g.appendChild(g.nextElementSibling);
  });
  const ind = document.getElementById("indice");
  m.querySelectorAll("h2").forEach(h => { const d = document.createElement("div"); d.textContent = h.textContent; ind.appendChild(d); });
  const ultima = [...m.querySelectorAll("h2")].pop();            // la tarjeta rápida, en su propia página
  const t = document.createElement("section"); t.className = "tarjeta";
  ultima.before(t);
  while (t.nextSibling) t.appendChild(t.nextSibling);
  t.insertAdjacentHTML("beforeend", '<div class="tijera">Tarjeta rápida en la contratapa: déjala a la vista junto a la caja.</div>');
  document.body.dataset.ok = 1;
</script></body></html>"""

def imponer(origen, destino):
    """Cuadernillo: páginas A5 de a dos en A4 apaisada, en el orden de una hoja doblada (múltiplo de 4)."""
    pags = list(PdfReader(str(origen)).pages)
    contratapa = pags.pop()                               # la tarjeta rápida va siempre atrás
    while (len(pags) + 1) % 4: pags.append(None)          # páginas en blanco antes de la contratapa
    pags.append(contratapa)
    n, ancho, alto = len(pags), 841.89, 595.28
    w = PdfWriter()
    for h in range(n // 4):
        for cara, (izq, der) in enumerate(((pags[n - 1 - 2 * h], pags[2 * h]), (pags[2 * h + 1], pags[n - 2 - 2 * h]))):   # frente y dorso
            hoja = PageObject.create_blank_page(width=ancho, height=alto)
            for pag, x in ((izq, 0), (der, ancho / 2)):
                if pag is not None:
                    dx = x + (ancho / 2 - float(pag.mediabox.width)) / 2
                    hoja.merge_transformed_page(pag, Transformation().translate(tx=dx, ty=0))
            vertical = PageObject.create_blank_page(width=alto, height=ancho)   # A4 vertical: la doble cara normal
            giro = Transformation().rotate(90).translate(tx=alto, ty=0) if cara == 0 else                    Transformation().rotate(-90).translate(tx=0, ty=ancho)       # el dorso va girado al otro lado
            vertical.merge_transformed_page(hoja, giro)
            w.add_page(vertical)
    w.write(str(destino))
    print(f"{n} páginas A5 → {n // 4} hojas A4 a doble cara ({n // 2} caras)")


async def main():
    html = (HTML.replace("__FUENTES__", fuentes)
                .replace("__IMAGEN__", (RAIZ / "docs" / "renders" / "vistaL_frente.png").as_uri())
                .replace("__MD__", json.dumps(md)))
    pagina = RAIZ / "docs" / "_manual.html"
    pagina.write_text(html, encoding="utf-8")
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge")
        pg = await b.new_page()
        await pg.goto(pagina.as_uri())
        await pg.wait_for_selector("body[data-ok='1']", timeout=60000)
        await pg.wait_for_timeout(500)
        lectura = RAIZ / "docs" / "manual_CTRL-04L.pdf"
        await pg.pdf(path=str(lectura), format="A5", print_background=True,
                     display_header_footer=True, header_template="<span></span>",
                     footer_template='<div style="width:100%;font:7pt Arial;text-align:center;color:#000"><span class="pageNumber"></span></div>',
                     margin={"top": "11mm", "bottom": "13mm", "left": "11mm", "right": "11mm"})
        await b.close()
    imponer(lectura, RAIZ / "docs" / "manual_CTRL-04L_cuadernillo.pdf")
    pagina.unlink()

asyncio.run(main())
