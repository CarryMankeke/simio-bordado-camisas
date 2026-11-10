"""Genera el informe de Power BI del Lab 1 (formato PBIP: modelo TMDL + informe PBIR) con 6 páginas:
Resumen, Modelo, Escenarios, Máquinas, Variabilidad y Teoría.

Solo usa los datos del enunciado (llegadas exp(60 s), bordado normal(150; 4 s), almacén de 10, 8 h) y las
30 réplicas de Simio. Los datos van dentro del archivo (CSV embebido en M), así el informe se actualiza en
cualquier PC sin depender de una ruta local.
Parte de un proyecto PBIP base guardado desde Power BI Desktop y le reescribe el modelo y el informe.
Uso: python3 generar_powerbi.py <carpeta PBIP base> <carpeta salida> <diagrama.png> <resultados_30_replicas.csv>
"""
import json, shutil, sys, uuid
from pathlib import Path

src, dst, png, csv_path = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
import csv as _csv, statistics as _st
CSV_TXT = csv_path.read_text(encoding="utf-8").strip()
FILAS = list(_csv.DictReader(CSV_TXT.splitlines()))
def _rango(esc, k):
    v = [float(f[k]) for f in FILAS if f["Escenario"] == esc]
    return f"{min(v):.0f} a {max(v):.0f}"
def _prom(esc, k):
    v = [float(f[k]) for f in FILAS if f["Escenario"] == esc and f[k] != ""]
    return _st.mean(v)
def _num(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")
if dst.exists():
    shutil.rmtree(dst)
shutil.copytree(src, dst)
_cache = dst / "Lab1.SemanticModel/.pbi/cache.abf"
if _cache.exists():
    _cache.unlink()   # el caché de la v2 trae datos viejos: Power BI lo rehace al actualizar

T = "Resultados"
VC_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.4.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"

# Colores fijos
C1, C2, C3, C4 = "#7A5195", "#2F6DB3", "#1B998B", "#E8A33D"   # 1, 2, 3, 4 máquinas
ROJO, GRIS, NAVY, TXT, TXT2 = "#C0392B", "#C5CBD3", "#1F3A5F", "#1F2933", "#5A6672"
COLOR_CONFIG = {"1 máquina": C1, "2 máquinas": C2, "3 máquinas": C3}
M1, M2, M3 = "#264653", "#E76F51", "#E9C46A"   # Bordado 1, 2, 3
COLOR_MAQ = {"Bordado 1": M1, "Bordado 2": M2, "Bordado 3": M3}
U = "UtilMaquina"
VERDE, VINO = "#3C8D5A", "#B5495B"   # despachadas, desviadas


def tag():
    return str(uuid.uuid4())


def crlf(text):
    return text.replace("\r\n", "\n").replace("\n", "\r\n")


def write_tmdl(path, text):
    path.write_bytes(crlf(text).encode("utf-8"))


# =================================================================== MODELO
tmdl_path = dst / "Lab1.SemanticModel/definition/tables/Resultados.tmdl"
tm = tmdl_path.read_text(encoding="utf-8").replace("\r\n", "\n")

# 1) 'Valor medida' ahora incluye nivel de servicio
inicio = tm.index("\tmeasure 'Valor medida' =")
fin = tm.index("\tmeasure 'Titulo linea'")
tm = tm[:inicio] + tm[fin:]


def measure(name, expr, fmt=None, folder=None):
    lines = expr.strip("\n").split("\n")
    if len(lines) == 1:
        out = f"\tmeasure '{name}' = {lines[0].strip()}\n"
    else:
        out = f"\tmeasure '{name}' =\n" + "".join(f"\t\t\t{l}\n" for l in lines)
    if fmt:
        out += f"\t\tformatString: {fmt}\n"
    if folder:
        out += f"\t\tdisplayFolder: {folder}\n"
    out += f"\t\tlineageTag: {tag()}\n\n"
    return out


def sw(fn):
    return f"""VAR m = SELECTEDVALUE(Medida[Medida], "Despachadas")
RETURN
    SWITCH(
        m,
        "Despachadas", {fn}(Resultados[Despachadas]),
        "Desviadas", {fn}(Resultados[Desviadas]),
        "Nivel de servicio (%)", {fn}(Resultados[NivelServicio_pct]),
        "Utilización (%)", {fn}(Resultados[Utilizacion_pct]),
        "Espera en cola (min)", {fn}(Resultados[EsperaCola_min]),
        "WIP en cola (camisas)", {fn}(Resultados[WIPCola])
    )"""


ic_txt = """VAR n = COUNTROWS(Resultados)
VAR h = IF(n > 1, T.INV.2T(0.05, n - 1) * STDEV.S(Resultados[{c}]) / SQRT(n))
RETURN IF(n > 0, FORMAT(AVERAGE(Resultados[{c}]), "0.0", "es-CL") & " ± " & FORMAT(h, "0.0", "es-CL"))"""

M = ""
# ---- medida elegida con los botones e intervalo de confianza
M += measure("Valor medida", sw("AVERAGE"), "0.0", "Medida elegida")
M += measure("Desv medida", sw("STDEV.S"), "0.00", "Medida elegida")
M += measure("Min medida", sw("MIN"), "0.0", "Medida elegida")
M += measure("Max medida", sw("MAX"), "0.0", "Medida elegida")
M += measure("N replicas", "COUNTROWS(Resultados)", "0", "Medida elegida")
M += measure("t Student 95", "VAR n = [N replicas]\nRETURN IF(n > 1, T.INV.2T(0.05, n - 1))", "0.000", "Medida elegida")
M += measure("Semiancho IC", "[t Student 95] * [Desv medida] / SQRT([N replicas])", "0.0", "Medida elegida")
M += measure("IC inferior", "[Valor medida] - [Semiancho IC]", "0.0", "Medida elegida")
M += measure("IC superior", "[Valor medida] + [Semiancho IC]", "0.0", "Medida elegida")
M += measure("Precision relativa", "DIVIDE([Semiancho IC], [Valor medida])", "0.0%", "Medida elegida")
M += measure("Titulo IC", 'SELECTEDVALUE(Medida[Medida], "Despachadas") & ": promedio de 10 réplicas con intervalo de confianza 95 % (t de Student, 9 gl)"', None, "Medida elegida")
M += measure("Maquinas eje", "AVERAGE(Resultados[Maquinas])", "0", "Medida elegida")
M += measure("Titulo dispersion", 'SELECTEDVALUE(Medida[Medida], "Despachadas") & " en cada réplica: cada punto es una jornada simulada (pasa el mouse para ver su detalle)"', None, "Medida elegida")
M += measure("Titulo precision", '"Qué tan preciso es el promedio de 10 réplicas: " & SELECTEDVALUE(Medida[Medida], "Despachadas")', None, "Medida elegida")
M += measure("Color config", f'SWITCH(SELECTEDVALUE(Resultados[Maquinas]), 1, "{C1}", 2, "{C2}", 3, "{C3}", 4, "{C4}", "{TXT2}")', None, "Colores")
M += measure("Color barra medida", f"""VAR m = SELECTEDVALUE(Medida[Medida], "Despachadas")
RETURN IF(m = "Utilización (%)" && [Rho] >= 1, "{ROJO}", [Color config])""", None, "Colores")
M += measure("Color utilizacion", f'IF([Rho] >= 1, "{ROJO}", "{TXT}")', None, "Colores")   # saturada: ρ = 2,5/c ≥ 1

# ---- resumen por escenario
M += measure("Prom Nivel servicio", "AVERAGE(Resultados[NivelServicio_pct])", "0.0", "Escenarios")
M += measure("Prom Espera cola", "AVERAGE(Resultados[EsperaCola_min])", "0.0", "Escenarios")
M += measure("Prom WIP cola", "AVERAGE(Resultados[WIPCola])", "0.00", "Escenarios")
M += measure("IC Despachadas", ic_txt.format(c="Despachadas"), None, "Escenarios")
M += measure("IC Desviadas", ic_txt.format(c="Desviadas"), None, "Escenarios")
M += measure("Aporte marginal", """VAR c = SELECTEDVALUE(Resultados[Maquinas])
VAR prev = IF(c > 1, CALCULATE(AVERAGE(Resultados[Despachadas]), REMOVEFILTERS(Resultados), Resultados[Maquinas] = c - 1), 0)
RETURN IF(NOT ISBLANK(c), AVERAGE(Resultados[Despachadas]) - prev)""", "+0.0;-0.0;0.0", "Escenarios")

# ---- resumen: tarjetas y texto de la configuración elegida (texto "—" si no hay una sola)
UNA = "HASONEVALUE(Resultados[Maquinas])"
M += measure("Res despachadas", f'IF({UNA}, [IC Despachadas], "—")', None, "Resumen")
M += measure("Res desviadas", f'IF({UNA}, [IC Desviadas], "—")', None, "Resumen")
M += measure("Res servicio", f'IF({UNA}, FORMAT([Prom Nivel servicio] / 100, "0.0 %", "es-CL"), "—")', None, "Resumen")
M += measure("Res espera", f'IF({UNA}, FORMAT([Prom Espera cola], "0.0", "es-CL") & " min", "—")', None, "Resumen")
M += measure("Res wip", f'IF({UNA}, FORMAT([Prom WIP cola], "0.0", "es-CL") & " camisas", "—")', None, "Resumen")
M += measure("Res utilizacion", f'IF({UNA}, FORMAT([Prom Utilizacion_pct] / 100, "0.0 %", "es-CL"), "—")', None, "Resumen")
M += measure("Texto resumen", """VAR c = IF(HASONEVALUE(Resultados[Maquinas]), VALUES(Resultados[Maquinas]))
VAR ns = [Prom Nivel servicio]
VAR ut = [Prom Utilizacion_pct]
RETURN
    IF(
        ISBLANK(c),
        "Elige 1, 2 o 3 máquinas arriba: las tarjetas y este texto muestran esa configuración. Los gráficos de abajo comparan las tres.",
        "Con " & c & IF(c = 1, " máquina", " máquinas") & " se despachan "
            & FORMAT(AVERAGE(Resultados[Despachadas]), "0", "es-CL") & " camisas por jornada y se desvían "
            & FORMAT(AVERAGE(Resultados[Desviadas]), "0", "es-CL") & ": se atiende el "
            & FORMAT(ns / 100, "0.0 %", "es-CL") & " de las camisas. Las máquinas bordan el "
            & FORMAT(ut / 100, "0 %", "es-CL") & " del tiempo" & IF([Rho] >= 1, ", sin holgura (ρ ≥ 1)", "") & ". "
            & IF(
                c > 1,
                "Pasar de " & (c - 1) & " a " & c & " máquinas suma " & FORMAT([Aporte marginal], "0", "es-CL") & " camisas despachadas por jornada.",
                "Es el caso base del enunciado."
            )
            & " En el almacén temporal esperan en promedio " & FORMAT([Prom WIP cola], "0.0", "es-CL") & " camisas y cada una espera "
            & FORMAT([Prom Espera cola], "0.0", "es-CL") & " min antes de bordarse."
    )""", None, "Resumen")

# ---- teoría de colas
M += measure("Lambda por hora", "3600 / 60", "0", "Teoria")
M += measure("Mu por hora", "3600 / 150", "0", "Teoria")
M += measure("Horas jornada", "8", "0", "Teoria")
M += measure("Demanda jornada", "IF(HASONEVALUE(Resultados[Maquinas]), [Lambda por hora] * [Horas jornada])", "0", "Teoria")
M += measure("Capacidad teorica", "VAR c = SELECTEDVALUE(Resultados[Maquinas])\nRETURN c * [Mu por hora] * [Horas jornada]", "0", "Teoria")
M += measure("Rho", "VAR c = SELECTEDVALUE(Resultados[Maquinas])\nRETURN DIVIDE([Lambda por hora], c * [Mu por hora])", "0.00", "Teoria")
M += measure("Limite rho", "IF(HASONEVALUE(Resultados[Maquinas]), 1)", "0.00", "Teoria")
# Balance de flujo: solo usa λ, μ, c y las 8 h del enunciado (sin suponer distribuciones)
M += measure("Despachadas teoricas", "MIN([Demanda jornada], [Capacidad teorica])", "0.0", "Teoria")
M += measure("Desviadas teoricas", "MAX(0, [Demanda jornada] - [Capacidad teorica])", "0.0", "Teoria")
M += measure("Utilizacion teorica", "IF(NOT ISBLANK([Rho]), 100 * MIN(1, [Rho]))", "0.0", "Teoria")
# Ley de Little con datos de Simio: WIP = (camisas que pasan por la cola por hora) × espera en horas
M += measure("WIP Little", "IF(HASONEVALUE(Resultados[Maquinas]), AVERAGE(Resultados[Despachadas]) / [Horas jornada] * AVERAGE(Resultados[EsperaCola_min]) / 60)", "0.00", "Teoria")

ancla = "\tmeasure 'Titulo linea'"
assert ancla in tm
tm = tm.replace(ancla, M + ancla, 1)

col_ns = "".join(f"""	column {c}
		dataType: double
		lineageTag: {tag()}
		summarizeBy: none
		sourceColumn: {c}

""" for c in ("NivelServicio_pct", "EsperaCola_min", "WIPCola", "Util1_pct", "Util2_pct", "Util3_pct", "Llegadas", "QuedanFin", "MaxAlmacen"))
ancla = "\tpartition Resultados = m\n"
assert ancla in tm
tm = tm.replace(ancla, col_ns + ancla, 1)

viejo = """				in
				    Config
"""
nuevo = """				    NS = Table.AddColumn(Config, "NivelServicio_pct", each if [Despachadas] + [Desviadas] = 0 then null else 100 * [Despachadas] / ([Despachadas] + [Desviadas]), type number)
				in
				    NS
"""
assert viejo in tm
tm = tm.replace(viejo, nuevo, 1)
# CSV v4 (10 nov): datos dentro del M + utilización por máquina, llegadas, camisas al cierre y máximo del almacén
viejo_origen = 'Csv.Document(File.Contents("C:\\lab1\\Lab1_resultados.csv"), [Delimiter=",", Columns=6, Encoding=65001, QuoteStyle=QuoteStyle.None]),'
assert tm.count(viejo_origen) == 1, "origen v2 no encontrado"
ncols = len(CSV_TXT.splitlines()[0].split(","))
texto_m = CSV_TXT.replace('"', '""').replace("\n", "#(lf)")
tm = tm.replace(viejo_origen, f'Csv.Document("{texto_m}", [Delimiter=",", Columns={ncols}, QuoteStyle=QuoteStyle.None]),', 1)
viejo_tipos = 'Tipos = Table.TransformColumnTypes(Enc, '
assert tm.count(viejo_tipos) == 1
tm = tm.replace(viejo_tipos, 'Vacios = Table.ReplaceValue(Enc, "", null, Replacer.ReplaceValue, {"Util2_pct", "Util3_pct"}),\n\t\t\t\t    Tipos = Table.TransformColumnTypes(Vacios, ', 1)
assert tm.count('{"Utilizacion_pct", type number}}') == 1
tm = tm.replace('{"Utilizacion_pct", type number}}', '{"Utilizacion_pct", type number}, ' + ", ".join('{"%s", type number}' % c for c in ("Util1_pct", "Util2_pct", "Util3_pct", "EsperaCola_min", "WIPCola", "Llegadas", "QuedanFin", "MaxAlmacen")) + '}', 1)
assert tm.count('" máquinas"), type text)\n') == 1
tm = tm.replace('" máquinas"), type text)\n', '" máquinas"), type text),\n', 1)
write_tmdl(tmdl_path, tm)

# 1b) tabla UtilMaquina: una fila por réplica y máquina habilitada (despivotea Util1..3 de Resultados)
def _colu(nombre, tipo, resumen="none"):
    return f"""	column {nombre}
		dataType: {tipo}
		lineageTag: {tag()}
		summarizeBy: {resumen}
		sourceColumn: {nombre}

"""
um = f"""table {U}
	lineageTag: {tag()}

	measure 'Util maquina' = AVERAGE({U}[Utilizacion_pct])
		formatString: 0.0
		lineageTag: {tag()}

	measure 'Util maquina linea' = IF(HASONEVALUE({U}[Configuracion]), AVERAGE({U}[Utilizacion_pct]))
		formatString: 0.0
		lineageTag: {tag()}

	measure 'Util min' = MIN({U}[Utilizacion_pct])
		formatString: 0.0
		lineageTag: {tag()}

	measure 'Util max' = MAX({U}[Utilizacion_pct])
		formatString: 0.0
		lineageTag: {tag()}

	measure 'Titulo util linea' = IF(HASONEVALUE({U}[Configuracion]), "Utilización de cada máquina en cada réplica con " & VALUES({U}[Configuracion]) & " (una línea por máquina)", "Elige UNA configuración arriba para ver cada máquina réplica a réplica")
		lineageTag: {tag()}

""" + _colu("Configuracion", "string") + _colu("Maquinas", "int64") + _colu("Replica", "int64") + _colu("Maquina", "string") + _colu("Utilizacion_pct", "double") + """	partition UtilMaquina = m
		mode: import
		source =
				let
				    Origen = Resultados,
				    Sel = Table.SelectColumns(Origen, {"Configuracion", "Maquinas", "Replica", "Util1_pct", "Util2_pct", "Util3_pct"}),
				    Filas = Table.UnpivotOtherColumns(Sel, {"Configuracion", "Maquinas", "Replica"}, "Maquina", "Utilizacion_pct"),
				    Nombre = Table.TransformColumns(Filas, {{"Maquina", each "Bordado " & Text.Middle(_, 4, 1), type text}}),
				    Tipos = Table.TransformColumnTypes(Nombre, {{"Utilizacion_pct", type number}})
				in
				    Tipos

	annotation PBI_ResultType = Table

"""
write_tmdl(dst / f"Lab1.SemanticModel/definition/tables/{U}.tmdl", um)
mt_path = dst / "Lab1.SemanticModel/definition/model.tmdl"
mt = mt_path.read_text(encoding="utf-8").replace("\r\n", "\n")
assert 'annotation PBI_QueryOrder = ["Resultados"]' in mt and "ref table Medida\n" in mt
mt = mt.replace('annotation PBI_QueryOrder = ["Resultados"]', f'annotation PBI_QueryOrder = ["Resultados","{U}"]')
mt = mt.replace("ref table Medida\n", f"ref table Medida\nref table {U}\n")
write_tmdl(mt_path, mt)

# 2) Medida: 4 botones (se conservan los lineageTag de la v2)
mp = dst / "Lab1.SemanticModel/definition/tables/Medida.tmdl"
med = mp.read_text(encoding="utf-8").replace("\r\n", "\n")
viejo = """				    ("Despachadas", 1),
				    ("Desviadas", 2),
				    ("Utilización (%)", 3)
"""
assert viejo in med
med = med.replace(viejo, """				    ("Despachadas", 1),
				    ("Desviadas", 2),
				    ("Nivel de servicio (%)", 3),
				    ("Utilización (%)", 4),
				    ("Espera en cola (min)", 5),
				    ("WIP en cola (camisas)", 6)
""")
write_tmdl(mp, med)

# =================================================================== INFORME
rep = dst / "Lab1.Report"
res_dir = rep / "StaticResources/RegisteredResources"
res_dir.mkdir(parents=True, exist_ok=True)
TEMA, IMG = "Lab1Tema.json", "Lab1_diagrama_flujo.png"
shutil.copyfile(png, res_dir / IMG)

tema = {
    "name": "Lab 1 Bordado",
    "dataColors": [C1, C2, C3, C4, NAVY, "#3C8D5A", "#B5495B", "#8C96A3"],
    "background": "#FFFFFF",
    "foreground": TXT,
    "tableAccent": NAVY,
    "good": "#2E7D32", "neutral": "#E8A33D", "bad": ROJO,
    "maximum": NAVY, "center": "#9AA5B1", "minimum": "#EEF1F4",
    "visualStyles": {
        "page": {"*": {"background": [{"color": {"solid": {"color": "#F3F5F8"}}, "transparency": 0}]}},
        "*": {"*": {
            "background": [{"show": True, "color": {"solid": {"color": "#FFFFFF"}}, "transparency": 0}],
            "border": [{"show": True, "color": {"solid": {"color": "#DDE2E8"}}, "radius": 8}],
        }},
        "textbox": {"*": {"background": [{"show": False}], "border": [{"show": False}]}},
        "actionButton": {"*": {"background": [{"show": False}], "border": [{"show": False}]}},
    },
}
(res_dir / TEMA).write_text(json.dumps(tema, ensure_ascii=False, indent=2), encoding="utf-8")

rj_path = rep / "definition/report.json"
rj = json.loads(rj_path.read_text(encoding="utf-8"))
base = rj["themeCollection"]["baseTheme"]
rj["themeCollection"]["customTheme"] = {"name": TEMA, "reportVersionAtImport": base["reportVersionAtImport"],
                                        "type": "RegisteredResources"}
rj["resourcePackages"] = [{"name": "RegisteredResources", "type": "RegisteredResources", "items": [
    {"name": TEMA, "path": TEMA, "type": "CustomTheme"},
    {"name": IMG, "path": IMG, "type": "Image"},
]}]
rj_path.write_text(json.dumps(rj, ensure_ascii=False, indent=2), encoding="utf-8")

# ------------------------------------------------------------------ ayudantes PBIR
pages_dir = rep / "definition/pages"
shutil.rmtree(pages_dir)
pages_dir.mkdir()


def lit(v):
    return {"expr": {"Literal": {"Value": v}}}


def s(texto):
    return lit("'" + texto.replace("'", "''") + "'")


def color(hexa):
    return {"solid": {"color": s(hexa)}}


def mref(prop, entity=T):
    return {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}}


def mcolor(prop):
    return {"solid": {"color": mref(prop)}}


def col(prop, entity=T, display=None, active=None):
    p = {"field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
         "queryRef": f"{entity}.{prop}"}
    if display:
        p["displayName"] = display
    if active is not None:
        p["active"] = active
    return p


def mea(prop, entity=T, display=None):
    p = {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
         "queryRef": f"{entity}.{prop}"}
    if display:
        p["displayName"] = display
    return p


def titulo(texto=None, medida=None, size=12, entity=T):
    props = {"show": lit("true"), "titleWrap": lit("true"), "fontSize": lit(f"{size}D"), "fontColor": color(TXT)}
    props["text"] = mref(medida, entity) if medida else s(texto)
    return {"title": [{"properties": props}]}


def sin_titulo():
    return {"title": [{"properties": {"show": lit("false")}}]}


def por_config(prop="fill"):
    """Color fijo por configuración (serie o categoría Resultados[Configuracion])."""
    out = []
    for valor, hexa in COLOR_CONFIG.items():
        out.append({"properties": {prop: color(hexa)},
                    "selector": {"data": [{"scopeId": {"Comparison": {
                        "ComparisonKind": 0,
                        "Left": {"Column": {"Expression": {"SourceRef": {"Entity": T}}, "Property": "Configuracion"}},
                        "Right": s(valor)["expr"]}}}]}})   # en scopeId el literal va sin envoltorio expr
    return out


def por_maquina(prop="fill"):
    """Color fijo por máquina (serie UtilMaquina[Maquina])."""
    return [{"properties": {prop: color(hexa)},
             "selector": {"data": [{"scopeId": {"Comparison": {
                 "ComparisonKind": 0,
                 "Left": {"Column": {"Expression": {"SourceRef": {"Entity": U}}, "Property": "Maquina"}},
                 "Right": s(valor)["expr"]}}}]}} for valor, hexa in COLOR_MAQ.items()]


def por_medida_color(medida_color, metadata=None):
    sel = {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}
    if metadata:
        sel["metadata"] = metadata
    return [{"properties": {"fill": mcolor(medida_color)}, "selector": sel}]


def serie_color(metadata, hexa):
    return {"properties": {"fill": color(hexa)}, "selector": {"metadata": metadata}}


class Pagina:
    def __init__(self, name, display):
        self.name, self.display = name, display
        self.dir = pages_dir / name
        (self.dir / "visuals").mkdir(parents=True)
        self.z = 0
        self.escribir_pagina()

    def escribir_pagina(self, interacciones=None):
        d = {"$schema": PAGE_SCHEMA, "name": self.name, "displayName": self.display,
             "displayOption": "FitToPage", "height": 720, "width": 1280}
        if interacciones:   # [(origen, destino, tipo)]
            d["visualInteractions"] = [{"source": a, "target": b, "type": t} for a, b, t in interacciones]
        (self.dir / "page.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    def visual(self, name, x, y, w, h, vtype, query=None, objects=None, container=None, sync=None):
        self.z += 1000
        if vtype == "tableEx":   # sin fila de totales: mezclaría las 3 configuraciones
            objects = dict(objects or {})
            objects.setdefault("total", [{"properties": {"totals": lit("false")}}])
        v = {"visualType": vtype}
        if query:
            v["query"] = {"queryState": query}
        if objects:
            v["objects"] = objects
        if container:
            v["visualContainerObjects"] = container
        if sync:
            v["syncGroup"] = {"groupName": sync, "fieldChanges": True, "filterChanges": True}
        if vtype not in ("textbox", "image"):
            v["drillFilterOtherVisuals"] = True
        data = {"$schema": VC_SCHEMA, "name": name,
                "position": {"x": x, "y": y, "z": self.z, "height": h, "width": w, "tabOrder": self.z},
                "visual": v}
        d = self.dir / "visuals" / name
        d.mkdir()
        (d / "visual.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def texto(self, name, x, y, w, h, parrafos):
        paragraphs = []
        for runs in parrafos:
            tr = []
            for t, estilo in runs:
                r = {"value": t}
                if estilo:
                    r["textStyle"] = estilo
                tr.append(r)
            paragraphs.append({"textRuns": tr})
        self.visual(name, x, y, w, h, "textbox", objects={"general": [{"properties": {"paragraphs": paragraphs}}]})

    def boton_texto(self, name, x, y, w, h, medida, fondo="#EAF1FA", size=14):
        """Botón sin acción usado como texto dinámico (el texto sale de una medida y se ajusta solo)."""
        self.visual(name, x, y, w, h, "actionButton", objects={
            "icon": [{"properties": {"show": lit("false")}}],
            "outline": [{"properties": {"show": lit("false")}}],
            "fill": [{"properties": {"show": lit("true")}},
                     {"properties": {"fillColor": color(fondo), "transparency": lit("0D")}, "selector": {"id": "default"}}],
            "text": [{"properties": {"show": lit("true")}},
                     {"properties": {"text": mref(medida), "fontSize": lit(f"{size}D"), "fontColor": color(TXT),
                                     "horizontalAlignment": s("left"), "leftMargin": lit("14D"), "rightMargin": lit("14D")},
                      "selector": {"id": "default"}}],
        })

    def tarjeta(self, name, x, y, w, h, medida, etiqueta, entity=T, size=26, valor_color=NAVY):
        self.visual(name, x, y, w, h, "card",
                    query={"Values": {"projections": [mea(medida, entity=entity, display=etiqueta)]}},
                    objects={"labels": [{"properties": {"fontSize": lit(f"{size}D"), "color": color(valor_color),
                                                        "labelDisplayUnits": lit("1D")}}],
                             "categoryLabels": [{"properties": {"show": lit("true"), "fontSize": lit("11D"),
                                                                "color": color(TXT2)}}]},
                    container=sin_titulo())

    def chips_config(self, name, x, y, w, h, una=False, entity=T, campo="Configuracion", etiqueta=None):
        etiqueta = etiqueta or ("Máquinas de bordar (elige una)" if una else "Máquinas de bordar (elige una o varias)")
        self.visual(name, x, y, w, h, "slicer",
                    query={"Values": {"projections": [col(campo, entity=entity, display=etiqueta, active=True)]}},
                    objects={"data": [{"properties": {"mode": s("Basic")}}],
                             "general": [{"properties": {"orientation": lit("1D")}}],
                             "selection": [{"properties": {"selectAllCheckboxEnabled": lit("false"),
                                                           "singleSelect": lit("true" if una else "false"),
                                                           "strictSingleSelect": lit("false")}}]})

    def chips_medida(self, name, x, y, w, h):
        self.visual(name, x, y, w, h, "slicer",
                    query={"Values": {"projections": [col("Medida", entity="Medida", display="Medida a graficar", active=True)]}},
                    objects={"data": [{"properties": {"mode": s("Basic")}}],
                             "general": [{"properties": {"orientation": lit("1D")}}],
                             "selection": [{"properties": {"selectAllCheckboxEnabled": lit("false"),
                                                           "singleSelect": lit("true"), "strictSingleSelect": lit("true")}}]})


PAGINAS = [("resumen", "Resumen"), ("modelo", "Modelo"), ("escenarios", "Escenarios"),
           ("maquinas", "Máquinas"), ("variabilidad", "Variabilidad"), ("teoria", "Teoría")]
SUBT = {
    "resumen": "Resumen: qué pasa con 1, 2 y 3 máquinas en una jornada de 8 h",
    "modelo": "El problema y el modelo en Simio",
    "escenarios": "Comparar 1, 2 y 3 máquinas con intervalos de confianza",
    "maquinas": "Cuánto trabaja cada máquina de bordar",
    "variabilidad": "Cada réplica es una jornada distinta",
    "teoria": "Cálculo a mano (balance de flujo) frente a simulación",
}


def encabezado(p):
    p.texto("titulo", 20, 10, 520, 62, [
        [("Lab 1 · Centro de bordado de camisas", {"fontSize": "17pt", "fontWeight": "bold", "color": NAVY})],
        [(SUBT[p.name], {"fontSize": "11pt", "color": TXT2})],
    ])
    n = len(PAGINAS)
    bw, gap = 108, 6
    x0 = 1260 - (n * bw + (n - 1) * gap)
    for i, (pid, disp) in enumerate(PAGINAS):
        activo = pid == p.name
        p.visual(f"nav_{pid}", x0 + i * (bw + gap), 22, bw, 34, "actionButton", objects={
            "icon": [{"properties": {"show": lit("false")}}],
            "outline": [{"properties": {"show": lit("false")}}],
            "fill": [{"properties": {"show": lit("true")}},
                     {"properties": {"fillColor": color(NAVY if activo else "#E3E8EF"), "transparency": lit("0D")},
                      "selector": {"id": "default"}}],
            "text": [{"properties": {"show": lit("true")}},
                     {"properties": {"text": s(disp), "fontSize": lit("11D"), "bold": lit("true" if activo else "false"),
                                     "fontColor": color("#FFFFFF" if activo else NAVY)},
                      "selector": {"id": "default"}}],
        }, container={"visualLink": [{"properties": {
            "show": lit("true"), "type": s("PageNavigation"), "navigationSection": s(pid)}}]})


pags = {pid: Pagina(pid, disp) for pid, disp in PAGINAS}
for p in pags.values():
    encabezado(p)

B = {"fontWeight": "bold"}
G = {"color": TXT2}

# ------------------------------------------------------------------ 1. Resumen
p = pags["resumen"]
p.chips_config("botonesRes", 20, 84, 878, 62, una=True)
for i, (nom, med, etq) in enumerate([
        ("kpiDesp", "Res despachadas", "Despachadas"), ("kpiDesv", "Res desviadas", "Desviadas"),
        ("kpiServ", "Res servicio", "Nivel de servicio"), ("kpiUtil", "Res utilizacion", "Utilización"),
        ("kpiEsp", "Res espera", "Espera en cola"), ("kpiWip", "Res wip", "WIP en cola")]):
    p.tarjeta(nom, 20 + i * 148, 156, 140, 90, med, etq, size=17)
p.boton_texto("narrativa", 20, 256, 878, 100, "Texto resumen", size=13)
p.visual("destino", 20, 366, 878, 344, "columnChart",
         query={"Category": {"projections": [col("Configuracion", display="Configuración", active=True)]},
                "Y": {"projections": [mea("Prom Despachadas", display="Despachadas"),
                                      mea("Prom Desviadas", display="Desviadas a otro centro")]}},
         objects={"dataPoint": [serie_color(f"{T}.Prom Despachadas", VERDE),
                                serie_color(f"{T}.Prom Desviadas", VINO)],
                  "labels": [{"properties": {"show": lit("true"), "fontSize": lit("11D")}}],
                  "legend": [{"properties": {"show": lit("true"), "position": s("Top")}}]},
         container=titulo("¿Adónde va cada camisa que llega? Promedio de 10 jornadas"))
p.visual("aporte", 918, 84, 342, 380, "clusteredColumnChart",
         query={"Category": {"projections": [col("Configuracion", display="Configuración", active=True)]},
                "Y": {"projections": [mea("Aporte marginal", display="Camisas extra por jornada")]}},
         objects={"dataPoint": por_config(),
                  "labels": [{"properties": {"show": lit("true"), "fontSize": lit("12D")}}]},
         container=titulo("Cuántas camisas más despacha cada máquina que se agrega"))
p.texto("notaRes", 918, 474, 342, 236, [
    [("De dónde sale cada número", {"fontSize": "13pt", "fontWeight": "bold", "color": NAVY})],
    [("Todo viene de las 10 réplicas de Simio con los datos del enunciado: llegadas exp(60 s), almacenamiento temporal de 10 camisas, bordado normal(150 s; 4 s) en máquinas de capacidad 1 y jornada de 8 h.", None)],
    [("Nivel de servicio = despachadas / (despachadas + desviadas). IC 95 % = promedio ± t(9 gl) · s / √10. Espera y WIP en cola: promedios que entrega Simio del almacenamiento temporal (la cola antes del bordado).", G)],
])
p.escribir_pagina([("botonesRes", "destino", "NoFilter"), ("botonesRes", "aporte", "NoFilter")])

# ------------------------------------------------------------------ 2. Modelo
p = pags["modelo"]
p.visual("diagrama", 20, 84, 860, 626, "image",
         objects={"general": [{"properties": {"imageUrl": {"expr": {"ResourcePackageItem": {
             "PackageName": "RegisteredResources", "PackageType": 1, "ItemName": IMG}}}}}],
                  "imageScaling": [{"properties": {"imageScalingType": s("Fit")}}]})
p.texto("modeloTxt", 900, 84, 360, 626, [
    [("El problema", {"fontSize": "14pt", "fontWeight": "bold", "color": NAVY})],
    [("Llegadas: ", B), ("una camisa cada 60 s en promedio (exponencial): λ = 60 camisas/h, unas 480 por jornada.", None)],
    [("Almacenamiento temporal: ", B), ("espacio propio para 10 camisas, compartido por todas las máquinas. Si está lleno, la camisa se desvía a otro centro; si no, espera ahí hasta que se libere una máquina.", None)],
    [("Bordado: ", B), ("cada máquina borda una camisa a la vez, normal(150 s; 4 s): μ = 24 camisas/h por máquina, 192 por jornada.", None)],
    [("Experimento: ", B), ("jornada de 8 h, 10 réplicas por escenario, con 1, 2 y 3 máquinas.", None)],
    [("Se mide: ", B), ("camisas despachadas, camisas desviadas, utilización de las máquinas, tiempo de espera promedio en la cola y WIP en cola (camisas esperando). Con ellas se calculan el nivel de servicio, los intervalos de confianza y cuánto suma cada máquina.", None)],
    [("En Simio: Source → TransferNode (¿almacén lleno?) → Server «AlmacenTemporal» (capacidad 10, tiempo 0) → 3 Servers «Bordado» de capacidad 1 en paralelo → Sink «Despacho»; el desvío va al Sink «OtroCentro». Los enlaces son Connectors (sin tiempo de traslado) y los objetos están a escala (1 cuadro = 1 m). La propiedad Maquinas habilita 1, 2 o 3 bordadoras.", G)],
])

# ------------------------------------------------------------------ 3. Escenarios
p = pags["escenarios"]
p.chips_config("botonesMaquinas", 20, 84, 420, 70)
p.chips_medida("botonesMedida", 450, 84, 810, 70)
p.visual("columnasIC", 20, 164, 600, 546, "clusteredColumnChart",
         query={"Category": {"projections": [col("Configuracion", display="Configuración", active=True)]},
                "Y": {"projections": [mea("Valor medida", display="Promedio")]},
                "Tooltips": {"projections": [mea("IC inferior", display="Límite inferior IC 95 %"),
                                             mea("IC superior", display="Límite superior IC 95 %"),
                                             mea("Semiancho IC", display="± (semiancho)")]}},
         objects={"dataPoint": por_medida_color("Color barra medida"),
                  "labels": [{"properties": {"show": lit("true"), "fontSize": lit("12D")}}],
                  "error": [
                      {"properties": {"enabled": lit("true")}, "selector": {"metadata": f"{T}.Valor medida"}},
                      {"properties": {"errorRange": {"kind": "ErrorRange", "explicit": {
                          "isRelative": lit("false"),
                          "lowerBound": mref("IC inferior"),
                          "upperBound": mref("IC superior")}}},
                       "selector": {"data": [{"dataViewWildcard": {"matchingOption": 0}}],
                                    "metadata": f"{T}.Valor medida", "highlightMatching": 1}},
                  ]},
         container=titulo(medida="Titulo IC"))
p.visual("tablaResumen", 640, 164, 620, 206, "tableEx",
         query={"Values": {"projections": [
             col("Configuracion", display="Configuración"),
             mea("IC Despachadas", display="Despachadas"),
             mea("IC Desviadas", display="Desviadas"),
             mea("Prom Nivel servicio", display="Servicio %"),
             mea("Prom Utilizacion_pct", display="Utiliz. %"),
             mea("Prom Espera cola", display="Espera min"),
             mea("Prom WIP cola", display="WIP"),
             mea("Aporte marginal", display="+ última máq."),
         ]}},
         objects={"values": [{"properties": {"fontColor": mcolor("Color utilizacion")},
                              "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                                           "metadata": f"{T}.Prom Utilizacion_pct"}}]},
         container=titulo("Promedio ± semiancho del IC 95 % (en rojo, la utilización de las configuraciones saturadas, ρ ≥ 1)"))
p.visual("lineasReplica", 640, 380, 620, 330, "lineChart",
         query={"Category": {"projections": [col("Replica", display="Réplica", active=True)]},
                "Y": {"projections": [mea("Valor medida", display="Valor")]},
                "Series": {"projections": [col("Configuracion", display="Configuración")]}},
         objects={"lineStyles": [{"properties": {"showMarker": lit("true")}}], "dataPoint": por_config()},
         container=titulo(medida="Titulo linea"))

# ------------------------------------------------------------------ 3b. Máquinas (pedido del ayudante: utilización de cada una)
p = pags["maquinas"]
p.chips_config("botonesConfigMaq", 20, 84, 420, 70, una=True, entity=U)
p.chips_config("botonesMaquina", 450, 84, 810, 70, entity=U, campo="Maquina", etiqueta="Máquina (elige una o varias)")
p.visual("utilMaquinas", 20, 164, 620, 546, "clusteredColumnChart",
         query={"Category": {"projections": [col("Configuracion", entity=U, display="Configuración", active=True)]},
                "Series": {"projections": [col("Maquina", entity=U, display="Máquina")]},
                "Y": {"projections": [mea("Util maquina", entity=U, display="Utilización (%)")]},
                "Tooltips": {"projections": [mea("Util min", entity=U, display="Mínimo en 10 réplicas"),
                                             mea("Util max", entity=U, display="Máximo en 10 réplicas")]}},
         objects={"dataPoint": por_maquina(),
                  "labels": [{"properties": {"show": lit("true"), "fontSize": lit("11D")}}],
                  "legend": [{"properties": {"show": lit("true"), "position": s("Top")}}],
                  "valueAxis": [{"properties": {"start": lit("0D"), "end": lit("100D")}}]},
         container=titulo("Utilización de cada máquina de bordar: promedio de 10 jornadas (un color por máquina)"))
p.visual("lineasMaquina", 660, 164, 600, 330, "lineChart",
         query={"Category": {"projections": [col("Replica", entity=U, display="Réplica", active=True)]},
                "Y": {"projections": [mea("Util maquina linea", entity=U, display="Utilización (%)")]},
                "Series": {"projections": [col("Maquina", entity=U, display="Máquina")]}},
         objects={"lineStyles": [{"properties": {"showMarker": lit("true")}}], "dataPoint": por_maquina()},
         container=titulo(medida="Titulo util linea", entity=U))
_u2 = [_prom("Maq2", f"Util{i}_pct") for i in (1, 2)]
_u3 = [_prom("Maq3", f"Util{i}_pct") for i in (1, 2, 3)]
p.texto("maqTxt", 660, 504, 600, 206, [
    [("Cómo leerlo", {"fontSize": "13pt", "fontWeight": "bold", "color": NAVY})],
    [(f"Con 1 y 2 máquinas cada una borda casi todo el turno ({_num(_prom('Maq1', 'Util1_pct'))} %; {_num(_u2[0])} y {_num(_u2[1])} %): llegan más camisas de las que alcanzan a bordar (ρ ≥ 1) y el almacén nunca se vacía.", None)],
    [(f"Con 3 máquinas cada una trabaja cerca del 82 % ({_num(_u3[0])}, {_num(_u3[1])} y {_num(_u3[2])} %). La camisa que sale del almacén va a una máquina libre elegida al azar, así que el trabajo se reparte parejo; las diferencias entre máquinas vienen de que el tiempo de bordado es aleatorio, normal(150 s; 4 s).", G)],
])
p.escribir_pagina([("botonesConfigMaq", "utilMaquinas", "NoFilter")])

# ------------------------------------------------------------------ 4. Variabilidad
p = pags["variabilidad"]
p.visual("dispersion", 20, 164, 630, 546, "scatterChart",
         query={"Category": {"projections": [col("Replica", display="Réplica", active=True)]},
                "Series": {"projections": [col("Configuracion", display="Configuración")]},
                "X": {"projections": [mea("Maquinas eje", display="Máquinas de bordar")]},
                "Y": {"projections": [mea("Valor medida", display="Valor")]},
                "Tooltips": {"projections": [mea("Prom Despachadas", display="Despachadas"),
                                             mea("Prom Desviadas", display="Desviadas"),
                                             mea("Prom Utilizacion_pct", display="Utilización (%)"),
                                             mea("Prom Espera cola", display="Espera en cola (min)"),
                                             mea("Prom WIP cola", display="WIP en cola")]}},
         objects={"dataPoint": por_config(),
                  "categoryAxis": [{"properties": {"start": lit("0.5D"), "end": lit("3.5D")}}]},
         container=titulo(medida="Titulo dispersion"))
p.chips_medida("botonesMedidaVar", 20, 84, 1240, 70)
p.visual("tablaPrecision", 670, 164, 590, 230, "tableEx",
         query={"Values": {"projections": [
             col("Configuracion", display="Configuración"),
             mea("Valor medida", display="Promedio"),
             mea("Desv medida", display="Desv. est."),
             mea("Semiancho IC", display="± IC 95 %"),
             mea("Precision relativa", display="± / promedio"),
         ]}},
         container=titulo(medida="Titulo precision"))
p.texto("varTxt", 670, 404, 590, 306, [
    [("Cómo leerlo", {"fontSize": "13pt", "fontWeight": "bold", "color": NAVY})],
    [(f"Con 1 máquina el despacho casi no cambia entre réplicas ({_rango('Maq1', 'Despachadas')}: la máquina nunca para), pero los desvíos sí ({_rango('Maq1', 'Desviadas')}), porque dependen de cuántas camisas llegan.", None)],
    [(f"Con 3 máquinas pasa lo contrario: el despacho sigue a la demanda ({_rango('Maq3', 'Despachadas')}) y los desvíos casi desaparecen ({_rango('Maq3', 'Desviadas')}).", None)],
    [("± / promedio = semiancho del IC 95 % dividido por el promedio: mientras más chico, más confiable es el promedio de las 10 réplicas.", G)],
])

# ------------------------------------------------------------------ 5. Teoría
p = pags["teoria"]
p.visual("capacidad", 20, 84, 620, 330, "lineClusteredColumnComboChart",
         query={"Category": {"projections": [col("Configuracion", display="Configuración", active=True)]},
                "Y": {"projections": [mea("Capacidad teorica", display="Capacidad teórica (192 · c)"),
                                      mea("Prom Despachadas", display="Despachadas (simulación)")]},
                "Y2": {"projections": [mea("Demanda jornada", display="Demanda (480 llegadas)")]}},
         objects={"dataPoint": [serie_color(f"{T}.Capacidad teorica", "#A7B1BC"),
                                serie_color(f"{T}.Prom Despachadas", NAVY),
                                serie_color(f"{T}.Demanda jornada", ROJO)],
                  "valueAxis": [{"properties": {"secShow": lit("false")}}],
                  "labels": [{"properties": {"show": lit("true")}}],
                  "legend": [{"properties": {"show": lit("true"), "position": s("Top")}}]},
         container=titulo("Con 1 y 2 máquinas el despacho choca con la capacidad; con 3, con la demanda"))
p.visual("rho", 660, 84, 600, 330, "lineClusteredColumnComboChart",
         query={"Category": {"projections": [col("Configuracion", display="Configuración", active=True)]},
                "Y": {"projections": [mea("Rho", display="ρ = λ / (c · μ)")]},
                "Y2": {"projections": [mea("Limite rho", display="Límite ρ = 1")]}},
         objects={"dataPoint": [serie_color(f"{T}.Rho", NAVY), serie_color(f"{T}.Limite rho", ROJO)],
                  "valueAxis": [{"properties": {"secShow": lit("false")}}],
                  "labels": [{"properties": {"show": lit("true")}}],
                  "legend": [{"properties": {"show": lit("true"), "position": s("Top")}}]},
         container=titulo("Intensidad de tráfico ρ: sobre la línea roja (ρ = 1) llegan más camisas de las que se pueden bordar"))
p.visual("tablaTeoria", 20, 424, 860, 286, "tableEx",
         query={"Values": {"projections": [
             col("Configuracion", display="Configuración"),
             mea("Rho", display="ρ"),
             mea("Despachadas teoricas", display="Desp. a mano"),
             mea("Prom Despachadas", display="Desp. Simio"),
             mea("Desviadas teoricas", display="Desv. a mano"),
             mea("Prom Desviadas", display="Desv. Simio"),
             mea("Utilizacion teorica", display="Util. % a mano"),
             mea("Prom Utilizacion_pct", display="Util. % Simio"),
             mea("WIP Little", display="WIP Little"),
             mea("Prom WIP cola", display="WIP Simio"),
         ]}},
         objects={"values": [{"properties": {"fontColor": mcolor("Color utilizacion")},
                              "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                                           "metadata": f"{T}.Prom Utilizacion_pct"}}]},
         container=titulo("Cálculo a mano (balance de flujo) frente a simulación, por jornada de 8 h"))
p.texto("teoriaTxt", 900, 424, 360, 286, [
    [("Por qué 1 y 2 máquinas se saturan", {"fontSize": "13pt", "fontWeight": "bold", "color": NAVY})],
    [("ρ = λ / (c · μ) = 60 / (24 · c) = 2,5 / c. ", B),
     ("Con 1 máquina ρ = 2,5 y con 2, ρ = 1,25: llegan más camisas de las que se bordan, el almacén de 10 se llena y el resto se desvía. Con 3, ρ = 0,83: sobra capacidad y la utilización baja a cerca de 83 %.", None)],
    [("A mano: despachadas = mín(480, 192 · c); desviadas = el resto; utilización = mín(1, ρ). La simulación desvía algo menos porque al cerrar la jornada quedan camisas en el almacén y en las máquinas (llegadas = despachadas + desviadas + las que quedan) y porque las llegadas varían de un día a otro.", G)],
    [("Ley de Little: WIP = (despachadas / 8 h) × espera. Con los datos de Simio da casi lo mismo que el WIP medido.", G)],
])

# ------------------------------------------------------------------ orden de páginas
(pages_dir / "pages.json").write_text(json.dumps({
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
    "pageOrder": [pid for pid, _ in PAGINAS],
    "activePageName": "resumen",
}, ensure_ascii=False, indent=2), encoding="utf-8")

print("OK", dst)
