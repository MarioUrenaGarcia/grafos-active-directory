"""Arma index.html con las escenas en secuencia y escribe escenas.json con sus tiempos."""
import json, os, re, sys
os.chdir(sys.argv[1])
escenas = []
for nombre in sys.argv[2].split(","):
    t = open(f"compositions/{nombre}.html", encoding="utf-8").read()
    dur = float(re.search(r'class="clip" data-start="0" data-duration="([\d.]+)"', t).group(1))
    escenas.append((nombre, dur))
hosts, t = [], 0.0
tiempos = []
for nombre, dur in escenas:
    hosts.append(f'''      <div id="{nombre}" data-composition-id="{nombre}" data-composition-src="compositions/{nombre}.html"
           data-start="{t:g}" data-duration="{dur:g}" data-track-index="1" data-track-kind="graphics"
           data-width="1600" data-height="1000"></div>''')
    tiempos.append({"escena": nombre, "inicio": t, "duracion": dur})
    t += dur
html = open("index.html", encoding="utf-8").read()
inicio = html.index('<div id="root"')
fin = html.index("    <script>\n      window.__timelines")
raiz = f'''<div id="root" data-composition-id="main" data-start="0" data-duration="{t:g}"
         data-width="1600" data-height="1000">
{chr(10).join(hosts)}
    </div>
'''
open("index.html", "w", encoding="utf-8").write(html[:inicio] + raiz + html[fin:])
json.dump(tiempos, open("escenas.json", "w"), indent=1)
# Instantes de revision: mitad y final de cada escena.
print(",".join(f"{e['inicio'] + e['duracion'] * 0.5:.2f},{e['inicio'] + e['duracion'] - 0.3:.2f}" for e in tiempos))
