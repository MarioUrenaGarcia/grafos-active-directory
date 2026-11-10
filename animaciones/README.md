# Animaciones de la presentación

Fuente de las animaciones que se ven en la presentación de estudio
(`docs/presentacion/`). Cada animación es una composición HTML con GSAP en
`compositions/`, y [HyperFrames](https://hyperframes.heygen.com) la renderiza a
video. `index.html` monta todas las escenas una tras otra y `escenas.json`
guarda el inicio y la duración de cada una.

- `assets/lib/diagrama.js`: construcción de los diagramas (nodos, aristas que se
  trazan, cajas, fichas que viajan) con la paleta del proyecto.
- `assets/lib/red-flujo.js`: la red de ejemplo de las tres escenas de flujo; su
  corte mínimo se calculó con `cortes.plan_de_defensa` del proyecto.
- `assets/fonts/`: Bebas Neue con su licencia SIL Open Font License 1.1.

## Uso

Requiere Node.js 22 o superior y FFmpeg.

```bash
npx hyperframes@0.9.19 preview
```

```bash
python montar.py . logo,dominio,kerberos,sesion,anidados,acl,escalada,ciclo,defensor,adyacencia,bfs,inverso,dijkstra,warshall,tarjan,brandes,cortevertice,redflujo,aumento,corteminimo,arquitectura,web,visor
```

```bash
bash renderizar.sh . escalada defensor
```

`montar.py` vuelve a armar `index.html` y `escenas.json` a partir de la lista de
escenas; `renderizar.sh` renderiza cada escena indicada a `clips/<escena>.mp4`
usando sus tiempos. Los videos de la presentación se copian después a
`docs/presentacion/animaciones/`.
