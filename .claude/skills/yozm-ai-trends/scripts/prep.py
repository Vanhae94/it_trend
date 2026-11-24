#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prep.py — 주간 분석 준비 (본문·관련 카드·과거 용어 파일 + 선정 판단용 수치)

선별 후보를 정한 뒤, 분석 에이전트가 읽을 파일을 작업 폴더(--out)에 만들고
선정 판단과 주간 요약에 쓸 수치를 stdout으로 보여준다(판단은 Claude가 한다).
과거 카드는 대상 주차보다 앞선 주차의 패치에서만 모은다(candidates.py와 같은 규칙).

  · w<주>_<id>.txt          — 기사 머리말(순위·조회수·flags·해시태그) + 요약 + 본문 평문
  · w<주>_related_<id>.txt  — 관련 과거 주차 카드(같은 시리즈·필자·주제, 재조명이면 자기 카드)
  · w<주>_past_terms.txt    — 지금까지 카드가 풀이한 key_terms 목록(중복 방지용)
  · stdout                  — 상위 5건 합·미분석 후보 합·선정 합(신규/재조명), 직전 관측 주차 대비 증가,
                              풀 이탈·첫 등장, 해시태그 → 기존 키, (--coverage) 재조명 후보의 카드 미커버 문장

사용(한 줄로 입력):
  py prep.py --root "C:\\...\\요즘IT" --week 2026-W48 --out "<작업 폴더>" --sel 4033,4029,4028,3997,3998 --related "4033=3979,3906;3998=3998,3951" --pick 4033,4029,4028,3998 --coverage 3997,3998
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

WEEK_RE = re.compile(r"\d{4}-W\d{2}")
COVERAGE_MIN = 0.3   # 카드 어휘가 이 비율 미만으로 덮인 문장을 '미커버'로 본다
COVERAGE_SHOW = 25   # 미커버 문장 출력 상한
# 문장 경계: 문장 부호(닫는 따옴표·괄호 포함) 또는 자주 쓰는 종결어미 뒤의 공백
SENT_SPLIT = re.compile(r"(?<=[.?!])[\"'”’)\]]?\s+|(?<=니다|어요|아요|에요|이다|했다|한다|된다|있다|없다|봤다|왔다)\s+")
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\-]*(?:\.[A-Za-z0-9]+)*|\d[\d,.]*\d%?|\d%|[가-힣]{3,}")


def load_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def clean(s):
    return re.sub(r"[ \t\u00a0]+", " ", html.unescape(s or "")).strip()


def norm(s):
    """별칭 대조용: 소문자 + 공백·하이픈·밑줄 제거(양쪽에 같은 규칙)."""
    return re.sub(r"[\s\-_]", "", (s or "").lower())


def split_ids(s):
    return list(dict.fromkeys(x.strip() for x in (s or "").split(",") if x.strip()))


def parse_related(s, warn=print):
    """'4033=3979,3906;3998=3998,3951' → {'4033': ['3979', '3906'], '3998': ['3998', '3951']}"""
    out = {}
    for part in (s or "").split(";"):
        if not part.strip():
            continue
        if "=" not in part:
            warn(f"WARN: --related 조각 '{part.strip()}'에 '='가 없어 건너뜁니다")
            continue
        k, v = part.split("=", 1)
        k = k.strip()
        if not k:
            warn(f"WARN: --related 조각 '{part.strip()}'에 기사 id가 없어 건너뜁니다")
            continue
        if k in out:
            warn(f"WARN: --related에 {k}가 두 번 나와 관련 id를 합칩니다")
        out[k] = list(dict.fromkeys(out.get(k, []) + split_ids(v)))
    return out


def iso_monday(week_id):
    y, w = (int(x) for x in week_id.split("-W"))
    return datetime.date.fromisocalendar(y, w, 1)


def previous_observed_week(root, week_id):
    """관측을 건너뛴 주가 있어도 직전에 실제로 수집한 주차를 찾는다."""
    ids = [os.path.basename(f)[:-5] for f in glob.glob(os.path.join(root, "_data", "weeks", "*-W*.json"))]
    earlier = sorted(w for w in ids if WEEK_RE.fullmatch(w) and w < week_id)
    return earlier[-1] if earlier else None


def collect_cards(root, before):
    """before 주차보다 앞선 분석 패치에서 선정 카드를 모은다: {id: [(week_id, card), ...]} (주차 오름차순)."""
    cards = {}
    for f in sorted(glob.glob(os.path.join(root, "_data", "analysis", "*-W*.patch.json"))):
        if f.endswith(".summary.patch.json"):
            continue
        d = load_json(f, {}) or {}
        wid = d.get("week_id") or os.path.basename(f).split(".")[0]
        if wid >= before:
            continue
        for aid, c in (d.get("articles") or {}).items():
            if c.get("selected") and "analysis" in c:
                cards.setdefault(aid, []).append((wid, c))
    return cards


def alias_map(taxonomy, keyword_freq=None):
    m = {}
    for k, vs in (taxonomy.get("keyword_aliases") or {}).items():
        m[norm(k)] = k
        for v in vs:
            m[norm(v)] = k
    for k in keyword_freq or {}:
        m.setdefault(norm(k), k)
    return m


def coverage(body, card):
    """본문 문장마다 카드 어휘가 덮는 비율을 재서, 덮임이 낮은 문장을 돌려준다(어림 지표).
    반환: (전체 문장 수, 평가한 문장 수, [(덮임, 문장), ...])"""
    text = json.dumps(card, ensure_ascii=False)
    sents = [s for s in SENT_SPLIT.split(body) if s and s.strip()]
    rated, miss = 0, []
    for s in sents:
        toks = set(TOKEN_RE.findall(s))
        if len(toks) < 4:
            continue
        rated += 1
        cov = sum(1 for t in toks if t in text) / len(toks)
        if cov < COVERAGE_MIN:
            miss.append((round(cov, 2), s.strip()))
    return len(sents), rated, miss


def delta_text(now, prev, gap):
    if prev is None:
        return "Δ신규"
    d = now - int(prev)
    if gap and gap > 1:
        return f"Δ{d:+,}/{gap}주(주당 {round(d / gap):+,})"
    return f"Δ{d:+,}"


def main():
    ap = argparse.ArgumentParser(description="주간 분석 준비 파일·수치 생성")
    ap.add_argument("--root", required=True)
    ap.add_argument("--week", required=True, help="YYYY-Wnn")
    ap.add_argument("--out", required=True, help="본문·관련 카드 파일을 쓸 작업 폴더(스크래치패드 권장)")
    ap.add_argument("--sel", required=True, help="파일을 만들 기사 id(쉼표 구분) — 분석 대상과 검토할 재조명 후보")
    ap.add_argument("--related", default="", help="관련 카드: 'id=관련id,관련id;id=...' (재조명이면 자기 id를 넣는다)")
    ap.add_argument("--pick", default="", help="조회수 합을 낼 최종 선정 id(생략하면 --sel 전체를 선정으로 본다)")
    ap.add_argument("--coverage", default="", help="직전 카드와 본문을 대조할 재조명 후보 id(쉼표 구분)")
    args = ap.parse_args()

    root, wk = args.root, args.week
    if not WEEK_RE.fullmatch(wk):
        print(f"ERROR: --week는 YYYY-Wnn 형식이어야 합니다(받은 값 {wk!r})")
        sys.exit(1)
    n = wk.split("-W")[1]
    cur = load_json(os.path.join(root, "_data", "weeks", f"{wk}.json"))
    if not cur:
        print(f"ERROR: {wk}.json 이 없습니다 — fetch_trends.py를 먼저 돌리세요.")
        sys.exit(1)
    A = {a["id"]: a for a in cur.get("articles", [])}
    sel = split_ids(args.sel)
    pick = split_ids(args.pick) or sel
    missing = [i for i in dict.fromkeys(sel + pick) if i not in A]
    if missing:
        print(f"ERROR: 이번 주 풀에 없는 id {missing}")
        sys.exit(1)
    related = parse_related(args.related)
    for k in related:
        if k not in sel:
            print(f"WARN: --related의 {k}가 --sel에 없습니다(관련 카드 파일만 만듭니다)")
    os.makedirs(args.out, exist_ok=True)

    prev_id = previous_observed_week(root, wk)
    prv = load_json(os.path.join(root, "_data", "weeks", f"{prev_id}.json"), {}) if prev_id else {}
    P = {a["id"]: a for a in (prv or {}).get("articles", [])}
    gap = (iso_monday(wk) - iso_monday(prev_id)).days // 7 if prev_id else None
    if gap and gap > 1:
        print(f"⚠ 직전 관측 주차는 {prev_id}({gap}주 전) — 증가분은 {gap}주 누적치입니다")

    # ── 본문 파일
    for aid in sel:
        a = A[aid]; r = a.get("raw") or {}
        body = clean(r.get("body"))
        with open(os.path.join(args.out, f"w{n}_{aid}.txt"), "w", encoding="utf-8") as f:
            f.write(f"ID: {aid}\n제목: {a.get('title')}\nURL: {a.get('url')}\n저자: {a.get('author')}\n발행: {a.get('published_at')}\n"
                    f"순위: {a.get('rank')}위 / 조회수 {int(r.get('view_count') or 0):,}\n요즘IT 원본 카테고리 flags: {a.get('category_flags')}\n"
                    f"hash_tags: {r.get('keywords')}\n\n[요약]\n{clean(r.get('summary'))}\n\n[본문]\n{body}\n")
        print(f"본문 {aid}: {len(body)}자, 발행 {(a.get('published_at') or '')[:10]}, 저자 {a.get('author')}")

    # ── 관련 카드·과거 용어(대상 주차 이전 카드만)
    cards = collect_cards(root, before=wk)
    for aid, rel in related.items():
        out = []
        for rid in rel:
            for cw, c in cards.get(rid, []):
                out.append({"id": rid, "week": cw, "primary": c["classify"]["primary_category"],
                            "topic_tags": c["classify"]["topic_tags"], "one_liner": c["analysis"]["one_liner"],
                            "key_points": c["analysis"]["key_points"], "so_what": c["analysis"]["so_what"],
                            "key_terms": [t["term"] for t in c["learning"]["key_terms"]],
                            "apply_points": c["learning"]["apply_points"],
                            "recall_quiz": c["learning"].get("recall_quiz")})
        with open(os.path.join(args.out, f"w{n}_related_{aid}.txt"), "w", encoding="utf-8") as f:
            f.write(f"[{aid}와 관련된 과거 주차 카드 — 같은 시리즈·같은 필자·같은 주제. 내용·용어·적용 지침·퀴즈를 되풀이하지 말 것]\n"
                    + json.dumps(out, ensure_ascii=False, indent=2))
        print(f"관련 {aid}: {[(o['id'], o['week']) for o in out]}")
    terms = sorted({t["term"] for v in cards.values() for _, c in v for t in c["learning"]["key_terms"]})
    with open(os.path.join(args.out, f"w{n}_past_terms.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(terms))
    print("과거 key_terms", len(terms))

    # ── 조회수 합(분모 함께). 신규는 미분석 후보와, 전체는 상위 5건과 견준다
    views = lambda a: int((a.get("raw") or {}).get("view_count") or 0)
    top5 = sorted(cur["articles"], key=lambda x: -views(x))[:5]
    t5 = sum(views(x) for x in top5)
    unan = [x for x in cur["articles"] if x["id"] not in cards]
    u_sum = sum(views(x) for x in unan)
    new_sum = sum(views(A[i]) for i in pick if i not in cards)
    rev_sum = sum(views(A[i]) for i in pick if i in cards)
    p_sum = new_sum + rev_sum
    print(f"\n상위5 합 {t5:,} {[(x['id'], x['rank'], views(x)) for x in top5]} · 그중 기분석 {[x['id'] for x in top5 if x['id'] in cards]}")
    print(f"미분석 {[(x['id'], x['rank'], views(x)) for x in unan]} 합 {u_sum:,}")
    label = "선정 합" if args.pick else "선정 합(--pick 없음 → --sel 전체)"
    line = f"{label} {p_sum:,}(신규 {new_sum:,} + 재조명 {rev_sum:,})"
    if t5:
        line += f" · 1위 비중 {views(top5[0]) / t5 * 100:.1f}% · 상위5 대비 {p_sum / t5 * 100:.1f}%"
    if u_sum:
        line += f" · 신규 = 미분석 후보 합 대비 {new_sum / u_sum * 100:.1f}%"
    print(line)
    for i in sel:
        a = A[i]; pv = ((P.get(i) or {}).get("raw") or {}).get("view_count")
        hist = [cw for cw, _ in cards.get(i, [])]
        print(f"  {i} {a['rank']}위 {views(a):,} {delta_text(views(a), pv, gap)}{' · 분석 ' + '·'.join(hist) if hist else ''}")
    if prv:
        print(f"{prev_id}→{wk} 이탈:", [(p["id"], p["rank"], p["title"][:26]) for p in prv["articles"] if p["id"] not in A])
        print(f"{wk} 첫 등장:", [(a["id"], a["rank"], a["title"][:26]) for a in cur["articles"] if a["id"] not in P])
    print("pool:", cur.get("pool_stats"), "· 비AI:", [(a["id"], a["rank"]) for a in cur["articles"] if "ai" not in (a.get("category_flags") or [])])

    # ── 해시태그 → 기존 키(힌트: 별칭과 keyword_freq 키를 공백·하이픈·밑줄 무시하고 대조)
    kf = (load_json(os.path.join(root, "_data", "index.json"), {}) or {}).get("keyword_freq") or {}
    amap = alias_map(load_json(os.path.join(root, "_data", "taxonomy.json"), {}) or {}, kf)
    print("\n해시태그 → 기존 키")
    for i in sel:
        hits = []
        for kw in (A[i].get("raw") or {}).get("keywords") or []:
            k = amap.get(norm(kw))
            if k:
                f = kf.get(k, {})
                hits.append(f"{kw.strip()}→{k}({f.get('count')}/{f.get('unique_articles')}, last {(f.get('weeks') or [None])[-1]})")
        print(f"  {i}:", hits or "기존 키 없음")

    # ── 재조명 후보의 카드 미커버 문장(어림 지표 — 판정은 사람/에이전트가 한다)
    for i in split_ids(args.coverage):
        if i not in A or not cards.get(i):
            print(f"\n[coverage] {i}: 풀에 없거나 {wk} 이전 분석 카드가 없습니다")
            continue
        cw, card = cards[i][-1]
        body = clean((A[i].get("raw") or {}).get("body"))
        total, rated, miss = coverage(body, card)
        kp = sum(len(k) for k in card["analysis"]["key_points"])
        print(f"\n[coverage] {i}: 본문 {len(body)}자 · {cw} 카드 KP 합 {kp}자 · 문장 {total}개 중 평가 {rated}개, "
              f"카드 어휘 덮임 {COVERAGE_MIN:.0%} 미만 {len(miss)}개")
        for c, s in miss[:COVERAGE_SHOW]:
            print(f"   {c} {s[:170]}")


if __name__ == "__main__":
    main()
