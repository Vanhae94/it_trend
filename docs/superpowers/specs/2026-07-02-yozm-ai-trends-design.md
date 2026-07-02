# 요즘IT AI 트렌드 주간 관측기 — 설계 문서

- **작성일**: 2026-07-02
- **프로젝트 루트**: `C:\Users\juse9\OneDrive\Desktop\지성\요즘IT`
- **스킬명**: `yozm-ai-trends`
- **참고 원본**: 옆 폴더 `논문정리`(AI Papers Weekly)의 아키텍처를 이식·각색

---

## 1. 목적 (Why)

요즘IT 매거진(`https://yozm.wishket.com/magazine/`)에서 **매주 한 번(사용자 요청 시)** 인기 글 중
**AI를 실질적으로 다루는 상위 4~5개**를 수집한다. Claude가 본문까지 읽어 한국어로 분석·요약하고,
누적 데이터로 **AI 트렌드 추이**를 도출해 **웜 다크("Nightdesk") 테마 HTML 리포트**로 정리한다.
목표는 개인 학습 — "요즘 AI가 실무에서 어떻게 다뤄지는지"의 흐름을 매주 관찰·공부하는 것.

**핵심 철학(원본 계승)**: 결정론적 작업(수집·집계·렌더)은 Python 스크립트가, 판단·서술(선별·분석·트렌드)은
Claude가 맡는다. Python 표준 라이브러리만 사용(pip 설치 없음).

---

## 2. 확정된 설계 결정 (What)

| 항목 | 결정 | 비고 |
|---|---|---|
| 수집 기준 | 사이트 **주간 인기 랭킹** → AI 필터 → 상위 4~5개 | "화제성"을 신호로 |
| AI 범위 | **카테고리 무관**, AI를 실질적으로 다루는 글 전반 | 프로덕트·디자인·커리어의 AI 글도 포함 |
| 아키텍처 | **논문정리 풀 클론** (fetch/merge/rollup/render 4스크립트 계약) | `--root` 인자, 멱등성 계승 |
| 분석 깊이 | **1단계**: 선별 4~5개 전부 본문까지 균일 분석 | 논문정리의 tier2(심층) 없음 |
| 학습 장치 | **둘 다**: 인사이트+실무적용 **및** 핵심용어+회상퀴즈 | |
| 디자인 | **Nightdesk** — 웜 다크(잉크브라운)+앰버/골드, 다크 기본 + 라이트 토글 | 원본 "Aurora Ink"(차가운 청록 다크)와 구별 |
| 실행 방식 | **수동 온디맨드** — "이번 주 요즘IT AI 트렌드 정리해줘" | 자동 스케줄은 로컬 파일 제약으로 제외 |

---

## 3. 데이터 소스 분석 (요즘IT)

수집 전략을 좌우하는 사실(2026-07-02 확인):

- **RSS 피드** `https://yozm.wishket.com/magazine/feed/` — 사이트 **신규글** 피드. 최신 4~5개.
  각 item에 `title / link / description(요약) / guid / content:encoded(본문 HTML)` 포함.
  **`<category>`·`<pubDate>` 없음** → 카테고리·날짜·인기순은 RSS로 못 얻음.
- **인기 페이지** `https://yozm.wishket.com/magazine/list/popular/` — HTTP 200(존재). 메인에는 "N주 인기" 블록도 있음.
  → **인기 랭킹(핫함 신호)의 출처.** 서버 렌더 HTML → 파싱 필요.
- **카테고리 페이지** `https://yozm.wishket.com/magazine/list/<cat>/` — `develop, ai, itservice, plan, design, business, product, career, trend, startup`.
- **개별 기사** `https://yozm.wishket.com/magazine/detail/<id>` — 구조화 메타 풍부:
  - Open Graph: `og:title, og:description(요약), og:keyword(키워드), og:image, og:url`
  - JSON-LD: `articleSection`(**카테고리**), `datePublished`(**발행일**)
  - 본문 컨테이너(HTML) — 추출 대상.
  → 전체 HTML 억지 파싱이 아니라 **OG/JSON-LD 태그만** 뽑으면 견고하게 제목·요약·카테고리·키워드·날짜 확보.

**결론**: 논문정리가 쓰던 "깔끔한 JSON API"는 없다. 대신 `인기 페이지(HTML) = 랭킹` + `기사 상세(OG/JSON-LD) = 메타·본문`
조합이 가장 견고한 결정론적 소스다.

---

## 4. 아키텍처 & 파이프라인

원본과 **동일한 4스크립트 계약** + `--root` + 멱등성. `fetch`만 HTML 파싱으로 각색된다.

```
사용자: "이번 주 요즘IT AI 트렌드 정리해줘"  ─▶  Claude가 SKILL.md 절차 오케스트레이션
  │
  ├─ ① fetch_trends.py    인기랭킹 파싱 → 후보 pool(상위 ~10~12) 수집 →
  │                        각 후보의 상세에서 og:*/JSON-LD 메타 + 본문 추출 →
  │                        _data/weeks/<주차>.json 저장(멱등). 분석 필드는 null 골격.
  ├─ ② [Claude] 선별·분석  후보 pool에서 AI 관련성 판단 → 인기순 상위 4~5개 선택 →
  │                        선택 글 전부 본문 기반 분석(classify/analysis/learning) →
  │                        _data/analysis/<주차>.patch.json 작성
  ├─   merge_analysis.py   패치를 주차 기록에 병합(raw 보존, 있는 키만 갱신)
  ├─ ③ rollup.py           전 주차 집계 → _data/index.json (카테고리·키워드 추이, streak, AI 점유율)
  │     [Claude]           누적 신호 근거로 week_summary(동향) 작성 → 패치에 포함/재머지
  └─ ④ render.py           분석 JSON → Nightdesk HTML + 월간/마스터 인덱스 멱등 재생성
                            (연속 등장 글엔 "N주 연속 인기" 배지 자동 부착)
```

**스크립트 계약(원본과 동형)**

| 스크립트 | 역할 | 주요 인자 |
|---|---|---|
| `fetch_trends.py` | 인기랭킹+상세 수집·평탄화·멱등 저장 | `--root` `--week auto\|YYYY-Wnn` `--pool 12` `--force` `--date YYYY-MM-DD` |
| `merge_analysis.py` | Claude 분석 패치를 주차 기록에 병합(raw 보존) | `--root` `--patch <경로>` |
| `rollup.py` | 전 주차 정량 롤업(index.json) 재생성 | `--root` |
| `render.py` | 분석 JSON → HTML 렌더 + 인덱스 재생성 | `--root` `--week YYYY-Wnn`(생략 시 인덱스만) |

---

## 5. 수집 전략 상세 (핵심 각색부)

1. **랭킹 수집**: `GET /magazine/list/popular/`(또는 메인 "주 인기" 블록)을 파싱해
   순위 매긴 후보 목록 생성 — `{rank, id, title, url}`. `id`는 `/magazine/detail/<id>`에서 추출.
   - ⚠️ **구현 시 확정**: 인기 페이지가 "주간 인기"인지 "누적/롤링 인기"인지 확인.
     주차 스냅샷 의미에 더 맞는 소스를 채택(주간 우선). 애매하면 메인 "주 인기" 블록 사용.
2. **상세 보강**: 후보 각각 `GET /magazine/detail/<id>` → **안정적 구조화 태그만** 추출:
   - `title ← og:title`, `summary ← og:description`, `keywords ← og:keyword`,
     `category ← JSON-LD articleSection`, `published_at ← JSON-LD datePublished`,
     `body ← 본문 컨테이너 텍스트`(best-effort).
   - ⚠️ **구현 시 확정**: 본문 컨테이너 셀렉터/마커. 실패 시 `og:description`으로 폴백.
3. **AI 필터·선별(Claude)**: 후보 pool의 `title/summary/keywords/category`를 보고 AI 관련성 판단 →
   인기순 상위 **4~5개** 선택. `candidate_pool[]`에 각 후보의 `ai_relevant`(bool)와 선택 여부 기록.
   - AI 관련 글이 4개 미만이면 그 사실을 리포트에 명시하고, 필요 시 `/magazine/list/ai/` 최신으로 보강.
4. **견고성**: fetch 실패 시 파이프라인 중단(부분 산출물 금지) + 재시도 안내. UA 헤더 + 지수 백오프.
   같은 주차 재수집은 `--force` 없으면 스킵(멱등).

---

## 6. 데이터 모델 (3층, 각색)

### 6.1 `_data/weeks/<주차>.json` — 불변 raw + Claude 분석

상단 메타: `schema_version, week_id, date_range_ko, month_folder, collected_at, source, article_count`

- **`candidate_pool[]`** — 인기랭킹 스냅샷 전체: `{rank, id, title, url, category, ai_relevant(bool), selected(bool)}`
  - "인기 N개 중 AI M개" 점유율 신호 + 감사용. **불변.**
- **`articles[]`** — 선별된 4~5개. 각 항목:
  - `id, title, title_note?, url, rank(인기순위), published_at, category(articleSection), author?`
  - **`raw`** (불변): `{ summary(og:description), keywords(og:keyword[]), body(본문 추출 텍스트), category }`
  - **`links[]`**: `[{label, url}]` — 최소 "원문" 링크. null URL 항목 제외.
  - **`classify`** (Claude, taxonomy 기준): `{ categories(≤2), primary_category, topic_tags(키워드 정규화), article_type, confidence }`
  - **`analysis`** (Claude, 1단계 — 논문 tier1 대체):
    - `one_liner` (40~70자 한 줄 핵심)
    - `summary_ko` (2~3문장 요약)
    - `key_points[]` (불릿 3~5, 가능하면 수치)
    - `why_now` (트렌드 관점 2~3문장 — 이 시스템의 정체성)
    - `so_what` (실무 시사점 2~3문장 — "그래서 뭐가 달라지나")
    - `reader` (추천 독자), `field_tags[]` (3~5 한국어)
  - **`learning`** (Claude — 인사이트+용어·퀴즈 둘 다):
    - `apply_points[]` (실무 적용 포인트 불릿 2~3)
    - `key_terms[{term, gloss}]` (핵심 용어 3개 + 한 줄 뜻)
    - `recall_quiz{question, answer}` (회상 문제 1개)
    - `spaced_review{flag(bool), review_due(date|null)}`
  - **`interest`** (정량 신호 — 업보트 대체): `{ popular_rank, weeks_on_popular(연속 등장 수) }`
- **`week_summary`** (Claude 주차 인사이트):
  - `headline_ko` (이번 주 한 줄 트렌드 — 히어로)
  - `clusters[{category, article_ranks[], theme_ko}]`
  - `emerging_keywords[]`
  - `narrative_ko` (3~5문장, **반드시 index.json 정량 근거 인용**)
  - `recent_trend_ko` (콜드스타트 분기 반영)
  - `ai_share_note` ("인기 N개 중 AI M개(P%)" 서술)
  - `caveats_ko` (표본 4~5개·인기 편향 경고, 상시 노출)

> `raw`/`candidate_pool`은 절대 수정 금지(증거). Claude는 거대 JSON을 직접 편집하지 않고
> **패치 JSON**(`analysis/<주차>.patch.json`)을 작성해 `merge_analysis.py`로 병합한다(있는 키만 갱신 → 부분 병합 안전).

### 6.2 `_data/index.json` — rollup 재생성(정량 단일 출처)

`category_timeseries`, `keyword_freq`, `article_weeks`(id→등장 주차 이력, streak 계산),
`ai_share_timeseries`(주별 인기 중 AI 비율), `per_week`, `totals.weeks`.

### 6.3 `_data/taxonomy.json` — 폐쇄형 분류 + 키워드 별칭

주차 간 비교를 위해 **고정 목록**만 사용. 신규 키워드는 `keyword_aliases`에 누적.

**1차 카테고리(10개, 요즘IT AI 실무형)**:

| key | label_ko | scope |
|---|---|---|
| `ai-coding` | AI 코딩·개발도구 | 바이브코딩, 코딩 에이전트, Copilot/Cursor/Claude Code |
| `ai-agents` | AI 에이전트·자동화 | 에이전트, 워크플로우, MCP, 툴 사용 |
| `models-llm` | 모델·LLM 동향 | 신모델 출시, 벤더 경쟁, 성능·벤치마크 |
| `ai-product` | AI 프로덕트·서비스 | AI 기능 탑재 제품, SaaS, 기능 기획 |
| `ways-of-working` | 일하는 법·조직 | 팀 생산성, 프로세스, AI 도입 |
| `career` | 커리어·직무 | 직무 변화, PM/개발/디자인 커리어, 생존 전략 |
| `design-ux` | 디자인·UX | AI 시대 디자인, UX, 크리에이티브 |
| `data-infra` | 데이터·인프라 | RAG, 벡터DB, 파인튜닝, 인프라 |
| `safety-risk` | 보안·리스크·윤리 | AI 보안, 저작권, 규제, 신뢰성 |
| `business-market` | 비즈니스·시장 | 투자, 시장 동향, 전략 |

- 규칙: `categories` ≤2개, `primary_category` 정확히 1개.
- 보조축 `article_type`: `튜토리얼 / 오피니언 / 사례 / 뉴스분석 / 인터뷰`.
- `keyword_aliases`: 한/영 동의어 통합 사전(예: `agent`↔`에이전트`↔`multi-agent`, `vibe-coding`↔`바이브코딩`).

---

## 7. 트렌드 방법론 (과적합 방지 — 원본 원칙 계승)

- **콜드스타트 분기**(`totals.weeks`): 1주=기준선 수립 중 / 2주=단순 등장·소멸만 / 3주+=지속·부상·식어감 판정.
- **연속 등장 배지**: 같은 기사가 여러 주 인기에 남으면 "🔁 N주 연속 인기". `article_weeks` 기반 render 자동 계산(as-of 주차).
- **정량/정성 분리**: 정성 서술은 반드시 index.json 숫자 인용. 표본 4~5개 + "인기 편향" caveat 상시.
- **AI 점유율 추이**: "이번 주 인기 12개 중 AI 7개(58%)" — 요즘IT 특화 신호를 주차별로 추적.
- **월간 종합**: 월말(또는 요청 시) 그 달 3~4개 흐름 도출 → `_data/months/<YYYY.MM>.json` → 월 인덱스 임베드.

---

## 8. 디자인 시스템 — "Nightdesk"

- 컨셉: **잉크브라운 위 앰버 등불** — 야간 트렌드 데스크. **다크 기본 + 라이트 토글**(localStorage 기억).
- 원본 "Aurora Ink"(차가운 청록 다크)와 **따뜻한 금색**으로 확실히 구별.
- 폰트: Pretendard(본문) · Fraunces(디스플레이 헤드라인) · Space Mono(수치·순위) — CDN, 차단 시 시스템 폰트 폴백.
- 단일 `_assets/style.css` 하나로 전 페이지 일관. 빌드 단계 없이 브라우저에서 바로 열림. 외부 차트 라이브러리 0
  (키워드 빈도=CSS 막대, 주차 추이=인라인 SVG).

**컬러 토큰(다크 기본)**
```
--bg:#17130E  --bg-2:#1C1710  --panel:#201A13
--surface:rgba(255,220,170,.04)  --surface-2:rgba(255,220,170,.07)
--border:#2E2619  --border-2:#3A3020
--text:#F5EEE3  --text-dim:#B3A791  --text-faint:#8C806C
--amber:#FFB020(주 액센트)  --gold:#FFC661  --ember:#FF7A45(핫/2차)  --star:#F4C860
```
**라이트 토글(웜 페이퍼)**
```
--bg:#FBF8F3  --panel:#FFFFFF
--text:#211C16  --text-dim:#6B6259  --text-faint:#A2988B
--border:#ECE4D8  --amber:#C2761A  --ember:#E8590C
```
색·무드 변경은 `style.css` 상단 `:root` CSS 변수만 수정하면 전체 일관 반영.

---

## 9. 폴더 구조 & 산출물 (논문정리와 동형)

```
요즘IT/
├─ README.md                         ← 사용법·파이프라인·데이터 모델 문서
├─ index.html                        ← 마스터 대시보드(전체 주차/월)
├─ 2026.07/                          ← 월별 폴더(점 구분)
│  ├─ index.html                     ← 월간 인덱스(+월말 종합 임베드)
│  └─ 2026-Wxx_주간리포트.html        ← 주간 리포트
├─ _assets/
│  ├─ style.css                      ← 단일 디자인 시스템 "Nightdesk"
│  └─ app.js                         ← 테마 토글 등(외부 라이브러리 0)
├─ _data/
│  ├─ taxonomy.json                  ← 폐쇄형 10 카테고리 + keyword_aliases
│  ├─ index.json                     ← rollup 정량 롤업
│  ├─ weeks/<주차>.json              ← 주차별 원본+분석(불변 raw)
│  ├─ weeks/<주차>.raw.json          ← 수집 원본 박제(감사용)
│  ├─ analysis/<주차>.patch.json     ← Claude 분석 패치
│  └─ months/<YYYY.MM>.json          ← 월간 종합
├─ docs/superpowers/specs/           ← 이 설계 문서 등
└─ .claude/
   ├─ launch.json                    ← 미리보기용 정적 서버(선택)
   └─ skills/yozm-ai-trends/
      ├─ SKILL.md                    ← 주간 워크플로우 절차(Claude 지침)
      ├─ schema.json                 ← weeks 기사 객체 데이터 명세
      ├─ scripts/                    ← fetch_trends / merge_analysis / rollup / render
      └─ templates/                  ← report / monthly / master_index / article_card
```

**환경 조건**: Python 3.8+(권장 3.10+, `datetime.date.fromisocalendar` 사용), 추가 패키지 없음.
Windows는 `py`, 경로에 한글·공백 있으니 항상 따옴표 + 절대경로. 파일 I/O는 UTF-8.

---

## 10. 스킬 사용법 (수동 온디맨드)

Claude Code에서 이 폴더를 열고: `"이번 주 요즘IT AI 트렌드 정리해줘"` (또는 슬래시 커맨드).
그러면 Claude가 ①수집 → ②AI 선별·분석 → ③트렌드 인사이트 → ④HTML 렌더를 순서대로 실행하고
산출물 경로와 기사 링크를 대화에 남긴다.

---

## 11. 구현 시 확정할 열린 항목 (Open Questions)

1. **인기 페이지 성격**: `/magazine/list/popular/`가 주간 vs 누적/롤링 인기인지 → 주차 스냅샷에 맞는 소스 확정.
2. **본문 컨테이너 셀렉터**: 기사 상세의 본문 HTML 마커 확정(+ 실패 시 og:description 폴백).
3. **인기 랭킹 항목 수**: 후보 pool 크기(기본 10~12) — AI 4~5개를 안정적으로 확보할 수 있는 값.
4. **HTML 파서**: 표준 라이브러리 `html.parser` 기반 최소 파서 + OG/JSON-LD 정규식 추출 조합.

---

## 12. 비목표 (Non-goals)

- 자동 스케줄 실행(로컬 파일 저장 제약 → 수동 트리거로 대체).
- tier2 심층 분석(1단계 균일 분석으로 통합).
- 요즘IT 전체 아카이브 크롤링(주간 인기 상위 AI 글에 한정).
- 외부 DB·프레임워크·유료 API 사용(표준 라이브러리 + 정적 HTML만).
