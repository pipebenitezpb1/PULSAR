"""Vistas previas del CTRL-04 (three.js + Edge headless) → vista_*.png"""
import asyncio, base64, os
VARIANTE = os.environ.get('VARIANTE', '')   # '' = ladrillo con puntitos; 'lima' / 'naranja' = filamento liso
from pathlib import Path
from playwright.async_api import async_playwright

AQUI = Path(__file__).parent
S = AQUI / "salida_laser"
stl = {k: base64.b64encode((S / f).read_bytes()).decode() for k, f in
       [("c", "CTRL-04L_1_caja.stl"), ("a", "CTRL-04L_acrilico_3mm.stl"), ("m", "CTRL-04L_3_marco_oled.stl"), ("r", "_referencia_componentes.stl"), ("l", "_laminas_montadas.stl")] + [(f"t{i}", f"_tapa_boton_{i}.stl") for i in range(4)] + [("k", "_perillas_montadas.stl"), ("u", "_funda_usb_montada.stl")]}

HTML = """<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#e9e7e2}</style></head><body>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three'; import {STLLoader} from 'three/addons/loaders/STLLoader.js';
const D=__DATA__, q=new URLSearchParams(location.search), vista=q.get('v');
const r=new THREE.WebGLRenderer({antialias:true}); r.setSize(1400,950); r.setPixelRatio(1); document.body.appendChild(r.domElement);
const sc=new THREE.Scene(); sc.background=new THREE.Color(0xe9e7e2);
sc.add(new THREE.HemisphereLight(0xffffff,0x8a857c,1.6)); const l=new THREE.DirectionalLight(0xffffff,1.6); l.position.set(-80,-120,200); sc.add(l);
const L=new STLLoader(); const geo=k=>L.parse(Uint8Array.from(atob(D[k]),c=>c.charCodeAt(0)).buffer);
const m=(k,col,op=1)=>{const g=geo(k);g.computeVertexNormals();const o=new THREE.Mesh(g,new THREE.MeshStandardMaterial({color:col,roughness:.7,transparent:op<1,opacity:op}));sc.add(o);return o};
const pecas=(mat)=>{mat.onBeforeCompile=(sh)=>{
  sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\\nvarying vec3 vWP;').replace('#include <worldpos_vertex>','#include <worldpos_vertex>\\nvWP=(modelMatrix*vec4(transformed,1.0)).xyz;');
  sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\\nvarying vec3 vWP;\\nfloat h3(vec3 p){return fract(sin(dot(p,vec3(12.9898,78.233,37.719)))*43758.5453);}').replace('#include <color_fragment>','#include <color_fragment>\\nif(h3(floor(vWP*2.2))>0.93) diffuseColor.rgb*=0.18;');
 }; return mat;};
const filamento=()=>__FIL__;
const mm=(k,mat)=>{const g=geo(k);g.computeVertexNormals();const o=new THREE.Mesh(g,mat);sc.add(o);return o};
const ca=mm('c',filamento()), ba=mm('m',filamento()), tu=mm('u',filamento()), re=m('r',0x2f8f46);
const ac=mm('a',new THREE.MeshStandardMaterial({color:0x0b0b0d,roughness:.12,metalness:.1}));
[0xd32f2f,0x1e6fd9,0xf2efe8,0xf5c518].forEach((c,i)=>mm('t'+i,new THREE.MeshStandardMaterial({color:c,roughness:.45})));
const pk=mm('k',new THREE.MeshStandardMaterial({color:0xefece4,roughness:.5}));
const la=mm('l',new THREE.MeshStandardMaterial({color:0xfff4ea,emissive:0xff7a3d,emissiveIntensity:.55,roughness:.6,transparent:true,opacity:.92}));
if(vista==='abierta'){ba.position.z=48; la.position.z=34; ac.position.z=20; pk.position.z=62;}
const cam=new THREE.PerspectiveCamera(30,1400/950,1,2000); cam.up.set(0,0,1);
const P={frente:[[52,-215,185],[52,56,8]],atras:[[200,330,140],[52,60,8]],abierta:[[-140,-240,230],[52,56,12]],lado:[[-150,-60,60],[52,62,20]]}[vista];
cam.position.set(...P[0]); cam.lookAt(...P[1]); r.render(sc,cam); document.body.dataset.ok=1;
</script></body></html>"""

async def main():
    pagina = AQUI / "_vista.html"
    LISOS = {"lima": "0x9bd22a", "naranja": "0xf26a1b", "negro": "0x1c1c1e", "crema": "0xe8dfc8",
             "azul": "0x1f3a6b", "menta": "0x7fd1b4", "morado": "0x6a3fa0", "amarillo": "0xf2b705", "rosado": "0xf08fb0"}
    PECAS = {"": "0xa9502f", "granito": "0x8f8f8c", "terrazo": "0xece6da", "arena": "0xc9a875"}   # con puntitos negros
    fil = (f"new THREE.MeshStandardMaterial({{color:{LISOS[VARIANTE]},roughness:.6}})" if VARIANTE in LISOS
           else f"pecas(new THREE.MeshStandardMaterial({{color:{PECAS[VARIANTE]},roughness:.85}}))")
    pagina.write_text(HTML.replace("__DATA__", str(stl).replace("'", '"')).replace("__FIL__", fil), encoding="utf-8")
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="msedge", headless=True, args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        pg = await b.new_page(viewport={"width": 1400, "height": 950})
        for v in os.environ.get("VISTAS", "frente,atras,abierta,lado").split(","):
            await pg.goto(pagina.as_uri() + f"?v={v}")
            await pg.wait_for_selector("body[data-ok='1']", timeout=120000)
            await pg.wait_for_timeout(800)
            await pg.screenshot(path=str(AQUI / (f"vistaL_{VARIANTE}_{v}.png" if VARIANTE else f"vistaL_{v}.png")))
        await b.close()
    pagina.unlink()

asyncio.run(main())
