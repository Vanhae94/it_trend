# 요즘IT AI 트렌드 주간 관측기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 요즘IT 인기 글 중 AI 관련 상위 4~5개를 매주(수동 요청 시) 수집·분석하고 누적 트렌드를 웜 다크 HTML 리포트로 정리하는 자기완결형 시스템을 만든다.

**Architecture:** 논문정리(AI Papers Weekly) 아키텍처를 이식. 결정론 작업(수집·집계·렌더)은 Python 표준 라이브러리 스크립트, 판단·서술(선별·분석·트렌드)은 Claude. 수집은 요즘IT 공개 JSON API(`articleListApi`, `fetchContentsDetail`) 사용 — HTML 파싱 없음. 데이터는 3층(weeks/index/taxonomy), 패치 기반 병합으로 멱등.

**Tech Stack:** Python 3.8+ (표준 라이브러리 `urllib`,`json`,`datetime`,`glob`,`html`,`re`만 — pip 없음), 순수 HTML/CSS/JS(외부 차트 라이브러리 0, 폰트 CDN). Windows/PowerShell 실행(`py`).

**참고 원본 경로(읽기용, 복사·각색 대상):** `C:\Users\juse9\OneDrive\Desktop\지성\논문정리`
**신규 프로젝트 루트(ROOT):** `C:\Users\juse9\OneDrive\Desktop\지성\요즘IT`
**스킬 디렉터리(SKILL_DIR):** `<ROOT>\.claude\skills\yozm-ai-trends`

> 모든 스크립트 파일은 `# -*- coding: utf-8 -*-` 및 파일 I/O `encoding="utf-8"` 유지. 콘솔 한글 출력 위해 상단에 `sys.stdout.reconfigure(encoding="utf-8")` try/except 포함.

---

## File Structure

| 파일 | 책임 | 유형 |
|---|---|---|
| `SKILL_DIR/scripts/fetch_trends.py` | 인기 목록+본문 API 수집·평탄화·멱등 저장 | 신규(전체 코드) |
| `SKILL_DIR/scripts/merge_analysis.py` | Claude 분석 패치를 주차 기록에 병합 | 신규(전체 코드) |
| `SKILL_DIR/scripts/rollup.py` | 전 주차 정량 롤업 → index.json | 신규(전체 코드) |
| `SKILL_DIR/scripts/render.py` | 분석 JSON → Nightdesk HTML + 인덱스 | 원본 복사+각색 |
| `SKILL_DIR/schema.json` | weeks 기사 객체 데이터 명세 | 신규(전체) |
| `SKILL_DIR/SKILL.md` | 주간 워크플로우 절차(Claude 지침) | 신규(전체) |
| `SKILL_DIR/templates/{report,monthly,master_index,article_card}.html` | HTML 템플릿 | 원본 복사+각색 |
| `<ROOT>/_data/taxonomy.json` | 폐쇄형 10 분류 + 키워드 별칭 | 신규(전체) |
| `<ROOT>/_assets/style.css` | Nightdesk 디자인 시스템 | 원본 복사+토큰 교체 |
| `<ROOT>/_assets/app.js` | 테마 토글 + 인덱스 필터 | 원본 그대로 복사 |
| `<ROOT>/.claude/launch.json` | 미리보기 정적 서버 | 신규(전체) |
| `<ROOT>/README.md` | 사용법 문서 | 신규(전체) |

각 파일은 단일 책임. 스크립트 4종은 서로 파일(weeks/index)로만 통신(잘 정의된 인터페이스).

---

## Task 1: 프로젝트 스캐폴딩 + launch.json

**Files:**
- Create: `<ROOT>\.claude\skills\yozm-ai-trends\scripts\` (디렉터리)
- Create: `<ROOT>\.claude\skills\yozm-ai-trends\templates\` (디렉터리)
- Create: `<ROOT>\_data\weeks\`, `<ROOT>\_data\analysis\`, `<ROOT>\_data\months\`, `<ROOT>\_assets\`
- Create: `<ROOT>\.claude\launch.json`

- [ ] **Step 1: 디렉터리 생성**

Bash:
```bash
cd "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT"
mkdir -p .claude/skills/yozm-ai-trends/scripts .claude/skills/yozm-ai-trends/templates _data/weeks _data/analysis _data/months _assets
```

- [ ] **Step 2: launch.json 작성** (미리보기용 정적 서버)

`<ROOT>\.claude\launch.json`:
```json
{
  "version": "0.0.1",
  "configurations": [
    {
      "name": "yozm-preview",
      "runtimeExecutable": "py",
      "runtimeArgs": ["-m", "http.server", "5599"],
      "port": 5599
    }
  ]
}
```

- [ ] **Step 3: 커밋**
```bash
git add -A && git commit -m "chore: 프로젝트 디렉터리 스캐폴딩 + launch.json"
```

---

## Task 2: taxonomy.json (폐쇄형 분류 + 키워드 별칭)

**Files:**
- Create: `<ROOT>\_data\taxonomy.json`

- [ ] **Step 1: 파일 작성**

`<ROOT>\_data\taxonomy.json`:
```json
{
  "schema_version": 1,
  "description": "요즘IT AI 트렌드 분석용 폐쇄형 분류 체계. 주차 간 비교를 위해 카테고리는 고정 목록만 사용한다. keyword_aliases는 신규 키워드 등장 시 누적 관리.",
  "primary_categories": [
    { "key": "ai-coding",        "label_ko": "AI 코딩·개발도구", "scope_ko": "바이브코딩, 코딩 에이전트, Copilot/Cursor/Claude Code, 코드 생성" },
    { "key": "ai-agents",        "label_ko": "AI 에이전트·자동화", "scope_ko": "에이전트, 워크플로우, MCP, 툴 사용, 자동화" },
    { "key": "models-llm",       "label_ko": "모델·LLM 동향", "scope_ko": "신모델 출시, 벤더 경쟁, 성능·벤치마크, 오픈소스 모델" },
    { "key": "ai-product",       "label_ko": "AI 프로덕트·서비스", "scope_ko": "AI 기능 탑재 제품, SaaS, 기능 기획, AX" },
    { "key": "ways-of-working",  "label_ko": "일하는 법·조직", "scope_ko": "팀 생산성, 프로세스, AI 도입, 협업" },
    { "key": "career",           "label_ko": "커리어·직무", "scope_ko": "직무 변화, PM/개발/디자인 커리어, 생존 전략, 채용" },
    { "key": "design-ux",        "label_ko": "디자인·UX", "scope_ko": "AI 시대 디자인, UX, 크리에이티브 도구" },
    { "key": "data-infra",       "label_ko": "데이터·인프라", "scope_ko": "RAG, 벡터DB, 파인튜닝, 인프라, 데이터 파이프라인" },
    { "key": "safety-risk",      "label_ko": "보안·리스크·윤리", "scope_ko": "AI 보안, 저작권, 규제, 신뢰성, 프라이버시" },
    { "key": "business-market",  "label_ko": "비즈니스·시장", "scope_ko": "투자, 시장 동향, 전략, 수익화" }
  ],
  "category_rules": {
    "max_categories_per_article": 2,
    "primary_category_count": 1,
    "note_ko": "기사당 categories는 최대 2개, primary_category는 정확히 1개. 무제한 허용 시 신호가 죽는다."
  },
  "article_type_axis": ["튜토리얼", "오피니언", "사례", "뉴스분석", "인터뷰"],
  "keyword_aliases": {
    "vibe-coding":     ["바이브코딩", "vibe coding", "바이브 코딩"],
    "claude-code":     ["claudecode", "claude code", "클로드코드", "클로드 코드"],
    "coding-agent":    ["코딩 에이전트", "coding agent", "code agent", "codex"],
    "ai-agent":        ["에이전트", "agent", "agents", "ai agent", "멀티에이전트", "multi-agent", "multi agent"],
    "mcp":             ["model context protocol", "엠씨피"],
    "rag":             ["retrieval augmented generation", "retrieval-augmented", "검색 증강"],
    "llm":             ["대규모 언어모델", "large language model", "언어모델"],
    "prompt":          ["프롬프트", "prompting", "프롬프트 엔지니어링", "prompt engineering"],
    "productivity":    ["생산성", "팀 생산성"],
    "open-source-llm": ["오픈소스 모델", "오픈소스 llm", "open source llm", "ollama", "llama", "qwen", "deepseek"],
    "security":        ["보안", "시큐리티"],
    "fine-tuning":     ["파인튜닝", "fine tuning", "미세조정"]
  }
}
```

- [ ] **Step 2: JSON 유효성 검증**

Run:
```bash
py -c "import json; json.load(open('C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/_data/taxonomy.json', encoding='utf-8')); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: 커밋**
```bash
git add -A && git commit -m "feat: 요즘IT AI 실무형 폐쇄 분류체계(taxonomy.json)"
```

---

## Task 3: schema.json (weeks 기사 객체 명세)

**Files:**
- Create: `<ROOT>\.claude\skills\yozm-ai-trends\schema.json`

- [ ] **Step 1: 파일 작성**

`SKILL_DIR\schema.json`:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "yozm-ai-trends/week.schema.json",
  "title": "주차별 기사 분석 기록 (_data/weeks/YYYY-Wnn.json)",
  "description": "fetch_trends.py가 raw + 골격을 생성하고, Claude가 selected/classify/analysis/learning/week_summary를 채운다. render.py가 이 파일로 HTML을 생성. raw는 절대 수정 금지(증거).",
  "type": "object",
  "required": ["schema_version", "week_id", "month_folder", "collected_at", "source", "articles"],
  "properties": {
    "schema_version": { "type": "integer", "const": 1 },
    "week_id": { "type": "string", "pattern": "^[0-9]{4}-W[0-9]{2}$" },
    "date_range_ko": { "type": "string" },
    "month_folder": { "type": "string", "pattern": "^[0-9]{4}\\.[0-9]{2}$" },
    "collected_at": { "type": "string" },
    "source": { "type": "string" },
    "pool_stats": {
      "type": "object",
      "properties": {
        "popular_fetched": { "type": "integer" },
        "ai_in_pool": { "type": "integer" },
        "pool_ai_share": { "type": "number" }
      }
    },
    "articles": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "title", "url", "rank", "raw", "links"],
        "properties": {
          "id": { "type": "string" },
          "title": { "type": "string" },
          "url": { "type": "string" },
          "rank": { "type": "integer", "description": "pool 내 view_count 순위 1..N" },
          "published_at": { "type": ["string", "null"] },
          "category": { "type": "string", "description": "대표 카테고리 라벨(요즘IT)" },
          "category_flags": { "type": "array", "items": { "type": "string" } },
          "author": { "type": "string" },
          "raw": {
            "type": "object",
            "description": "API 원본(평탄화). 불변.",
            "properties": {
              "summary": { "type": "string" },
              "keywords": { "type": "array", "items": { "type": "string" } },
              "body": { "type": "string", "description": "raw_content 평문 본문" },
              "view_count": { "type": "integer" },
              "read_time": { "type": "integer" },
              "is_popular_news": { "type": "boolean" },
              "category_flags": { "type": "array", "items": { "type": "string" } },
              "date_published": { "type": ["string", "null"] }
            }
          },
          "links": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["rank", "label", "url"],
              "properties": {
                "rank": { "type": "integer" },
                "label": { "type": "string" },
                "url": { "type": "string" }
              }
            }
          },
          "selected": { "type": ["boolean", "null"], "description": "Claude가 이번 주 분석 대상(4~5개)에 true" },
          "classify": {
            "type": ["object", "null"],
            "properties": {
              "categories": { "type": "array", "maxItems": 2, "items": { "type": "string" } },
              "primary_category": { "type": "string" },
              "topic_tags": { "type": "array", "items": { "type": "string" } },
              "article_type": { "type": "string" },
              "confidence": { "type": "string", "enum": ["high", "medium", "low"] }
            }
          },
          "analysis": {
            "type": ["object", "null"],
            "description": "1단계 분석(본문 기반, selected 전부).",
            "properties": {
              "one_liner": { "type": "string", "description": "40~70자 한 줄 핵심" },
              "summary_ko": { "type": "string", "description": "2~3문장 요약" },
              "key_points": { "type": "array", "items": { "type": "string" }, "description": "불릿 3~5" },
              "why_now": { "type": "string", "description": "트렌드 관점 2~3문장" },
              "so_what": { "type": "string", "description": "실무 시사점 2~3문장" },
              "reader": { "type": "string" },
              "field_tags": { "type": "array", "items": { "type": "string" } }
            }
          },
          "learning": {
            "type": ["object", "null"],
            "properties": {
              "apply_points": { "type": "array", "items": { "type": "string" } },
              "key_terms": {
                "type": "array",
                "items": { "type": "object", "properties": { "term": { "type": "string" }, "gloss": { "type": "string" } } }
              },
              "recall_quiz": { "type": "object", "properties": { "question": { "type": "string" }, "answer": { "type": "string" } } },
              "spaced_review": { "type": "object", "properties": { "flag": { "type": "boolean" }, "review_due": { "type": ["string", "null"] } } }
            }
          },
          "interest": {
            "type": "object",
            "properties": {
              "view_count": { "type": "integer" },
              "popular_rank": { "type": "integer" },
              "weeks_on_popular": { "type": ["integer", "null"] }
            }
          }
        }
      }
    },
    "week_summary": {
      "type": ["object", "null"],
      "properties": {
        "headline_ko": { "type": "string" },
        "clusters": {
          "type": "array",
          "items": { "type": "object", "properties": {
            "category": { "type": "string" },
            "article_ranks": { "type": "array", "items": { "type": "integer" } },
            "theme_ko": { "type": "string" }
          } }
        },
        "emerging_keywords": { "type": "array", "items": { "type": "string" } },
        "narrative_ko": { "type": "string" },
        "recent_trend_ko": { "type": "string" },
        "ai_share_note": { "type": "string" },
        "caveats_ko": { "type": "string" }
      }
    }
  }
}
```

- [ ] **Step 2: JSON 유효성 검증**

Run:
```bash
py -c "import json; json.load(open('C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/.claude/skills/yozm-ai-trends/schema.json', encoding='utf-8')); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: 커밋**
```bash
git add -A && git commit -m "feat: weeks 기사 객체 데이터 명세(schema.json)"
```

---

## Task 4: fetch_trends.py (수집기, 신규 전체 코드) + 테스트

**Files:**
- Create: `SKILL_DIR\scripts\fetch_trends.py`
- Create: `SKILL_DIR\scripts\tests\fixtures\list_popular.json` (테스트 픽스처)
- Create: `SKILL_DIR\scripts\tests\fixtures\detail_3801.json` (테스트 픽스처)
- Test: `SKILL_DIR\scripts\tests\test_fetch_trends.py`

- [ ] **Step 1: 테스트 픽스처 저장(실제 API 응답 박제)**

Bash:
```bash
cd "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/.claude/skills/yozm-ai-trends/scripts"
mkdir -p tests/fixtures
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
curl -s -A "$UA" "https://yozm.wishket.com/api/articleListApi/?category=popular&page=1&ordering=new" -o tests/fixtures/list_popular.json
curl -s -A "$UA" "https://yozm.wishket.com/api/fetchContentsDetail/?id=3801&affectView=false" -o tests/fixtures/detail_3801.json
py -c "import json; a=json.load(open('tests/fixtures/list_popular.json',encoding='utf-8')); d=json.load(open('tests/fixtures/detail_3801.json',encoding='utf-8')); print('list ok=%s n=%d' % (a['ok'], len(a['data']['results']))); print('detail ok=%s has_raw=%s' % (d['ok'], 'raw_content' in d['data']))"
```
Expected: `list ok=True n=10` / `detail ok=True has_raw=True`

- [ ] **Step 2: 실패하는 테스트 작성**

`SKILL_DIR\scripts\tests\test_fetch_trends.py`:
```python
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
    item = load("list_popular.json")["data"]["results"][0]
    detail = load("detail_3801.json")["data"]
    art = ft.flatten(item, detail, rank=1)
    assert art["id"] and art["title"] and art["url"].endswith(str(item["id"]))
    assert art["raw"]["body"]           # raw_content 채워짐
    assert isinstance(art["raw"]["keywords"], list)
    assert art["selected"] is None and art["analysis"] is None
    assert art["interest"]["view_count"] == item["view_count"]
    assert "ai" in art["category_flags"]
```

- [ ] **Step 3: 테스트 실행 → 실패 확인**

Run:
```bash
cd "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/.claude/skills/yozm-ai-trends/scripts"
py -m pytest tests/test_fetch_trends.py -q  ||  py tests/test_fetch_trends.py
```
Expected: FAIL/에러 — `fetch_trends` 모듈/함수 없음. (pytest 미설치 시 아래 Step 5의 수동 러너 사용)

- [ ] **Step 4: fetch_trends.py 구현**

`SKILL_DIR\scripts\fetch_trends.py`:
```python
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
    print(f"FETCH_ERROR {type(last_err).__name__}: {last_err}", file=sys.stderr)
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
    return cats[0].get("name") if cats else ""


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
    ranked = rank_by_view(ai_items)[:args.pool]

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
        "pool_stats": {
            "popular_fetched": popular_fetched,
            "ai_in_pool": ai_in_pool,
            "pool_ai_share": round(ai_in_pool / popular_fetched, 3) if popular_fetched else 0,
        },
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
```

- [ ] **Step 5: 테스트 실행 → 통과 확인**

Run (pytest 있으면):
```bash
cd "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/.claude/skills/yozm-ai-trends/scripts"
py -m pytest tests/test_fetch_trends.py -q
```
pytest 없으면 수동 러너:
```bash
py -c "import tests.test_fetch_trends as t; [getattr(t,n)() for n in dir(t) if n.startswith('test_')]; print('ALL PASS')"
```
Expected: 모든 테스트 통과(`ALL PASS`).

- [ ] **Step 6: 실제 수집 스모크 테스트(이번 주)**

Run:
```bash
py "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/.claude/skills/yozm-ai-trends/scripts/fetch_trends.py" --root "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT" --week auto
```
Expected: `STATUS=ok week=... ai_articles=N (인기 M개 중 AI K개)` + 기사 목록 출력. `_data/weeks/<주차>.json` 생성됨.

- [ ] **Step 7: 커밋**
```bash
git add -A && git commit -m "feat: 요즘IT 인기 AI 글 수집기(fetch_trends.py) + 테스트"
```

---

## Task 5: merge_analysis.py (패치 병합, 신규 전체 코드)

**Files:**
- Create: `SKILL_DIR\scripts\merge_analysis.py`

- [ ] **Step 1: 파일 작성**

`SKILL_DIR\scripts\merge_analysis.py`:
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
merge_analysis.py — Claude가 작성한 분석 패치를 주차 기록에 병합

Claude는 거대한 weeks/*.json을 직접 편집하지 않는다. 분석만 담은 작은 패치 JSON을 작성하고,
이 스크립트가 raw를 보존한 채 selected/classify/analysis/learning/week_summary만 안전히 합친다(멱등, 부분 갱신).

패치 형식:
{
  "week_id": "2026-W27",
  "articles": {
    "<id>": { "selected": true, "classify": {...}, "analysis": {...}, "learning": {...} },
    ...
  },
  "week_summary": { ... }
}
(articles의 각 키는 일부만 있어도 됨 — 있는 키만 갱신.)

사용: py merge_analysis.py --root "C:\\...\\요즘IT" --patch "C:\\...\\patch.json"
"""
import argparse
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MERGE_KEYS = ("selected", "classify", "analysis", "learning")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--patch", required=True)
    args = ap.parse_args()

    with open(args.patch, encoding="utf-8") as f:
        patch = json.load(f)

    week_id = patch.get("week_id")
    if not week_id:
        print("ERROR: patch에 week_id 없음", file=sys.stderr)
        sys.exit(1)

    week_path = os.path.join(args.root, "_data", "weeks", f"{week_id}.json")
    if not os.path.exists(week_path):
        print(f"ERROR: {week_path} 없음. 먼저 fetch_trends.py 실행", file=sys.stderr)
        sys.exit(1)

    with open(week_path, encoding="utf-8") as f:
        week = json.load(f)

    patch_articles = patch.get("articles") or {}
    by_id = {a.get("id"): a for a in week.get("articles", [])}
    updated = 0
    unknown = []
    for aid, fields in patch_articles.items():
        target = by_id.get(str(aid))
        if not target:
            unknown.append(aid)
            continue
        for k in MERGE_KEYS:
            if k in fields:
                target[k] = fields[k]
        updated += 1

    if "week_summary" in patch:
        week["week_summary"] = patch["week_summary"]

    with open(week_path, "w", encoding="utf-8") as f:
        json.dump(week, f, ensure_ascii=False, indent=2)

    print(f"STATUS=ok week={week_id} updated_articles={updated}")
    if unknown:
        print(f"WARN: weeks 파일에 없는 id(무시됨): {', '.join(map(str, unknown))}", file=sys.stderr)
    if "week_summary" in patch:
        print("week_summary 갱신됨")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 병합 스모크 테스트**

임시 패치로 검증(이번 주 수집 완료 상태에서, 첫 기사 id 하나에 selected=true 병합):
```bash
cd "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT"
py -c "import json,glob; p=sorted(glob.glob('_data/weeks/*-W*.json'))[-1]; p=[x for x in [p] if not x.endswith('.raw.json')][0]; w=json.load(open(p,encoding='utf-8')); aid=w['articles'][0]['id']; wid=w['week_id']; json.dump({'week_id':wid,'articles':{aid:{'selected':True}}}, open('_data/analysis/'+wid+'.patch.json','w',encoding='utf-8'), ensure_ascii=False); print('patch for',wid,aid)"
py ".claude/skills/yozm-ai-trends/scripts/merge_analysis.py" --root "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT" --patch "_data/analysis/$(py -c "import json,glob;print(json.load(open(sorted([x for x in glob.glob('_data/weeks/*.json') if not x.endswith('.raw.json')])[-1],encoding='utf-8'))['week_id'])").patch.json"
```
Expected: `STATUS=ok week=... updated_articles=1`

- [ ] **Step 3: 커밋**
```bash
git add -A && git commit -m "feat: 분석 패치 병합기(merge_analysis.py)"
```

---

## Task 6: rollup.py (정량 롤업, 신규 전체 코드)

**Files:**
- Create: `SKILL_DIR\scripts\rollup.py`

- [ ] **Step 1: 파일 작성**

`SKILL_DIR\scripts\rollup.py`:
```python
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
        tags = [normalize_kw(k, alias_map) for k in (article.get("raw", {}).get("keywords") or [])]
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
                weeks.append(json.load(f))
        except Exception as e:  # noqa: BLE001
            print(f"WARN: {p} 읽기 실패: {e}", file=sys.stderr)
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
            wk_views += int(a.get("raw", {}).get("view_count") or 0)
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
```

- [ ] **Step 2: 롤업 스모크 테스트**

Run:
```bash
py "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/.claude/skills/yozm-ai-trends/scripts/rollup.py" --root "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT"
```
Expected: `STATUS=ok weeks=1 selected=... keywords=...` + `_data/index.json` 생성.

- [ ] **Step 3: 커밋**
```bash
git add -A && git commit -m "feat: 정량 롤업(rollup.py) — 추이·streak·AI 점유율"
```

---

## Task 7: _assets/app.js + style.css (Nightdesk)

**Files:**
- Create: `<ROOT>\_assets\app.js` (원본 그대로 복사)
- Create: `<ROOT>\_assets\style.css` (원본 복사 + 토큰 교체)

- [ ] **Step 1: app.js 그대로 복사**

Bash:
```bash
cp "C:/Users/juse9/OneDrive/Desktop/지성/논문정리/_assets/app.js" "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/_assets/app.js"
```
(테마 토글 로직만 있고 색상 없음 → 그대로 사용. localStorage 키 `aipw-theme`는 유지해도 무해.)

- [ ] **Step 2: style.css 복사**

Bash:
```bash
cp "C:/Users/juse9/OneDrive/Desktop/지성/논문정리/_assets/style.css" "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/_assets/style.css"
```

- [ ] **Step 3: `:root`(다크 기본) 토큰 블록 교체**

`<ROOT>\_assets\style.css`의 `:root { ... }` 블록(색상 부분)을 Nightdesk 값으로 교체. `--ink*/--panel/--surface*/--border*` 및 `--text*`, 액센트(`--aurora* → --amber*`)를 아래로 바꾼다. 폰트·shape·type 토큰은 유지:
```css
:root {
  --ink:        #17130E;
  --ink-2:      #1C1710;
  --panel:      #201A13;
  --surface:    rgba(255,220,170,.04);
  --surface-2:  rgba(255,220,170,.07);
  --border:     #2E2619;
  --border-2:   #3A3020;

  --text:       #F5EEE3;
  --text-dim:   #B3A791;
  --text-faint: #8C806C;

  --aurora:     #FFB020;  /* 주 액센트(앰버) */
  --aurora-2:   #FF9A3C;  /* 보조 */
  --aurora-3:   #C98A3A;  /* 분위기용 */
  --ember:      #FF7A45;  /* 핫/열기 */
  --rose:       #FF8FA0;  /* 강조2 */
  --star:       #F4C860;  /* 골드 */

  --grad-aurora: linear-gradient(115deg, #FFB020 0%, #FF7A45 100%);
  --grad-text:   linear-gradient(100deg, #FFC661 0%, #FF9A3C 100%);
  /* shadow/glow는 앰버 톤으로 */
  --glow:      0 0 0 1px rgba(255,176,32,.25), 0 8px 32px -8px rgba(255,176,32,.28);
}
```
(원본에 있던 `--shadow`, `--font-*`, `--fs-*`, `--radius*`, `--gap`, `--maxw` 줄은 그대로 남긴다.)

- [ ] **Step 4: `[data-theme="light"]` 토큰 블록 교체**

```css
[data-theme="light"] {
  --ink:        #FBF8F3;
  --ink-2:      #FFFFFF;
  --panel:      #FFFFFF;
  --surface:    rgba(120,80,20,.03);
  --surface-2:  rgba(120,80,20,.06);
  --border:     #ECE4D8;
  --border-2:   #DFD3C2;

  --text:       #211C16;
  --text-dim:   #6B6259;
  --text-faint: #A2988B;

  --aurora:     #C2761A;
  --aurora-2:   #B8600F;
  --aurora-3:   #9A6A2A;
  --ember:      #E8590C;
  --star:       #B98A12;

  --grad-text:  linear-gradient(100deg, #C2761A 0%, #E8590C 100%);
  --glow:       0 0 0 1px rgba(194,118,26,.3), 0 8px 28px -10px rgba(194,118,26,.25);
}
```

- [ ] **Step 5: 하드코딩 청록 잔재 치환**

`style.css` 전체에서 원본 오로라 하드코딩 hex를 앰버로 치환(있을 때만):
- `#3DDC97` → `#FFB020`
- `#2BB6C9` → `#FF7A45`
- `#5BE8AC` → `#FFC661`
- `#46C8D6` → `#FF9A3C`

Run(확인):
```bash
grep -nE "#3DDC97|#2BB6C9|#5BE8AC|#46C8D6" "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/_assets/style.css" || echo "청록 잔재 없음(OK)"
```
Expected: `청록 잔재 없음(OK)`

- [ ] **Step 6: 커밋**
```bash
git add -A && git commit -m "feat: Nightdesk 디자인 시스템(style.css) + app.js"
```

---

## Task 8: 템플릿 4종 (원본 복사 + 각색)

**Files:**
- Create: `SKILL_DIR\templates\report.html`, `monthly.html`, `master_index.html` (복사+각색)
- Create: `SKILL_DIR\templates\article_card.html` (paper_card.html 복사+각색)

- [ ] **Step 1: 4개 템플릿 복사**

Bash:
```bash
S="C:/Users/juse9/OneDrive/Desktop/지성/논문정리/.claude/skills/ai-paper-trends/templates"
D="C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/.claude/skills/yozm-ai-trends/templates"
cp "$S/report.html" "$D/report.html"
cp "$S/monthly.html" "$D/monthly.html"
cp "$S/master_index.html" "$D/master_index.html"
cp "$S/paper_card.html" "$D/article_card.html"
```

- [ ] **Step 2: article_card.html 내용 교체 (전체 덮어쓰기)**

`SKILL_DIR\templates\article_card.html` 전체를 아래로 교체(render.py Task 9의 build_card 토큰과 1:1 대응):
```html
<article class="article-card" style="--i:{{STAGGER}}" data-tags="{{TAGS}}">
  <span class="rank">{{RANK}}</span>
  <span class="pc-cat">{{CAT}}</span>
  <h3 class="paper-card__title"><a href="{{URL}}" target="_blank" rel="noopener">{{TITLE}}</a></h3>
  <p class="pc-authors">{{AUTHORS}}</p>

  <div class="badges">{{BADGES}}</div>
  <div class="chip-row">{{CHIPS}}</div>

  <p class="pc-oneliner">{{ONELINER}}</p>
  <div class="pc-body">{{BODY}}</div>
  {{KEYPOINTS}}
  {{WHYNOW}}
  {{SOWHAT}}

  <div class="pc-meta-row">{{META}}</div>

  <div class="terms">{{TERMS}}</div>
  {{APPLY}}

  <div class="link-group">{{LINKS}}</div>
  {{QUIZ}}
</article>
```
(클래스명 `paper-card__title/pc-*`는 style.css의 기존 규칙 재사용을 위해 유지. 최상위만 `article-card`.)

- [ ] **Step 3: report.html 각색 (문구/토큰)**

`SKILL_DIR\templates\report.html`에서 아래를 수정(구조·CSS 링크·테마 토글 버튼은 유지):
- 사이트/헤더 문구: "AI 논문" → "요즘IT AI 트렌드", "논문" → "글/기사" 로 라벨 텍스트 교체.
- 남는 토큰 `{{TITLE}}{{ASSETS}}{{ROOT}}{{MONTH_LABEL}}{{EYEBROW}}{{HERO_TITLE}}{{LEDE}}{{STATS}}{{COUNT}}{{CARDS}}{{INSIGHT}}{{CAVEAT}}{{GENERATED}}` 는 render.py가 채우므로 그대로 둔다.
- 카드 포함 방식은 render가 `{{CARDS}}`에 article_card들을 주입하므로 변경 불필요.

- [ ] **Step 4: monthly.html / master_index.html 각색**

- 헤더/타이틀의 "논문" 계열 문구를 "요즘IT AI 트렌드/글"로 교체.
- 토큰(`{{...}}`)은 유지(render.py가 채움): monthly = `TITLE,ASSETS,ROOT,EYEBROW,HERO_TITLE,LEDE,STATS,SYNTHESIS,WEEK_CARDS,GENERATED`; master = `STATS,TOP_KEYWORDS,MONTH_SECTIONS,GENERATED`.
- 각 HTML `<head>`의 `<title>`과 `<link rel="stylesheet" href="{{ASSETS}}/style.css">`, 테마 토글 스크립트(`app.js`) 참조가 그대로인지 확인.

- [ ] **Step 5: 검증(다음 Task 9 렌더 후 남는 토큰 없어야 함)**

이 Task 단독 검증은 생략하고 Task 9 Step 3에서 통합 검증한다.

- [ ] **Step 6: 커밋**
```bash
git add -A && git commit -m "feat: Nightdesk 템플릿 4종(report/monthly/master_index/article_card)"
```

---

## Task 9: render.py (원본 복사 + 각색)

**Files:**
- Create: `SKILL_DIR\scripts\render.py` (논문정리 render.py 복사 후 아래 함수 교체)

- [ ] **Step 1: 원본 복사**

Bash:
```bash
cp "C:/Users/juse9/OneDrive/Desktop/지성/논문정리/.claude/skills/ai-paper-trends/scripts/render.py" "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/.claude/skills/yozm-ai-trends/scripts/render.py"
```

- [ ] **Step 2: 유지되는 부분**

다음은 그대로 사용: 상단 import/`esc`/`short`/`load_tpl`/`fill`/`load_json`/`load_all_weeks`/`cat_label_map`/`now_str`/`first_sentence`/`build_kwbar`/`render_indexes`/`build_monthly_synthesis`/`main`. 단 아래 세부만 변경:
- `paper_tags(paper)` → 키워드 소스가 `raw.keywords`(hash_tags)이므로 함수 내부 `raw.get("ai_keywords")`를 `raw.get("keywords")`로 교체.
- `build_sparkline`의 SVG gradient stop `#3DDC97/#2BB6C9` → `#FFB020/#FF7A45` 로 교체(2군데 `stop-color`).
- `render_indexes`/`week_card`/`build_monthly_synthesis` 내 `w.get("papers")` → `w.get("articles")`, `raw.get("upvotes")` 합산 → `raw.get("view_count")` 합산, `"📄 {n}편"`/"▲" 라벨 → `"📄 {n}건"`/"👁"으로 교체. `week_card`는 selected 기준으로 개수 집계.

- [ ] **Step 3: `build_card` 함수 전체 교체**

render.py의 `build_card`와 `build_deep`를 삭제하고 아래로 교체(tier2/deep 제거, analysis/learning 사용):
```python
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

    one = an.get("one_liner") or first_sentence(raw.get("summary")) or esc(article.get("title"))
    oneliner = esc(one)

    body_html = f'<p>{esc(an.get("summary_ko") or raw.get("summary") or "")}</p>'

    keypoints_html = ""
    if an.get("key_points"):
        lis = "".join(f"<li>{esc(x)}</li>" for x in an["key_points"])
        keypoints_html = f'<ul class="pc-contrib">{lis}</ul>'

    whynow_html = f'<div class="pc-body"><h4>왜 지금</h4><p>{esc(an["why_now"])}</p></div>' if an.get("why_now") else ""
    sowhat_html = f'<div class="pc-body"><h4>실무 시사점</h4><p>{esc(an["so_what"])}</p></div>' if an.get("so_what") else ""

    meta_bits = []
    if cls.get("article_type"):
        meta_bits.append(f'<span class="pc-diff">{esc(cls["article_type"])}</span>')
    if an.get("reader"):
        meta_bits.append(f'<span>{esc(an["reader"])}</span>')
    if pub:
        meta_bits.append(f'<span>📅 {esc(pub)}</span>')
    meta_html = " · ".join(meta_bits)

    terms_html = ""
    if learn.get("key_terms"):
        terms_html = "".join(
            f'<span class="term"><b>{esc(kt.get("term"))}</b> {esc(kt.get("gloss"))}</span>'
            for kt in learn["key_terms"]
        )

    apply_html = ""
    if learn.get("apply_points"):
        lis = "".join(f"<li>{esc(x)}</li>" for x in learn["apply_points"])
        apply_html = f'<div class="pc-body"><h4>📌 실무 적용 포인트</h4><ul>{lis}</ul></div>'

    btns = [f'<a class="btn btn--primary" href="{esc(l["url"])}" target="_blank" rel="noopener">{esc(l["label"])}</a>'
            for l in sorted(article.get("links", []), key=lambda x: x.get("rank", 99))]
    links_html = "".join(btns)

    quiz_html = ""
    rq = learn.get("recall_quiz") or {}
    if rq.get("question"):
        quiz_html = (
            '<div class="quiz">'
            f'<p class="quiz__q"><b>RECALL ↺</b> {esc(rq["question"])}</p>'
            f'<details><summary>정답 보기</summary><p class="quiz__a">{esc(rq.get("answer"))}</p></details>'
            '</div>'
        )

    return fill(load_tpl("article_card.html"), {
        "STAGGER": str(idx),
        "TAGS": esc(" ".join((an.get("field_tags") or []) + chips)).lower(),
        "RANK": str(article.get("rank", idx)),
        "CAT": esc(cat),
        "URL": esc(url),
        "TITLE": esc(article.get("title")),
        "AUTHORS": esc(author),
        "BADGES": badges_html,
        "CHIPS": chips_html,
        "ONELINER": oneliner,
        "BODY": body_html,
        "KEYPOINTS": keypoints_html,
        "WHYNOW": whynow_html,
        "SOWHAT": sowhat_html,
        "META": meta_html,
        "TERMS": terms_html,
        "APPLY": apply_html,
        "LINKS": links_html,
        "QUIZ": quiz_html,
    })
```

- [ ] **Step 4: `render_week`의 카드 선택/통계/스트릭 교체**

`render_week` 함수에서 다음을 교체:
- `papers = week.get("papers") or []` → 아래로:
```python
    all_articles = week.get("articles") or []
    articles = [a for a in all_articles if a.get("selected") and a.get("analysis")]
    if not articles:
        articles = [a for a in all_articles if a.get("selected")]  # 분석 전 미리보기 폴백
```
- streak 계산의 `paper_weeks = ...paper_weeks...` → `article_weeks = (index_data or {}).get("article_weeks") or {}` 로, `streak_for`가 `article_weeks.get(pid, [])` 사용.
- `cards = ... for i, p in enumerate(papers)` → `for i, a in enumerate(articles)` 그리고 `streak_for(a.get("id"))`.
- 통계 3칸 교체:
```python
    pool = week.get("pool_stats") or {}
    share_pct = round((pool.get("pool_ai_share") or 0) * 100)
    distinct_tags = len({t for a in articles for t in paper_tags(a)})
    stats = (stat_block(len(articles), "선정 글")
             + stat_block(f"{share_pct}%", "인기 중 AI")
             + stat_block(distinct_tags, "키워드"))
```
- 헤더/캡션 문구:
```python
    headline = ws.get("headline_ko") or "이번 주 요즘IT 인기 AI 글을 수집·분석했습니다."
    lede = f'이번 주 한 줄 트렌드: <b>{esc(headline)}</b>' if ws.get("headline_ko") else esc(headline)
    caveat = ws.get("caveats_ko") or "요즘IT 인기 목록의 AI 관련 상위 글 기준이며, view_count는 누적 조회수(관심도)로 최신·중요도와 다를 수 있습니다."
```
- `fill(load_tpl("report.html"), {...})`의 매핑에서 `"HERO_TITLE": f'이번 주 가장 주목받은 <em>요즘IT AI 글 {len(articles)}건</em>'`, `"TITLE": f"{week_id} 요즘IT AI 트렌드 리포트"`로 교체(나머지 키 동일).

- [ ] **Step 5: `build_insight`의 신호 소스 교체**

`build_insight`에서:
- 좌측 notes에 `ai_share_note` 추가:
```python
    if ws.get("ai_share_note"):
        notes.append(f'<div class="insight__note"><h3>📊 AI 점유율</h3><p>{esc(ws["ai_share_note"])}</p></div>')
```
- 키워드 빈도: `for p in (week.get("papers")...)` → `articles = [a for a in (week.get("articles") or []) if a.get("selected")]` 후 그 태그 집계.
- 스파크라인: `per_week[w].get("total_upvotes",0)` → `per_week[w].get("total_views", 0)`, 라벨 "주차별 관심도(업보트) 추이" → "주차별 관심도(조회수) 추이".

- [ ] **Step 6: 통합 렌더 + 남는 토큰 검사**

Run:
```bash
py "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/.claude/skills/yozm-ai-trends/scripts/render.py" --root "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT" --week $(py -c "import json,glob;print(json.load(open(sorted([x for x in glob.glob('C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/_data/weeks/*.json') if not x.endswith('.raw.json')])[-1],encoding='utf-8'))['week_id'])")
grep -rlE "\{\{[A-Z_]+\}\}" "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/2026.07/" "C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/index.html" && echo "남은 토큰 있음(FAIL)" || echo "남은 토큰 없음(OK)"
```
Expected: `WROTE ...주간리포트.html`, `WROTE .../index.html`, 그리고 `남은 토큰 없음(OK)`.

- [ ] **Step 7: 커밋**
```bash
git add -A && git commit -m "feat: Nightdesk 렌더러(render.py) — analysis/learning·조회수·streak"
```

---

## Task 10: SKILL.md (주간 워크플로우 지침)

**Files:**
- Create: `SKILL_DIR\SKILL.md`

- [ ] **Step 1: 파일 작성**

`SKILL_DIR\SKILL.md`:
```markdown
---
name: yozm-ai-trends
description: >-
  요즘IT 매거진 인기 글 중 AI를 실질적으로 다루는 상위 4~5개를 매주 수집·분석·요약하고,
  누적 데이터로 최근 AI 트렌드 인사이트를 도출해 예쁜 한국어 HTML 리포트로 정리한다.
  "이번 주 요즘IT 정리", "요즘IT AI 트렌드", "주간 AI 트렌드", "월간 종합 트렌드" 요청에 사용. 개인 학습용.
---

# 요즘IT AI 트렌드 분석 (yozm-ai-trends)

매주 요즘IT 인기 AI 글 상위 4~5개를 수집→분석→요약하고 누적 트렌드를 HTML 리포트로 만든다.
**결정론적 작업은 스크립트, 판단·서술은 너(Claude)** 가 맡는다.

## 핵심 경로
- ROOT 기본값: `C:\Users\juse9\OneDrive\Desktop\지성\요즘IT`
- 스크립트: `<ROOT>\.claude\skills\yozm-ai-trends\scripts\` (fetch_trends/merge_analysis/rollup/render)
- 데이터: `<ROOT>\_data\` (weeks/ analysis/ months/ taxonomy.json index.json)
- 산출물: `<ROOT>\<YYYY.MM>\<week>_주간리포트.html`, 각 월 index.html, 루트 index.html
- 명세: 같은 폴더 schema.json, `<ROOT>\_data\taxonomy.json`

> Windows/PowerShell. 경로에 한글·공백 → 항상 따옴표 + 절대경로. Python은 `py`.

## 주간 워크플로우

### ① 수집 (스크립트)
```
py "<ROOT>\.claude\skills\yozm-ai-trends\scripts\fetch_trends.py" --root "<ROOT>" --week auto
```
- stdout 요약(순위·제목·👁조회수·카테고리·키워드)만 읽는다. 거대 JSON 통독 금지.
- `STATUS=exists`면 이미 수집됨 → 재수집 필요 시 `--force`.
- `FETCH_ERROR`면 네트워크 문제 → 사용자에게 알리고 잠시 후 재시도. **부분 산출물 금지.**
- AI 글이 4개 미만이면 받은 만큼 진행하고 리포트에 명시.

### ② 선별 + 1차 분석 (너 — 본문 기반)
`<ROOT>\_data\weeks\<week>.json`의 `articles[]`(view_count 상위 AI 후보 pool)를 읽는다.
각 기사의 `raw.summary`+`raw.body`(raw_content 평문)+`raw.keywords`로 판단한다.

1. **선별**: AI 관련성을 확인해 이번 주 다룰 상위 **4~5개**에 `selected: true`. (딥러닝 무관·광고성은 제외)
2. 선별한 각 기사에 schema.json 형식대로 채운다:
   - `classify`: taxonomy.json의 **폐쇄형 10 카테고리**에서 `primary_category` 1개 + `categories` ≤2개.
     `topic_tags`는 `raw.keywords`(hash_tags)를 `keyword_aliases`로 정규화. `article_type`, `confidence`.
   - `analysis`: `one_liner`(40~70자), `summary_ko`(2~3문장), `key_points`(3~5), `why_now`(트렌드 관점),
     `so_what`(실무 시사점), `reader`, `field_tags`(3~5 한국어).
   - `learning`: `apply_points`(실무 적용 2~3), `key_terms`(용어 3개+뜻), `recall_quiz`(Q/A 1개), `spaced_review`.
3. **패치 JSON** 작성 → `<ROOT>\_data\analysis\<week>.patch.json`
   (형식: `{week_id, articles:{<id>:{selected,classify,analysis,learning}}, week_summary}`). 그다음:
```
py "<ROOT>\.claude\skills\yozm-ai-trends\scripts\merge_analysis.py" --root "<ROOT>" --patch "<ROOT>\_data\analysis\<week>.patch.json"
```

### ③ 트렌드 인사이트 (너 + 누적 데이터)
```
py "<ROOT>\.claude\skills\yozm-ai-trends\scripts\rollup.py" --root "<ROOT>"
```
- rollup stdout(누적 상위 키워드)과 `index.json`의 `category_timeseries`/`keyword_freq`/`ai_share_timeseries`/`totals.weeks`를
  근거로 `week_summary` 작성(패치에 포함해 재머지).
- `headline_ko`, `clusters`(primary_category로 묶어 ≥2건이면 클러스터), `narrative_ko`(3~5문장, **정량 근거 인용**),
  `recent_trend_ko`, `ai_share_note`("인기 N개 중 AI M개(P%)"), `caveats_ko`.
- **콜드스타트 분기**(`totals.weeks`): 1주=기준선 수립 중 / 2주=단순 등장·소멸 / 3주+=지속·부상·식어감.
- **과적합 방지**: 정성 문장은 index.json 숫자 근거. view_count는 "관심도"(중요도 아님). 표본 4~5개 caveat 상시.

### ④ HTML 렌더 (스크립트)
```
py "<ROOT>\.claude\skills\yozm-ai-trends\scripts\render.py" --root "<ROOT>" --week <week>
```
- 주간 리포트 + 월간 index + 마스터 index 멱등 재생성. 연속 등장 글은 "🔁 N주 연속 인기" 자동 표시.
- 끝나면 산출물 경로와 기사 원문 링크를 대화에 남긴다.

## 월간 종합 (월말 또는 요청 시)
`index.json`의 `per_week`에서 해당 월 주차를 모아 3~4개 흐름 도출 → `<ROOT>\_data\months\<YYYY.MM>.json`
(`{month, headline_ko, synthesis:[{title, tag:persist|emerging|cooling, body}]}`) 작성 → render 재실행.

## 견고성 체크리스트
- fetch 실패 시 중단(부분 산출물 금지), 재시도 안내.
- 같은 주 재실행 안전(merge/rollup/render 멱등). 분석 수정은 패치만 고쳐 재머지·재렌더.
- 분류 애매하면 `confidence:"low"`.
```

- [ ] **Step 2: 프론트매터 검증**

Run:
```bash
py -c "import io; s=open('C:/Users/juse9/OneDrive/Desktop/지성/요즘IT/.claude/skills/yozm-ai-trends/SKILL.md',encoding='utf-8').read(); assert s.startswith('---') and 'name: yozm-ai-trends' in s; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: 커밋**
```bash
git add -A && git commit -m "feat: 주간 워크플로우 지침(SKILL.md)"
```

---

## Task 11: README.md

**Files:**
- Create: `<ROOT>\README.md`

- [ ] **Step 1: 파일 작성** (논문정리 README를 요즘IT용으로 각색 — 아래 핵심 골자를 담아 작성)

`<ROOT>\README.md` 에 다음 섹션 포함: 제목/소개("요즘IT AI 트렌드 주간 관측기"), 매주 사용법(`"이번 주 요즘IT AI 트렌드 정리해줘"`), 파이프라인(①fetch_trends ②Claude 분석 ③rollup ④render), 데이터 소스(요즘IT JSON API: `articleListApi`/`fetchContentsDetail`, `affectView=false`, `category flag=='ai'` 필터, `view_count` 신호), 폴더 구조(설계 §9), 데이터 모델 3층, 트렌드 방법론(콜드스타트·streak·AI 점유율), 디자인("Nightdesk" 다크 기본+라이트 토글), 셋업(Python 3.8+, pip 없음, `py`), 트러블슈팅(FETCH_ERROR/STATUS=exists/한글 UTF-8), 자주 쓰는 명령. 세부는 `docs/superpowers/specs/2026-07-02-yozm-ai-trends-design.md` 참조 링크.

- [ ] **Step 2: 커밋**
```bash
git add -A && git commit -m "docs: README(사용법·파이프라인·데이터 모델)"
```

---

## Task 12: 엔드투엔드 검증 (실주차 전체 실행 + 미리보기)

**Files:** (없음 — 실행/검증만)

- [ ] **Step 1: 깨끗한 상태에서 전체 파이프라인 재실행**

이번 주차로 fetch→(Claude 분석 패치 작성)→merge→rollup→render 전 과정을 실행. 분석 패치는 SKILL.md ② 절차대로 Claude가 작성.
```bash
ROOT="C:/Users/juse9/OneDrive/Desktop/지성/요즘IT"
S="$ROOT/.claude/skills/yozm-ai-trends/scripts"
py "$S/fetch_trends.py" --root "$ROOT" --week auto --force
# (Claude가 _data/analysis/<week>.patch.json 작성)
py "$S/merge_analysis.py" --root "$ROOT" --patch "$ROOT/_data/analysis/<week>.patch.json"
py "$S/rollup.py" --root "$ROOT"
py "$S/render.py" --root "$ROOT" --week <week>
```
Expected: 각 단계 `STATUS=ok`/`WROTE`.

- [ ] **Step 2: 산출물 육안 검증(미리보기 서버)**

`.claude/launch.json`의 `yozm-preview`로 정적 서버를 띄워 브라우저에서 확인(preview_start 사용). 확인 항목:
- 주간 리포트가 Nightdesk 다크 테마로 렌더(앰버 액센트), 카드에 조회수·읽기시간·카테고리·한줄핵심·핵심포인트·왜지금·실무시사점·용어·퀴즈·원문 버튼.
- 라이트 토글 동작(우상단), 새로고침 후 테마 기억.
- 마스터 index.html에 월 밴드/주차 카드/누적 키워드 막대.
- 남은 `{{TOKEN}}` 없음(Task 9 Step 6에서 이미 확인).

- [ ] **Step 3: 멱등성 확인**

동일 명령 재실행 시 중복 링크/파일 없이 동일 결과인지 확인:
```bash
py "$S/rollup.py" --root "$ROOT"; py "$S/render.py" --root "$ROOT" --week <week>
git status -s   # 재렌더로 인한 변경이 있으면 diff 확인(내용 동일해야 함)
```

- [ ] **Step 4: 최종 커밋**
```bash
git add -A && git commit -m "chore: 첫 주차 엔드투엔드 검증 산출물"
```

---

## Self-Review (작성자 점검 결과)

- **Spec 커버리지**: §3 API → Task 4; §5 수집 전략 → Task 4(filter_ai/rank_by_view/flatten); §6 데이터 모델 → Task 3(schema)/4(fetch)/5(merge)/6(rollup); §6.3 taxonomy → Task 2; §7 방법론(콜드스타트·streak·AI 점유율) → Task 6(rollup)+9(render)+10(SKILL ③); §8 Nightdesk → Task 7+8; §9 폴더 → Task 1; §10 사용법 → Task 10+11. 누락 없음.
- **플레이스홀더**: `<week>` 는 실행 시 주차로 치환되는 실인자(플레이스홀더 아님). 각 단계에 실제 코드/명령/기대 출력 포함.
- **타입 일관성**: fetch가 쓰는 `articles[].{id(str),raw.keywords,raw.view_count,selected}` ↔ merge `MERGE_KEYS=(selected,classify,analysis,learning)` ↔ rollup `article_weeks/view_timeseries/pool_ai_share` ↔ render `build_card`(analysis/learning/interest 키) ↔ article_card.html 토큰 1:1 확인. `paper_tags`는 `raw.keywords` 사용으로 통일.
- **주의**: render.py 각색은 "복사 후 지정 함수 교체" 방식 — 실행자는 원본 `논문정리 render.py`를 읽어 대응 함수를 교체할 것. Task 8 템플릿 토큰과 Task 9 build_card 매핑이 정확히 일치해야 남은 토큰 0.
