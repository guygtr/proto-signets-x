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

# --- Compteur « nouveaux » ---------------------------------------------------
# PREV garde les liens (identifiants) de la génération précédente. Un signet est
# « nouveau » si son lien n'y figure pas. Si l'Excel n'a pas changé depuis la
# dernière génération, on garde la même base de comparaison (les badges restent).
PREV = OUT.parent / "previous-ids.json"
old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else None
old_ids = [x["lien"] for x in old["signets"]] if old else None
cur_ids = [x["lien"] for x in items]
base = None
if old_ids is not None and set(old_ids) != set(cur_ids):
    base = {"genere": old.get("genere", ""), "ids": sorted(old_ids)}          # nouvelle génération
    PREV.write_text(json.dumps(base, ensure_ascii=False, indent=0), encoding="utf-8")
elif PREV.exists():
    base = json.loads(PREV.read_text(encoding="utf-8"))                       # mêmes données : même base
elif old_ids is not None:
    base = {"genere": old.get("genere", ""), "ids": sorted(old_ids)}          # première fois avec le compteur
    PREV.write_text(json.dumps(base, ensure_ascii=False, indent=0), encoding="utf-8")
known = set(base["ids"]) if base else set(cur_ids)  # tout premier build : rien n'est « nouveau »
for it in items:
    it["nouveau"] = it["lien"] not in known
nouveaux = sum(it["nouveau"] for it in items)

# Même contenu qu'avant → on garde la date de génération d'origine (rien d'inventé)
same = old is not None and [{k: v for k, v in x.items() if k != "nouveau"} for x in old["signets"]] == [{k: v for k, v in x.items() if k != "nouveau"} for x in items]
genere = old["genere"] if same else datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
payload = {"genere": genere, "precedente": (base or {}).get("genere", ""), "total": len(items), "nouveaux": nouveaux, "signets": items}
OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"{len(items)} signets ({nouveaux} nouveaux depuis {payload['precedente'] or 'le premier build'}) -> {OUT}" + (" [données inchangées]" if same else ""))
