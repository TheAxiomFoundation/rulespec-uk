#!/usr/bin/env python3
"""Provision-role audit: flag working-age-named rules whose proof atoms sit in
pensioner-part context (the Newham £16,000/£6,000 class of bug — sufficiency
checks pass because the numeral is present; only provision-role reading
catches the wrong-part anchor).

Usage: role-audit.py <module.yaml> <provisions.jsonl>
Flags are LEADS, not verdicts: adjudicate each by reading the span (footnote
proximity, "not pensioners" headers, and composite class D/E/F parts are
common false positives)."""
import sys, json, yaml
module_path, prov_path = sys.argv[1], sys.argv[2]
P = {}
for line in open(prov_path):
    r = json.loads(line); P[r["citation_path"]] = r.get("body") or ""
doc = yaml.safe_load(open(module_path))
WA = ("working_age","class_","taper","capital","non_dependant","second_adult",
      "excess_income","minimum_claimant")
flags = []
for rule in doc.get("rules", []):
    name = rule.get("name","")
    for a in (((rule.get("metadata") or {}).get("proof") or {}).get("atoms") or []):
        src = a.get("source") or {}
        ex, cp = src.get("excerpt"), src.get("corpus_citation_path")
        if not ex or not cp: continue
        body = P.get(cp, "")
        i = body.find(ex)
        if i < 0:
            flags.append((name, cp.rsplit("/",1)[-1], "EXCERPT-NOT-FOUND", ex[:40])); continue
        ctx = body[max(0,i-400):i+len(ex)+150].lower()
        wa_rule = any(k in name for k in WA)
        pens_ctx = (("pensioner" in ctx and "not pensioner" not in ctx
                     and "not a pensioner" not in ctx and "not pensioners" not in ctx)
                    or "pension credit" in ctx or "state pension" in ctx)
        wa_ctx = any(k in ctx for k in ("not a pensioner","not pensioners","working age",
                                        "working-age","class d","class e","class 1","class 2","class 3"))
        if wa_rule and pens_ctx and not wa_ctx and "pension_credit" not in name:
            flags.append((name, cp.rsplit("/",1)[-1], "PENSIONER-CTX", ex[:40]))
print(f"{len(flags)} flag(s)")
for f in flags: print("  ", *f)
sys.exit(1 if flags else 0)
