#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brinquedo sensorial modular: UMA peça única, impressa 2x (ou mais).

Cada peça é idêntica: base em formato de flor (com rosca fêmea escondida
embaixo) + coluna espiralada + pino roscado no topo. Uma cópia enrosca em
cima da outra — sem cara de porca e parafuso: montado vira um totem
flor/espiral/flor/espiral, e o pino da peça de cima fica como o pino do
brinquedo original. Dá para encadear quantas peças quiser.

Gera STL binário usando apenas a biblioteca padrão do Python (sem numpy),
além de uma imagem PNG de pré-visualização.

Impressão (FDM): em pé, como gerada, sem suportes — o teto interno da
rosca fêmea é um cone de 45 graus, autoportante.
"""

import math
import struct
import zlib
import os

OUT = os.path.dirname(os.path.abspath(__file__))
N = 96  # segmentos angulares
TAU = 2 * math.pi

# ---------------- parâmetros ----------------
# flor (base da peça)
FLW_T = 13.0        # espessura da flor
FLW_R = 18.0        # raio médio das pétalas
FLW_A = 4.0         # amplitude das pétalas
FLW_K = 8           # número de pétalas
FLW_RIP = 0.45      # ondulação horizontal na lateral (textura sensorial)
FLW_RIP_P = 4.0     # período da ondulação

# coluna espiralada
COL_TOP = 43.0      # topo da coluna (altura da peça sem o pino)
COL_R = 11.0        # raio médio
COL_A = 2.5         # amplitude dos gomos
COL_K = 6           # número de gomos
COL_TWIST = math.radians(120)  # torção total

# rosca (senoidal — imprime bem e enrosca macio)
PITCH = 5.0         # passo
AMP = 1.25          # amplitude (profundidade do filete = 2*AMP)
R_STUD = 6.5        # raio médio do pino (macho)
CLEAR = 0.45        # folga radial da rosca fêmea
STUD_Z0 = COL_TOP - 3.0   # pino começa 3 mm dentro da coluna
STUD_Z1 = COL_TOP + 10.0  # ponta do pino (10 mm expostos = 2 voltas)
HOLE_D = 11.0       # profundidade roscada do furo (na base da flor)
CONE_TIP = 0.5      # raio no ápice do teto cônico do furo


def add_quad(tris, a, b, c, d):
    tris.append((a, b, c))
    tris.append((a, c, d))


def make_ring(rfun, z):
    pts = []
    for i in range(N):
        phi = TAU * i / N
        r = rfun(phi, z)
        pts.append((r * math.cos(phi), r * math.sin(phi), z))
    return pts


def wall(tris, rings, invert=False):
    """Faixa de quads entre anéis consecutivos. invert=True para superfícies internas."""
    for j in range(len(rings) - 1):
        lo, hi = rings[j], rings[j + 1]
        for i in range(N):
            i2 = (i + 1) % N
            if invert:
                add_quad(tris, lo[i], hi[i], hi[i2], lo[i2])
            else:
                add_quad(tris, lo[i], lo[i2], hi[i2], hi[i])


def fan_up(tris, ring, z):
    c = (0.0, 0.0, z)
    for i in range(N):
        tris.append((c, ring[i], ring[(i + 1) % N]))


def fan_down(tris, ring, z):
    c = (0.0, 0.0, z)
    for i in range(N):
        tris.append((c, ring[(i + 1) % N], ring[i]))


# ---------------- perfis ----------------
def r_flor(phi, z):
    return FLW_R + FLW_A * math.cos(FLW_K * phi) + FLW_RIP * math.cos(TAU * z / FLW_RIP_P)


def r_coluna(phi, z):
    frac = (z - FLW_T) / (COL_TOP - FLW_T)
    return COL_R + COL_A * math.cos(COL_K * (phi + COL_TWIST * frac))


def r_pino(phi, z):
    # rosca macho; ponta com alívio (lead-in) nos últimos 2 mm
    t = min(1.0, max(0.0, (STUD_Z1 - z) / 2.0))
    c = math.cos(TAU * z / PITCH - phi)
    return R_STUD + AMP * (t * c - (1.0 - t))


def r_furo(phi, z):
    # rosca fêmea: mesmo passo/fase, raio médio maior (folga); entrada aliviada
    t = min(1.0, max(0.0, z / 2.0))
    c = math.cos(TAU * z / PITCH - phi)
    return (R_STUD + CLEAR) + AMP * (t * c + (1.0 - t))


# ---------------- peça ----------------
def build_peca():
    tris = []

    # --- corpo (flor + coluna, com furo roscado embaixo) ---
    rings = []
    steps_f = 26
    for j in range(steps_f + 1):                       # lateral da flor
        z = FLW_T * j / steps_f
        rings.append(make_ring(r_flor, z))
    steps_c = 30
    for j in range(steps_c + 1):                       # ombro + coluna
        z = FLW_T + (COL_TOP - FLW_T) * j / steps_c
        rings.append(make_ring(r_coluna, z))
    wall(tris, rings)
    fan_up(tris, rings[-1], COL_TOP)                   # topo da coluna

    # furo roscado (abre para baixo, na base da flor)
    hsteps = 32
    hrings = [make_ring(r_furo, HOLE_D * j / hsteps) for j in range(hsteps + 1)]
    # teto cônico a 45 graus (autoportante na impressão)
    cone_h = (R_STUD + CLEAR + AMP) - CONE_TIP
    csteps = 16
    crings = []
    for j in range(csteps + 1):
        f = j / csteps
        z = HOLE_D + cone_h * f
        crings.append(make_ring(
            lambda phi, zz, f=f: r_furo(phi, HOLE_D) * (1.0 - f) + CONE_TIP * f, z))
    wall(tris, hrings + crings[1:], invert=True)
    fan_down(tris, crings[-1], HOLE_D + cone_h)        # ápice do cone (face interna)

    # fundo: anel entre o perfil da flor e a boca do furo
    outer0, hole0 = rings[0], hrings[0]
    for i in range(N):
        i2 = (i + 1) % N
        tris.append((outer0[i], hole0[i], hole0[i2]))
        tris.append((outer0[i], hole0[i2], outer0[i2]))

    # --- pino roscado no topo (sólido sobreposto; o fatiador une) ---
    pino = []
    psteps = 40
    prings = [make_ring(r_pino, STUD_Z0 + (STUD_Z1 - STUD_Z0) * j / psteps)
              for j in range(psteps + 1)]
    wall(pino, prings)
    fan_down(pino, prings[0], STUD_Z0)
    fan_up(pino, prings[-1], STUD_Z1)
    return tris, pino


# ---------------- utilidades de malha ----------------
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
    """Cada aresta orientada deve aparecer exatamente uma vez, com a oposta também."""
    edges = {}
    def key(p):
        return (round(p[0], 5), round(p[1], 5), round(p[2], 5))
    for t in tris:
        k = [key(p) for p in t]
        for i in range(3):
            a, b = k[i], k[(i + 1) % 3]
            if a == b:
                continue  # aresta degenerada (ápice de cone), inofensiva
            e = (a, b)
            edges[e] = edges.get(e, 0) + 1
    bad = 0
    for (a, b), n in edges.items():
        if n != 1 or edges.get((b, a), 0) != 1:
            bad += 1
    return bad


def write_stl(path, tris):
    with open(path, "wb") as f:
        f.write(b"brinquedo sensorial modular - peca identica".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for t in tris:
            n = normal(t)
            f.write(struct.pack("<3f", *n))
            for v in t:
                f.write(struct.pack("<3f", *v))
            f.write(struct.pack("<H", 0))


# ---------------- render de pré-visualização (PNG) ----------------
def render(scene, path, W=900, H=620):
    """scene: lista de (tris, cor). Projeção ortográfica isométrica, pintor."""
    yaw, elev = math.radians(35), math.radians(24)
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
    corpo, pino = build_peca()
    peca = corpo + pino
    print("peca: %d tris | corpo: vol %.1f cm3, arestas ruins %d | pino: vol %.1f cm3, arestas ruins %d"
          % (len(peca), volume(corpo) / 1000.0, check_manifold(corpo),
             volume(pino) / 1000.0, check_manifold(pino)))

    write_stl(os.path.join(OUT, "peca_identica_imprimir_2x.stl"), peca)

    verde, amarelo = (46, 155, 95), (240, 185, 30)
    p1 = transform(peca, lambda v: (v[0] - 62, v[1], v[2]))
    p2 = transform(peca, lambda v: (v[0] - 8, v[1], v[2]))
    base = transform(peca, lambda v: (v[0] + 58, v[1], v[2]))
    topo = transform(peca, lambda v: (v[0] + 58, v[1], v[2] + COL_TOP))
    render([(p1, verde), (p2, amarelo), (base, verde), (topo, amarelo)],
           os.path.join(OUT, "preview.png"))
    print("STL e preview gerados em", OUT)


if __name__ == "__main__":
    main()
