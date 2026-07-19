#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brinquedo sensorial "vórtice": UMA peça única, impressa 2x.

Cada peça = base flangeada + 4 aletas helicoidais livres em volta de um
centro vazado. As DUAS CÓPIAS IDÊNTICAS se enroscam uma na outra: as
aletas de uma giram para dentro dos vãos da outra (300 graus de giro até
assentar). Montado, forma um fuso espiral contínuo de 8 aletas
intercaladas — a "rosca" é a própria escultura, nada de porca e parafuso.

Funciona porque virar a peça de cabeça para baixo (rotação no espaço) NÃO
inverte o sentido da hélice — as aletas da cópia virada descem exatamente
pelos vãos helicoidais da outra.

Gera STL binário usando apenas a biblioteca padrão do Python (sem numpy),
além de uma imagem PNG de pré-visualização.

Impressão (FDM): em pé, como gerada, sem suportes. O giro das aletas
desloca cada camada ~0,4 mm — dentro do que imprime bem com aletas de
5+ mm de espessura.
"""

import math
import struct
import zlib
import os

OUT = os.path.dirname(os.path.abspath(__file__))
TAU = 2 * math.pi

# ---------------- parâmetros ----------------
# Versão mini: dimensionada para ~6 g de filamento no TOTAL (2 cópias em PLA)
K = 4                    # aletas por peça (montado: 8 intercaladas)
GAP_MM = 0.35            # folga entre aletas das duas cópias, no raio interno
BASE_H = 4.7             # altura da base
FIN_Z0 = BASE_H          # onde as aletas começam (topo da base)
FIN_LEN = 20.5           # comprimento da zona das aletas
SEAT = FIN_Z0 + FIN_LEN  # onde a base da cópia oposta assenta
FIN_Z1 = SEAT - 0.25     # ponta das aletas (0,25 mm antes da base oposta)
FIN_ROOT = FIN_Z0 - 2.0  # raiz enterrada 2 mm na base (união no fatiador)
ASSY_H = SEAT + BASE_H   # altura total montado
TWIST = math.radians(300)    # giro total das aletas (o "aperto" da rosca)
OMEGA = TWIST / FIN_LEN  # rad/mm
R_IN = 3.4               # raio interno das aletas (miolo vazado)
R_OUT_MIN = 7.0          # raio externo nas pontas
R_OUT_BULGE = 2.3        # barriga do fuso no meio
TIP_TAPER_L = 3.5        # afinamento angular na ponta (entrada fácil)
TIP_ROUND_L = 1.2        # arredondamento radial na ponta
FIN_W = TAU / (2 * K) - GAP_MM / R_IN  # largura angular da aleta

# base flangeada
BASE_R0 = 9.5            # raio no chão
BASE_R1 = 7.6            # raio no ombro (cobre a raiz das aletas)
BASE_FLUTE = 0.5         # sulcos espirais decorativos na base

# estimativa de peso (PLA)
PLA_G_CM3 = 1.24
FRAC_FIN = 0.95          # aletas finas saem quase maciças (perímetros)
FRAC_BASE = 0.6          # base: paredes + topo/fundo + preenchimento leve

NSEG = 96                # segmentos angulares (superfícies de revolução)


# ---------------- perfis das aletas ----------------
def fin_width(z):
    """Largura angular; afina perto da ponta para facilitar a entrada."""
    t = min(1.0, max(0.0, (FIN_Z1 - z) / TIP_TAPER_L))
    return FIN_W * (0.5 + 0.5 * t)


def r_out(z):
    """Raio externo: barriga suave (fuso)."""
    s = min(1.0, max(0.0, (z - FIN_Z0) / FIN_LEN))
    r = R_OUT_MIN + R_OUT_BULGE * math.sin(math.pi * s)
    t = min(1.0, max(0.0, (FIN_Z1 - z) / TIP_ROUND_L))
    return r - 0.8 * (1.0 - t)


def fin_center(i, z):
    return i * TAU / K + OMEGA * (z - FIN_Z0)


# ---------------- construção de malha ----------------
def add_quad(tris, a, b, c, d):
    tris.append((a, b, c))
    tris.append((a, c, d))


def polygon_ring(i, z):
    """Seção transversal da aleta i na altura z: setor anular, CCW."""
    c = fin_center(i, z)
    w = fin_width(z)
    a, b = c - w / 2.0, c + w / 2.0
    ro, ri = r_out(z), R_IN
    pts = []
    OA, IA, RE = 8, 6, 2  # subdivisões: arco externo, interno, bordas radiais
    for j in range(OA + 1):                      # arco externo, a -> b
        t = a + (b - a) * j / OA
        pts.append((ro * math.cos(t), ro * math.sin(t), z))
    for j in range(1, RE + 1):                   # borda radial em b, ro -> ri
        r = ro + (ri - ro) * j / RE
        pts.append((r * math.cos(b), r * math.sin(b), z))
    for j in range(1, IA + 1):                   # arco interno, b -> a
        t = b + (a - b) * j / IA
        pts.append((ri * math.cos(t), ri * math.sin(t), z))
    for j in range(1, RE):                       # borda radial em a, ri -> ro
        r = ri + (ro - ri) * j / RE
        pts.append((r * math.cos(a), r * math.sin(a), z))
    return pts


def centroid(ring):
    n = len(ring)
    return (sum(p[0] for p in ring) / n, sum(p[1] for p in ring) / n, ring[0][2])


def build_fin(i):
    tris = []
    steps = 110
    rings = [polygon_ring(i, FIN_ROOT + (FIN_Z1 - FIN_ROOT) * j / steps)
             for j in range(steps + 1)]
    npts = len(rings[0])
    for j in range(steps):
        lo, hi = rings[j], rings[j + 1]
        for k in range(npts):
            k2 = (k + 1) % npts
            add_quad(tris, lo[k], lo[k2], hi[k2], hi[k])
    c0, c1 = centroid(rings[0]), centroid(rings[-1])
    for k in range(npts):                        # tampa inferior (normal -z)
        tris.append((c0, rings[0][(k + 1) % npts], rings[0][k]))
    for k in range(npts):                        # tampa da ponta (normal +z)
        tris.append((c1, rings[-1][k], rings[-1][(k + 1) % npts]))
    return tris


def r_base(phi, z):
    flare = BASE_R1 + (BASE_R0 - BASE_R1) * (1.0 - z / BASE_H) ** 1.5
    return flare + BASE_FLUTE * math.cos(2 * K * (phi + OMEGA * (z - FIN_Z0)))


def build_base():
    tris = []
    steps = 20
    rings = []
    for j in range(steps + 1):
        z = BASE_H * j / steps
        ring = []
        for i in range(NSEG):
            phi = TAU * i / NSEG
            r = r_base(phi, z)
            ring.append((r * math.cos(phi), r * math.sin(phi), z))
        rings.append(ring)
    for j in range(steps):
        lo, hi = rings[j], rings[j + 1]
        for i in range(NSEG):
            i2 = (i + 1) % NSEG
            add_quad(tris, lo[i], lo[i2], hi[i2], hi[i])
    c = (0.0, 0.0, 0.0)
    for i in range(NSEG):
        tris.append((c, rings[0][(i + 1) % NSEG], rings[0][i]))
    c = (0.0, 0.0, BASE_H)
    for i in range(NSEG):
        tris.append((c, rings[-1][i], rings[-1][(i + 1) % NSEG]))
    return tris


def build_peca():
    shells = [build_base()]
    for i in range(K):
        shells.append(build_fin(i))
    return shells


# ---------------- utilidades ----------------
def transform(tris, fn):
    return [tuple(fn(v) for v in t) for t in tris]


def normal(t):
    (ax, ay, az), (bx, by, bz), (cx, cy, cz) = t
    ux, uy, uz = bx - ax, by - ay, bz - az
    vx, vy, vz = cx - ax, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    ln = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
    return (nx / ln, ny / ln, nz / ln)


def volume(tris):
    v = 0.0
    for (a, b, c) in tris:
        v += (a[0] * (b[1] * c[2] - b[2] * c[1])
              - a[1] * (b[0] * c[2] - b[2] * c[0])
              + a[2] * (b[0] * c[1] - b[1] * c[0]))
    return v / 6.0


def check_manifold(tris):
    edges = {}
    def key(p):
        return (round(p[0], 5), round(p[1], 5), round(p[2], 5))
    for t in tris:
        k = [key(p) for p in t]
        for i in range(3):
            a, b = k[i], k[(i + 1) % 3]
            if a == b:
                continue
            edges[(a, b)] = edges.get((a, b), 0) + 1
    bad = 0
    for (a, b), n in edges.items():
        if n != 1 or edges.get((b, a), 0) != 1:
            bad += 1
    return bad


def check_clearance():
    """Folga angular mínima entre aletas das duas cópias, ao longo da altura."""
    worst = 1e9
    z = FIN_Z0 + 0.5
    while z < SEAT:
        wa = fin_width(z)                 # aleta da peça de baixo
        wb = fin_width(ASSY_H - z)        # aleta da cópia virada, nessa altura
        gap = TAU / (2 * K) - wa / 2.0 - wb / 2.0
        worst = min(worst, gap)
        z += 0.5
    return worst


def write_stl(path, tris):
    with open(path, "wb") as f:
        f.write(b"brinquedo vortice - peca identica, imprimir 2x".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for t in tris:
            n = normal(t)
            f.write(struct.pack("<3f", *n))
            for v in t:
                f.write(struct.pack("<3f", *v))
            f.write(struct.pack("<H", 0))


# ---------------- render de pré-visualização (PNG) ----------------
def render(scene, path, W=940, H=620):
    yaw, elev = math.radians(35), math.radians(22)
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    ce, se = math.cos(elev), math.sin(elev)
    lx, ly, lz = 0.4, -0.6, 0.7
    ll = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ll, ly / ll, lz / ll

    def proj(p):
        x1 = p[0] * cy_ - p[1] * sy_
        y1 = p[0] * sy_ + p[1] * cy_
        return x1, p[2] * ce - y1 * se, y1 * ce + p[2] * se

    pts = [proj(v) for tris, _ in scene for t in tris for v in t]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    scale = min((W - 60) / (maxx - minx), (H - 60) / (maxy - miny))

    def to_px(sx, sy2):
        return ((sx - minx) * scale + 30, H - ((sy2 - miny) * scale + 30))

    items = []
    for tris, color in scene:
        for t in tris:
            p = [proj(v) for v in t]
            d = (p[0][2] + p[1][2] + p[2][2]) / 3.0
            n = normal(t)
            shade = 0.35 + 0.65 * max(0.0, n[0] * lx + n[1] * ly + n[2] * lz)
            col = tuple(min(255, int(c * shade)) for c in color)
            items.append((d, [to_px(q[0], q[1]) for q in p], col))
    items.sort(key=lambda it: it[0])

    buf = bytearray([245] * (W * H * 3))
    for _, (a, b, c), col in items:
        x0 = max(0, int(min(a[0], b[0], c[0])))
        x1 = min(W - 1, int(max(a[0], b[0], c[0])) + 1)
        y0 = max(0, int(min(a[1], b[1], c[1])))
        y1 = min(H - 1, int(max(a[1], b[1], c[1])) + 1)
        d = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(d) < 1e-9:
            continue
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                w0 = ((b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])) / d
                w1 = ((c[0] - b[0]) * (y - b[1]) - (c[1] - b[1]) * (x - b[0])) / d
                if w0 >= 0 and w1 >= 0 and w0 + w1 <= 1:
                    idx = (y * W + x) * 3
                    buf[idx:idx + 3] = bytes(col)

    raw = b"".join(b"\x00" + bytes(buf[y * W * 3:(y + 1) * W * 3]) for y in range(H))
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


# ---------------- main ----------------
def main():
    shells = build_peca()
    peca = [t for s in shells for t in s]
    bad = sum(check_manifold(s) for s in shells)
    vol_base = volume(shells[0])
    vol_fins = sum(volume(s) for s in shells[1:])
    vol = vol_base + vol_fins
    gap = check_clearance()
    print("peca: %d tris, volume %.2f cm3, arestas ruins %d" % (len(peca), vol / 1000.0, bad))
    print("folga minima entre as copias: %.2f graus (%.2f mm no raio interno)"
          % (math.degrees(gap), gap * R_IN))
    assert gap * R_IN > 0.25, "folga insuficiente entre as aletas!"

    g_peca = PLA_G_CM3 * (FRAC_BASE * vol_base + FRAC_FIN * vol_fins) / 1000.0
    print("filamento estimado (PLA): %.1f g por peca, %.1f g nas duas copias"
          % (g_peca, 2 * g_peca))
    assert 2 * g_peca <= 6.0, "estouro do limite de 6 g de filamento!"

    write_stl(os.path.join(OUT, "peca_vortice_mini_6g.stl"), peca)

    # montagem: virar a copia (rotacao propria, mantem o sentido da helice)
    # e girar 75 graus para intercalar as aletas
    delta = math.radians(75.0)
    cd, sd = math.cos(delta), math.sin(delta)
    def montada(v):
        x, y = v[0] * cd - v[1] * sd, v[0] * sd + v[1] * cd
        return (x, -y, ASSY_H - v[2])

    rosa, branca = (240, 110, 165), (225, 222, 218)
    p1 = transform(peca, lambda v: (v[0] - 30, v[1], v[2]))
    p2 = transform(peca, lambda v: (v[0] - 3, v[1], v[2]))
    baixo = transform(peca, lambda v: (v[0] + 27, v[1], v[2]))
    cima = transform([tuple(montada(v) for v in t) for t in peca],
                     lambda v: (v[0] + 27, v[1], v[2]))
    render([(p1, rosa), (p2, branca), (baixo, rosa), (cima, branca)],
           os.path.join(OUT, "preview.png"))
    print("STL e preview gerados em", OUT)


if __name__ == "__main__":
    main()
