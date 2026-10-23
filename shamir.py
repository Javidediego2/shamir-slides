"""
Shamir (SSSS) con verificabilidad de las partes (VSS de Feldman).

- repartir(texto, n, t)          -> (partes, publico)
- verificar_parte(parte, publico)-> True/False   (cada participante comprueba la suya)
- recuperar(partes, publico)     -> texto        (descarta partes falsas; ValueError si no hay t válidas)

'publico' contiene p, g, t y los compromisos: no es secreto y se da a todos.
Cada parte es (x, y).
"""

import secrets

# Las partes y el polinomio viven en Z_q (q primo).
# Los compromisos viven en Z_p*, donde g tiene orden exactamente q.
Q = 2**521 - 1


# ---------- Primalidad y grupo ----------
def es_primo(n, rondas=40):
    """Test de Miller-Rabin."""
    if n < 2:
        return False
    for r in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]:
        if n % r == 0:
            return n == r
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for _ in range(rondas):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def generar_grupo(bits_p=1536, q=Q):
    """Busca p = k*q + 1 primo y g de orden q. Tarda unos segundos."""
    extra = bits_p - q.bit_length()
    k = (1 << extra) | secrets.randbits(extra)
    k -= k % 2
    while True:
        k += 2
        p = k * q + 1
        if es_primo(p, 20):
            break
    h = 2
    while True:
        g = pow(h, (p - 1) // q, p)
        if g != 1:
            return p, g
        h += 1


# ---------- Texto <-> número ----------
def texto_a_entero(w):
    return int.from_bytes(w.encode("utf-8"), "big")


def entero_a_texto(n):
    longitud = (n.bit_length() + 7) // 8
    return n.to_bytes(longitud, "big").decode("utf-8")


# ---------- Piezas del esquema ----------
def evaluar(coef, x, q=Q):
    resultado = 0
    for c in reversed(coef):
        resultado = (resultado * x + c) % q
    return resultado


def lagrange_en_cero(partes, q=Q):
    xs = [x for x, y in partes]
    ys = [y for x, y in partes]
    total = 0
    for i in range(len(xs)):
        L = 1
        for j in range(len(xs)):
            if i != j:
                L = L * (-xs[j]) * pow(xs[i] - xs[j], -1, q) % q
        total = (total + ys[i] * L) % q
    return total


# ---------- Funciones principales ----------
def repartir(texto, n, t, grupo=None):
    """
    Devuelve (partes, publico).
    - partes:  lista de (x, y), una para cada participante (SECRETAS).
    - publico: dict con p, g, t y compromisos (se puede dar a todos).
    'grupo' = (p, g) permite reutilizar un grupo ya generado.
    """
    if not (2 <= t <= n):
        raise ValueError("Se requiere 2 <= t <= n")
    secreto = texto_a_entero(texto)
    if secreto >= Q:
        raise ValueError("El texto es demasiado largo (máximo ~65 bytes)")

    p, g = grupo if grupo else generar_grupo()

    coef = [secreto] + [secrets.randbelow(Q) for _ in range(t - 1)]
    compromisos = [pow(g, c, p) for c in coef]
    partes = [(x, evaluar(coef, x)) for x in range(1, n + 1)]

    publico = {"p": p, "g": g, "t": t, "compromisos": compromisos}
    return partes, publico


def verificar_parte(parte, publico):
    """Comprueba g^y == prod( C_j ^ (x^j) )  (mod p), con exponentes mod q."""
    x, y = parte
    p, g, compromisos = publico["p"], publico["g"], publico["compromisos"]
    if not (0 <= y < Q) or x < 1:
        return False
    lado_izq = pow(g, y, p)
    lado_der = 1
    for j, c_j in enumerate(compromisos):
        lado_der = lado_der * pow(c_j, pow(x, j, Q), p) % p
    return lado_izq == lado_der


def recuperar(partes, publico):
    """
    Verifica cada parte, descarta las falsas o repetidas y reconstruye
    el texto con t válidas. Lanza ValueError si no hay suficientes.
    """
    t = publico["t"]
    validas, vistas = [], set()

    for parte in partes:
        x = parte[0]
        if x in vistas:
            print(f"La parte {x} está repetida y fue descartada.")
        elif not verificar_parte(parte, publico):
            print(f"La parte {x} es FALSA y fue descartada.")
        else:
            validas.append(parte)
            vistas.add(x)

    if len(validas) < t:
        raise ValueError(
            f"No hay suficientes partes válidas: se necesitan {t} y solo hay {len(validas)}."
        )
    return entero_a_texto(lagrange_en_cero(validas[:t]))


# ---------- Ejemplo de uso ----------
if __name__ == "__main__":
    partes, publico = repartir("hola Complu", n=5, t=3)
    print(texto_a_entero('hola Complu'))
    print(partes)
    # Cada participante puede comprobar que SU parte es coherente
    print("Verificación individual:", [verificar_parte(pt, publico) for pt in partes])

    # Recuperar con 3 partes buenas
    print("Secreto:", recuperar([partes[0], partes[2], partes[4]], publico))

    # Una parte falsa entre 4: se descarta y se recupera igualmente
    falsa = (2, (partes[1][1] + 1) % Q)
    print("Secreto:", recuperar([partes[0], falsa, partes[2], partes[3]], publico))

    # Con solo 2 válidas: error
    try:
        recuperar([partes[0], falsa, partes[2]], publico)
    except ValueError as e:
        print("ERROR ->", e)