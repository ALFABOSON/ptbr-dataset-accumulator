#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Brinquedo sensorial em 2 peças com rosca (inspirado em coluna espiral + tampa flor).

Peça 1 (base):  coluna espiralada (perfil estrela torcido) com pino roscado no topo.
Peça 2 (tampa): disco em formato de flor com furo roscado embaixo.

As duas peças se enroscam (rosca senoidal, passo 5.5 mm, folga radial 0.45 mm).

Gera STL binário usando apenas a biblioteca padrão do Python (sem numpy).
Também gera uma imagem PNG de pré-visualização.

Impressão (FDM, sem suportes):
  - base:  em pé, como gerada
  - tampa: de cabeça para baixo (topo plano na mesa, furo da rosca para cima)
    -> o STL da tampa já é exportado nessa orientação de impressão.
"""

import math
import struct
import zlib
import os

OUT = os.path.dirname(os.path.abspath(__file__))
N = 96  # segmentos angulares
TAU = 2 * math.pi

# ---------------- parâmetros ----------------
# coluna (base)
COL_H = 60.0        # altura da coluna
COL_R = 14.0        # raio médio
COL_A = 3.5         # amplitude dos gomos
COL_K = 6           # número de gomos
COL_TWIST = math.radians(150)  # torção total

# rosca
PITCH = 5.5         # passo
AMP = 1.3           # amplitude (profundidade do filete = 2*AMP)
R_STUD = 7.0        # raio médio do pino roscado (macho)
CLEAR = 0.45        # folga radial da rosca fêmea
STUD_Z0 = COL_H - 3.0   # pino começa 3 mm dentro da coluna (união por sobreposição)
STUD_Z1 = COL_H + 11.0  # ponta do pino

# tampa (flor)
CAP_T = 16.0        # espessura
CAP_R = 17.0        # raio médio das pétalas
CAP_A = 4.0         # amplitude das pétalas
CAP_K = 8           # número de pétalas
CAP_RIP = 0.45      # ondulação horizontal na lateral (textura sensorial)
CAP_RIP_P = 4.0     # período da ondulação
HOLE_D = 12.5       # profundidade do furo roscado


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


def tube(tris, rfun, z0, z1, steps, cap_bottom=True, cap_top=True):
    """Superfície de revolução generalizada r(phi, z), fechada com tampas em leque."""
    rings = [make_ring(rfun, z0 + (z1 - z0) * j / steps) for j in range(steps + 1)]
    for j in range(steps):
        lo, hi = rings[j], rings[j + 1]
        for i in range(N):
            i2 = (i + 1) % N
            add_quad(tris, lo[i], lo[i2], hi[i2], hi[i])
    if cap_bottom:
        c = (0.0, 0.0, z0)
        ring0 = rings[0]
        for i in range(N):
            tris.append((c, ring0[(i + 1) % N], ring0[i]))
    if cap_top:
        c = (0.0, 0.0, z1)
        ringt = rings[-1]
        for i in range(N):
            tris.append((c, ringt[i], ringt[(i + 1) % N]))
    return rings


# ---------------- perfis ----------------
def r_coluna(phi, z):
    return COL_R + COL_A * math.cos(COL_K * (phi + COL_TWIST * z / COL_H))


def r_pino(phi, z):
    # rosca macho senoidal; ponta com alívio (lead-in) nos últimos 2 mm
    t = min(1.0, max(0.0, (STUD_Z1 - z) / 2.0))
    c = math.cos(TAU * z / PITCH - phi)
    return R_STUD + AMP * (t * c - (1.0 - t))


def r_furo(phi, z):
    # rosca fêmea: mesmo passo/fase, raio médio maior (folga); entrada aliviada
    t = min(1.0, max(0.0, z / 2.0))
    c = math.cos(TAU * z / PITCH - phi)
    return (R_STUD + CLEAR) + AMP * (t * c + (1.0 - t))


def r_flor(phi, z):
    return CAP_R + CAP_A * math.cos(CAP_K * phi) + CAP_RIP * math.cos(TAU * z / CAP_RIP_P)


# ---------------- peça 1: base ----------------
def build_base():
    tris = []
    tube(tris, r_coluna, 0.0, COL_H, 60)
    tube(tris, r_pino, STUD_Z0, STUD_Z1, 40)  # sólido sobreposto (fatiador une)
    return tris


# ---------------- peça 2: tampa ----------------
def build_tampa():
    """Na orientação de USO: topo plano em z=CAP_T, furo roscado abrindo para baixo (z=0)."""
    tris = []
    # furo é medido a partir da face inferior (z=0) para cima
    def r_furo_local(phi, z):
        return r_furo(phi, z)

    # parede externa da flor
    steps = 32
    rings = [make_ring(r_flor, CAP_T * j / steps) for j in range(steps + 1)]
    for j in range(steps):
        lo, hi = rings[j], rings[j + 1]
        for i in range(N):
            i2 = (i + 1) % N
            add_quad(tris, lo[i], lo[i2], hi[i2], hi[i])
    # topo: disco cheio (leque, normal +z)
    c = (0.0, 0.0, CAP_T)
    top = rings[-1]
    for i in range(N):
        tris.append((c, top[i], top[(i + 1) % N]))
    # parede do furo (normais para dentro)
    hsteps = 32
    hrings = [make_ring(r_furo_local, HOLE_D * j / hsteps) for j in range(hsteps + 1)]
    for j in range(hsteps):
        lo, hi = hrings[j], hrings[j + 1]
        for i in range(N):
            i2 = (i + 1) % N
            add_quad(tris, lo[i], hi[i], hi[i2], lo[i2])
    # teto do furo (normal -z)
    c = (0.0, 0.0, HOLE_D)
    ceil = hrings[-1]
    for i in range(N):
        tris.append((c, ceil[(i + 1) % N], ceil[i]))
    # fundo: anel entre perfil da flor e boca do furo (normal -z)
    outer0, hole0 = rings[0], hrings[0]
    for i in range(N):
        i2 = (i + 1) % N
        tris.append((outer0[i], hole0[i], hole0[i2]))
        tris.append((outer0[i], hole0[i2], outer0[i2]))
    return tris


# ---------------- utilidades de malha ----------------
def transform(tris, fn):
    return [tuple(fn(v) for v in t) for t in tris]


def flip_z(tris, height):
    """Vira a peça de cabeça para baixo (para orientação de impressão)."""
    out = []
    for a, b, c in tris:
        a2 = (a[0], -a[1], height - a[2])
        b2 = (b[0], -b[1], height - b[2])
        c2 = (c[0], -c[1], height - c[2])
        out.append((a2, b2, c2))
    return out


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
            e = (k[i], k[(i + 1) % 3])
            edges[e] = edges.get(e, 0) + 1
    bad = 0
    for (a, b), n in edges.items():
        if n != 1 or edges.get((b, a), 0) != 1:
            bad += 1
    return bad


def write_stl(path, tris):
    with open(path, "wb") as f:
        f.write(b"brinquedo sensorial - gerado por script".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for t in tris:
            n = normal(t)
            f.write(struct.pack("<3f", *n))
            for v in t:
                f.write(struct.pack("<3f", *v))
            f.write(struct.pack("<H", 0))


# ---------------- render de pré-visualização (PNG) ----------------
def render(scene, path, W=900, H=560):
    """scene: lista de (tris, cor). Projeção ortográfica isométrica, pintor."""
    yaw, elev = math.radians(35), math.radians(28)
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    ce, se = math.cos(elev), math.sin(elev)
    lx, ly, lz = 0.4, -0.6, 0.7
    ll = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / ll, ly / ll, lz / ll

    def proj(p):
        x1 = p[0] * cy_ - p[1] * sy_
        y1 = p[0] * sy_ + p[1] * cy_
        sx = x1
        sy2 = p[2] * ce - y1 * se
        depth = y1 * ce + p[2] * se
        return sx, sy2, depth

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
            # normal no espaço da câmera para sombreamento simples
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
    base = build_base()
    tampa_uso = build_tampa()

    print("base:  %d tris, volume %.1f cm3" % (len(base), volume(base) / 1000.0))
    print("tampa: %d tris, volume %.1f cm3, arestas ruins: %d"
          % (len(tampa_uso), volume(tampa_uso) / 1000.0, check_manifold(tampa_uso)))

    # tampa exportada já na orientação de impressão (topo plano na mesa, rosca p/ cima)
    tampa_print = flip_z(tampa_uso, CAP_T)
    write_stl(os.path.join(OUT, "peca1_base_espiral.stl"), base)
    write_stl(os.path.join(OUT, "peca2_tampa_flor.stl"), tampa_print)

    verde, amarelo = (46, 155, 95), (240, 185, 30)
    dx = 52.0
    tampa_solta = transform(tampa_print, lambda v: (v[0] + dx, v[1], v[2]))
    tampa_montada = transform(tampa_uso, lambda v: (v[0] - dx - 12, v[1], v[2] + COL_H))
    base_montada = transform(base, lambda v: (v[0] - dx - 12, v[1], v[2]))
    render([(base, verde), (tampa_solta, amarelo),
            (base_montada, verde), (tampa_montada, amarelo)],
           os.path.join(OUT, "preview.png"))
    print("STLs e preview gerados em", OUT)


if __name__ == "__main__":
    main()
