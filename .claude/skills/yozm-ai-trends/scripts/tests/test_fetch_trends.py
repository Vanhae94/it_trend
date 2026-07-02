# -*- coding: utf-8 -*-
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import fetch_trends as ft

FIX = os.path.join(HERE, "fixtures")

def load(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return json.load(f)

def test_iso_week_id():
    import datetime
    assert ft.iso_week_id(datetime.date(2026, 7, 2)) == "2026-W27"

def test_filter_ai_only_keeps_ai_flagged():
    items = load("list_popular.json")["data"]["results"]
    ai = ft.filter_ai(items)
    assert len(ai) >= 1
    for it in ai:
        assert any(c.get("flag") == "ai" for c in (it.get("category") or []))

def test_rank_by_view_desc():
    items = load("list_popular.json")["data"]["results"]
    ranked = ft.rank_by_view(items)
    views = [it.get("view_count", 0) for it in ranked]
    assert views == sorted(views, reverse=True)

def test_flatten_shape():
    results = load("list_popular.json")["data"]["results"]
    # NOTE: pick an AI-flagged item explicitly rather than assuming results[0]
    # is AI-flagged, so this test stays stable regardless of which article
    # happens to rank #1 in the live fixture at capture time.
    item = next(it for it in results if ft.is_ai(it))
    detail = load("detail_3801.json")["data"]
    art = ft.flatten(item, detail, rank=1)
    assert art["id"] and art["title"] and art["url"].endswith(str(item["id"]))
    assert art["raw"]["body"]           # raw_content 채워짐
    assert isinstance(art["raw"]["keywords"], list)
    assert art["selected"] is None and art["analysis"] is None
    assert art["interest"]["view_count"] == item["view_count"]
    assert "ai" in art["category_flags"]
