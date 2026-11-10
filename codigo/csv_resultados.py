#!/usr/bin/env python3
"""Convierte la salida de orientar_camiones.exe (líneas CSV,...) en resultados_30_replicas.csv, la tabla que lee el Power BI.
uso: python3 csv_resultados.py <salida_de_orientar_camiones.txt> <resultados_30_replicas.csv>"""
import csv, sys

rows = [l.strip().split(',')[1:] for l in open(sys.argv[1], encoding='utf-8', errors='replace') if l.startswith('CSV,')]
hdr, data = rows[0], rows[1:]
idx = {h: i for i, h in enumerate(hdr)}
out = []
for r in data:
    n = int(r[0][3])                      # Maq1 / Maq2 / Maq3 -> bordadoras activas
    g = lambda k: float(r[idx[k]])
    us = [g('Util%d' % i) for i in (1, 2, 3)]
    out.append({'Escenario': r[0], 'Maquinas': n, 'Replica': int(r[1]),
                'Despachadas': g('Despachadas'), 'Desviadas': g('Desviadas'),
                'Utilizacion_pct': round(sum(us[:n]) / n, 3),
                'Util1_pct': round(us[0], 3), 'Util2_pct': round(us[1], 3) if n >= 2 else '',
                'Util3_pct': round(us[2], 3) if n >= 3 else '',
                'EsperaCola_min': round(g('EsperaAlm_h') * 60, 3), 'WIPCola': round(g('WIPAlm'), 3),
                'Llegadas': g('Creadas'), 'QuedanFin': g('EnSistemaFin'), 'MaxAlmacen': g('MaxAlm')})
with open(sys.argv[2], 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()), lineterminator='\n')
    w.writeheader(); w.writerows(out)
print(len(out), 'réplicas ->', sys.argv[2])
