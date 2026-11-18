"""v6: cuadros donde el presentador mira abajo (celular) y que quedan a la vista (no tapados por un corte). Uso: revisar6.py mirada.json plan.json [umbral]"""
import json, sys
import numpy as np
FPS = 30000 / 1001
f = json.load(open(sys.argv[1])); cortes = json.load(open(sys.argv[2]))["cortes"]
U = float(sys.argv[3]) if len(sys.argv) > 3 else 0.35
t = np.array([q[0] for q in f]); ok = np.array([q[1] is not None for q in f])
X = np.array([q[1] if q[1] else [0] * 14 for q in f], float)
yaw, pitch, ih, iv = X[:, 0], X[:, 1], X[:, 2], X[:, 3]
abajo = (X[:, 4] + X[:, 5]) / 2; parp = (X[:, 6] + X[:, 7]) / 2; lado = np.maximum((X[:, 8] + X[:, 11]) / 2, (X[:, 9] + X[:, 10]) / 2)
# base de cada cuadro: mediana móvil de 6 s del pitch (la cámara cambia de encuadre entre piezas)
pm = np.array([np.median(pitch[max(0, k - 90):k + 90][ok[max(0, k - 90):k + 90]]) if ok[k] else 0 for k in range(len(t))])
tapado = np.zeros(len(t), bool)
for a, b in cortes: tapado |= (t >= a) & (t < b)
print(f"cuadros {len(t)} · con cara {ok.sum()} · tapados {tapado.sum()}")
for n, v in [("abajo", abajo), ("parpadeo", parp), ("lado", lado), ("pitch-base", pitch - pm), ("yaw", np.abs(yaw))]:
    w = v[ok & ~tapado]; print(f"{n:11s} p50 {np.percentile(w,50):.3f} p90 {np.percentile(w,90):.3f} p97 {np.percentile(w,97):.3f} p99 {np.percentile(w,99):.3f}")
mira = ok & ((abajo > U) | (pitch - pm > 7) | (lado > 0.55) | (np.abs(yaw) > 18))
# eventos visibles: ≥4 cuadros seguidos marcados (descarta parpadeos sueltos), sin cara también cuenta si está a la vista
ev, k = [], 0
while k < len(t):
    if mira[k] and not tapado[k]:
        k0 = k
        while k < len(t) and mira[k] and not tapado[k]: k += 1
        if k - k0 >= 4: ev.append([round(t[k0], 2), round(t[k - 1], 2), round(float(abajo[k0:k].max()), 2), round(float((pitch - pm)[k0:k].max()), 1)])
    k += 1
sinc = ~ok & ~tapado
print("sin cara a la vista:", int(sinc.sum()), "cuadros")
print(len(ev), "eventos visibles:"); [print(e) for e in ev]
json.dump(ev, open("eventos6.json", "w"))
