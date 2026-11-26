"""Vista esquemática da geometria declarada no JSON de cena RFID."""

import base64
from itertools import product
from math import isfinite


def _vetor(valor):
    if not isinstance(valor, (list, tuple)) or len(valor) != 3:
        return None
    if all(isinstance(v, (int, float)) and isfinite(v) for v in valor):
        return valor
    return None


def vista_da_cena(cena):
    """Projeta volumes, antenas e etiquetas de origem, com a mesma escala nos três eixos."""
    volumes = []
    for chave, cor in (
        ("cabin", "#c4deed"), ("read_zone", "#68dccb"),
        ("cage", "#809fb8"), ("textile_volume", "#a9beca"),
    ):
        volume = cena.get(chave) or {}
        centro, tamanho = _vetor(volume.get("center")), _vetor(volume.get("size"))
        if not centro or not tamanho or min(tamanho) <= 0 or not volume.get("enabled", True):
            continue
        vertices = [
            tuple(c + sinal * t / 2 for c, sinal, t in zip(centro, sinais, tamanho))
            for sinais in product((-1, 1), repeat=3)
        ]
        volumes.append((vertices, cor))

    def posicoes(chave):
        return [p for item in cena.get(chave, []) if (p := _vetor(item.get("position")))]

    antenas, etiquetas = posicoes("antennas"), posicoes("tags")
    pontos = [p for vertices, _ in volumes for p in vertices] + antenas + etiquetas
    if not pontos:
        return '<span class="rf-no-geometry">Sem geometria disponível no JSON.</span>'

    # Projeção ortogonal vista do lado direito, de frente e de cima.
    def projetar(p):
        x, y, z = p
        return .8660254 * x + .5 * y, .25 * x - .4330127 * y - .8660254 * z

    xs, ys = zip(*(projetar(p) for p in pontos))
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    escala = min(252 / max(max(xs) - min(xs), .001), 139 / max(max(ys) - min(ys), .001))

    def tela(p):
        x, y = projetar(p)
        return 140 + (x - cx) * escala, 82 + (y - cy) * escala

    formas = []
    for vertices, cor in volumes:
        coords = [tela(p) for p in vertices]
        # Um bit por eixo no índice do vértice. Vizinhos diferem em um único bit.
        arestas = []
        for i, (x, y) in enumerate(coords):
            for eixo in (1, 2, 4):
                if not i & eixo:
                    x2, y2 = coords[i | eixo]
                    arestas.append(f'M{x:.2f},{y:.2f} L{x2:.2f},{y2:.2f}')
        formas.append(f'<path d="{" ".join(arestas)}" stroke="{cor}" fill="none" stroke-width="1.2"/>')
    for p in etiquetas:
        x, y = tela(p)
        formas.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="2.1" fill="#f0c57d"/>')
    for p in antenas:
        x, y = tela(p)
        formas.append(f'<rect x="{x-3:.2f}" y="{y-3:.2f}" width="6" height="6" fill="#6ce6d6" stroke="#102c3c"/>')
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 164">' + ''.join(formas) + '</svg>'
    dados = base64.b64encode(svg.encode('ascii')).decode('ascii')
    return f'<img src="data:image/svg+xml;base64,{dados}" width="280" height="164" alt="Projeção dos volumes, antenas e etiquetas presentes na cena de origem.">'
