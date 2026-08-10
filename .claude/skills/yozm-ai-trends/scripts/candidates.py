#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
candidates.py — 2트랙 선별 보조 (신규 / 재조명 후보 분류)

요즘IT 인기 목록은 롤링이라 상위권 글이 여러 주 눌러앉는다. 매주 '아직 안 다룬 글'만
좇으면 선정작이 계속 하위권으로 내려가므로, 주간 리포트는 두 트랙으로 고른다.

  · 신규(3건)   — 한 번도 분석하지 않은 글 중 상위
  · 재조명(2건) — 이미 분석했지만 인기 풀에 계속 살아남은 글을 다른 각도로 다시

이 스크립트는 판단하지 않고 후보만 정리해 보여준다(선별은 Claude가 한다).

사용: py candidates.py --root "C:\\...\\요즘IT" [--week auto|2026-W34]
"""
import argparse
import datetime
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def iso_week_id(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def short(n):
    n = int(n or 0)
    return f"{n/1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def streak_of(pid, week_id, weeks_covered, article_weeks):
    """이번 주에서 거슬러 올라가며 연속 등장한 주차 수(render.py와 동일 규칙)."""
    appears = set(article_weeks.get(pid, []))
    appears.add(week_id)
    covered = list(weeks_covered)
    if week_id not in covered:
        covered.append(week_id)
        covered.sort()
    i = covered.index(week_id)
    s = 0
    while i >= 0 and covered[i] in appears:
        s += 1
        i -= 1
    return s


def main():
    ap = argparse.ArgumentParser(description="2트랙(신규/재조명) 선별 후보 정리")
    ap.add_argument("--root", required=True)
    ap.add_argument("--week", default="auto")
    ap.add_argument("--fresh", type=int, default=3, help="신규 트랙 목표 건수")
    ap.add_argument("--revisit", type=int, default=2, help="재조명 트랙 목표 건수")
    args = ap.parse_args()

    week_id = iso_week_id(datetime.date.today()) if args.week == "auto" else args.week
    root = args.root

    wk = load_json(os.path.join(root, "_data", "weeks", f"{week_id}.json"))
    if not wk:
        print(f"ERROR: {week_id}.json 없음 — fetch_trends.py 를 먼저 실행하세요.", file=sys.stderr)
        sys.exit(2)
    idx = load_json(os.path.join(root, "_data", "index.json"), {}) or {}
    analyzed = idx.get("analyzed_weeks") or {}
    article_weeks = idx.get("article_weeks") or {}
    weeks_covered = [w for w in (idx.get("weeks_covered") or []) if w < week_id]

    arts = sorted(wk.get("articles") or [], key=lambda a: a.get("rank") or 999)
    fresh, revisit = [], []
    for a in arts:
        aid = a.get("id")
        hist = [w for w in analyzed.get(aid, []) if w < week_id]
        row = {
            "id": aid,
            "rank": a.get("rank"),
            "views": (a.get("raw") or {}).get("view_count") or 0,
            "title": a.get("title") or "",
            "cat": a.get("category") or "",
            "flags": (a.get("raw") or {}).get("category_flags") or [],
            "read": (a.get("raw") or {}).get("read_time") or 0,
            "hist": hist,
            "streak": streak_of(aid, week_id, weeks_covered, article_weeks),
            "has_body": bool(((a.get("raw") or {}).get("body") or "").strip()),
        }
        (revisit if hist else fresh).append(row)

    pool = wk.get("pool_stats") or {}
    print(f"WEEK={week_id}  기간 {wk.get('date_range_ko','')}  "
          f"인기 {pool.get('popular_fetched')}건 중 AI {pool.get('ai_in_pool')}건 "
          f"({round((pool.get('pool_ai_share') or 0)*100)}%)")
    print(f"후보 {len(arts)}건 = 신규 {len(fresh)} / 재조명 {len(revisit)}\n")

    def show(rows, title, want):
        print(f"── {title} (목표 {want}건, 후보 {len(rows)}건)")
        if not rows:
            print("   (없음)\n")
            return
        for r in rows:
            hist = ("분석 " + "·".join(w.replace("2026-", "") for w in r["hist"])) if r["hist"] else "미분석"
            body = "" if r["has_body"] else "  ⚠본문없음(--pool 확대 필요)"
            print(f'   {r["rank"]:>2}위 {short(r["views"]):>6} [{r["cat"]}] {hist}'
                  f' · 인기 {r["streak"]}주 연속 · {r["read"]}분 · id:{r["id"]}{body}')
            print(f'        {r["title"][:60]}')
        print()

    show(fresh, "① 신규 트랙 — 한 번도 분석하지 않은 글", args.fresh)
    show(revisit, "② 재조명 트랙 — 이미 분석했으나 인기 풀에 남은 글", args.revisit)

    nonai = [r for r in arts if "ai" not in [f.lower() for f in ((r.get("raw") or {}).get("category_flags") or [])]]
    print(f"참고: 요즘IT 원본 분류에 AI 플래그가 없는 글 {len(nonai)}건"
          f"{' — ' + ', '.join(str(r.get('rank')) + '위' for r in nonai) if nonai else ''}")
    missing = [r["id"] for r in fresh + revisit if not r["has_body"]]
    if missing:
        print(f"⚠ 본문 미수집 {len(missing)}건: {', '.join(missing)} "
              f"→ fetch_trends.py --week {week_id} --pool 20 --force 로 재수집")
    print("\n선별 기준(SKILL.md ②): 신규는 인기 상위부터, 재조명은 연속 등장이 길고 "
          "직전 분석 이후 새 각도가 있는 글. 카테고리 5축이 겹치지 않게 조합할 것.")


if __name__ == "__main__":
    main()
