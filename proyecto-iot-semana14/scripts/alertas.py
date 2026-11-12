"""Umbral dinámico semanal = promedio + 2 * desviación estándar poblacional.
Publica la diferencia (temperatura actual - umbral) para que Grafana alerte al ser > 0.
"""
from datetime import datetime, timezone, timedelta
from statistics import mean, pstdev
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from comun import config, cliente


def evaluar():
    c = config()
    aula = c['AULA_ID']
    with cliente(c) as db:
        # Solo temperatura: evita mezclar unidades de humedad/luminosidad.
        base = f'''from(bucket: "{c['INFLUX_BUCKET']}")
          |> range(start: -7d, stop: -2m)
          |> filter(fn: (r) => r._measurement == "lecturas" and r._field == "valor" and r.variable == "temperatura" and r.aula == "{aula}")
	  |> filter(fn: (r) => r._value > 5.0)
          |> keep(columns: ["_time", "_value"])'''
        tablas = db.query_api().query(base, org=c['INFLUX_ORG'])
        valores = [float(r.values['_value']) for t in tablas for r in t.records]
        if len(valores) < 20:
            print(f'[UMBRAL] Hay {len(valores)} lecturas anteriores. Necesitamos >= 20 para el ensayo inicial.')
            return False
        actual_q = f'''from(bucket: "{c['INFLUX_BUCKET']}")
          |> range(start: -10m)
          |> filter(fn: (r) => r._measurement == "lecturas" and r._field == "valor" and r.variable == "temperatura" and r.aula == "{aula}")
          |> last()'''
        tablas_act = db.query_api().query(actual_q, org=c['INFLUX_ORG'])
        ultimos = [(r.get_time(),float(r.get_value())) for t in tablas_act for r in t.records]
        if not ultimos:
            print('[UMBRAL] No hay lectura reciente (<10 minutos); no se evalúa la alarma.')
            return False
        fecha, temp = max(ultimos, key=lambda par: par[0])
        if temp <= 5.0:
            print("[UMBRAL] Lectura sospechosa; se omite la evaluación.")
            return False
        promedio, desviacion = mean(valores), pstdev(valores)
        umbral = promedio + 2 * desviacion
        diferencia = temp - umbral
        p = (Point('alerta_dinamica').tag('aula',aula)
             .field('promedio',round(promedio,3))
             .field('desviacion',round(desviacion,3))
             .field('umbral',round(umbral,3))
             .field('temperatura_actual',round(temp,3))
             .field('exceso',round(diferencia,3))
             .field('muestras',len(valores))
             .time(datetime.now(timezone.utc), WritePrecision.NS))
        db.write_api(write_options=SYNCHRONOUS).write(bucket=c['INFLUX_BUCKET'],org=c['INFLUX_ORG'],record=p)
        print(f'[UMBRAL] {aula}: actual={temp:.2f} C, promedio={promedio:.2f}, sigma={desviacion:.2f}, umbral={umbral:.2f}, exceso={diferencia:.2f}, lecturas={len(valores)}')
        if diferencia > 0:
            print('[AVISO] Temperatura superior al umbral dinámico. Grafana notificará si la regla está configurada.')
        else:
            print('[OK] Temperatura dentro de lo esperado.')
        return diferencia > 0


if __name__ == '__main__':
    try:
        evaluar()
    except Exception as exc:
        print('[ERROR]', exc)
        raise SystemExit(1)
