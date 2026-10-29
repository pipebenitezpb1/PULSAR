"""CTRL-04L con la tapa: abierta y cerrada → tapa_vistas.png"""
import asyncio, base64
from pathlib import Path
from playwright.async_api import async_playwright
from perillas_buzz import VARIANTES

AQUI = Path(__file__).parent
S = AQUI / "salida_laser"
B = S / "perillas_buzz"
f = [("c", S / "CTRL-04L_1_caja.stl"), ("a", S / "CTRL-04L_acrilico_3mm.stl"), ("m", S / "CTRL-04L_3_marco_oled.stl"),
     ("r", S / "_referencia_componentes.stl"), ("l", S / "_laminas_montadas.stl"), ("u", S / "_funda_usb_montada.stl")]
f += [(f"t{i}", S / f"_tapa_boton_{i}.stl") for i in range(4)]
f += [("H_cuerpo", B / "_mont_H_ala_cuerpo.stl"), ("H_acento", B / "_mont_H_ala_acento.stl"), ("tc", S / "_tapa_montada_cuerpo.stl"), ("ta", S / "_tapa_montada_acento.stl")]
stl = {k: base64.b64encode(p.read_bytes()).decode() for k, p in f}
COL = {"lima": 0x9bd22a, "indigo": 0x3d2c8d, "blanco": 0xf2efe8}
var = [{"t": "TAPA ABIERTA", "z": 34}, {"t": "TAPA PUESTA", "z": 0}]

HTML = """<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#e9e7e2;font:700 26px system-ui;color:#3d2c8d}
#g{display:grid;grid-template-columns:repeat(2,700px)}.c{position:relative}.c span{position:absolute;left:24px;top:18px;letter-spacing:.08em}</style></head><body><div id="g"></div>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three'; import {STLLoader} from 'three/addons/loaders/STLLoader.js';
const D=__DATA__, V=__VAR__, L=new STLLoader();
const geo=k=>{const g=L.parse(Uint8Array.from(atob(D[k]),c=>c.charCodeAt(0)).buffer); g.computeVertexNormals(); return g};
const M=(c,r=.6,e={})=>new THREE.MeshStandardMaterial(Object.assign({color:c,roughness:r},e));
for(const v of V){
  const r=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true}); r.setSize(700,560); r.setPixelRatio(1);
  const sc=new THREE.Scene(); sc.background=new THREE.Color(0xe9e7e2);
  sc.add(new THREE.HemisphereLight(0xffffff,0x8a857c,1.6)); const l=new THREE.DirectionalLight(0xffffff,1.7); l.position.set(-80,-120,200); sc.add(l);
  const add=(k,m)=>sc.add(new THREE.Mesh(geo(k),m));
  add('c',M(0x9bd22a)); add('u',M(0x9bd22a)); add('m',M(0x3d2c8d)); add('r',M(0x1d1d22,.8));
  add('a',M(0x0b0b0d,.12,{metalness:.1}));
  add('l',M(0xf4ffe0,.6,{emissive:0x9bd22a,emissiveIntensity:.6,transparent:true,opacity:.92}));
  [0xd32f2f,0x1e6fd9,0xf2efe8,0xf5c518].forEach((c,i)=>add('t'+i,M(c,.45)));
  add('H_cuerpo',M(0x3d2c8d,.5)); add('H_acento',M(0x9bd22a,.45));
  for (const [k,col] of [['tc',0x3d2c8d],['ta',0x9bd22a]]) { const o=new THREE.Mesh(geo(k),M(col,.5)); o.position.z=v.z; sc.add(o); }
  const cam=new THREE.PerspectiveCamera(30,700/560,1,2000); cam.up.set(0,0,1); cam.position.set(-40,-150,150); cam.lookAt(46,52,22);
  r.render(sc,cam);
  const d=document.createElement('div'); d.className='c'; d.appendChild(r.domElement);
  const s=document.createElement('span'); s.textContent=v.t; d.appendChild(s); document.getElementById('g').appendChild(d);
}
document.body.dataset.ok=1;
</script></body></html>"""

async def main():
    pagina = AQUI / "_vista_tapa.html"
    pagina.write_text(HTML.replace("__DATA__", str(stl).replace("'", '"')).replace("__VAR__", str(var).replace("'", '"')), encoding="utf-8")
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", headless=True, args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        pg = await b.new_page(viewport={"width": 1400, "height": 560})
        await pg.goto(pagina.as_uri())
        await pg.wait_for_selector("body[data-ok='1']", timeout=180000)
        await pg.wait_for_timeout(800)
        await pg.screenshot(path=str(AQUI / "tapa_vistas.png"))
        await b.close()
    pagina.unlink()

asyncio.run(main())
