"""Ejecuta continuamente ingestión + cálculo de alertas cada minuto."""
import time
import argparse
from ingesta import sincronizar
from alertas import evaluar

ap = argparse.ArgumentParser()
ap.add_argument('--una-vez', action='store_true', help='Ejecuta una sola vez para comprobar')
ap.add_argument('--dias', type=int, default=1, help='Histórico inicial por aula')
args = ap.parse_args()
if not 1 <= args.dias <= 30:
    ap.error('--dias debe estar entre 1 y 30')

while True:
    try:
        sincronizar(args.dias)
        evaluar()
    except KeyboardInterrupt:
        print('Detenido por el usuario')
        break
    except Exception as exc:
        print('[AVISO] Error temporal en este ciclo:', exc)
    if args.una_vez:
        break
    try:
        time.sleep(60)
    except KeyboardInterrupt:
        print('Detenido por el usuario')
        break
