#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render.py — 분석 JSON → 예쁜 HTML 리포트 (템플릿 주입)

주차별 weeks/*.json(Claude가 분석 채움) + index.json(정량 롤업)을 읽어
report.html / monthly.html / master_index.html / article_card.html 템플릿에 주입한다.
조건부 렌더(빈 링크·미분석 생략), 순수 CSS/SVG 시각화, 인덱스 멱등 재생성.

사용:
  py render.py --root "C:\\...\\요즘IT" --week 2026-W27   # 주간 렌더 + 인덱스 재생성
  py render.py --root "C:\\...\\요즘IT"                    # 인덱스만 재생성
"""
import argparse
import datetime
import glob
import html
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL_DIR = os.path.join(SKILL_DIR, "templates")
LEFTOVER = re.compile(r"\{\{[A-Z_]+\}\}")


# ----------------------------- 유틸 -----------------------------
def esc(s):
    return html.escape(str(s if s is not None else ""))


def short(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "0"
    if n >= 1000:
        return f"{n/1000:.1f}k".replace(".0k", "k")
    return str(n)


def load_tpl(name):
    with open(os.path.join(TPL_DIR, name), encoding="utf-8") as f:
        return f.read()


def fill(tpl, mapping):
    for k, v in mapping.items():
        tpl = tpl.replace("{{" + k + "}}", v if v is not None else "")
    return LEFTOVER.sub("", tpl)  # 미사용 토큰 제거


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_all_weeks(root):
    weeks = []
    for p in sorted(glob.glob(os.path.join(root, "_data", "weeks", "*.json"))):
        if p.endswith(".raw.json"):
            continue
        weeks.append(load_json(p))
    weeks.sort(key=lambda w: w.get("week_id", ""))
    return weeks


def cat_label_map(taxonomy):
    m = {}
    for c in (taxonomy.get("primary_categories") or []):
        m[c["key"]] = c.get("label_ko", c["key"])
    return m


def now_str():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")


def first_sentence(text):
    t = (text or "").replace("\n", " ").strip()
    if not t:
        return ""
    for sep in ["다. ", ". ", "다.", "."]:
        idx = t.find(sep)
        if 0 < idx < 160:
            return t[:idx + (1 if sep.strip() == "." else 2)].strip()
    return t[:140].strip()


def paper_tags(paper):
    cls = paper.get("classify") or {}
    if cls.get("topic_tags"):
        return cls["topic_tags"]
    return [k.strip().lower().replace(" ", "-") for k in (paper.get("raw", {}).get("keywords") or [])]


# ----------------------------- 카드 -----------------------------
def build_card(article, idx, cat_labels, streak=1):
    raw = article.get("raw", {})
    an = article.get("analysis") or {}
    learn = article.get("learning") or {}
    cls = article.get("classify") or {}
    interest = article.get("interest") or {}

    url = next((l["url"] for l in article.get("links", []) if l.get("rank") == 1), article.get("url", ""))

    cat = ""
    if cls.get("primary_category") and cls["primary_category"] != "(미분류)":
        cat = cat_labels.get(cls["primary_category"], cls["primary_category"])
    elif article.get("category"):
        cat = article["category"]

    author = article.get("author") or "요즘IT"
    pub = str(article.get("published_at") or "")[:10]

    # 배지: 조회수 · 읽기시간 · 연속 인기
    badges = [f'<span class="badge badge--up">👁 {short(interest.get("view_count") or raw.get("view_count"))}</span>']
    if raw.get("read_time"):
        badges.append(f'<span class="badge badge--cm">⏱ {raw["read_time"]}분</span>')
    if streak and streak >= 2:
        badges.insert(0, f'<span class="badge badge--streak">🔁 {streak}주 연속 인기</span>')
    badges_html = "".join(badges)

    chips = paper_tags(article)[:6]
    chips_html = "".join(f'<span class="chip">{esc(c)}</span>' for c in chips)

    one = an.get("one_liner") or first_sentence(raw.get("summary")) or article.get("title")
    oneliner = esc(one)

    # 항상 보이는 요약(gist)
    summary_txt = an.get("summary_ko") or raw.get("summary") or ""
    summary_html = f'<p>{esc(summary_txt)}</p>' if summary_txt else ""

    # 항상 보이는 메타 라인(유형·독자·발행일)
    meta_bits = []
    if cls.get("article_type"):
        meta_bits.append(f'<span class="ac-tag">{esc(cls["article_type"])}</span>')
    if an.get("reader"):
        meta_bits.append(f'<span>{esc(an["reader"])}</span>')
    if pub:
        meta_bits.append(f'<span>📅 {esc(pub)}</span>')
    meta_html = " · ".join(meta_bits)

    # 접이식 상세: 핵심 포인트 · 왜 지금 · 실무 시사점 · 실무 적용 · 핵심 용어 · 복습 퀴즈
    sec = []
    if an.get("key_points"):
        lis = "".join(f"<li>{esc(x)}</li>" for x in an["key_points"])
        sec.append(f'<div class="ac-sec"><h4>핵심 포인트</h4><ul class="ac-list">{lis}</ul></div>')
    if an.get("why_now"):
        sec.append(f'<div class="ac-sec"><h4>왜 지금</h4><p>{esc(an["why_now"])}</p></div>')
    if an.get("so_what"):
        sec.append(f'<div class="ac-sec"><h4>실무 시사점</h4><p>{esc(an["so_what"])}</p></div>')
    if learn.get("apply_points"):
        lis = "".join(f"<li>{esc(x)}</li>" for x in learn["apply_points"])
        sec.append(f'<div class="ac-sec"><h4>실무 적용 포인트</h4><ul class="ac-list">{lis}</ul></div>')
    if learn.get("key_terms"):
        terms = "".join(
            f'<span class="term"><b>{esc(kt.get("term"))}</b> {esc(kt.get("gloss") or "")}</span>'
            for kt in learn["key_terms"]
        )
        sec.append(f'<div class="ac-sec"><h4>핵심 용어</h4><div class="terms">{terms}</div></div>')
    rq = learn.get("recall_quiz") or {}
    if rq.get("question"):
        sec.append(
            '<div class="ac-sec"><div class="quiz">'
            f'<p class="quiz__q"><b>RECALL ↺</b> {esc(rq["question"])}</p>'
            f'<details><summary>정답 보기</summary><p class="quiz__a">{esc(rq.get("answer"))}</p></details>'
            '</div></div>'
        )
    detail_html = ""
    if sec:
        detail_html = (
            '<details class="ac-detail"><summary>'
            '<span class="ac-detail-caret">▸</span>'
            '<span class="ac-detail-label">자세히 보기</span>'
            '<span class="ac-detail-hint">핵심 포인트 · 왜 지금 · 실무 시사점 · 용어 · 복습</span>'
            f'</summary><div class="ac-detail-body">{"".join(sec)}</div></details>'
        )

    btns = [f'<a class="btn btn--primary" href="{esc(l["url"])}" target="_blank" rel="noopener">{esc(l["label"])}</a>'
            for l in sorted(article.get("links", []), key=lambda x: x.get("rank", 99))]
    links_html = "".join(btns)

    return fill(load_tpl("article_card.html"), {
        "STAGGER": str(idx),
        "TAGS": esc(" ".join((an.get("field_tags") or []) + chips)).lower(),
        "RANK": f"{int(article.get('rank', idx)):02d}",
        "CAT": esc(cat),
        "URL": esc(url),
        "TITLE": esc(article.get("title")),
        "AUTHORS": esc(author),
        "BADGES": badges_html,
        "CHIPS": chips_html,
        "ONELINER": oneliner,
        "SUMMARY": summary_html,
        "META": meta_html,
        "DETAIL": detail_html,
        "LINKS": links_html,
    })


# ----------------------------- 시각화 -----------------------------
def build_kwbar(tag_counts, title="이번 주 키워드 빈도"):
    if not tag_counts:
        return ""
    rows = sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:6]
    vmax = max(v for _, v in rows) or 1
    out = [f'<h4>{esc(title)}</h4>']
    for i, (t, v) in enumerate(rows):
        pct = round(v / vmax * 100)
        out.append(
            f'<div class="kwbar__row"><span title="{esc(t)}">{esc(t)}</span>'
            f'<div class="kwbar__track"><i style="--v:{pct}%;--d:{0.15+i*0.08:.2f}s"></i></div>'
            f'<b>{v}</b></div>'
        )
    return "".join(out)


def build_sparkline(points, label="주차별 관심도(조회수) 추이"):
    """points: [(wid, value), ...] 오름차순"""
    if len(points) < 2:
        return ('<h4 style="margin-top:1.4rem">' + esc(label) + '</h4>'
                '<p style="font-size:.75rem;color:var(--text-faint);font-family:var(--font-mono)">'
                '데이터 축적 중 — 2주 이상부터 추이가 표시됩니다.</p>')
    W, H, px, py = 300, 90, 14, 14
    vals = [v for _, v in points]
    vmax, vmin = max(vals), min(vals)
    span = (vmax - vmin) or 1
    n = len(points)
    coords = []
    for i, (_, v) in enumerate(points):
        x = px + i * (W - 2 * px) / (n - 1)
        y = (H - py) - (v - vmin) / span * (H - 2 * py)
        coords.append((x, y))
    line_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    area = f'M {coords[0][0]:.1f},{H-py} ' + " ".join(f"L {x:.1f},{y:.1f}" for x, y in coords) + f' L {coords[-1][0]:.1f},{H-py} Z'
    dots = "".join(f'<circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="2.6"/>' for x, y in coords)
    labels = ""
    for i, (wid, _) in enumerate(points):
        wk = wid.split("-W")[-1] if "-W" in wid else wid
        anchor = "start" if i == 0 else ("end" if i == n - 1 else "middle")
        labels += f'<text x="{coords[i][0]:.1f}" y="{H-2}" text-anchor="{anchor}">W{esc(wk)}</text>'
    return (
        f'<h4 style="margin-top:1.4rem">{esc(label)}</h4>'
        f'<svg class="trend-svg" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(label)}">'
        '<defs>'
        '<linearGradient id="auroraStroke" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#FFB020"/><stop offset="1" stop-color="#FF7A45"/></linearGradient>'
        '<linearGradient id="auroraFill" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#FFB020"/><stop offset="1" stop-color="#FFB020" stop-opacity="0"/></linearGradient>'
        '</defs>'
        f'<path class="area" d="{area}"/><polyline class="line" points="{line_pts}"/>{dots}{labels}'
        '</svg>'
    )


def build_insight(week, index_data):
    ws = week.get("week_summary") or {}
    # 좌: 서술형 인사이트
    notes = []
    if ws.get("narrative_ko"):
        notes.append(f'<div class="insight__note"><h3>📋 이번 주 요약</h3><p>{esc(ws["narrative_ko"])}</p></div>')
    if ws.get("recent_trend_ko"):
        notes.append(f'<div class="insight__note"><h3>🌊 최근 동향</h3><p>{esc(ws["recent_trend_ko"])}</p></div>')
    if ws.get("ai_share_note"):
        notes.append(f'<div class="insight__note"><h3>📊 AI 점유율</h3><p>{esc(ws["ai_share_note"])}</p></div>')
    if ws.get("emerging_keywords"):
        chips = "".join(f'<span class="chip">{esc(k)}</span>' for k in ws["emerging_keywords"])
        notes.append(f'<div class="insight__note"><h3>✨ 새로 부상 <span class="tag tag--emerging">EMERGING</span></h3><div class="chip-row" style="margin-top:.5rem">{chips}</div></div>')
    if not notes:
        notes.append('<div class="insight__note"><p style="color:var(--text-faint)">동향 분석이 아직 작성되지 않았습니다.</p></div>')

    # 우: 이번 주 키워드 빈도 + 조회수 추이
    articles = [a for a in (week.get("articles") or []) if a.get("selected")]
    tag_counts = {}
    for a in articles:
        for t in set(paper_tags(a)):
            tag_counts[t] = tag_counts.get(t, 0) + 1
    kwbar = build_kwbar(tag_counts)

    spark = ""
    per_week = (index_data or {}).get("per_week") or {}
    if per_week:
        pts = [(w, per_week[w].get("total_views", 0)) for w in sorted(per_week)]
        spark = build_sparkline(pts, label="주차별 관심도(조회수) 추이")

    return (
        '<div class="insight"><div class="insight__grid">'
        f'<div>{"".join(notes)}</div>'
        f'<aside class="kwbar">{kwbar}{spark}</aside>'
        '</div></div>'
    )


def stat_block(num, label):
    return f'<div class="stat"><span class="stat__num">{num}</span><span class="stat__label">{esc(label)}</span></div>'


# ----------------------------- 주간 리포트 -----------------------------
def render_week(root, week_id, taxonomy, index_data):
    week = load_json(os.path.join(root, "_data", "weeks", f"{week_id}.json"))
    if not week:
        print(f"ERROR: {week_id}.json 없음", file=sys.stderr)
        sys.exit(1)
    cat_labels = cat_label_map(taxonomy)
    all_articles = week.get("articles") or []
    articles = [a for a in all_articles if a.get("selected") and a.get("analysis")]
    if not articles:
        articles = [a for a in all_articles if a.get("selected")]  # 분석 전 미리보기 폴백
    ws = week.get("week_summary") or {}

    # 연속 등장(streak): 이번 주에서 거슬러 올라가며 연속으로 트렌딩한 주차 수
    weeks_covered = (index_data or {}).get("weeks_covered") or []
    article_weeks = (index_data or {}).get("article_weeks") or {}

    def streak_for(pid):
        appears = set(article_weeks.get(pid, []))
        appears.add(week_id)  # 이번 주는 당연히 포함
        if week_id not in weeks_covered:
            return 1
        i = weeks_covered.index(week_id)
        s = 0
        while i >= 0 and weeks_covered[i] in appears:
            s += 1
            i -= 1
        return s

    cards = "\n".join(build_card(a, i + 1, cat_labels, streak_for(a.get("id"))) for i, a in enumerate(articles))

    pool = week.get("pool_stats") or {}
    share_pct = round((pool.get("pool_ai_share") or 0) * 100)
    distinct_tags = len({t for a in articles for t in paper_tags(a)})
    stats = (stat_block(len(articles), "선정 글")
             + stat_block(f"{share_pct}%", "인기 중 AI")
             + stat_block(distinct_tags, "키워드"))

    headline = ws.get("headline_ko") or "이번 주 요즘IT 인기 AI 글을 수집·분석했습니다."
    lede = f'이번 주 한 줄 트렌드: <b>{esc(headline)}</b>' if ws.get("headline_ko") else esc(headline)
    caveat = ws.get("caveats_ko") or "요즘IT 인기 목록의 AI 관련 상위 글 기준이며, view_count는 누적 조회수(관심도)로 최신·중요도와 다를 수 있습니다."

    out = fill(load_tpl("report.html"), {
        "TITLE": f"{week_id} 요즘IT AI 트렌드 리포트",
        "ASSETS": "../_assets",
        "ROOT": "..",
        "MONTH_LABEL": esc(week.get("month_folder", "")),
        "EYEBROW": esc(f'{week_id} · {week.get("date_range_ko","")}'),
        "HERO_TITLE": f'이번 주 가장 주목받은 <em>요즘IT AI 글 {len(articles)}건</em>',
        "LEDE": lede,
        "STATS": stats,
        "COUNT": str(len(articles)),
        "CARDS": cards,
        "INSIGHT": build_insight(week, index_data),
        "CAVEAT": esc(caveat),
        "GENERATED": now_str(),
    })

    month_dir = os.path.join(root, week.get("month_folder", "misc"))
    os.makedirs(month_dir, exist_ok=True)
    out_path = os.path.join(month_dir, f"{week_id}_주간리포트.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"WROTE {out_path}")
    return out_path


# ----------------------------- 주차 카드 -----------------------------
def week_card(week, href):
    articles = [a for a in (week.get("articles") or []) if a.get("selected")]
    ws = week.get("week_summary") or {}
    total_views = sum(int(a.get("raw", {}).get("view_count") or 0) for a in articles)
    tag_counts = {}
    for a in articles:
        for t in set(paper_tags(a)):
            tag_counts[t] = tag_counts.get(t, 0) + 1
    top = [t for t, _ in sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:3]]
    chips = "".join(f'<span class="chip">{esc(t)}</span>' for t in top)
    title = ws.get("headline_ko") or "주간 트렌딩 리포트"
    return (
        f'<a class="week-card" href="{esc(href)}" data-tags="{esc(" ".join(top)).lower()}">'
        f'<span class="week-card__wk">{esc(week.get("week_id"))} · {esc(week.get("date_range_ko",""))}</span>'
        f'<div class="week-card__title">{esc(title)}</div>'
        f'<div class="week-card__meta"><span>📄 {len(articles)}건</span><span>👁 {short(total_views)}</span></div>'
        f'<div class="chip-row">{chips}</div>'
        '</a>'
    )


# ----------------------------- 인덱스 재생성 -----------------------------
def render_indexes(root, taxonomy, index_data):
    weeks = load_all_weeks(root)
    by_month = {}
    for w in weeks:
        by_month.setdefault(w.get("month_folder", "misc"), []).append(w)

    # 월간 인덱스
    for month, mweeks in by_month.items():
        mweeks_sorted = sorted(mweeks, key=lambda w: w.get("week_id", ""), reverse=True)
        cards = "\n".join(week_card(w, f'{w.get("week_id")}_주간리포트.html') for w in mweeks_sorted)
        m_articles = sum(len([a for a in (w.get("articles") or []) if a.get("selected")]) for w in mweeks)
        m_views = sum(int(a.get("raw", {}).get("view_count") or 0)
                      for w in mweeks for a in (w.get("articles") or []) if a.get("selected"))
        stats = stat_block(len(mweeks), "주차") + stat_block(m_articles, "글") + stat_block(short(m_views), "총 조회수")
        y, mm = month.split(".") if "." in month else (month, "")
        synthesis = build_monthly_synthesis(root, month, mweeks, index_data)
        out = fill(load_tpl("monthly.html"), {
            "TITLE": f"{month} 월간 요즘IT AI 트렌드",
            "ASSETS": "../_assets",
            "ROOT": "..",
            "EYEBROW": esc(f"{month} · 월간 관측 일지"),
            "HERO_TITLE": f"{esc(y)}년 {esc(mm)}월 <em>요즘IT AI 글 흐름</em>",
            "LEDE": f"이 달 {len(mweeks)}개 주차, 총 {m_articles}건의 요즘IT AI 글을 정리했습니다.",
            "STATS": stats,
            "SYNTHESIS": synthesis,
            "WEEK_CARDS": cards,
            "GENERATED": now_str(),
        })
        mdir = os.path.join(root, month)
        os.makedirs(mdir, exist_ok=True)
        with open(os.path.join(mdir, "index.html"), "w", encoding="utf-8") as f:
            f.write(out)
        print(f"WROTE {os.path.join(mdir, 'index.html')}")

    # 마스터 인덱스
    total_articles = sum(len([a for a in (w.get("articles") or []) if a.get("selected")]) for w in weeks)
    distinct_kw = len((index_data or {}).get("keyword_freq") or {})
    stats = stat_block(len(weeks), "주차") + stat_block(total_articles, "글") + stat_block(distinct_kw or "—", "누적 키워드")

    # 누적 상위 키워드 패널
    top_kw_html = ""
    kf = (index_data or {}).get("keyword_freq") or {}
    if kf:
        counts = {t: r["count"] for t, r in kf.items()}
        bar = build_kwbar(counts, title="누적 상위 키워드")
        top_kw_html = f'<section class="section"><h2 class="section-title"><span class="ix">★</span> 누적 트렌드 신호</h2><div class="insight"><aside class="kwbar">{bar}</aside></div></section>'

    # 월별 섹션
    sections = []
    for month in sorted(by_month, reverse=True):
        mweeks_sorted = sorted(by_month[month], key=lambda w: w.get("week_id", ""), reverse=True)
        cards = "\n".join(week_card(w, f'{month}/{w.get("week_id")}_주간리포트.html') for w in mweeks_sorted)
        sections.append(
            f'<div class="month-band"><h2>{esc(month)}</h2><div class="rule"></div>'
            f'<a href="{esc(month)}/index.html">월간 상세 →</a></div>'
            f'<div class="card-grid">{cards}</div>'
        )
    if not sections:
        sections.append('<div class="empty-state"><div class="big">아직 리포트가 없습니다</div>'
                        '<p>스킬을 실행해 첫 주간 리포트를 생성하세요.</p></div>')

    out = fill(load_tpl("master_index.html"), {
        "STATS": stats,
        "TOP_KEYWORDS": top_kw_html,
        "MONTH_SECTIONS": "\n".join(sections),
        "GENERATED": now_str(),
    })
    with open(os.path.join(root, "index.html"), "w", encoding="utf-8") as f:
        f.write(out)
    print(f"WROTE {os.path.join(root, 'index.html')}")


def build_monthly_synthesis(root, month, mweeks, index_data):
    """_data/months/{month}.json 이 있으면 월간 종합 섹션을 임베드. 없으면 안내."""
    data = load_json(os.path.join(root, "_data", "months", f"{month}.json"))
    if not data:
        return ('<div class="caveat"><span>🗓️</span><p>월간 종합 트렌드는 <b>월말</b>에 생성됩니다. '
                '현재는 주차별 리포트를 누적 중입니다.</p></div>')
    notes = []
    for blk in (data.get("synthesis") or []):
        tagcls = {"persist": "tag--persist", "emerging": "tag--emerging", "cooling": "tag--cooling"}.get(blk.get("tag"), "tag--persist")
        tagtxt = {"persist": "지속", "emerging": "부상", "cooling": "식어감"}.get(blk.get("tag"), "")
        tag_html = f'<span class="tag {tagcls}">{tagtxt}</span>' if tagtxt else ""
        notes.append(f'<div class="insight__note"><h3>{esc(blk.get("title"))} {tag_html}</h3><p>{esc(blk.get("body"))}</p></div>')
    # 월간 추이 (이 달 주차별 조회수)
    pts = [(w.get("week_id"), sum(int(a.get("raw", {}).get("view_count") or 0)
                                   for a in (w.get("articles") or []) if a.get("selected")))
           for w in sorted(mweeks, key=lambda x: x.get("week_id", ""))]
    spark = build_sparkline(pts, label="이 달 주차별 관심도 추이")
    headline = data.get("headline_ko") or "이 달의 요즘IT AI 트렌드"
    return (
        '<section class="section"><h2 class="section-title"><span class="ix">∑</span> 월간 종합 트렌드</h2>'
        f'<p class="hero__lede" style="margin-bottom:1.3rem">{esc(headline)}</p>'
        '<div class="insight"><div class="insight__grid">'
        f'<div>{"".join(notes)}</div><aside class="kwbar">{spark}</aside>'
        '</div></div></section>'
    )


# ----------------------------- main -----------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--week", default=None, help="YYYY-Wnn (지정 시 주간 렌더)")
    args = ap.parse_args()
    root = args.root

    taxonomy = load_json(os.path.join(root, "_data", "taxonomy.json"), {})
    index_data = load_json(os.path.join(root, "_data", "index.json"), {})

    if args.week:
        render_week(root, args.week, taxonomy, index_data)
    render_indexes(root, taxonomy, index_data)
    print("STATUS=ok")


if __name__ == "__main__":
    main()
