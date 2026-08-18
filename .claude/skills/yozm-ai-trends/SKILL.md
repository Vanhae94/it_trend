---
name: yozm-ai-trends
description: >-
  요즘IT 매거진 인기 글 상위 4~5개를 매주 수집·분석·요약하고,
  누적 데이터로 최근 IT 트렌드 인사이트를 도출해 예쁜 한국어 HTML 리포트로 정리한다.
  전반 IT 소식을 다루되 인기글 중 AI 비중은 부가 지표로 관측.
  "이번 주 요즘IT 위클리", "요즘IT 주간 정리", "주간 IT 트렌드", "월간 종합 트렌드" 요청에 사용. 개인 학습용.
---

# 요즘IT 위클리 — 주간 IT 트렌드 (yozm-ai-trends)

매주 요즘IT 인기 글 상위 4~5개를 수집→분석→요약하고 누적 트렌드를 HTML 리포트로 만든다.
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
- 후보가 4개 미만이면 받은 만큼 진행하고 리포트에 명시.

### ①-2 후보 정리 (스크립트)
```
py "<ROOT>\.claude\skills\yozm-ai-trends\scripts\candidates.py" --root "<ROOT>" --week <week>
```
- 인기 목록이 **롤링**이라 상위권 글이 여러 주 눌러앉는다. 후보를 **신규/재조명**으로 갈라 보여준다.
- `⚠본문없음`이 뜨면 `fetch_trends.py --pool 20 --force`로 재수집(집계 기준 `--pages 2`는 유지 — AI 비중 시계열 보존).

### ② 선별 + 1차 분석 (너 — 본문 기반)
`<ROOT>\_data\weeks\<week>.json`의 `articles[]`(view_count 상위 인기 후보 pool)를 읽는다.
각 기사의 `raw.summary`+`raw.body`(raw_content 평문)+`raw.keywords`로 판단한다.

1. **선별 — 2트랙으로 5건**에 `selected: true` (단순 광고성·홍보성 제외):
   - **신규 3건**: 한 번도 분석하지 않은 글 중 인기 상위부터.
   - **재조명 2건**: 이미 분석했으나 인기 풀에 계속 살아남은 글.
     우선순위는 **조회수 × 마지막 분석 이후 경과 주차**로 잡는다(연속 등장 길이만 보지 말 것).
     `candidates.py` 출력의 '분석 Wnn' 이력과 조회수를 함께 보고, **주간 조회 증가분이 사실상 0인 글**은
     이미 식은 글이므로 우선순위를 낮춘다(직전 주차 weeks JSON과 view_count를 비교하면 나온다).
     재조명은 **반드시 새 각도**여야 한다 — 직전 분석의 `one_liner`/`key_points`/`key_terms`를
     `_data/analysis/<이전주차>.patch.json`에서 확인하고 겹치면 다른 관점(누적 관점, 후속 사건,
     반대 사례, 실무 적용 각도)으로 다시 쓴다. `why_now`에 **몇 번째 재조명인지와 이전 주차**를 밝힌다.
   - 두 트랙 합쳐 `primary_category` 5개가 **서로 겹치지 않게** 조합한다.
   - 신규가 3건에 못 미치면 재조명을 늘리고(그 반대도 가능), 그 사실을 `week_summary`에 적는다.
   - 선정 근거는 사실대로 쓴다. "미분석 글만 골랐다"처럼 **후보 수를 감추는 표현 금지**
     (예: "미분석 9건 중 주제가 겹치지 않도록 3건" + "재조명 2건").
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
- **부상 판정 기준**: 서로 다른 **2주 이상** 등장한 키만 "부상". 1주만 나온 키는 판정을 다음 주로 미루고
  그 사실을 `recent_trend_ko`에 남긴다(다음 주에 실제로 재등장했는지 확인해 결론낸다).
- **선별이 만든 착시를 반드시 분리**: 조회수 합·키워드 결번/복귀는 트렌드가 아니라 **선별 결과**일 때가 많다.
  재조명 트랙은 같은 기사의 태그를 다시 집계하므로 누적 카운트를 부풀린다. 신규 트랙만 고르면 조회수 합이 내려간다.
  이런 변화는 `caveats_ko`에 "관심도 변화가 아니라 선별 방식의 결과"라고 명시한다.
- **누적 카운트는 연인원이다**: `keyword_freq`의 `count`는 재조명 재집계를 포함한 연인원이고,
  `unique_articles`가 실제 고유 기사 수다. 둘이 다른 키를 인용할 때는 **반드시 함께 적는다**
  (예: "ai-regulation 3회(고유 기사 1건) — 같은 글을 세 번 읽은 결과").
- **조회수 합은 분모와 함께**: 선정 5건 합만 쓰지 말고 그 주 인기 상위 5건 합(이론적 상한) 대비 비율을 함께 계산해
  "회복/하락"을 판단한다. 1위 글 하나가 합의 큰 부분을 차지하면 그 사실도 밝힌다.
- **카드 간 사실 충돌 점검**: 같은 주 다른 카드가 전한 후속 사건이 어떤 카드의 전제를 뒤집지 않는지 확인하고,
  뒤집는다면 그 카드에 한 줄로 연결한다(예: 미결 사안이 다른 카드에서 해결된 경우).
- **태그 키는 기존 사전 우선**: 새 키를 만들기 전에 `index.json`의 `keyword_freq`와 taxonomy `keyword_aliases`를
  먼저 확인한다(예: `팀AX`→기존 `ax`, `AI거버넌스`→기존 `ai-regulation`). 동의어가 갈리면 시계열이 쪼개진다.
  단 **hash_tags에 근거 없는 태그는 지표를 위해서라도 붙이지 않는다.**
- **과적합 방지**: 정성 문장은 index.json 숫자 근거. view_count는 "관심도"(중요도 아님). 표본 4~5개 caveat 상시.

### ④ HTML 렌더 (스크립트)
```
py "<ROOT>\.claude\skills\yozm-ai-trends\scripts\render.py" --root "<ROOT>" --week <week>
```
- 주간 리포트 + 월간 index + 마스터 index 멱등 재생성. 연속 등장 글은 "🔁 N주 연속 인기",
  재조명 트랙은 "🔎 재조명 N회차" 배지가 `index.json`의 `analyzed_weeks` 기준으로 자동 표시된다.
- 끝나면 산출물 경로와 기사 원문 링크를 대화에 남긴다.

## 월간 종합 (월말 또는 요청 시)
`index.json`의 `per_week`에서 해당 월 주차를 모아 3~4개 흐름 도출 → `<ROOT>\_data\months\<YYYY.MM>.json`
(`{month, headline_ko, synthesis:[{title, tag:persist|emerging|cooling, body}]}`) 작성 → render 재실행.

## 견고성 체크리스트
- fetch 실패 시 중단(부분 산출물 금지), 재시도 안내.
- 같은 주 재실행 안전(merge/rollup/render 멱등). 분석 수정은 패치만 고쳐 재머지·재렌더.
- 분류 애매하면 `confidence:"low"`.
