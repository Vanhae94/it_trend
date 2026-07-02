# 📰 요즘IT AI 트렌드 주간 관측기

매주(사용자 요청 시) [요즘IT](https://yozm.wishket.com/) 인기 글 중 AI 관련 상위 4~5개를 수집·분석·요약하고,
누적 데이터로 최근 AI 트렌드를 도출해 **예쁜 한국어 HTML 리포트**로 정리하는 개인 학습용 시스템.

> **핵심 철학:** 결정론적 작업(수집·집계·렌더)은 Python 스크립트가, 판단·서술(선별·분석·트렌드 인사이트)은 Claude가 맡는다.
> Python 표준 라이브러리만 사용 — **추가 설치(pip) 없음**.

---

## ⚡ 매주 사용법 (TL;DR)

Claude Code에서 이 폴더를 열고:

```
이번 주 요즘IT AI 트렌드 정리해줘
```

그러면 Claude가 `.claude/skills/yozm-ai-trends/SKILL.md` 절차를 따라 자동으로:
1. **수집** — 요즘IT 인기 글 API에서 AI 관련 후보 pool을 가져옴
2. **선별 + 1차 분석** — 본문 기반으로 상위 4~5개를 골라 한국어 요약·분류
3. **트렌드 인사이트** — 누적 데이터(`index.json`)로 "최근 동향" 도출
4. **HTML 생성** — 주간 리포트 + 월간/마스터 인덱스 갱신

결과물: [`index.html`](index.html)(전체 대시보드)과 `2026.07/2026-Wxx_주간리포트.html`.

---

## 🧭 동작 원리 (파이프라인)

```
사용자: "이번 주 요즘IT AI 트렌드 정리해줘"  ─▶  Claude가 SKILL.md 절차를 오케스트레이션
  │
  ├─ ① fetch_trends.py   요즘IT JSON API 호출 → AI 필터·평탄화 → _data/weeks/<주차>.json 저장 (멱등)
  ├─ ② [Claude]          본문(raw_content) 기반 선별(4~5개) + 분석 → 패치 JSON 작성
  │                       → merge_analysis.py로 weeks 기록에 병합
  ├─ ③ rollup.py         전 주차 집계 → _data/index.json (정량 신호 단일 출처)
  │     [Claude]          누적 신호 근거로 week_summary(동향) 작성 → 재머지
  └─ ④ render.py         분석 JSON → 템플릿 주입 → HTML + 인덱스 멱등 재생성
                         (연속 등장 글엔 "🔁 N주 연속 인기" 배지 자동 부착)
```

---

## 🔌 데이터 소스

요즘IT 공개 JSON API를 그대로 사용한다(HTML 파싱 없음).

| 용도 | 엔드포인트 | 주요 필드 |
|---|---|---|
| 인기 목록 | `GET /api/articleListApi/?category=popular&page=N&ordering=new` | `id`, `title`, `description`, `view_count`, `category[].flag`, `date_published`, `read_time` |
| 본문 상세 | `GET /api/fetchContentsDetail/?id=ID&affectView=false` | `raw_content`(본문 평문), `hash_tags` |

- **AI 필터**: 목록 응답의 `category[].flag == 'ai'` 인 글만 후보로 남긴다.
- **인기 신호**: `view_count`(누적 조회수) 내림차순으로 pool을 정렬해 상위 N개만 상세 조회한다.
- **`affectView=false` 필수**: 상세 조회가 실제 사용자 조회수를 올리지 않도록(조회수 오염 방지) 항상 이 값으로 호출한다.

---

## 📁 폴더 구조

```
요즘IT/                                    ← 프로젝트 루트 (이 폴더 전체가 자기완결형)
├─ README.md                             ← 이 문서
├─ index.html                            ← 마스터 대시보드 (전체 주차/월)
├─ 2026.07/                              ← 월별 폴더 (점 구분)
│  ├─ index.html                         ← 월간 인덱스 (+ 월말 종합 임베드)
│  └─ 2026-W27_주간리포트.html            ← 주간 리포트
├─ _assets/
│  ├─ style.css                          ← 단일 공통 디자인 시스템 "Nightdesk"
│  └─ app.js                             ← 테마 토글 등 (외부 라이브러리 0)
├─ _data/                                ← 모든 데이터 (재생성·트렌드 분석 소스)
│  ├─ taxonomy.json                      ← 폐쇄형 카테고리 10개 + 키워드 별칭 사전
│  ├─ index.json                         ← 전 주차 정량 롤업 (rollup.py가 매주 재생성)
│  ├─ weeks/<주차>.json                  ← 주차별 원본+분석 기록 (불변 raw)
│  ├─ weeks/<주차>.raw.json              ← API 원본 응답 박제 (감사용)
│  ├─ analysis/<주차>.patch.json         ← Claude가 작성하는 분석 패치
│  └─ months/<YYYY.MM>.json              ← 월간 종합 트렌드 (월말 생성)
├─ docs/superpowers/{specs,plans}/       ← 설계·계획 문서
└─ .claude/
   ├─ launch.json                        ← 미리보기용 정적 서버 설정 (선택)
   └─ skills/yozm-ai-trends/
      ├─ SKILL.md                        ← 주간 워크플로우 절차 (Claude의 지침)
      ├─ schema.json                     ← weeks 기사 객체 데이터 명세
      ├─ scripts/                        ← fetch_trends / merge_analysis / rollup / render
      └─ templates/                      ← report / monthly / master_index / article_card
```

---

## 🗃️ 데이터 모델 (3층)

1. **`_data/weeks/<주차>.json`** — 불변 기록. API 원본을 평탄화한 `raw`(수정 금지) + Claude가 채우는
   `selected`/`classify`/`analysis`/`learning` + 주차 `week_summary`. `articles[]`는 view_count 상위 AI 후보 pool 전체이며,
   그중 이번 주 리포트에 실을 4~5개만 `selected: true`. 정확한 필드는
   [`schema.json`](.claude/skills/yozm-ai-trends/schema.json) 참조.
2. **`_data/index.json`** — `rollup.py`가 weeks 전체를 읽어 결정론적으로 만드는 **정량 신호 단일 출처**.
   `category_timeseries`(카테고리별 주차 추이), `keyword_freq`(누적 키워드 빈도), `article_weeks`(기사별 등장 주차 이력 — streak 계산 근거),
   `view_timeseries`(주차별 조회수 합), `ai_share_timeseries`(주차별 인기 풀 중 AI 비율) 등을 담는다.
3. **`_data/taxonomy.json`** — 폐쇄형 1차 카테고리 10개(주차 간 비교용) + `keyword_aliases`(동의어 통합 사전).

> Claude는 거대한 weeks JSON을 직접 편집하지 않고, 작은 **패치 JSON**(`_data/analysis/<주차>.patch.json`)을 작성해
> `merge_analysis.py`로 병합한다 → 안전·재현 가능. 분석을 고치려면 패치만 수정 후 재병합·재렌더.
> `merge_analysis.py`는 **있는 키만 갱신**하므로 여러 번 부분 병합해도 안전하다.

---

## 🔧 구성요소 (스크립트)

모든 스크립트는 `py <스크립트> --root "<프로젝트 루트 절대경로>"` 형식. 위치:
`.claude/skills/yozm-ai-trends/scripts/`

| 스크립트 | 역할 | 주요 인자 |
|---|---|---|
| `fetch_trends.py` | 요즘IT 인기 목록+본문 API 수집·AI 필터·평탄화·멱등 저장 | `--root` `--week auto\|YYYY-Wnn` `--pool 12` `--pages 2` `--force` `--date YYYY-MM-DD` |
| `merge_analysis.py` | Claude의 분석 패치를 주차 기록에 병합(`raw` 보존) | `--root` `--patch <경로>` |
| `rollup.py` | 전 주차 정량 롤업(`index.json`) 재생성 | `--root` |
| `render.py` | 분석 JSON → HTML 렌더 + 인덱스 재생성 | `--root` `--week YYYY-Wnn`(생략 시 인덱스만) |

**멱등성:** 같은 주차 재수집은 `--force` 없으면 스킵(`STATUS=exists`). merge/rollup/render는 항상 안전하게 재실행 가능(중복 없음).

---

## 📈 트렌드 분석 방법론 (과적합 방지가 핵심)

표본이 주 4~5건으로 작기 때문에 **정량(스크립트 집계)과 정성(Claude 서술)을 분리**하고, 정성 문장은 반드시 정량 근거를 인용한다.

- **콜드스타트 분기**(`index.json`의 `totals.weeks` 기준):
  - 1주차 → "기준선 수립 중"(비교 데이터 없음)
  - 2주차 → 직전 주 대비 단순 등장/소멸만 (성급한 "부상/지속" 단정 금지)
  - 3주차+ → 지속(최근 3~4주 중 3주+) / 부상(서로 다른 2주+ 등장) / 식어감(3주+ 데이터 시) 판정
- **연속 등장(streak)**: 같은 글이 여러 주 연속으로 인기 풀에 오르면 카드에 **"🔁 N주 연속 인기"** 배지가 자동으로 붙는다.
  `rollup.py`가 기사별 등장 주차를 `index.json`의 `article_weeks`에 기록하고, `render.py`가 렌더 대상 주차에서
  거슬러 올라가며 연속 등장 주차 수를 계산한다.
- **AI 점유율 추이**: `pool_ai_share`(인기 목록 중 AI 관련 글 비율)를 주차별로 추적해 AI 화제성 자체의 등락을 함께 서술한다.
- **상시 경고(caveat)**: "view_count = 관심도 지표이지 중요도가 아니다"를 리포트에 항상 명시한다. 표본이 주 4~5건으로 작다는 점도 함께 밝힌다.
- **시각화**: 외부 차트 라이브러리 0 — 키워드 빈도는 CSS 막대, 주차 추이는 인라인 SVG로 그린다.

---

## 🎨 디자인 시스템 — "Nightdesk"

- 컨셉: 웜 다크 잉크브라운 바탕에 앰버/골드 액센트 — 저녁 데스크에서 훑어보는 개인 관측 일지. **다크 기본 + 라이트 토글**(localStorage 기억).
- 단일 [`_assets/style.css`](_assets/style.css) 하나로 모든 페이지 일관. 빌드 단계 없이 브라우저에서 바로 열림.
- 외부 차트 라이브러리 0 — 모든 그래프는 CSS/SVG로 직접 그린다.
- 색감·무드를 바꾸려면 `style.css` 상단의 CSS 변수(`:root`, `[data-theme="light"]`)만 수정하면 전체가 일관되게 바뀐다.

---

## 🚀 새 환경에서 셋업 (포터빌리티)

**이 폴더 전체를 복사**하면 그대로 동작한다. 시스템이 자기완결형이기 때문:

1. **필요 조건**
   - Python **3.8+ 필요**(`datetime.date.fromisocalendar` 사용, 권장 3.10+). 추가 패키지 **없음(pip 불필요)**.
   - 인터넷 (요즘IT API 수집 + 폰트 CDN).
   - 선별·분석·인사이트 단계는 **Claude Code**가 수행(스킬 자동 인식).
2. **경로**: 스크립트는 `--root`로 루트를 받으므로 폴더 위치가 어디든 OK. 한글·공백 경로는 항상 **따옴표 + 절대경로**.
3. **OS 차이**: Windows는 `py`, macOS/Linux는 `python3`. 경로 구분자만 주의(스크립트는 `os.path`로 OS 무관).
4. **인코딩**: 모든 파일 I/O는 UTF-8. 콘솔 한글 출력을 위해 각 스크립트 상단에 `sys.stdout.reconfigure(encoding="utf-8")`가 들어 있다.
5. **스킬 인식**: Claude Code에서 이 폴더를 작업 디렉터리로 열면 `.claude/skills/yozm-ai-trends`가 자동 등록된다.
6. **확인**: `py ".claude/skills/yozm-ai-trends/scripts/fetch_trends.py" --root "<루트>" --week auto` 가
   `STATUS=ok ...`를 출력하면 정상.

---

## 🧯 트러블슈팅

| 증상 | 원인·해결 |
|---|---|
| `FETCH_ERROR` | 네트워크/요즘IT API 일시 오류 → 잠시 후 재시도. 부분 산출물은 만들지 않음. |
| `STATUS=exists` | 이번 주는 이미 수집됨. 다시 받으려면 `--force` 추가. |
| 한글 깨짐 | 모든 파일 I/O는 UTF-8. 새 스크립트 추가 시 `encoding="utf-8"` 유지. |
| `py`를 못 찾음 | macOS/Linux면 `python3`로 교체. |
| 디자인 변경이 안 보임 | 브라우저 CSS 캐시 → 새로고침(Ctrl+F5). |

---

## 📌 자주 쓰는 명령 요약

```bash
# 이번 주 수집
py ".claude/skills/yozm-ai-trends/scripts/fetch_trends.py" --root "." --week auto

# 분석 병합 (Claude가 작성한 패치를 반영)
py ".claude/skills/yozm-ai-trends/scripts/merge_analysis.py" --root "." --patch "_data/analysis/2026-W27.patch.json"

# 정량 롤업 (index.json 재생성)
py ".claude/skills/yozm-ai-trends/scripts/rollup.py" --root "."

# 주간 렌더 (+인덱스)
py ".claude/skills/yozm-ai-trends/scripts/render.py" --root "." --week 2026-W27

# 인덱스만 재생성
py ".claude/skills/yozm-ai-trends/scripts/render.py" --root "."
```

> 자세한 주간 절차는 [`SKILL.md`](.claude/skills/yozm-ai-trends/SKILL.md), 데이터 명세는
> [`schema.json`](.claude/skills/yozm-ai-trends/schema.json) 참조.
> 설계 배경과 구현 계획은 [`docs/superpowers/specs/2026-07-02-yozm-ai-trends-design.md`](docs/superpowers/specs/2026-07-02-yozm-ai-trends-design.md),
> [`docs/superpowers/plans/2026-07-02-yozm-ai-trends.md`](docs/superpowers/plans/2026-07-02-yozm-ai-trends.md) 참조.
