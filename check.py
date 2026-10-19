"""Monitor de sitios MBC.

Revisa cada URL de sites.json. Si un sitio cae, abre un issue «🔴 Caído: <host>»
(GitHub le manda correo al dueño del repo) y avisa por Telegram. Cuando vuelve,
comenta, cierra el issue y avisa «🟢 Recuperado». Así solo alerta en el cambio de
estado, no cada 5 minutos.
"""
import json
import os
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

TIMEOUT = 20
REINTENTO_SEG = 30
CERT_MIN_DIAS = 14
REPO = os.environ.get("GITHUB_REPOSITORY", "")
RUN_URL = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{REPO}/actions/runs/{os.environ.get('GITHUB_RUN_ID', '')}"


def revisar(sitio):
    """Devuelve None si está bien, o el motivo de la falla."""
    req = urllib.request.Request(sitio["url"], headers={"User-Agent": "mbc-uptime/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            final = urllib.parse.urlparse(r.geturl()).hostname or ""
            if r.status >= 400:
                return f"HTTP {r.status}"
            destino = sitio.get("destino")
            if destino and final != destino:
                return f"redirige a {final}, se esperaba {destino}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except urllib.error.URLError as e:
        motivo = e.reason
        if isinstance(motivo, socket.gaierror):
            return "el dominio no resuelve (falta el registro DNS)"
        if isinstance(motivo, ssl.SSLError):
            return f"certificado HTTPS inválido ({motivo})"
        return f"sin respuesta ({motivo})"
    except Exception as e:  # timeouts y otros
        return f"sin respuesta ({e})"
    return None


def dias_cert(host):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=TIMEOUT) as s:
        with ctx.wrap_socket(s, server_hostname=host) as t:
            vence = ssl.cert_time_to_seconds(t.getpeercert()["notAfter"])
    return int((vence - time.time()) // 86400)


def gh(*args):
    return subprocess.run(["gh", *args, "-R", REPO], capture_output=True, text=True, check=True).stdout


def issues_abiertos():
    out = gh("issue", "list", "--state", "open", "--label", "caido", "--json", "number,title", "--limit", "100")
    return {i["title"].split(": ", 1)[-1]: i["number"] for i in json.loads(out)}


def telegram(texto):
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not (token and chat):
        print("Telegram no configurado; solo issue/correo")
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": texto, "disable_web_page_preview": "true"}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", data=data, timeout=TIMEOUT)
    except Exception as e:
        print(f"Telegram falló: {e}")


def main():
    sitios = json.load(open(os.path.join(os.path.dirname(__file__), "sites.json")))
    fallas = {s["url"]: revisar(s) for s in sitios}
    if any(fallas.values()):
        time.sleep(REINTENTO_SEG)  # una segunda opinión antes de despertar a nadie
        fallas = {u: (revisar(s) if fallas[u] else None) for s in sitios for u in [s["url"]]}

    abiertos = issues_abiertos()
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    for s in sitios:
        host = urllib.parse.urlparse(s["url"]).hostname
        falla = fallas[s["url"]]
        print(f"{'🔴' if falla else '🟢'} {host}: {falla or 'OK'}")
        if falla and host not in abiertos:
            cuerpo = (f"**{s['nombre']}** ({s['url']}) está caído desde {ahora}.\n\n"
                      f"- Motivo: {falla}\n- Proyecto Vercel: `{s['vercel']}`\n- Registro DNS: `{s['dns']}`\n- Corrida: {RUN_URL}\n\n"
                      "Si el motivo es DNS, revisar GoDaddy › metabuild.city › DNS: agregar registro nuevo, nunca editar el de `@`.")
            gh("issue", "create", "--title", f"🔴 Caído: {host}", "--label", "caido", "--body", cuerpo)
            telegram(f"🔴 CAÍDO · {s['nombre']}\n{s['url']}\nMotivo: {falla}\nDNS: {s['dns']} · Vercel: {s['vercel']}")
        elif not falla and host in abiertos:
            gh("issue", "close", str(abiertos[host]), "--comment", f"🟢 Recuperado {ahora}.")
            telegram(f"🟢 RECUPERADO · {s['nombre']}\n{s['url']}")

        if not falla:
            try:
                dias = dias_cert(host)
                if dias < CERT_MIN_DIAS and f"cert {host}" not in abiertos:
                    gh("issue", "create", "--title", f"🔴 Caído: cert {host}", "--label", "caido",
                       "--body", f"El certificado HTTPS de {host} vence en {dias} días. Vercel: `vercel certs issue {host}`.")
                    telegram(f"⚠️ Certificado de {host} vence en {dias} días")
                elif dias >= CERT_MIN_DIAS and f"cert {host}" in abiertos:
                    gh("issue", "close", str(abiertos[f"cert {host}"]), "--comment", f"Certificado renovado ({dias} días).")
            except Exception as e:
                print(f"   no pude leer el cert de {host}: {e}")


if __name__ == "__main__":
    main()
