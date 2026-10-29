"""Hoja de contacto de las variantes de perilla (three.js + Edge headless) → perillas_variantes.png"""
import asyncio, base64
from pathlib import Path
from playwright.async_api import async_playwright

AQUI = Path(__file__).parent
S = AQUI / "salida_laser" / "perillas"
fs = sorted(S.glob("_*.stl"))
stl = {f.stem[1:]: base64.b64encode(f.read_bytes()).decode() for f in fs}

HTML = """<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#e9e7e2;font:600 22px system-ui;color:#333}
#g{display:grid;grid-template-columns:repeat(4,350px)}.c{position:relative}.c span{position:absolute;left:0;right:0;bottom:14px;text-align:center}</style></head><body><div id="g"></div>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three'; import {STLLoader} from 'three/addons/loaders/STLLoader.js';
const D=__DATA__, L=new STLLoader();
for(const [k,b64] of Object.entries(D)){
  const r=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true}); r.setSize(350,380); r.setPixelRatio(1);
  const sc=new THREE.Scene(); sc.background=new THREE.Color(0xe9e7e2);
  sc.add(new THREE.HemisphereLight(0xffffff,0x8a857c,1.5)); const l=new THREE.DirectionalLight(0xffffff,1.8); l.position.set(-40,-60,90); sc.add(l);
  const g=L.parse(Uint8Array.from(atob(b64),c=>c.charCodeAt(0)).buffer); g.computeVertexNormals(); g.center();
  sc.add(new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:0x9bd22a,roughness:.6})));
  const cam=new THREE.PerspectiveCamera(30,350/380,1,500); cam.up.set(0,0,1); cam.position.set(-24,-38,26); cam.lookAt(0,0,0.5);
  r.render(sc,cam);
  const d=document.createElement('div'); d.className='c'; d.appendChild(r.domElement);
  const s=document.createElement('span'); s.textContent=k.replace('_',' · '); d.appendChild(s); document.getElementById('g').appendChild(d);
}
document.body.dataset.ok=1;
</script></body></html>"""

async def main():
    pagina = AQUI / "_vista_perillas.html"
    pagina.write_text(HTML.replace("__DATA__", str(stl).replace("'", '"')), encoding="utf-8")
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", headless=True, args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        pg = await b.new_page(viewport={"width": 1400, "height": 760})
        await pg.goto(pagina.as_uri())
        await pg.wait_for_selector("body[data-ok='1']", timeout=120000)
        await pg.wait_for_timeout(800)
        await pg.screenshot(path=str(AQUI / "perillas_variantes.png"))
        await b.close()
    pagina.unlink()

asyncio.run(main())
