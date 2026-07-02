# 요즘IT AI 트렌드 주간 관측기 — 설계 문서

- **작성일**: 2026-07-02 (2026-07-02 내부 JSON API 발견으로 §3·§5·§6 개정)
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
| 수집 기준 | 사이트 **인기 목록(view_count)** → AI 필터 → 상위 4~5개 | "화제성"을 신호로 |
| AI 범위 | **카테고리 무관**, AI를 실질적으로 다루는 글 전반 | `category[].flag=='ai'`로 결정론 선별 |
| 아키텍처 | **논문정리 풀 클론** (fetch/merge/rollup/render 4스크립트 계약) | `--root` 인자, 멱등성 계승 |
| 분석 깊이 | **1단계**: 선별 4~5개 전부 본문까지 균일 분석 | 논문정리의 tier2(심층) 없음 |
| 학습 장치 | **둘 다**: 인사이트+실무적용 **및** 핵심용어+회상퀴즈 | |
| 디자인 | **Nightdesk** — 웜 다크(잉크브라운)+앰버/골드, 다크 기본 + 라이트 토글 | 원본 "Aurora Ink"(차가운 청록 다크)와 구별 |
| 실행 방식 | **수동 온디맨드** — "이번 주 요즘IT AI 트렌드 정리해줘" | 자동 스케줄은 로컬 파일 제약으로 제외 |

---

## 3. 데이터 소스 분석 (요즘IT) — 내부 JSON API

요즘IT는 Next.js SPA이며 페이지가 런타임에 **공개 내부 JSON API**를 호출한다(2026-07-02 네트워크 관찰로 확인).
따라서 HTML 파싱이 전혀 필요 없고, curl/`urllib`+`json`으로 바로 수집 가능 — 논문정리의 HF JSON API와 동일한 성격.

### 3.1 목록 API (인기/카테고리 피드)
```
GET https://yozm.wishket.com/api/articleListApi/?category=<cat>&page=<n>&ordering=new
```
- `category`: `popular`(인기) 또는 `ai/develop/product/plan/design/business/career/trend/startup/itservice`(카테고리별).
- `ordering=new`(최신순), `page`(1부터, 페이지당 10개).
- 응답: `{ ok:true, data:{ count, next, previous, results:[ item ] } }`.
- **item 필드**: `id, title, author, description`(요약), `date_published, repr_date_published, featured,
  view_count`(누적 조회수=인기 신호), `read_time`(분), `is_popular_news`(bool),
  `category`(객체 배열: `[{name, flag, order, og_*}]`), `thumbnail_image, is_news_scrapped`.
- **AI 필터의 핵심**: 각 item의 `category`는 객체 배열이며 항목마다 `flag`가 있다. 인기글 상당수가
  `flag=='ai'`를 (develop/product/plan 등과 **함께**) 달고 있다 → **`flag=='ai'` 포함 여부로 "카테고리 무관 AI 글"을
  결정론적으로 선별**할 수 있다.

### 3.2 상세 API (본문)
```
GET https://yozm.wishket.com/api/fetchContentsDetail/?id=<id>&affectView=false
```
- `affectView=false` **필수** — `true`면 조회수를 증가시킨다(수집이 데이터를 오염시키지 않도록 반드시 false).
- 응답 `data`: 목록 item 필드 + `content`(본문 HTML), **`raw_content`(본문 평문 — Claude가 읽을 텍스트)**,
  `hash_tags`(문자열 배열, 키워드), `meta_description, date_modified`.

### 3.3 보조(참고, 미사용 가능)
`RSS /magazine/feed/`(신규 5개, 본문 포함) · `/api/popularArticleListApi/` · `/api/articleActionStatusApi/?newsId=`.
기사 원문 URL은 `https://yozm.wishket.com/magazine/detail/<id>`.

---

## 4. 아키텍처 & 파이프라인

원본과 **동일한 4스크립트 계약** + `--root` + 멱등성. `fetch`가 요즘IT API를 쓰도록 각색된다(HTML 파싱 없음).

```
사용자: "이번 주 요즘IT AI 트렌드 정리해줘"  ─▶  Claude가 SKILL.md 절차 오케스트레이션
  │
  ├─ ① fetch_trends.py    articleListApi(popular) 호출 → AI 플래그 필터 → view_count 상위 pool 수집 →
  │                        각 글 fetchContentsDetail 호출로 본문·키워드 보강 →
  │                        _data/weeks/<주차>.json 저장(멱등). 분석 필드는 null 골격.
  ├─ ② [Claude] 선별·분석  pool에서 AI 관련성 확인 → 상위 4~5개 selected=true →
  │                        선택 글 전부 raw_content 기반 분석(classify/analysis/learning) →
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
| `fetch_trends.py` | 인기 목록+본문 수집·평탄화·멱등 저장 | `--root` `--week auto\|YYYY-Wnn` `--pool 12` `--pages 2` `--force` `--date YYYY-MM-DD` |
| `merge_analysis.py` | Claude 분석 패치를 주차 기록에 병합(raw 보존) | `--root` `--patch <경로>` |
| `rollup.py` | 전 주차 정량 롤업(index.json) 재생성 | `--root` |
| `render.py` | 분석 JSON → HTML 렌더 + 인덱스 재생성 | `--root` `--week YYYY-Wnn`(생략 시 인덱스만) |

---

## 5. 수집 전략 상세 (JSON API 기반)

1. **인기 목록 수집**: `articleListApi?category=popular&ordering=new&page=1`(필요 시 `--pages`만큼 다음 페이지도) 호출 →
   후보 pool. 각 item에서 `id/title/description/view_count/category/date_published/read_time/is_popular_news` 확보.
2. **AI 결정론 선별**: `category[].flag`에 `ai`가 있는 item만 남긴다(= 카테고리 무관 AI 글). 나머지는 pool 통계용으로만 카운트.
3. **핫함 순위**: 남은 AI 글을 `view_count` 내림차순 정렬 → 상위 `--pool`(기본 12)까지 저장, 그중 Claude가 4~5개 선정.
   (view_count는 누적 조회수라 "관심도" 지표로 다루고, `is_popular_news`·최신성과 함께 해석.)
4. **본문 보강**: 저장 대상 각 글을 `fetchContentsDetail?id=<id>&affectView=false`로 호출 →
   `raw_content`(평문 본문)·`hash_tags`(키워드) 확보.
5. **견고성**: 네트워크 실패 시 파이프라인 중단(부분 산출물 금지) + 지수 백오프 재시도. UA 헤더 부착.
   같은 주차 재수집은 `--force` 없으면 스킵(멱등). AI 글이 4개 미만이면 리포트에 그 사실을 명시.

---

## 6. 데이터 모델 (3층, 각색)

### 6.1 `_data/weeks/<주차>.json` — 불변 raw + Claude 분석

상단 메타: `schema_version, week_id, date_range_ko, month_folder, collected_at, source, pool_stats`

- **`pool_stats`**: `{ popular_fetched(int), ai_in_pool(int), pool_ai_share(float) }` — "인기 N개 중 AI M개" 점유율 신호.
- **`articles[]`** — 수집된 AI 후보 pool(view_count 상위 ~12개). 각 항목:
  - `id, title, url, rank`(pool 내 view_count 순위), `published_at, category`(대표 카테고리 라벨), `category_flags[]`, `author`
  - **`raw`** (불변, API 원본): `{ summary(description), keywords(hash_tags[]), body(raw_content),
    view_count, read_time, is_popular_news, category_flags[], date_published }`
  - **`links[]`**: `[{rank,label,url}]` — 최소 "원문"(`/magazine/detail/<id>`). null URL 제외.
  - **`selected`** (Claude): `true`면 이번 주 분석 대상(4~5개). fetch는 `null`로 둔다.
  - **`classify`** (Claude, taxonomy 기준): `{ categories(≤2), primary_category, topic_tags(hash_tags 정규화), article_type, confidence }`
  - **`analysis`** (Claude, 1단계 — 논문 tier1 대체):
    `one_liner`(40~70자), `summary_ko`(2~3문장), `key_points[]`(불릿 3~5), `why_now`(트렌드 관점 2~3문장),
    `so_what`(실무 시사점 2~3문장), `reader`(추천 독자), `field_tags[]`(3~5 한국어)
  - **`learning`** (Claude — 인사이트+용어·퀴즈 둘 다):
    `apply_points[]`(실무 적용 2~3), `key_terms[{term,gloss}]`(핵심 용어 3개), `recall_quiz{question,answer}`,
    `spaced_review{flag(bool), review_due(date|null)}`
  - **`interest`** (정량 신호): `{ view_count, popular_rank, weeks_on_popular(연속 등장 수) }`
- **`week_summary`** (Claude 주차 인사이트):
  `headline_ko`, `clusters[{category, article_ranks[], theme_ko}]`, `emerging_keywords[]`,
  `narrative_ko`(3~5문장, **반드시 index.json 정량 근거 인용**), `recent_trend_ko`(콜드스타트 분기),
  `ai_share_note`("인기 N개 중 AI M개(P%)"), `caveats_ko`(표본 4~5개·조회수 편향 경고, 상시)

> `raw`는 절대 수정 금지(증거). Claude는 거대 JSON을 직접 편집하지 않고 **패치 JSON**(`analysis/<주차>.patch.json`)을
> 작성해 `merge_analysis.py`로 병합한다(있는 키만 갱신 → 부분 병합 안전). `articles[]`가 곧 후보 pool이며 `selected`로 분석 대상을 표시(별도 배열 불필요).

### 6.2 `_data/index.json` — rollup 재생성(정량 단일 출처)

`category_timeseries`(selected 기준), `keyword_freq`(selected 기준), `article_weeks`(id→등장 주차 이력 — pool 기준, streak 계산),
`view_timeseries`(주별 selected view_count 합), `ai_share_timeseries`(주별 pool_ai_share), `per_week`, `totals.weeks`.

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

- 규칙: `categories` ≤2개, `primary_category` 정확히 1개. 보조축 `article_type`: `튜토리얼/오피니언/사례/뉴스분석/인터뷰`.
- `keyword_aliases`: 한/영 동의어 통합(예: `vibe-coding`↔`바이브코딩`, `agent`↔`에이전트`↔`multi-agent`, `claude-code`↔`claudecode`).

---

## 7. 트렌드 방법론 (과적합 방지 — 원본 원칙 계승)

- **콜드스타트 분기**(`totals.weeks`): 1주=기준선 / 2주=단순 등장·소멸만 / 3주+=지속·부상·식어감 판정.
- **연속 등장 배지**: 같은 기사가 여러 주 인기 pool에 남으면 "🔁 N주 연속 인기". `article_weeks` 기반 render 자동 계산(as-of 주차).
- **정량/정성 분리**: 정성 서술은 반드시 index.json 숫자 인용. 표본 4~5개 + "조회수=관심도(중요도 아님)" caveat 상시.
- **AI 점유율 추이**: "이번 주 인기 pool 중 AI N%(pool_ai_share)"를 주차별 추적 — 요즘IT 특화 신호.
- **월간 종합**: 월말(또는 요청 시) 그 달 3~4개 흐름 도출 → `_data/months/<YYYY.MM>.json` → 월 인덱스 임베드.

---

## 8. 디자인 시스템 — "Nightdesk"

- 컨셉: **잉크브라운 위 앰버 등불** — 야간 트렌드 데스크. **다크 기본 + 라이트 토글**(localStorage 기억).
- 원본 "Aurora Ink"(차가운 청록 다크)와 **따뜻한 금색**으로 구별.
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
--grad-amber: linear-gradient(115deg,#FFB020 0%,#FF7A45 100%)
```
**라이트 토글(웜 페이퍼)**
```
--bg:#FBF8F3  --panel:#FFFFFF
--text:#211C16  --text-dim:#6B6259  --text-faint:#A2988B
--border:#ECE4D8  --amber:#C2761A  --ember:#E8590C
```
색·무드 변경은 `style.css` 상단 `:root` CSS 변수만 수정하면 전체 일관 반영.
※ render.py의 인라인 SVG 스파크라인 gradient stop(원본 `#3DDC97/#2BB6C9`)도 앰버(`#FFB020/#FF7A45`)로 교체.

---

## 9. 폴더 구조 & 산출물 (논문정리와 동형)

```
요즘IT/
├─ README.md                         ← 사용법·파이프라인·데이터 모델 문서
├─ index.html                        ← 마스터 대시보드(전체 주차/월)
├─ 2026.07/                          ← 월별 폴더(점 구분)
│  ├─ index.html                     ← 월간 인덱스(+월말 종합 임베드)
│  └─ 2026-Wxx_주간리포트.html        ← 주간 리포트
├─ _assets/  ( style.css "Nightdesk" · app.js 테마 토글 )
├─ _data/
│  ├─ taxonomy.json · index.json
│  ├─ weeks/<주차>.json               ← 주차별 원본+분석(불변 raw)
│  ├─ weeks/<주차>.raw.json           ← API 원본 박제(감사용)
│  ├─ analysis/<주차>.patch.json      ← Claude 분석 패치
│  └─ months/<YYYY.MM>.json           ← 월간 종합
├─ docs/superpowers/{specs,plans}/    ← 설계·계획 문서
└─ .claude/
   ├─ launch.json                    ← 미리보기용 정적 서버(선택)
   └─ skills/yozm-ai-trends/
      ├─ SKILL.md · schema.json
      ├─ scripts/  ( fetch_trends · merge_analysis · rollup · render )
      └─ templates/ ( report · monthly · master_index · article_card )
```

**환경 조건**: Python 3.8+(권장 3.10+, `datetime.date.fromisocalendar` 사용), 추가 패키지 없음.
Windows는 `py`, 경로에 한글·공백 있으니 항상 따옴표 + 절대경로. 파일 I/O는 UTF-8.

---

## 10. 스킬 사용법 (수동 온디맨드)

Claude Code에서 이 폴더를 열고: `"이번 주 요즘IT AI 트렌드 정리해줘"` (또는 슬래시 커맨드).
Claude가 ①수집 → ②AI 선별·분석 → ③트렌드 인사이트 → ④HTML 렌더를 순서대로 실행하고
산출물 경로와 기사 링크를 대화에 남긴다.

---

## 11. 구현 시 확정할 열린 항목 (Open Questions)

1. **pool 크기·페이지 수**: `--pool`(기본 12), `--pages`(기본 1~2) — AI 4~5개를 안정 확보할 값 실측.
2. **주차 중복 정책**: 인기 목록은 주 단위가 아니라 롤링이라, 같은 글이 여러 주에 잡힐 수 있음 →
   그대로 두고 "N주 연속 인기" streak로 표현(설계 채택). 필요 시 직전 주와 동일 세트면 안내.
3. **정렬 기준 옵션**: 기본 `view_count` 내림차순. 최신 편중 완화가 필요하면 `is_popular_news`+최근성 가중 검토(후순위).

---

## 12. 비목표 (Non-goals)

- 자동 스케줄 실행(로컬 파일 제약 → 수동 트리거).
- tier2 심층 분석(1단계 균일 분석으로 통합).
- HTML 스크래핑/헤드리스 브라우저(공개 JSON API로 충분 → 표준 라이브러리만).
- 요즘IT 전체 아카이브 크롤링(인기 AI 글 상위에 한정).
