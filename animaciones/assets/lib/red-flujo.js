/* Red de ejemplo para las tres escenas de flujo. Su corte minimo se calculo
   con cortes.plan_de_defensa del proyecto: 3 accesos (u3 -> ou, c -> b2 y
   g -> b1), verificado. Los caminos de aumento son los que encuentra el BFS de
   Edmonds-Karp sobre esta red. */
(function () {
  "use strict";
  const INF = "∞";
  window.RED_FLUJO = {
    nodos: [
      ["S", 110, 480, { color: "#11263f", r: 30, etiqueta: "S", etqArriba: true }],
      ["u1", 330, 200, { tipo: "User", r: 22, etiqueta: "u1", etqArriba: true }],
      ["u2", 330, 400, { tipo: "User", r: 22, etiqueta: "u2", etqArriba: true }],
      ["u3", 330, 620, { tipo: "User", r: 22, etiqueta: "u3", etqArriba: true }],
      ["u4", 330, 820, { tipo: "User", r: 22, etiqueta: "u4" }],
      ["g", 620, 300, { tipo: "Group", r: 24, etiqueta: "g", etqArriba: true }],
      ["c", 620, 560, { tipo: "Computer", r: 24, etiqueta: "c" }],
      ["ou", 620, 820, { tipo: "OU", r: 22, etiqueta: "ou" }],
      ["b1", 900, 240, { tipo: "User", r: 22, etiqueta: "b1", etqArriba: true }],
      ["b2", 900, 480, { tipo: "User", r: 22, etiqueta: "b2", etqArriba: true }],
      ["b3", 900, 720, { tipo: "User", r: 22, etiqueta: "b3" }],
      ["DA", 1180, 480, { tipo: "objetivo", r: 36, etiqueta: "DOMAIN ADMINS", etqArriba: true }],
      ["T", 1440, 480, { color: "#11263f", r: 30, etiqueta: "T", etqArriba: true }],
    ],
    // [origen, destino, capacidad, tipo de arista]
    aristas: [
      ["S", "u1", INF, "super"], ["S", "u2", INF, "super"], ["S", "u3", INF, "super"], ["S", "u4", INF, "super"],
      ["u1", "g", "1", "MEMBER_OF"], ["u2", "g", "1", "MEMBER_OF"], ["u2", "c", "1", "CAN_RDP"],
      ["u3", "ou", "1", "GENERIC_ALL"], ["u4", "c", "1", "EXECUTE_DCOM"],
      ["g", "c", "2", "ADMIN_TO + GENERIC_ALL"], ["g", "b1", "1", "GENERIC_ALL"], ["c", "b2", "1", "HAS_SESSION"],
      ["ou", "b3", INF, "CONTAINS"],
      ["b1", "DA", "1", "MEMBER_OF"], ["b2", "DA", "1", "MEMBER_OF"], ["b3", "DA", "1", "MEMBER_OF"],
      ["DA", "T", INF, "super"],
    ],
    caminos: [
      ["S", "u1", "g", "b1", "DA", "T"],
      ["S", "u2", "c", "b2", "DA", "T"],
      ["S", "u3", "ou", "b3", "DA", "T"],
    ],
    lado: ["S", "u1", "u2", "u3", "u4", "g", "c"],
    corte: [["g", "b1"], ["c", "b2"], ["u3", "ou"]],
  };

  // Dibuja la red completa en un diagrama y devuelve accesos por clave "a-b".
  window.construirRed = function (d, prefijo, o = {}) {
    const R = window.RED_FLUJO;
    d.desde(R.nodos.map(([id, x, y, op]) => [`${prefijo}-${id}`, x, y, op]));
    const A = {};
    R.aristas.forEach(([a, b, cap, tipo]) => {
      const sup = tipo === "super", est = tipo === "CONTAINS";
      A[`${a}-${b}`] = d.arista(`${prefijo}-${a}-${b}`, `${prefijo}-${a}`, `${prefijo}-${b}`, {
        ancho: sup ? 2.5 : 4, color: sup ? "#9aa7b8" : est ? "#b8c2d0" : "#33496b",
        etiqueta: o.conCapacidad ? cap : null, etqClase: "etq-cap", etqLado: 20,
      });
    });
    return A;
  };
})();
