"""Descarga datos reales de Adafruit IO y persiste series temporales en InfluxDB 2.x."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote
import json
import time
import requests
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from comun import ROOT, config, fecha_utc, cliente

ESTADO = Path(__file__).with_name('estado_sync.json')
FEEDS = ['temperatura', 'humedad', 'luminosidad', 'personas']


def fecha_iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace('+00:00','Z')


def cargar_estado():
    if not ESTADO.exists():
        return {}
    try:
        return json.loads(ESTADO.read_text(encoding='utf-8'))
    except (ValueError, OSError):
        raise RuntimeError('estado_sync.json está corrupto; haz una copia y revísalo antes de continuar')


def guardar_estado(estado):
    tmp = ESTADO.with_suffix('.tmp')
    tmp.write_text(json.dumps(estado, indent=2), encoding='utf-8')
    tmp.replace(ESTADO)


def descargar(session, c, feed, inicio, fin):
    url = 'https://io.adafruit.com/api/v2/{}/feeds/{}/data'.format(
        quote(c['AIO_USERNAME'], safe=''), quote(feed, safe=''))
    params = {'start_time':fecha_iso(inicio), 'end_time':fecha_iso(fin), 'limit':1000}
    vistos = set()
    while url:
        if url in vistos:
            raise RuntimeError('Paginación repetida en Adafruit IO')
        vistos.add(url)
        resp = session.get(url, params=params, timeout=30)
        if resp.status_code == 429:
            raise RuntimeError('Adafruit IO limitó las solicitudes HTTP (429). Espera un poco y reintenta.')
        resp.raise_for_status()
        bloque = resp.json()
        if not isinstance(bloque,list):
            raise RuntimeError('Respuesta inesperada de Adafruit IO')
        yield bloque
        url = resp.links.get('next', {}).get('url')
        params = None  # El enlace siguiente ya incluye los parámetros.
        if url:
            time.sleep(0.25)


def sincronizar(dias=1):
    c = config()
    estado = cargar_estado()
    ahora = datetime.now(timezone.utc)
    inicio_aula = fecha_utc(c['AULA_DESDE_UTC']) if c['AULA_DESDE_UTC'] else None
    headers = {'X-AIO-Key': c['AIO_KEY']}
    total = 0
    with requests.Session() as http, cliente(c) as db:
        http.headers.update(headers)
        writer = db.write_api(write_options=SYNCHRONOUS)
        for feed in FEEDS:
            clave = c['AULA_ID'] + ':' + feed
            inicio = fecha_utc(estado[clave]) if clave in estado else ahora - timedelta(days=dias)
            if inicio_aula:
                inicio = max(inicio, inicio_aula)
            recibidos = 0
            ultima = inicio
            for bloque in descargar(http, c, feed, inicio, ahora):
                puntos = []
                for rec in bloque:
                    try:
                        valor = float(rec['value'])
                        ts = fecha_utc(rec['created_at'])
                    except (ValueError, TypeError, KeyError):
                        continue
                    if ts < inicio or ts > ahora:
                        continue
                    p = (Point('lecturas')
                         .tag('aula', c['AULA_ID'])
                         .tag('variable', feed)
                         .field('valor', valor)
                         .time(ts, WritePrecision.NS))
                    puntos.append(p)
                    ultima = max(ultima, ts)
                if puntos:
                    writer.write(bucket=c['INFLUX_BUCKET'], org=c['INFLUX_ORG'], record=puntos)
                    recibidos += len(puntos)
                    # No guardamos avance hasta que InfluxDB confirmó la escritura.
                    estado[clave] = fecha_iso(ultima)
                    guardar_estado(estado)
            print(f'[Adafruit -> InfluxDB] {feed}: {recibidos} lecturas procesadas ({c["AULA_ID"]})')
            total += recibidos
    print(f'[OK] Ciclo terminado. {total} lecturas procesadas; los timestamps repetidos se sobrescriben.')
    return total


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--dias',type=int,default=1,help='Días de histórico a importar en el primer uso por aula (1-30)')
    args = ap.parse_args()
    if not 1 <= args.dias <= 30:
        ap.error('--dias debe estar entre 1 y 30')
    try:
        sincronizar(args.dias)
    except Exception as exc:
        print('[ERROR]', exc)
        raise SystemExit(1)
