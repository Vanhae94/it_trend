#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rollup.py — 전 주차 정량 롤업 (_data/index.json 재생성)

모든 _data/weeks/*.json을 읽어 결정론적으로 집계한다. 차트·'최근 동향' 추론·연속 등장 계산의 근거.
category_timeseries/keyword_freq는 selected 기사 기준, article_weeks(streak)는 pool 전체 기준.
매주 실행하며 항상 전체 재생성(멱등).

사용: py rollup.py --root "C:\\...\\요즘IT"
"""
import argparse
import datetime
import glob
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def load_taxonomy(root):
    path = os.path.join(root, "_data", "taxonomy.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_alias_map(taxonomy):
    rev = {}
    for canon, variants in (taxonomy.get("keyword_aliases") or {}).items():
        rev[canon.lower()] = canon
        for v in variants:
            rev[v.lower()] = canon
    return rev


def normalize_kw(kw, alias_map):
    k = (kw or "").strip().lower()
    if not k:
        return None
    return alias_map.get(k, k.replace(" ", "-"))


def article_tags(article, alias_map):
    cls = article.get("classify")
    if cls and cls.get("topic_tags"):
        tags = cls["topic_tags"]
    else:
        tags = [normalize_kw(k, alias_map) for k in ((article.get("raw") or {}).get("keywords") or [])]
    out, seen = [], set()
    for t in tags:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def primary_category(article):
    cls = article.get("classify")
    if cls and cls.get("primary_category"):
        return cls["primary_category"]
    return "(미분류)"


def is_selected(a):
    return bool(a.get("selected"))


def load_weeks(root):
    weeks = []
    for p in sorted(glob.glob(os.path.join(root, "_data", "weeks", "*.json"))):
        if p.endswith(".raw.json"):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                w = json.load(f)
        except Exception as e:  # noqa: BLE001
            print(f"WARN: {p} 읽기 실패: {e}", file=sys.stderr)
            continue
        if not w.get("week_id"):
            print(f"WARN: {p} week_id 없음 — 건너뜀", file=sys.stderr)
            continue
        weeks.append(w)
    weeks.sort(key=lambda w: w.get("week_id", ""))
    return weeks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    args = ap.parse_args()
    root = args.root

    taxonomy = load_taxonomy(root)
    alias_map = build_alias_map(taxonomy)
    weeks = load_weeks(root)

    category_timeseries = {}   # cat -> {week: count}  (selected)
    keyword_freq = {}          # tag -> {weeks:set, count:int, first_seen:str}  (selected)
    article_weeks = {}         # id -> [등장 주차]  (pool 전체 — streak)
    view_timeseries = {}       # week -> selected view_count 합
    ai_share_timeseries = {}   # week -> pool_ai_share
    per_week = {}
    total_selected = 0

    for w in weeks:
        wid = w.get("week_id", "?")
        articles = w.get("articles") or []
        wk_tag_count = {}
        wk_views = 0
        for a in articles:
            aid = a.get("id")
            if aid:
                article_weeks.setdefault(aid, []).append(wid)  # pool 전체
            if not is_selected(a):
                continue
            total_selected += 1
            wk_views += int((a.get("raw") or {}).get("view_count") or 0)
            cat = primary_category(a)
            category_timeseries.setdefault(cat, {})
            category_timeseries[cat][wid] = category_timeseries[cat].get(wid, 0) + 1
            for t in article_tags(a, alias_map):
                rec = keyword_freq.setdefault(t, {"weeks": set(), "count": 0, "first_seen": wid})
                rec["count"] += 1
                rec["weeks"].add(wid)
                if wid < rec["first_seen"]:
                    rec["first_seen"] = wid
                wk_tag_count[t] = wk_tag_count.get(t, 0) + 1

        view_timeseries[wid] = wk_views
        ai_share_timeseries[wid] = (w.get("pool_stats") or {}).get("pool_ai_share", 0)
        top_tags = sorted(wk_tag_count.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
        ws = w.get("week_summary") or {}
        per_week[wid] = {
            "month_folder": w.get("month_folder"),
            "date_range_ko": w.get("date_range_ko"),
            "selected_count": sum(1 for a in articles if is_selected(a)),
            "pool_ai_share": (w.get("pool_stats") or {}).get("pool_ai_share", 0),
            "total_views": wk_views,
            "top_tags": [t for t, _ in top_tags],
            "headline_ko": ws.get("headline_ko") or "",
            "analyzed": bool(ws),
        }

    keyword_freq_out = {t: {"count": r["count"], "weeks": sorted(r["weeks"]), "first_seen": r["first_seen"]}
                        for t, r in keyword_freq.items()}

    index = {
        "schema_version": 1,
        "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "weeks_covered": [w.get("week_id") for w in weeks],
        "category_timeseries": category_timeseries,
        "keyword_freq": keyword_freq_out,
        "article_weeks": article_weeks,
        "view_timeseries": view_timeseries,
        "ai_share_timeseries": ai_share_timeseries,
        "per_week": per_week,
        "totals": {"selected": total_selected, "weeks": len(weeks)},
    }

    out_path = os.path.join(root, "_data", "index.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"STATUS=ok weeks={len(weeks)} selected={total_selected} keywords={len(keyword_freq_out)}")
    print(f"path={out_path}")
    if keyword_freq_out:
        top = sorted(keyword_freq_out.items(), key=lambda kv: (-kv[1]["count"], kv[0]))[:8]
        print("상위 키워드(누적):")
        for t, r in top:
            print(f"  - {t}: {r['count']}회, {len(r['weeks'])}주 등장, 최초 {r['first_seen']}")


if __name__ == "__main__":
    main()
