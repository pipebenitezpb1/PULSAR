"""Genera docs/manual_CTRL-04L.pdf (A4, blanco y negro, para imprimir) a partir de MANUAL.md, con Edge headless."""
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

RAIZ = Path(__file__).resolve().parent.parent
md = (RAIZ / "MANUAL.md").read_text(encoding="utf-8")
md = md.split("## Índice", 1)[1].split("---", 1)[1]           # sin el título ni el índice: van en la portada
fuentes = (RAIZ / "dashboard" / "fonts" / "fonts.css").as_uri()

HTML = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<link rel="stylesheet" href="__FUENTES__">
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
<style>
  @page { size: A4; margin: 16mm 15mm 18mm; }
  * { box-sizing: border-box; }
  html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { margin: 0; color: #000; font: 10.5pt/1.45 'Barlow', Arial, sans-serif; }
  img { filter: grayscale(1) contrast(1.1); max-width: 100%; }
  h1, h2, h3 { font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif; text-transform: uppercase; letter-spacing: .02em; break-after: avoid; }
  h2 { font-size: 20pt; margin: 22pt 0 8pt; padding: 3pt 0 4pt; border-top: 3pt solid #000; border-bottom: 1pt solid #000; }
  h3 { font-size: 13pt; margin: 14pt 0 4pt; }
  p, li { margin: 4pt 0; }
  ul, ol { padding-left: 16pt; }
  table { width: 100%; border-collapse: collapse; margin: 6pt 0 10pt; break-inside: avoid; font-size: 9.5pt; }
  th, td { border: 1pt solid #000; padding: 3pt 6pt; text-align: left; vertical-align: top; }
  th { background: #e6e6e6; font-family: 'Barlow Condensed', 'Arial Narrow', sans-serif; font-size: 10.5pt; text-transform: uppercase; }
  blockquote { margin: 8pt 0; padding: 5pt 10pt; border-left: 3pt solid #000; background: #f0f0f0; }
  blockquote p { margin: 0; }
  code { font-family: 'Space Mono', Consolas, monospace; font-size: 9pt; }
  pre { border: 1pt solid #000; padding: 6pt 8pt; background: #f0f0f0; break-inside: avoid; }
  hr { display: none; }
  .junto { break-inside: avoid; }
  a { color: #000; text-decoration: none; }
  /* portada */
  .portada { height: 260mm; display: flex; flex-direction: column; break-after: page; }
  .portada .marca { font: 400 9pt 'Space Mono', monospace; letter-spacing: .14em; border-bottom: 2pt solid #000; padding-bottom: 4pt; }
  .portada h1 { font-size: 64pt; line-height: .9; margin: 18mm 0 4mm; }
  .portada .sub { font: 600 16pt 'Barlow Condensed', sans-serif; text-transform: uppercase; }
  .portada img { margin: 10mm auto 0; width: 150mm; }
  .portada .indice { margin-top: auto; columns: 2; font-size: 10pt; border-top: 2pt solid #000; padding-top: 6pt; }
  .portada .indice div { break-inside: avoid; padding: 1.5pt 0; }
  .portada .pie { font: 9pt 'Space Mono', monospace; margin-top: 6pt; }
  /* la tarjeta rápida: página propia, recortable */
  .tarjeta { break-before: page; }
  .tarjeta table { border: 2.5pt solid #000; font-size: 12pt; }
  .tarjeta td { padding: 6pt 10pt; }
  .tarjeta .tijera { font: 9pt 'Space Mono', monospace; margin-top: 6pt; }
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
  t.insertAdjacentHTML("beforeend", '<div class="tijera">✂ Recorta esta tarjeta y déjala junto a la caja.</div>');
  document.body.dataset.ok = 1;
</script></body></html>"""

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
        await pg.pdf(path=str(RAIZ / "docs" / "manual_CTRL-04L.pdf"), format="A4", print_background=True,
                     display_header_footer=True, header_template="<span></span>",
                     footer_template='<div style="width:100%;font:8pt Arial;text-align:center;color:#000">CTRL-04L · Manual de uso · <span class="pageNumber"></span> / <span class="totalPages"></span></div>',
                     margin={"top": "16mm", "bottom": "18mm", "left": "15mm", "right": "15mm"})
        await b.close()
    pagina.unlink()

asyncio.run(main())
