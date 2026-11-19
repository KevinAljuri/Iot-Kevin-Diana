import os
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Busca el .env del directorio desde donde se ejecuta el script.
load_dotenv(dotenv_path=Path.cwd() / ".env")

token = os.getenv("INFLUX_TOKEN")
org = os.getenv("INFLUX_ORG", "uts")
if not token:
    raise SystemExit("ERROR: Falta INFLUX_TOKEN en el .env del proyecto activo")

temperaturas = [27.0 + (i % 5) * 0.3 for i in range(25)]
promedio = statistics.mean(temperaturas)
sigma = statistics.pstdev(temperaturas)
umbral = promedio + 2 * sigma
actual = 40.0
exceso = actual - umbral
ahora = datetime.now(timezone.utc)
puntos = []

for i, temperatura in enumerate(temperaturas):
    puntos.append(
        Point("lecturas")
        .tag("aula", "SIM-S15")
        .tag("variable", "temperatura")
        .field("valor", float(temperatura))
        .time(ahora - timedelta(minutes=(25-i) * 4))
    )

puntos.append(
    Point("lecturas")
    .tag("aula", "SIM-S15")
    .tag("variable", "temperatura")
    .field("valor", actual)
    .time(ahora)
)
puntos.append(
    Point("alerta_dinamica")
    .tag("aula", "SIM-S15")
    .field("exceso", float(exceso))
    .time(ahora)
)

with InfluxDBClient(url="http://localhost:8086", token=token, org=org) as db:
    db.write_api(write_options=SYNCHRONOUS).write(
        bucket="aulas_prueba_s15", org=org, record=puntos
    )

print("[OK] Datos simulados guardados en InfluxDB")
print(f"[UMBRAL] Promedio: {promedio:.2f} C")
print(f"[UMBRAL] Sigma: {sigma:.2f}")
print(f"[UMBRAL] Limite: {umbral:.2f} C")
print(f"[ALERTA] Actual: {actual:.2f} C")
print(f"[ALERTA] Exceso: {exceso:.2f} C")
