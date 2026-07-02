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
