"""Configuración y cliente InfluxDB para el proyecto B192 (Semana 14)."""
from datetime import datetime, timezone
from pathlib import Path
import os
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')


def config():
    keys = ['AIO_USERNAME', 'AIO_KEY', 'INFLUX_TOKEN', 'INFLUX_ORG', 'INFLUX_BUCKET', 'AULA_ID']
    c = {k: os.getenv(k, '').strip() for k in keys}
    bad = [k for k, v in c.items() if not v or v.startswith('PON_AQUI') or v.startswith('CAMBIA_')]
    if bad:
        raise ValueError('Revisa el archivo .env, faltan: ' + ', '.join(bad))
    c['AULA_DESDE_UTC'] = os.getenv('AULA_DESDE_UTC','').strip()
    return c


def fecha_utc(s):
    dt = datetime.fromisoformat(s.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('La fecha debe incluir zona horaria, por ejemplo Z para UTC')
    return dt.astimezone(timezone.utc)


def cliente(c):
    return InfluxDBClient(url='http://localhost:8086', token=c['INFLUX_TOKEN'], org=c['INFLUX_ORG'], timeout=30000)
