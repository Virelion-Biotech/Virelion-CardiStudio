from __future__ import annotations
from collections import Counter
from typing import Any
import math

def summarize_population(rows: list[dict]) -> dict[str, Any]:
    if not rows: return {"n": 0, "features": {}}
    keys = [k for k in rows[0] if k not in {"population_id"}]
    out = {"n": len(rows), "features": {}}
    for k in keys:
        vals = [r[k] for r in rows if r.get(k) is not None]
        if not vals: continue
        if isinstance(vals[0], (int, float)) and not isinstance(vals[0], bool):
            mean = sum(vals)/len(vals)
            var = sum((x-mean)**2 for x in vals)/max(1, len(vals)-1)
            out["features"][k] = {"type":"numeric","n":len(vals),"mean":mean,"sd":math.sqrt(var),"min":min(vals),"max":max(vals)}
        else:
            c = Counter(map(str, vals)); out["features"][k] = {"type":"categorical","n":len(vals),"counts":dict(c)}
    return out

def balance_report(rows: list[dict], group_field: str, features: list[str]) -> dict[str, Any]:
    groups = sorted({str(r.get(group_field)) for r in rows})
    result = {"group_field": group_field, "groups": {g: sum(str(r.get(group_field))==g for r in rows) for g in groups}, "features": {}}
    for f in features:
        by = {g: [r[f] for r in rows if str(r.get(group_field))==g and isinstance(r.get(f), (int,float))] for g in groups}
        result["features"][f] = {g: (sum(v)/len(v) if v else None) for g,v in by.items()}
    return result
