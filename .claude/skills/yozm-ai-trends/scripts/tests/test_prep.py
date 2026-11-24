# -*- coding: utf-8 -*-
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import prep

SCRIPT = os.path.join(os.path.dirname(HERE), "prep.py")


def _art(aid, rank, views, flags=("ai",), keywords=(), body="본문", title=None):
    return {"id": aid, "title": title or f"글 {aid}", "url": f"https://x/{aid}", "rank": rank, "author": "필자",
            "published_at": "2026-11-01T09:00:00+09:00", "category_flags": list(flags),
            "raw": {"view_count": views, "keywords": list(keywords), "summary": "요약", "body": body}}


def _card(term, one_liner="한 줄"):
    return {"selected": True,
            "classify": {"primary_category": "ai", "topic_tags": ["claude-code"]},
            "analysis": {"one_liner": one_liner, "key_points": ["핵심 문장 하나"], "so_what": "시사점"},
            "learning": {"key_terms": [{"term": term, "gloss": "뜻"}], "apply_points": ["적용"],
                         "recall_quiz": {"question": "질문", "answer": "답"}}}


def _root(tmp_path):
    d = tmp_path / "_data"
    (d / "weeks").mkdir(parents=True)
    (d / "analysis").mkdir()
    # W40 다음 관측이 W42(W41 미관측)
    (d / "weeks" / "2026-W40.json").write_text(json.dumps({"week_id": "2026-W40", "articles": [
        _art("1", 1, 900), _art("2", 2, 500)]}), encoding="utf-8")
    (d / "weeks" / "2026-W40.raw.json").write_text("{}", encoding="utf-8")
    (d / "weeks" / "2026-W42.json").write_text(json.dumps({"week_id": "2026-W42", "pool_stats": {"pool_ai_share": 0.5},
        "articles": [_art("1", 1, 1000, keywords=["클로드 코드", "AI-Slop"]),
                     _art("3", 2, 300, flags=("develop",), body="새 글&nbsp;본문  끝")]}),
        encoding="utf-8")
    (d / "analysis" / "2026-W40.patch.json").write_text(json.dumps({"week_id": "2026-W40", "articles": {"1": _card("용어A")}}),
                                                         encoding="utf-8")
    (d / "analysis" / "2026-W40.summary.patch.json").write_text(json.dumps({"week_id": "2026-W40", "week_summary": {}}),
                                                                 encoding="utf-8")
    # 대상 주차(W42) 자신의 패치 — 과거 카드로 섞이면 안 된다
    (d / "analysis" / "2026-W42.patch.json").write_text(json.dumps({"week_id": "2026-W42", "articles": {"3": _card("용어B"), "1": _card("용어C")}}),
                                                         encoding="utf-8")
    (d / "index.json").write_text(json.dumps({"keyword_freq": {"claude-code": {"count": 5, "unique_articles": 4, "weeks": ["2026-W40"]},
                                                               "ai-slop": {"count": 1, "unique_articles": 1, "weeks": ["2026-W34"]}}}),
                                  encoding="utf-8")
    (d / "taxonomy.json").write_text(json.dumps({"keyword_aliases": {"claude-code": ["클로드코드"]}}), encoding="utf-8")
    return tmp_path


def _run(root, out, *extra):
    return subprocess.run([sys.executable, "-X", "utf8", SCRIPT, "--root", str(root), "--week", "2026-W42", "--out", str(out), *extra],
                          capture_output=True, text=True, encoding="utf-8")


def test_parse_related_and_split_ids():
    warns = []
    assert prep.parse_related("4033=3979, 3906;3998=3998", warns.append) == {"4033": ["3979", "3906"], "3998": ["3998"]}
    assert prep.parse_related("", warns.append) == {} and warns == []
    assert prep.split_ids(" 1, ,2,1 ") == ["1", "2"]


def test_parse_related_warns_on_malformed_parts():
    warns = []
    got = prep.parse_related("4033:3979;=3998;1=2;1=3", warns.append)
    assert got == {"1": ["2", "3"]}
    assert len(warns) == 3


def test_norm_ignores_space_hyphen_underscore():
    amap = prep.alias_map({"keyword_aliases": {"claude-code": ["클로드코드"]}}, {"ai-slop": {}})
    assert amap[prep.norm("클로드 코드")] == "claude-code"
    assert amap[prep.norm("Claude_Code")] == "claude-code"
    assert amap[prep.norm("AISlop")] == "ai-slop"


def test_previous_observed_week_skips_unobserved(tmp_path):
    root = _root(tmp_path)
    assert prep.previous_observed_week(str(root), "2026-W42") == "2026-W40"   # W41 없음, raw 제외
    assert prep.previous_observed_week(str(root), "2026-W40") is None


def test_collect_cards_excludes_target_and_later_weeks(tmp_path):
    root = _root(tmp_path)
    cards = prep.collect_cards(str(root), before="2026-W42")
    assert list(cards) == ["1"] and [w for w, _ in cards["1"]] == ["2026-W40"]


def test_clean_collapses_nbsp_and_entities():
    assert prep.clean("a&nbsp;b   c") == "a b c"


def test_delta_text_gap_and_sign():
    assert prep.delta_text(1000, None, 1) == "Δ신규"
    assert prep.delta_text(1000, 900, 1) == "Δ+100"
    assert prep.delta_text(50, 100, 1) == "Δ-50"
    assert prep.delta_text(1100, 900, 2) == "Δ+200/2주(주당 +100)"


def test_coverage_separates_covered_and_uncovered():
    card = {"analysis": {"key_points": ["Claude Code 세션 한도를 사용량 기준으로 다시 정리했다"]}}
    body = ("Claude Code 세션 한도를 사용량 기준으로 다시 정리했다. "
            "전혀 다른 주제의 문장으로 마무리하며 끝맺는다. 짧다.")
    total, rated, miss = prep.coverage(body, card)
    assert total == 3 and rated == 2
    assert [s for _, s in miss] == ["전혀 다른 주제의 문장으로 마무리하며 끝맺는다."]


def test_coverage_splits_on_closing_quote_and_endings():
    sents = [s for s in prep.SENT_SPLIT.split("그는 “됐다.” 다음 문장이다 그리고 둘 다 남는다.") if s.strip()]
    assert sents == ["그는 “됐다.", "다음 문장이다", "그리고 둘 다 남는다."]


def test_main_writes_files_and_reports(tmp_path):
    root = _root(tmp_path)
    out = tmp_path / "out"
    r = _run(root, out, "--sel", "1,3", "--related", "3=1;1=1", "--pick", "1,3", "--coverage", "1")
    assert r.returncode == 0, r.stderr
    body = (out / "w42_3.txt").read_text(encoding="utf-8")
    assert "새 글 본문 끝" in body and " " not in body
    related = (out / "w42_related_1.txt").read_text(encoding="utf-8")
    assert '"week": "2026-W40"' in related and "2026-W42" not in related and '"recall_quiz"' in related
    assert (out / "w42_past_terms.txt").read_text(encoding="utf-8") == "용어A"      # W42 자기 패치의 용어B·C 제외
    assert "⚠ 직전 관측 주차는 2026-W40(2주 전)" in r.stdout
    assert "1 1위 1,000 Δ+100/2주(주당 +50) · 분석 2026-W40" in r.stdout
    assert "2026-W40→2026-W42 이탈: [('2', 2," in r.stdout
    assert "선정 합 1,300(신규 300 + 재조명 1,000)" in r.stdout and "신규 = 미분석 후보 합 대비 100.0%" in r.stdout
    assert "클로드 코드→claude-code(5/4" in r.stdout and "AI-Slop→ai-slop(1/1" in r.stdout
    assert "[coverage] 1:" in r.stdout and "2026-W40 카드" in r.stdout


def test_main_rejects_ids_outside_pool_and_bad_week(tmp_path):
    root = _root(tmp_path)
    r = _run(root, tmp_path / "out", "--sel", "9")
    assert r.returncode == 1 and "풀에 없는 id" in r.stdout
    r = _run(root, tmp_path / "out", "--sel", "1", "--pick", "1,9")
    assert r.returncode == 1 and "['9']" in r.stdout
    r = subprocess.run([sys.executable, "-X", "utf8", SCRIPT, "--root", str(root), "--week", "auto", "--out", str(tmp_path / "o"),
                        "--sel", "1"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1 and "YYYY-Wnn" in r.stdout
