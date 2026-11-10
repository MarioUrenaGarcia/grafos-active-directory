<p align="center">
  <img src="docs/media/logo.gif" width="360" alt="Logo animado: tres objetos con accesos hacia una diana roja, interrumpidos por una barra ámbar que representa el corte mínimo">
</p>

<h1 align="center">Rutas de acceso y defensa mínima en Active Directory</h1>

<p align="center">
  <b>Un directorio convertido en grafo: de las rutas que llegan al núcleo del dominio al plan de defensa más pequeño posible, con su demostración.</b>
</p>

<p align="center">
  <a href="docs/presentacion/index.html"><b>Presentación de estudio</b></a>
  &nbsp;|&nbsp;
  <a href="docs/visor.html"><b>Visor interactivo</b></a>
</p>

<p align="center">
  <sub>La web del proyecto se publica con GitHub Pages desde <code>docs/</code>. Su dirección está en el enlace <b>Website</b> del panel <b>About</b> del repositorio. Dentro del repositorio, GitHub muestra los archivos HTML como código: para verlos funcionando, abre la web o descarga el proyecto y abre los archivos en el navegador.</sub>
</p>

---

Proyecto final de Matemáticas Discretas. Modela un entorno de Active Directory
como un grafo dirigido y aplica algoritmos de teoría de grafos para pasar del
análisis de rutas de acceso al cálculo de un plan de defensa mínimo, con su
demostración.

El conjunto de datos es el entorno ficticio de demostración del ejemplo de
cybersecurity de Neo4j (basado en el proyecto BloodHound). Este proyecto no usa
Neo4j: carga los datos con Python y reimplementa desde cero cada algoritmo, de
modo que el porqué matemático de cada respuesta queda a la vista.

## Idea central

Cada objeto del directorio (usuario, equipo, grupo, dominio, GPO, OU) es un
vértice. Una arista dirigida `A -> B` significa que quien controla `A` puede
llegar a controlar `B`. Con esa semántica, toda ruta de un objeto cualquiera
hasta un objetivo de alto valor (por ejemplo el grupo de administradores del
dominio) es una posible vía de compromiso.

<p align="center">
  <img src="docs/media/escalada.gif" width="720" alt="Animación de una ruta real del conjunto de datos que se enciende en naranja hasta DOMAIN ADMINS">
  <br>
  <sub>Caso real del conjunto de datos: <code>CaronOstrye16 -EXECUTE_DCOM-&gt; COMP00045 -HAS_SESSION-&gt; PingFrankel165 -MEMBER_OF-&gt; DOMAIN ADMINS</code>, con su contexto (la OU NV_COMPUTERS, la GPO_13 y DOMAIN USERS). Es el camino de menor esfuerzo: peso 3 + 4 + 1 = 8 en 3 saltos.</sub>
</p>

El ejemplo original de Neo4j se detiene al mostrar esas rutas. Este proyecto
responde además la pregunta que sigue: cuál es el conjunto mínimo de accesos que
hay que revocar para que ninguna ruta llegue, y cómo se demuestra que es mínimo.
La respuesta sale del teorema de flujo máximo - corte mínimo y del teorema de
Menger.

El grafo tiene 953 vértices y 4698 aristas de 16 tipos de acceso. Hay 6
objetivos de alto valor: DOMAIN ADMINS, DOMAIN CONTROLLERS, ENTERPRISE DOMAIN
CONTROLLERS, ADMINISTRATORS, ENTERPRISE ADMINS y el propio dominio
TestCompany.Local.

## Contexto de seguridad

En un dominio de Active Directory, un intruso rara vez llega al núcleo de un
solo paso. Lo habitual es que empiece en una cuenta o un equipo de poco valor y
avance aprovechando relaciones legítimas del directorio: pertenencias a grupos,
derechos de administración sobre equipos, sesiones abiertas que dejan
credenciales en memoria y permisos sobre otros objetos (ACL). Cada uno de esos
pasos es una arista del grafo, así que una ruta de acceso es un camino y
defenderse equivale a cortar caminos.

<p align="center">
  <img src="docs/media/ciclo.gif" width="720" alt="Animación de las cinco fases de un compromiso a través de tres zonas de la red">
  <br>
  <sub>Tres zonas (estaciones de trabajo, servidores y núcleo del dominio de nivel 0) y cinco fases: punto de apoyo, reconocimiento, movimiento lateral, escalada y control del dominio. Grafo ilustrativo.</sub>
</p>

<table>
  <tr>
    <td width="50%"><img src="docs/media/dominio.gif" width="100%" alt="Animación del dominio con el controlador al centro y los objetos agrupados por tipo"></td>
    <td width="50%"><img src="docs/media/sesion.gif" width="100%" alt="Animación de una sesión que deja la credencial en el equipo y permite escalar"></td>
  </tr>
  <tr>
    <td><sub>El dominio TestCompany.Local: el controlador al centro y los objetos agrupados por tipo (300 usuarios, 301 equipos, 308 grupos, 21 OU, 22 GPO).</sub></td>
    <td><sub>Por qué una sesión es una arista: la credencial de PingFrankel165 queda en COMP00045 y quien controla el equipo llega a DOMAIN ADMINS.</sub></td>
  </tr>
</table>

El enfoque es conceptual y defensivo: el proyecto no ejecuta ninguna acción
sobre un dominio real, solo analiza un export ficticio para medir la exposición
y calcular qué accesos conviene revocar.

## Temas de matemáticas discretas y su algoritmo

| Pregunta | Tema | Algoritmo | Módulo |
|----------|------|-----------|--------|
| Si se compromete X, qué alcanza a controlar | Alcanzabilidad | BFS y DFS | `recorridos.py` |
| Quién puede llegar a un objetivo | Grafo inverso | BFS sobre aristas invertidas | `recorridos.py` |
| Ruta más corta a un objetivo | Caminos mínimos | BFS | `recorridos.py` |
| Ruta de menor esfuerzo | Grafos ponderados | Dijkstra | `caminos.py` |
| Núcleos de control mutuo | Componentes fuertemente conexas, grafo condensado (DAG) | Tarjan | `componentes.py` |
| Permisos efectivos por grupos anidados | Relación binaria y cerradura transitiva | Warshall con mapas de bits | `transitiva.py` |
| Objetos puente en las rutas | Centralidad de intermediación | Brandes | `centralidad.py` |
| Cuellos de botella de una ruta | Vértices de corte | Eliminación de nodo y recómputo de alcance | `cortes.py` |
| Plan de defensa mínimo | Flujo máximo, corte mínimo, teorema de Menger | Edmonds-Karp | `cortes.py` |
| Reducción de exposición | Comparación antes y después | Recorridos de alcance | `riesgo.py` |

### Recorridos y caminos mínimos

El grafo guarda dos listas de adyacencia, la de salida y la de entrada, de modo
que la misma BFS responde "qué alcanza X" (aristas de salida) y "quién llega a
X" (aristas de entrada). La BFS visita por niveles y el primer camino que
encuentra a cada objeto es uno de los de menos saltos. Todo recorrido cuesta
O(V + E).

<p align="center">
  <img src="docs/media/bfs.gif" width="720" alt="Animación de una búsqueda en anchura que avanza por niveles desde el nodo S">
  <br>
  <sub>BFS por niveles desde S: los nodos de la frontera se dibujan huecos y los expandidos, rellenos. La fila inferior es la cola en orden de descubrimiento (S A B C D E F G T) y al final se marca el camino mínimo S, A, E, T.</sub>
</p>

Dijkstra usa un montículo con borrado perezoso y una escala ordinal de esfuerzo
por tipo de acceso, definida en `pesos.py`:

| Peso | Tipos de acceso |
|------|-----------------|
| 1 | `MEMBER_OF`, `CONTAINS`, `ADMIN_TO`, `GENERIC_ALL`, `DC_SYNC`, `GET_CHANGES`, `GET_CHANGES_ALL` |
| 2 | `GP_LINK`, `OWNS`, `WRITE_DACL`, `WRITE_OWNER`, `GENERIC_WRITE` |
| 3 | `CAN_RDP`, `EXECUTE_DCOM`, `ALLOWED_TO_DELEGATE` |
| 4 | `HAS_SESSION` |

Los pesos ordenan el esfuerzo relativo de cada paso; no son probabilidades.

### Componentes fuertemente conexas

Dos objetos están en la misma componente cuando cada uno puede llegar al otro:
es un núcleo de control mutuo. Tarjan las encuentra en un solo recorrido en
profundidad (implementado de forma iterativa, con pila explícita) y el grafo de
componentes es siempre un DAG.

<p align="center">
  <img src="docs/media/tarjan.gif" width="720" alt="Animación del algoritmo de Tarjan coloreando componentes y condensando el grafo">
  <br>
  <sub>Grafo de 9 nodos: Tarjan cierra las componentes en el orden {f}, {d, e}, {g, h, i}, {a, b, c} y el grafo se condensa en un DAG de 4 supernodos.</sub>
</p>

En los datos hay 828 componentes y solo 2 no triviales: una de 125 objetos que
contiene a DOMAIN ADMINS, DOMAIN CONTROLLERS, ENTERPRISE DOMAIN CONTROLLERS y al
dominio, y otra de 2 grupos. El grafo condensado tiene 2180 aristas.

### Cerradura transitiva y centralidad

<p align="center">
  <img src="docs/media/anidados.gif" width="720" alt="Animación de grupos anidados y sus pertenencias efectivas">
  <br>
  <sub>Grupos anidados: la cadena de MEMBER_OF se enciende y aparecen en ámbar las pertenencias efectivas que agrega la cerradura transitiva (nombres ilustrativos).</sub>
</p>

- **Warshall con mapas de bits** se aplica a los 308 grupos: cada fila de la
  matriz es un entero de Python y la regla "si i llega a k, i hereda todo lo que
  alcanza k" se resuelve con un OR de bits.
- **Brandes** calcula la intermediación sobre el subgrafo de rutas hacia DOMAIN
  ADMINS (144 aristas). El objeto puente más importante es el equipo COMP00083,
  con 76.

## El plan de defensa mínimo

<p align="center">
  <img src="docs/media/defensor.gif" width="720" alt="Animación de las cuatro etapas del plan de defensa: medir, calcular el corte, revocar y verificar">
  <br>
  <sub>Medir (38 de 300 usuarios llegan a DOMAIN ADMINS), calcular el corte, revocar y verificar (0 de 300). Grafo ilustrativo con las cifras reales.</sub>
</p>

Se modela como un problema de flujo en una red:

1. Una superfuente `S` se conecta a todos los objetos de entrada considerados.
2. Todos los objetivos de alto valor se conectan a un supersumidero `T`.
3. Cada acceso revocable aporta capacidad. Los accesos estructurales del
   directorio (contención `CONTAINS` y vínculo de políticas `GP_LINK`) se tratan
   como no revocables, con capacidad infinita, porque un administrador no los
   elimina para defenderse.

Las aristas paralelas se agrupan por par ordenado de objetos: la capacidad del
par es el número de accesos revocables que lo unen (por ejemplo, 300 pares
grupo -> equipo tienen a la vez `ADMIN_TO` y `GENERIC_ALL`, y valen 2). Las
conexiones con `S` y con `T` también tienen capacidad infinita, que en el código
se representa como 2^30.

El flujo máximo de `S` a `T` se calcula con Edmonds-Karp: cada camino de aumento
es el más corto en la red residual, hallado con BFS, y aporta el valor de su
cuello de botella.

<p align="center">
  <img src="docs/media/aumento.gif" width="720" alt="Animación de Edmonds-Karp encontrando caminos de aumento uno a uno">
  <br>
  <sub>Edmonds-Karp: los caminos de aumento aparecen uno a uno, cada uno limitado por su cuello de botella; el flujo sube y los arcos que se llenan quedan saturados.</sub>
</p>

Por el teorema de flujo máximo - corte mínimo, el valor del flujo iguala el
tamaño del corte mínimo, y por el teorema de Menger ese número es la cantidad
máxima de rutas disjuntas en aristas. El corte (los arcos de capacidad finita
que salen del lado de `S` en la red residual) entrega la lista concreta de
accesos a revocar, y el teorema garantiza que no existe una lista más corta.
Además, tras revocar esos accesos se recorre de nuevo el grafo para comprobar de
forma independiente que ningún objeto de entrada alcanza ya el objetivo.

Resultado para DOMAIN ADMINS:

| Objetos de entrada | Corte mínimo | Expuestos antes | Expuestos después | Verificado |
|--------------------|--------------|-----------------|-------------------|------------|
| Usuarios (300) | 15 accesos | 38 (12.7 %) | 0 | Sí |
| Todos los que no son de alto valor (947) | 15 accesos | 142 (15.0 %) | 0 | Sí |

Con los usuarios como entrada, los 15 accesos son pertenencias directas
`MEMBER_OF` de usuarios a DOMAIN ADMINS, cuyo grado de entrada es exactamente 15.

Caso límite: si la única ruta hacia el objetivo es estructural, ningún conjunto
finito de accesos revocables la corta. El plan lo informa con un tamaño de corte
igual a 2^30 (1073741824), una lista de accesos vacía y la verificación en falso.

## Requisitos

- Python 3.10 o superior.
- Solo biblioteca estándar. No hay dependencias que instalar.
- Opcional: Jupyter y matplotlib, solo para abrir el cuaderno.

## Uso

Desde la carpeta del proyecto:

```bash
python main.py resumen
```

```bash
python main.py consultas
```

```bash
python main.py alcance --usuario "PiedadFlatley255@TestCompany.Local"
```

```bash
python main.py quien-llega --objetivo "DOMAIN ADMINS@TestCompany.Local"
```

```bash
python main.py camino --origen "PiedadFlatley255@TestCompany.Local" --destino "ENTERPRISE DOMAIN CONTROLLERS@TestCompany.Local"
```

```bash
python main.py permisos --usuario "PiedadFlatley255@TestCompany.Local"
```

```bash
python main.py scc
```

```bash
python main.py centralidad
```

```bash
python main.py cortes --origen "PiedadFlatley255@TestCompany.Local" --objetivo "ENTERPRISE DOMAIN CONTROLLERS@TestCompany.Local"
```

```bash
python main.py defensa --objetivo "DOMAIN ADMINS@TestCompany.Local"
```

```bash
python main.py reporte --salida reporte.html
```

```bash
python main.py visor --salida visor.html
```

| Subcomando | Qué hace | Opciones (valor por omisión) |
|------------|----------|------------------------------|
| `resumen` | Conteo de objetos y accesos por tipo y lista de objetivos de alto valor | - |
| `consultas` | Consultas reconstruidas del ejemplo original | `--limite` (15) |
| `alcance` | Todo lo que alcanza un objeto y cuáles son de alto valor | `--usuario` (obligatoria) |
| `quien-llega` | Objetos que pueden llegar a un objetivo, por tipo | `--objetivo` (DOMAIN ADMINS) |
| `camino` | Camino más corto (BFS) y de menor esfuerzo (Dijkstra) | `--origen`, `--destino` (obligatorias) |
| `scc` | Componentes fuertemente conexas y grafo condensado | `--limite` (5) |
| `permisos` | Grupos efectivos por cerradura transitiva | `--usuario` (obligatoria) |
| `centralidad` | Objetos puente por intermediación | `--objetivo` (DOMAIN ADMINS), `--limite` (15) |
| `cortes` | Vértices de corte entre un origen y un objetivo | `--origen` (obligatoria), `--objetivo` (DOMAIN ADMINS) |
| `defensa` | Plan de defensa mínimo y exposición antes y después | `--objetivo` (DOMAIN ADMINS), `--fuentes usuarios` o `todos` (usuarios) |
| `reporte` | Reporte HTML autocontenido | `--usuario` (PiedadFlatley255), `--objetivo` (DOMAIN ADMINS), `--salida` (reporte.html) |
| `visor` | Visor offline en un solo HTML | `--salida` (visor.html) |
| `servir` | Aplicación web interactiva | `--puerto` (8000), `--sin-abrir` |

`--datos RUTA` es una opción global que permite usar otro archivo de grafo en el
mismo formato. Va antes del subcomando:

```bash
python main.py --datos otra/ruta.json resumen
```

Un objeto se puede indicar por su identificador interno, por su nombre o por su
identificador de objeto (objectid). La excepción son `centralidad` y `reporte`,
cuyo `--objetivo` solo acepta el objectid; por omisión usan el de DOMAIN ADMINS.
Si un objeto no existe o los datos no se pueden leer, el programa imprime
`Error: ...` o un aviso equivalente y termina con código 1.

## Aplicación web interactiva

La forma recomendada de explorar el grafo es la aplicación web. Se levanta con:

```bash
python main.py servir
```

Esto arranca un servidor local (solo biblioteca estándar de Python, sin Flask ni
nada que instalar) y abre el navegador en `http://127.0.0.1:8000/`. El backend en
Python ejecuta cada algoritmo bajo demanda y la página reproduce su ejecución
paso a paso sobre el grafo.

El grafo se dibuja en un lienzo con una simulación de fuerzas escrita en
JavaScript, sin bibliotecas externas:

- **Conexiones al pasar el cursor:** al colocarse sobre un objeto se resaltan sus
  vecinos y los accesos que entran y salen de él, con flechas y partículas que
  avanzan en el sentido del control; el resto del grafo se atenúa. Con un clic
  el resaltado queda fijado hasta hacer clic en un espacio vacío o pulsar `Esc`.
- **Lectura de las aristas:** al pasar el cursor sobre una arista se muestra su
  tipo de acceso y lo que permite. La leyenda explica los colores de los objetos,
  los estilos de arista y los tipos de acceso, y resalta cada uno en el grafo.
- **Exploración:** los nodos se arrastran, la rueda del ratón acerca o aleja, el
  doble clic enfoca un objeto y el selector de disposición alterna entre la vista
  por fuerzas y la radial, donde cada objeto queda en el anillo de su distancia en
  saltos al objetivo.
- **Búsqueda y detalle:** el buscador ubica cualquier objeto por nombre y lo lleva
  al centro. Al elegir un objeto se abre una tarjeta con su tipo, su distancia al
  objetivo y la lista de lo que controla y de quien lo controla.
- **Reproducción:** la animación arranca al ejecutar y un reproductor con línea de
  tiempo permite pausar, retroceder, avanzar paso a paso, saltar al resultado y
  elegir la velocidad.
- **Atajos de teclado:** `/` busca, `Espacio` reproduce o pausa, las flechas
  avanzan o retroceden un paso, `Inicio` y `Fin` saltan al comienzo o al
  resultado, `E` ejecuta, `F` ajusta la vista, `+` y `-` acercan o alejan, `R`
  cambia la disposición y `P` oculta el panel.

Los algoritmos disponibles son:

- **BFS y Dijkstra:** se elige un objeto de origen con un clic y se ve crecer la
  frontera de la búsqueda y resaltarse el camino hallado. En Dijkstra se pueden
  ajustar los pesos de cada tipo de acceso.
- **Plan de defensa:** anima el algoritmo de flujo máximo encontrando los caminos
  de aumento uno a uno y termina mostrando en rojo el corte mínimo y en verde los
  objetos que quedan aislados del objetivo.

Para DOMAIN ADMINS, la página dibuja un subgrafo de 148 objetos (los 147 que
pueden llegar a él y el propio objetivo) y 601 accesos.

El servidor escucha solo en `127.0.0.1` y expone una API de lectura:
`/api/objetivos`, `/api/grafo`, `/api/bfs`, `/api/dijkstra` y `/api/defensa`.
Valida que los índices sean enteros dentro de rango y que los pesos de Dijkstra
sean números no negativos.

El puerto se cambia con `--puerto` y `--sin-abrir` evita abrir el navegador.

La guía visual de la interfaz (paleta, tipografía, logo, iconos, codificación del
grafo y animaciones) está en [DISENO.md](DISENO.md).

## Visor offline

El subcomando `visor` genera, como alternativa sin servidor, un único archivo
HTML autocontenido que se abre con doble clic y no requiere tener Python
corriendo. Usa la misma interfaz que la aplicación web, con la reproducción paso
a paso incluida: incrusta el grafo y un backend en JavaScript que responde las
mismas rutas que el servidor y calcula las trazas igual que `trazas.py`.

```bash
python main.py visor --salida visor.html
```

La web publica una copia en `docs/visor.html`, porque GitHub Pages solo sirve
archivos estáticos y no puede ejecutar el servidor de Python. Para regenerarla:

```bash
python main.py visor --salida docs/visor.html
```

El backend en JavaScript se comparó contra Python en 1789 consultas sin
diferencias. En el plan de defensa puede variar el número de caminos de aumento
mostrados, porque Python recorre un conjunto cuyo orden no está fijado, pero el
corte mínimo que se obtiene es el mismo.

## Presentación de estudio

`docs/presentacion/index.html` es una presentación pensada para entender el
proyecto completo, desde los fundamentos de Active Directory hasta el detalle de
cada algoritmo y de la implementación. Los temas principales se acompañan de
animaciones en video que muestran el concepto o el algoritmo sobre un grafo
pequeño o sobre un caso real de los datos.

- Se navega con las flechas, `Espacio`, `Re Pag` y `Av Pag`; `Inicio` y `Fin`
  van a la primera y a la última diapositiva.
- `I` abre el índice por partes y `Esc` lo cierra.
- La animación de la diapositiva activa arranca sola y el botón de su esquina la
  repite.
- El escenario de 1920 x 1080 se escala a cualquier ventana, y la dirección
  guarda el número de diapositiva para poder compartir un punto concreto.

## Cuaderno Jupyter

El archivo `demostracion.ipynb` recorre el proyecto paso a paso: carga el grafo,
explica cada algoritmo y lo ejecuta sobre los datos mostrando sus salidas y
gráficas (el subgrafo de rutas, un camino de acceso, la centralidad y el corte
mínimo). Importa el paquete `grafo_ad` y usa matplotlib para las figuras. Se
abre con Jupyter o con la extensión de notebooks de un editor:

```bash
jupyter notebook demostracion.ipynb
```

## Consultas reconstruidas del ejemplo original

El subcomando `consultas` reimplementa en Python las consultas del ejemplo de
Neo4j: sesiones activas, acceso directo a objetos de alto valor, equipos con
sesiones de varios usuarios, acceso RDP directo o heredado por grupos, objetos
de alto valor que alcanza un usuario y una ruta concreta hacia un objetivo. Son
la base sobre la que se construye el análisis de defensa.

Sobre los datos encuentran 264 sesiones activas, 30 accesos directos a objetos de
alto valor, 66 equipos con sesiones de varios usuarios y 118 accesos RDP (30
directos y 88 heredados a través de hasta tres niveles de grupos).

## Validación

La corrección se ancla a cifras conocidas del entorno. El usuario de referencia
(PiedadFlatley255) alcanza 928 objetos, de los cuales exactamente cuatro son de
alto valor (DOMAIN ADMINS, DOMAIN CONTROLLERS, ENTERPRISE DOMAIN CONTROLLERS y el
dominio), igual que reporta la guía del ejemplo original, y la ruta hacia el
grupo de controladores de dominio de la empresa reproduce la cadena descrita
allí:

```
PiedadFlatley255 -MEMBER_OF-> DOMAIN ADMINS -ADMIN_TO-> FLLABDC -MEMBER_OF-> ENTERPRISE DOMAIN CONTROLLERS
```

Para ejecutar la batería de pruebas:

```bash
python -m unittest discover -s pruebas
```

Son 29 pruebas:

- `test_algoritmos.py` (12): cada algoritmo sobre grafos sintéticos pequeños,
  incluido el caso de una ruta solo estructural.
- `test_datos.py` (4): las cifras del conjunto de datos real y la defensa de
  DOMAIN ADMINS verificada con exposición 0 después del corte.
- `test_trazas.py` (6): las trazas que reproduce la web y la disposición radial.
- `test_visor.py` (7): la página compartida, la fuente incrustada, los iconos, el
  backend del visor y el escape de los datos incrustados.

## Cómo se hicieron las animaciones

<p align="center">
  <img src="docs/media/logo.gif" width="480" alt="Animación del logo armándose: tres objetos, sus accesos, la diana roja y la barra ámbar del corte">
  <br>
  <sub>Se arma el logo: tres objetos con accesos hacia una diana roja y la barra ámbar del corte mínimo.</sub>
</p>

Las animaciones de la presentación se hicieron con HyperFrames, que convierte
páginas HTML en video. Cada animación es una composición HTML cuyo movimiento
se describe con una línea de tiempo de GSAP. Para renderizarla, HyperFrames abre
la composición en un navegador sin interfaz, la avanza cuadro a cuadro y
codifica los cuadros a video.

- La fuente de las composiciones está en `animaciones/`.
- Los videos MP4 renderizados están en `docs/presentacion/animaciones/`.
- Los GIF de este documento y de la portada de la web, en `docs/media/`, son
  versiones cortas y reducidas de esos mismos videos.

Regenerar los videos requiere Node.js 22 o superior y FFmpeg. Los comandos se
ejecutan dentro de `animaciones/`: el primero abre una vista previa de todas las
escenas y el segundo renderiza las escenas indicadas a `clips/`. El detalle está
en `animaciones/README.md`.

```bash
npx hyperframes@0.9.19 preview
```

```bash
bash renderizar.sh . escalada defensor
```

Nada de esto es necesario para usar el analizador, que sigue dependiendo solo de
Python.

## Estructura

```
README.md            Este documento.
DISENO.md            Documento de diseño de la interfaz.
main.py              Punto de entrada.
grafo_ad/
  modelo.py          Carga del JSON y grafo dirigido con adyacencia directa e inversa.
  recorridos.py      BFS, DFS, alcanzabilidad y caminos más cortos.
  caminos.py         Dijkstra para caminos de menor esfuerzo.
  pesos.py           Modelo de pesos por tipo de acceso.
  componentes.py     Componentes fuertemente conexas (Tarjan) y grafo condensado.
  transitiva.py      Cerradura transitiva de la pertenencia a grupos (Warshall).
  centralidad.py     Subgrafo de rutas y centralidad de intermediación (Brandes).
  cortes.py          Vértices de corte y plan de defensa mínimo (Edmonds-Karp).
  riesgo.py          Métricas de exposición antes y después.
  consultas.py       Reimplementación de las consultas del ejemplo original.
  trazas.py          Algoritmos instrumentados que registran su ejecución.
  reporte.py         Reporte HTML autocontenido.
  visor.py           Generador del visor offline.
  interfaz_web.py    Página de la aplicación web (HTML, CSS, JavaScript, iconos y logo).
  recursos/          Fuente de los títulos (Bebas Neue) y su licencia OFL.
  servidor.py        Servidor web con la API de análisis.
  cli.py             Interfaz de línea de comandos.
pruebas/             Pruebas unitarias y de integración.
data/                Conjunto de datos (cybersecurity-json-data.json).
demostracion.ipynb   Cuaderno Jupyter que recorre el proyecto.
diseno/
  logo.svg           Logo.
  iconos.svg         Hoja de iconos de la interfaz.
animaciones/         Fuente HyperFrames de las animaciones (composiciones HTML con GSAP y
                     los scripts para montarlas y renderizarlas).
docs/                Web del proyecto, publicada con GitHub Pages.
  index.html         Portada.
  presentacion/
    index.html       Presentación de estudio.
    animaciones/     Videos MP4 de las animaciones.
    recursos/        Logo, fuente Bebas Neue y su licencia OFL.
  visor.html         Visor interactivo offline.
  media/             GIF animados del README y de la portada.
```

El cuaderno usa matplotlib solo para sus gráficas; el paquete `grafo_ad` no
tiene dependencias externas.

## Datos y fuente

Los datos provienen del ejemplo de cybersecurity de Neo4j
(`neo4j-graph-examples/cybersecurity`) y describen un entorno de Active Directory
ficticio creado para demostración. El export JSON contiene 953 vértices y 4698
aristas; la documentación del ejemplo cita 4858 relaciones, cifra que no coincide
con el archivo JSON publicado y que aquí se toma directamente del archivo. El
análisis de este proyecto es de carácter académico y defensivo: su objetivo es
cuantificar y reducir la exposición de un entorno.

Los títulos de la interfaz, la presentación y la web usan Bebas Neue (Dharma
Type), distribuida bajo la SIL Open Font License 1.1; el texto de la licencia
acompaña a cada copia de la fuente.
