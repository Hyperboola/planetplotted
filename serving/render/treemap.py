"""Treemap "squarified" (Bruls, Huizing e van Wijk, 2000).

Divide un rettangolo in rettangoli con area proporzionale ai valori,
il più possibile vicini al quadrato, così si leggono bene.
I valori vanno passati in ordine decrescente.
"""


def _layout(sizes, x, y, dx, dy):
    covered = sum(sizes)
    rects = []
    if dx >= dy:  # riempie una colonna sul lato sinistro
        width = covered / dy
        for s in sizes:
            rects.append((x, y, width, s / width))
            y += s / width
    else:         # riempie una riga in alto
        height = covered / dx
        for s in sizes:
            rects.append((x, y, s / height, height))
            x += s / height
    return rects


def _leftover(sizes, x, y, dx, dy):
    covered = sum(sizes)
    if dx >= dy:
        width = covered / dy
        return x + width, y, dx - width, dy
    height = covered / dx
    return x, y + height, dx, dy - height


def _worst(sizes, x, y, dx, dy):
    return max(max(w / h, h / w) for _, _, w, h in _layout(sizes, x, y, dx, dy))


def _squarify(sizes, x, y, dx, dy):
    if len(sizes) <= 1:
        return _layout(sizes, x, y, dx, dy) if sizes else []
    i = 1
    while i < len(sizes) and _worst(sizes[:i], x, y, dx, dy) >= _worst(sizes[:i + 1], x, y, dx, dy):
        i += 1
    head, tail = sizes[:i], sizes[i:]
    return _layout(head, x, y, dx, dy) + _squarify(tail, *_leftover(head, x, y, dx, dy))


def squarify(values, x, y, width, height):
    """Restituisce un rettangolo (x, y, larghezza, altezza) per ogni valore."""
    total = sum(values)
    sizes = [v * width * height / total for v in values]
    return _squarify(sizes, x, y, width, height)
