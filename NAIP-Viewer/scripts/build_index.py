# -*- coding: utf-8 -*-
"""
NAIP 数据索引生成脚本
从 public/data/NAIP2610 的 CSV（GBK 编码）生成前端索引 JSON 到 public/data/index/。
用法: python scripts/build_index.py   （或 npm run index）
"""
import csv
import io
import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_SRC = os.path.join(BASE, "public", "data", "NAIP2610")
OUT = os.path.join(BASE, "public", "data", "index")


def read_csv(path):
    """读取 GBK 编码 CSV，返回 (header, rows)"""
    raw = open(path, "rb").read().decode("gbk", errors="replace")
    r = list(csv.reader(io.StringIO(raw)))
    header = [h.strip() for h in r[0]]
    rows = []
    for line in r[1:]:
        if not any(c.strip() for c in line):
            continue
        line = (line + [""] * len(header))[: len(header)]
        rows.append({h: v.strip() for h, v in zip(header, line)})
    return header, rows


def write_json(name, obj):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  {name}  {os.path.getsize(p)/1024:.0f} KB")


# ChartTypeEx_CH -> 展示分组
CHART_GROUPS = [
    ("机场细则", ["机场细则"]),
    ("机场图 / 停机位", ["机场图_停机位置图"]),
    ("离场图 (SID)", ["标准仪表离场图"]),
    ("进场图 (STAR)", ["标准仪表进场图"]),
    ("进近图 (ILS)", ["仪表进近图_ILS"]),
    ("进近图 (VOR)", ["仪表进近图_VOR"]),
    ("进近图 (NDB)", ["仪表进近图_NDB"]),
    ("进近图 (RNP/RNAV)", ["进近图_RNAV_RNP_RADAR_GPS_GNSS"]),
    ("目视进近图", ["目视进近图"]),
    ("障碍物 / 地形图", ["机场障碍物图_精密进近地形图"]),
    ("放油区 / 最低监视引导高度图", ["最低监视引导高度图_放油区图"]),
    ("其他", ["其他"]),
]


def build_airports_and_charts():
    print("[1/7] 机场与航图索引...")
    _, ap_rows = read_csv(os.path.join(DATA_SRC, "Terminal", "Airports.csv"))
    airports = []
    chart_index = {}
    for r in ap_rows:
        icao = r["CODE_ID"]
        if not icao:
            continue
        folder = os.path.join(DATA_SRC, "Terminal", icao)
        charts = []
        cpath = os.path.join(folder, "Charts.csv")
        if os.path.isfile(cpath):
            _, c_rows = read_csv(cpath)
            brief_pdf = None
            for f in os.listdir(folder):
                if f.endswith(".pdf") and not f.startswith(icao + "-"):
                    brief_pdf = f
                    break
            for r2 in c_rows:
                page, ctype = r2["PAGE_NUMBER"], r2["ChartTypeEx_CH"]
                sup = r2["IS_SUP"] == "True"
                if not page:
                    fn = brief_pdf if ctype == "机场细则" else ""
                elif sup:
                    fn = f"{icao}-{page.replace('/', '')}(SUP).pdf"
                else:
                    fn = f"{icao}-{page}.pdf"
                exists = bool(fn) and os.path.isfile(os.path.join(folder, fn))
                charts.append({
                    "n": r2["ChartName"], "p": page, "t": ctype,
                    "s": sup, "m": r2["IsModify"] == "True",
                    "f": fn if exists else "",
                })
        else:
            for f in os.listdir(folder):
                if f.endswith(".pdf"):
                    charts.append({"n": r["TXT_NAME"], "p": "", "t": "机场细则",
                                   "s": False, "m": False, "f": f})
        if not charts:
            continue
        airports.append({"icao": icao, "name": r["TXT_NAME"], "bureau": r["BUREAU_NAME"]})
        chart_index[icao] = charts

    airports.sort(key=lambda a: a["icao"])
    write_json("airports.json", airports)
    os.makedirs(os.path.join(OUT, "charts"), exist_ok=True)
    for icao, charts in chart_index.items():
        with open(os.path.join(OUT, "charts", icao + ".json"), "w", encoding="utf-8") as f:
            json.dump(charts, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  charts/*.json x{len(chart_index)}")


def build_airport_details():
    print("[2/7] 机场详情（跑道/标高）...")
    _, ad_rows = read_csv(os.path.join(DATA_SRC, "AD_HP.csv"))
    _, rwy_rows = read_csv(os.path.join(DATA_SRC, "RWY.csv"))
    _, rdir_rows = read_csv(os.path.join(DATA_SRC, "RWY_DIRECTION.csv"))
    details = {}
    for r in ad_rows:
        icao = r["CODE_ID"]
        if not icao:
            continue
        details[icao] = {
            "elev": r["VAL_ELEV"], "uom": r["UOM_DIST_VER"],
            "magvar": r["VAL_MAG_VAR"],
            "transAlt": r["VAL_TRANSITION_ALT"] if r["VAL_TRANSITION_ALT"] not in ("0", "") else "",
            "transLvl": r["VAL_TRANSITION_LEVEL"] if r["VAL_TRANSITION_LEVEL"] not in ("0", "") else "",
            "intl": r["IS_INTERNATIONAL"],
            "rwys": [],
        }
    rwy_by_id = {}
    for r in rwy_rows:
        rwy_by_id[r["RWY_ID"]] = r
        ap = details.get(r["CODE_AIRPORT"])
        if ap is None:
            continue
        ap["rwys"].append({
            "desig": r["TXT_DESIG"], "len": r["VAL_LEN"], "wid": r["VAL_WID"],
            "comp": r["CODE_COMPOSITION"], "pcr": r["TXT_DESCR_STRENGTH"],
        })
    for r in rdir_rows:
        rw = rwy_by_id.get(r["RWY_ID"])
        if rw is None:
            continue
        ap = details.get(rw["CODE_AIRPORT"])
        if ap is None:
            continue
        for d in ap["rwys"]:
            if d["desig"] == rw["TXT_DESIG"]:
                d.setdefault("dirs", []).append({
                    "brg": r["VAL_TRUE_BRG"], "slope": r["TXT_SLOPE"],
                    "displ": r["VAL_THR_DISPLACE"], "tora": r["VAL_STW_LENGTH"],
                })
    for ap in details.values():
        ap["rwys"].sort(key=lambda x: x["desig"])
    write_json("airport_details.json", details)


def build_general_docs():
    print("[3/7] NAIP 总资料...")
    _, doc_rows = read_csv(os.path.join(DATA_SRC, "GENERAL_DOC.csv"))
    by_id, roots, docs = {}, [], []
    for r in doc_rows:
        d = {"id": r["ID"], "title": r["Content"] or r["Title"], "pdf": r["PdfName"],
             "order": int(r["Order"] or 0), "parent": r["ParentId"], "children": []}
        by_id[d["id"]] = d
        docs.append(d)
    for d in docs:
        if d["parent"] and d["parent"] in by_id:
            by_id[d["parent"]]["children"].append(d)
        else:
            roots.append(d)

    def sort_rec(nodes):
        nodes.sort(key=lambda x: x["order"])
        for n in nodes:
            sort_rec(n["children"])
    sort_rec(roots)

    def prune(nodes):
        out = []
        for n in nodes:
            if n["pdf"]:
                out.append({"t": n["title"], "p": n["pdf"] + ".pdf", "c": prune(n["children"])})
            else:
                out.extend(prune(n["children"]))
        return out
    write_json("docs.json", prune(roots))


def build_navdata():
    print("[4/7] 导航台/航路点...")
    nav = {"vor": [], "ndb": [], "dpt": []}
    for key, fn in (("vor", "VOR.csv"), ("ndb", "NDB.csv"), ("dpt", "DESIGNATED_POINT.csv")):
        _, rows = read_csv(os.path.join(DATA_SRC, fn))
        for r in rows:
            nav[key].append({
                "id": r["CODE_ID"], "name": r["TXT_NAME"], "type": r["CODE_TYPE"],
                "fir": r["CODE_FIR"], "ch": r["CODE_CHANNEL"],
                "freq": (r["VAL_FREQ"] + " " + r["UOM_FREQ"]) if r["VAL_FREQ"] else "",
                "lat": r["GEO_LAT_ACCURACY"], "lon": r["GEO_LONG_ACCURACY"],
                "rmk": r["TXT_RMK"],
            })
    write_json("navdata.json", nav)


def build_airspaces():
    print("[5/7] 空域...")
    out = {"fir": [], "ctr": [], "res": [], "spc": []}
    specs = [
        ("fir", "AIRSPACE.csv", "AIRSPACE_CLASS.csv", "AIRSPACE_RADIO.csv"),
        ("ctr", "CONTROLLED.csv", "CONTROLLED_CLASS.csv", "CONTROLLED_RADIO.csv"),
        ("res", "RESTRICTED.csv", "RESTRICTED_CLASS.csv", "RESTRICTED_RADIO.csv"),
        ("spc", "SPECIAL_AIRSPACE.csv", "SPECIAL_AIRSPACE_CLASS.csv", "SPECIAL_AIRSPACE_RADIO.csv"),
    ]
    for key, main_f, class_f, radio_f in specs:
        _, rows = read_csv(os.path.join(DATA_SRC, main_f))
        _, cls_rows = read_csv(os.path.join(DATA_SRC, class_f))
        _, radio_rows = read_csv(os.path.join(DATA_SRC, radio_f))
        cls_by_as = {}
        for c in cls_rows:
            upper = (f"{c['VAL_DIST_VER_UPPER']}{c['UOM_DIST_VER_UPPER']}"
                     if c["VAL_DIST_VER_UPPER"] else c["CODE_DIST_VER_UPPER"])
            cls_by_as.setdefault(c["AIRSPACE_ID"], []).append(
                f"{c['CODE_DIST_VER_LOWER'] or 'GND'} - {upper}")
        radio_by_as = {}
        for c in radio_rows:
            radio_by_as.setdefault(c["AIRSPACE_ID"], []).append(
                f"{c['TXT_SECTOR']} {c['VAL_FREQ']}{c['UOM_FREQ']} {c['TXT_FREQ_TYPE']}".strip())
        for r in rows:
            aid = r["AIRSPACE_ID"]
            out[key].append({
                "id": r["CODE_ID"], "name": r["TXT_NAME"], "type": r["TXT_LOCAL_TYPE"],
                "reason": r["EX_RESTRICT_REASON"], "time": r["EX_RESTRICT_TIME"],
                "rmk": r["TXT_RMK"], "h": r["horizontal_range"], "v": r["vertical_range"],
                "cls": cls_by_as.get(aid, []), "radio": radio_by_as.get(aid, []),
            })
    write_json("airspaces.json", out)


def build_routes():
    print("[6/7] 航路...")
    _, rte_rows = read_csv(os.path.join(DATA_SRC, "EN_ROUTE_RTE.csv"))
    _, seg_rows = read_csv(os.path.join(DATA_SRC, "SEGMENT.csv"))
    _, rseg_rows = read_csv(os.path.join(DATA_SRC, "RTE_SEG.csv"))
    _, restrict_rows = read_csv(os.path.join(DATA_SRC, "ROUTE_RESTRICT.csv"))
    seg_by_id = {s["SEGMENT_ID"]: s for s in seg_rows}
    routes = {r["EN_ROUTE_RTE_ID"]: {
        "desig": r["TXT_DESIG"], "type": r["TXT_LOC_TYPE"],
        "len": r["VAL_LEN"], "lenSM": r["VAL_LEN_SEAMILE"], "moca": r["VAL_MTCA"],
        "pts": [],
    } for r in rte_rows}
    rsegs = [r for r in rseg_rows if r["EN_ROUTE_RTE_ID"] in routes]
    rsegs.sort(key=lambda r: int(r["VAL_SORT"] or 0))
    for rs in rsegs:
        seg = seg_by_id.get(rs["SEGMENT_ID"])
        if seg is None:
            continue
        rt = routes[rs["EN_ROUTE_RTE_ID"]]
        rt["pts"].append(seg["CODE_POINT_START"])
        rt["pts"].append(seg["CODE_POINT_END"])
    for rt in routes.values():
        dedup = []
        for p in rt["pts"]:
            if not dedup or dedup[-1] != p:
                dedup.append(p)
        rt["pts"] = dedup
    restricts = [{"code": r["REMARK_CHAR"], "rmk": r["SPECIAL_REMARK"]}
                 for r in restrict_rows if r["SPECIAL_REMARK"]]
    write_json("routes.json", {
        "routes": [v for v in routes.values() if v["pts"]],
        "restrictions": restricts,
    })

    _, al_rows = read_csv(os.path.join(DATA_SRC, "FLIGHT_AIRLINE.csv"))
    write_json("airline_routes.json", [{
        "name": r["name"], "type": r["LineType"],
        "from": r["START_CITY"], "to": r["END_CITY"],
        "dist": r["Distance"], "msa": r["MinSafeAltitude"], "route": r["Routes"],
    } for r in al_rows])

    _, hold_rows = read_csv(os.path.join(DATA_SRC, "ROUTE_HOLDING.csv"))
    write_json("holdings.json", [{
        "name": r["LOCATION_POINT"], "type": r["HOLDING_TYPE"],
        "lat": r["GEO_LAT_ACCURACY"], "lon": r["GEO_LONG_ACCURACY"],
        "rmk": r["TXT_SPECIAL_REMARK"],
    } for r in hold_rows if r["TXT_SPECIAL_REMARK"]])


def build_meta():
    print("[7/7] 元信息...")
    _, rows = read_csv(os.path.join(DATA_SRC, "SYSTEMSETTING.csv"))
    write_json("meta.json", {r["KEYNAME"]: r["KEYVALUE"] for r in rows})


if __name__ == "__main__":
    if not os.path.isdir(DATA_SRC):
        raise SystemExit(f"数据目录不存在: {DATA_SRC}\n"
                         "请将 NAIP2610 数据放入 public/data/（见 README）")
    print(f"数据源: {DATA_SRC}")
    build_airports_and_charts()
    build_airport_details()
    build_general_docs()
    build_navdata()
    build_airspaces()
    build_routes()
    build_meta()
    print("完成。")
