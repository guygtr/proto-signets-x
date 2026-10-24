#!/usr/bin/env python3
"""Convertit l'Excel des signets X (lecture seule) en data/signets.json.

Usage : python3 scripts/build-data.py [chemin/vers/Signets_X.xlsx]
"""
import json, sys, datetime, pathlib
import openpyxl

SRC = sys.argv[1] if len(sys.argv) > 1 else "/workspace/x_signets/Signets_X.xlsx"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "signets.json"
COLS = ["Catégorie", "Date", "Soumis par", "Sujet", "Brève description", "Lien X", "Type", "Langue", "J'aime"]
KEYS = ["categorie", "date", "soumisPar", "sujet", "description", "lien", "type", "langue", "jaime"]

wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
rows = wb["Signets"].iter_rows(values_only=True)
header = [str(h).strip() if h else "" for h in next(rows)]
idx = [header.index(c) for c in COLS]  # échoue clairement si une colonne manque

items, seen = [], set()
for r in rows:
    if not r or all(v in (None, "") for v in r):
        continue
    it = {k: r[i] for k, i in zip(KEYS, idx)}
    d = it["date"]
    if isinstance(d, (datetime.datetime, datetime.date)):
        it["date"] = d.strftime("%Y-%m-%d")
    else:
        it["date"] = str(d or "")[:10]
    it["jaime"] = int(it["jaime"] or 0)
    for k in KEYS:
        if isinstance(it[k], str):
            it[k] = it[k].strip()
        elif it[k] is None:
            it[k] = ""
    sp = it["soumisPar"]
    handle, _, name = sp.partition(" (")
    it["handle"] = handle.strip()
    it["nom"] = name[:-1].strip() if name.endswith(")") else (name.strip() or handle.lstrip("@"))
    if it["lien"] in seen:
        continue
    seen.add(it["lien"])
    items.append(it)

items.sort(key=lambda x: x["date"], reverse=True)
OUT.parent.mkdir(parents=True, exist_ok=True)
payload = {"genere": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "total": len(items), "signets": items}
OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"{len(items)} signets -> {OUT}")
