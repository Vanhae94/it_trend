#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_trends.py — 요즘IT 인기 AI 글 주간 수집기 (멱등)

요즘IT 공개 JSON API에서 인기 목록을 받아 category flag로 AI 글만 필터하고,
view_count 상위 pool을 골라 각 글 본문(raw_content)까지 보강해
주차별 불변 기록(_data/weeks/YYYY-Wnn.json)으로 저장한다.
분석 필드(selected/classify/analysis/learning/week_summary)는 골격(null)만 만들고 Claude가 채운다.

표준 라이브러리만 사용(urllib + json). 사용:
  py fetch_trends.py --root "C:\\...\\요즘IT" [--week auto|2026-W27] [--pool 12] [--pages 1] [--force]
"""
import argparse
import datetime
import json
import os
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

LIST_URL = "https://yozm.wishket.com/api/articleListApi/?category=popular&page={page}&ordering=new"
DETAIL_URL = "https://yozm.wishket.com/api/fetchContentsDetail/?id={id}&affectView=false"
ARTICLE_URL = "https://yozm.wishket.com/magazine/detail/{id}"
UA = "yozm-ai-trends/1.0 (personal study)"


def iso_week_id(d):
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def parse_week_id(week_id):
    y, w = week_id.split("-W")
    return int(y), int(w)


def monday_of_week(week_id):
    y, w = parse_week_id(week_id)
    return datetime.date.fromisocalendar(y, w, 1)


def month_folder_for_week(week_id):
    mon = monday_of_week(week_id)
    return f"{mon.year}.{mon.month:02d}"


def date_range_ko(week_id):
    mon = monday_of_week(week_id)
    sun = mon + datetime.timedelta(days=6)
    if mon.month == sun.month:
        return f"{mon.year}-{mon.month:02d}-{mon.day:02d} ~ {sun.month:02d}-{sun.day:02d}"
    return f"{mon.year}-{mon.month:02d}-{mon.day:02d} ~ {sun.year}-{sun.month:02d}-{sun.day:02d}"


def fetch_json(url, retries=2, timeout=20):
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retries:
                time.sleep(2 ** attempt)
    print(f"FETCH_ERROR: {type(last_err).__name__}: {last_err}", file=sys.stderr)
    sys.exit(2)


def short(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "0"
    if n >= 1000:
        return f"{n/1000:.1f}k".replace(".0k", "k")
    return str(n)


def is_ai(item):
    return any((c or {}).get("flag") == "ai" for c in (item.get("category") or []))


def filter_ai(items):
    return [it for it in items if is_ai(it)]


def rank_by_view(items):
    return sorted(items, key=lambda it: int(it.get("view_count") or 0), reverse=True)


def display_category(cats):
    """대표 카테고리: ai 아닌 첫 항목, 없으면 첫 항목 이름."""
    cats = cats or []
    non_ai = next((c.get("name") for c in cats if c.get("flag") != "ai" and c.get("name")), None)
    if non_ai:
        return non_ai
    return (cats[0].get("name") or "") if cats else ""


def build_pool_stats(popular_fetched, ai_in_pool):
    return {
        "popular_fetched": popular_fetched,
        "ai_in_pool": ai_in_pool,
        "pool_ai_share": round(ai_in_pool / popular_fetched, 3) if popular_fetched else 0,
    }


def flatten(item, detail, rank):
    """list item + detail(data) -> schema.json 기사 객체."""
    detail = detail or {}
    aid = item.get("id")
    cats = item.get("category") or []
    flags = [c.get("flag") for c in cats if c.get("flag")]
    author = (item.get("author") or {}).get("name") or ""
    url = ARTICLE_URL.format(id=aid)
    view = int(item.get("view_count") or 0)
    raw = {
        "summary": item.get("description") or "",
        "keywords": detail.get("hash_tags") or [],
        "body": detail.get("raw_content") or "",
        "view_count": view,
        "read_time": int(item.get("read_time") or 0),
        "is_popular_news": bool(item.get("is_popular_news")),
        "category_flags": flags,
        "date_published": item.get("date_published"),
    }
    return {
        "id": str(aid),
        "title": item.get("title") or "",
        "url": url,
        "rank": rank,
        "published_at": item.get("date_published"),
        "category": display_category(cats),
        "category_flags": flags,
        "author": author,
        "raw": raw,
        "links": [{"rank": 1, "label": "원문", "url": url}],
        "selected": None,
        "classify": None,
        "analysis": None,
        "learning": None,
        "interest": {"view_count": view, "popular_rank": rank, "weeks_on_popular": None},
    }


def collect_pool(pages):
    """여러 페이지의 popular 목록을 합쳐 반환."""
    all_items = []
    for page in range(1, pages + 1):
        data = fetch_json(LIST_URL.format(page=page))
        if not (isinstance(data, dict) and data.get("ok")):
            print("FETCH_ERROR: 목록 응답 형식 오류", file=sys.stderr)
            sys.exit(2)
        results = (data.get("data") or {}).get("results") or []
        all_items.extend(results)
        if not (data.get("data") or {}).get("next"):
            break
    return all_items


def main():
    ap = argparse.ArgumentParser(description="요즘IT 인기 AI 글 수집 (멱등)")
    ap.add_argument("--root", required=True)
    ap.add_argument("--week", default="auto", help="auto 또는 YYYY-Wnn")
    ap.add_argument("--date", default=None, help="기준 날짜 YYYY-MM-DD (week=auto)")
    ap.add_argument("--pool", type=int, default=12, help="저장할 AI 후보 최대 수")
    ap.add_argument("--pages", type=int, default=2, help="popular 목록 페이지 수")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    if args.week == "auto":
        base = datetime.date.fromisoformat(args.date) if args.date else datetime.date.today()
        week_id = iso_week_id(base)
    else:
        week_id = args.week

    root = args.root
    data_dir = os.path.join(root, "_data", "weeks")
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, f"{week_id}.json")
    raw_path = os.path.join(data_dir, f"{week_id}.raw.json")

    if os.path.exists(out_path) and not args.force:
        print(f"STATUS=exists week={week_id} path={out_path}")
        print("이미 수집된 주차입니다. 재수집하려면 --force 를 사용하세요.")
        return

    pool_items = collect_pool(args.pages)
    ai_items = filter_ai(pool_items)
    ranked = rank_by_view(ai_items)[:max(0, args.pool)]

    # 원본 박제(감사·재현용)
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump({"list": pool_items}, f, ensure_ascii=False, indent=2)

    articles = []
    for i, item in enumerate(ranked):
        detail_resp = fetch_json(DETAIL_URL.format(id=item.get("id")))
        detail = (detail_resp or {}).get("data") if isinstance(detail_resp, dict) else None
        articles.append(flatten(item, detail, i + 1))
        time.sleep(0.3)  # 예의상 간격

    popular_fetched = len(pool_items)
    ai_in_pool = len(ai_items)
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    record = {
        "schema_version": 1,
        "week_id": week_id,
        "date_range_ko": date_range_ko(week_id),
        "month_folder": month_folder_for_week(week_id),
        "collected_at": now,
        "source": f"yozm articleListApi?category=popular (pages={args.pages}) + fetchContentsDetail",
        "pool_stats": build_pool_stats(popular_fetched, ai_in_pool),
        "articles": articles,
        "week_summary": None,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    print(f"STATUS=ok week={week_id} ai_articles={len(articles)} "
          f"(인기 {popular_fetched}개 중 AI {ai_in_pool}개) month={record['month_folder']}")
    print(f"path={out_path}")
    print(f"기간: {record['date_range_ko']}")
    for a in articles:
        kws = ", ".join(a["raw"]["keywords"][:4])
        print(f"  {a['rank']}. {a['title']}")
        print(f"     👁 {short(a['raw']['view_count'])} · {a['raw']['read_time']}분 · {a['category']} · id:{a['id']}")
        if kws:
            print(f"     키워드: {kws}")


if __name__ == "__main__":
    main()
