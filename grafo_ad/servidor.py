"""Servidor web del analizador, construido con la biblioteca estandar.

Carga el grafo una vez y expone una pequena API JSON que ejecuta los algoritmos
instrumentados bajo demanda. Cada peticion corre el algoritmo real en Python y
devuelve su traza; la pagina la reproduce paso a paso. No hay dependencias
externas: solo http.server, json y threading.

La escucha se limita a 127.0.0.1 (solo la maquina local), ya que la aplicacion
es una herramienta de analisis sin estado compartido ni escritura de datos.
"""

from __future__ import annotations

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .cortes import TIPOS_ESTRUCTURALES
from .interfaz_web import PAGINA
from .modelo import Grafo, OBJECTID_DOMAIN_ADMINS, cargar_json
from .trazas import (bfs_traza, defensa_traza, dijkstra_traza, layout_radial,
                     subgrafo_objetivo)


class _Contexto:
    """Estado compartido del servidor: el grafo y los indices de nodos."""

    def __init__(self, grafo: Grafo) -> None:
        self.grafo = grafo
        self.ids = list(grafo.nodos.keys())
        self.idx = {nid: i for i, nid in enumerate(self.ids)}

    def objetivos(self) -> list[dict]:
        return [
            {"i": self.idx[n.id], "nombre": n.nombre}
            for n in self.grafo.altos_valores()
        ]

    def objetivo_por_omision(self) -> int:
        da = self.grafo.buscar_por_objectid(OBJECTID_DOMAIN_ADMINS)
        if da is not None:
            return self.idx[da.id]
        return self.objetivos()[0]["i"]

    def grafo_payload(self, objetivo_i: int) -> dict:
        objetivo_id = self.ids[objetivo_i]
        permitidos = subgrafo_objetivo(self.grafo, objetivo_id)
        pos = layout_radial(self.grafo, objetivo_id, permitidos)
        nodos = []
        for nid in permitidos:
            n = self.grafo.nodos[nid]
            x, y = pos.get(nid, (0.0, 0.0))
            nodos.append({
                "i": self.idx[nid], "nombre": n.nombre, "tipo": n.tipo,
                "hv": 1 if n.alto_valor else 0, "x": round(x, 2), "y": round(y, 2),
            })
        aristas = [
            [self.idx[a.origen], self.idx[a.destino], a.tipo]
            for a in self.grafo.aristas
            if a.origen in permitidos and a.destino in permitidos
        ]
        usuarios = [self.idx[n.id] for n in self.grafo.por_tipo("User") if n.id in permitidos]
        return {
            "objetivo": objetivo_i,
            "objetivoNombre": self.grafo.nodos[objetivo_id].nombre,
            "nodos": nodos,
            "aristas": aristas,
            "usuarios": usuarios,
            "totalNodos": len(permitidos),
        }

    def fuentes(self, objetivo_id: str, permitidos: set[str], modo: str) -> list[str]:
        if modo == "todos":
            return [n for n in permitidos if not self.grafo.nodos[n].alto_valor]
        return [n.id for n in self.grafo.por_tipo("User") if n.id in permitidos]


class _Manejador(BaseHTTPRequestHandler):
    contexto: _Contexto = None  # se asigna antes de servir

    def log_message(self, formato, *args):
        # Silencia el registro por peticion para no ensuciar la consola.
        pass

    def _responder_json(self, datos, codigo=200):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _responder_html(self, texto):
        cuerpo = texto.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def _entero(self, params, clave, minimo, maximo):
        """Lee y valida un parametro entero dentro de un rango."""
        valores = params.get(clave)
        if not valores:
            raise ValueError(f"Falta el parámetro {clave}")
        try:
            v = int(valores[0])
        except (TypeError, ValueError):
            raise ValueError(f"El parámetro {clave} no es un entero")
        if not (minimo <= v <= maximo):
            raise ValueError(f"El parámetro {clave} está fuera de rango")
        return v

    def do_GET(self):
        ctx = self.contexto
        ruta = urlparse(self.path)
        params = parse_qs(ruta.query)
        n = len(ctx.ids)
        try:
            if ruta.path == "/" or ruta.path == "/index.html":
                self._responder_html(PAGINA)
                return
            if ruta.path == "/api/objetivos":
                self._responder_json({
                    "objetivos": ctx.objetivos(),
                    "porOmision": ctx.objetivo_por_omision(),
                })
                return
            if ruta.path == "/api/grafo":
                obj = self._entero(params, "objetivo", 0, n - 1)
                self._responder_json(ctx.grafo_payload(obj))
                return
            if ruta.path in ("/api/bfs", "/api/dijkstra"):
                obj = self._entero(params, "objetivo", 0, n - 1)
                org = self._entero(params, "origen", 0, n - 1)
                objetivo_id = ctx.ids[obj]
                origen_id = ctx.ids[org]
                permitidos = subgrafo_objetivo(ctx.grafo, objetivo_id)
                if origen_id not in permitidos:
                    raise ValueError("El origen no alcanza el objetivo")
                if ruta.path == "/api/bfs":
                    datos = bfs_traza(ctx.grafo, ctx.idx, permitidos, origen_id, objetivo_id)
                else:
                    pesos = self._pesos(params)
                    datos = dijkstra_traza(ctx.grafo, ctx.idx, permitidos,
                                           origen_id, objetivo_id, pesos)
                self._responder_json(datos)
                return
            if ruta.path == "/api/defensa":
                obj = self._entero(params, "objetivo", 0, n - 1)
                modo = (params.get("fuentes", ["usuarios"])[0])
                if modo not in ("usuarios", "todos"):
                    modo = "usuarios"
                objetivo_id = ctx.ids[obj]
                permitidos = subgrafo_objetivo(ctx.grafo, objetivo_id)
                fuentes = ctx.fuentes(objetivo_id, permitidos, modo)
                datos = defensa_traza(ctx.grafo, ctx.idx, permitidos, objetivo_id,
                                      fuentes, TIPOS_ESTRUCTURALES)
                self._responder_json(datos)
                return
            self._responder_json({"error": "ruta no encontrada"}, 404)
        except ValueError as exc:
            self._responder_json({"error": str(exc)}, 400)

    def _pesos(self, params):
        """Lee un posible mapa de pesos personalizado del parametro pesos."""
        crudo = params.get("pesos")
        if not crudo:
            return None
        try:
            datos = json.loads(crudo[0])
        except json.JSONDecodeError:
            raise ValueError("El parámetro pesos no es JSON válido")
        if not isinstance(datos, dict):
            raise ValueError("El parámetro pesos debe ser un objeto")
        limpio = {}
        for clave, valor in datos.items():
            if not isinstance(valor, (int, float)) or valor < 0:
                raise ValueError("Los pesos deben ser números no negativos")
            limpio[str(clave)] = int(valor)
        return limpio


def iniciar(ruta_datos: str, puerto: int = 8000, abrir: bool = True) -> None:
    """Carga el grafo y arranca el servidor en el puerto indicado."""
    grafo = cargar_json(ruta_datos)
    _Manejador.contexto = _Contexto(grafo)
    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), _Manejador)
    url = f"http://127.0.0.1:{puerto}/"
    print(f"Servidor activo en {url}")
    print(f"Grafo cargado: {len(grafo)} objetos, {len(grafo.aristas)} accesos.")
    print("Presiona Ctrl+C para detener.")
    if abrir:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nDeteniendo el servidor.")
        servidor.shutdown()
