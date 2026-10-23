import io
from contextlib import redirect_stdout
from flask import Flask, request, jsonify
import shamir as sh

app = Flask(__name__)

# El grupo (p, g) se genera UNA vez al arrancar, no en cada petición
GRUPO = sh.generar_grupo()


def corto(n, k=10):
    s = str(n)
    return s if len(s) <= 2 * k else f"{s[:k]}…{s[-k:]}"


@app.post("/")
def run():
    try:
        # Entrada en la diapositiva, una cosa por línea:
        #   línea 1: texto secreto
        #   línea 2: n
        #   línea 3: t
        #   línea 4 (opcional): la palabra "falsa" para simular una parte falsa
        lineas = [l.strip() for l in request.json["datos"].splitlines() if l.strip()]
        texto, n, t = lineas[0], int(lineas[1]), int(lineas[2])
        poner_falsa = len(lineas) > 3 and lineas[3].lower() == "falsa"

        partes, publico = sh.repartir(texto, n, t, grupo=GRUPO)

        out = [f"Secreto como entero: {corto(sh.texto_a_entero(texto))}", ""]
        out.append(f"Partes (n={n}, t={t}):")
        for pt in partes:
            ok = sh.verificar_parte(pt, publico)
            out.append(f"  x={pt[0]}  y={corto(pt[1])}  verificada: {ok}")

        # Recuperación con las primeras t partes (cambiando la 2ª si piden "falsa")
        usadas = list(partes[:t + 1] if poner_falsa else partes[:t])
        if poner_falsa:
            x, y = usadas[1]
            usadas[1] = (x, (y + 1) % sh.Q)

        buf = io.StringIO()
        with redirect_stdout(buf):        # captura los print de recuperar()
            try:
                secreto = sh.recuperar(usadas, publico)
                resultado = f"Secreto recuperado: {secreto}"
            except ValueError as e:
                resultado = f"ERROR: {e}"
        out += ["", buf.getvalue().strip(), resultado]

        return jsonify(resultado="\n".join(l for l in out if l is not None))
    except Exception as e:
        return jsonify(resultado=f"Error en la entrada: {e}")


if __name__ == "__main__":
    app.run(port=5000)