# 추천 필터 완화 정책 변경 계획

작성일: 2026-04-13

관련 이슈: https://github.com/skn-ai22-251029/SKN22-Final-2Team-WEB/issues/375

## 목적
- 사용자 질문에서 너무 많은 분류값이 추출되었을 때 추천 후보가 0개가 되는 문제를 줄입니다.
- `health_concern`뿐 아니라 `subcategory`, 연령대, 품종/세부 조건처럼 데이터 커버리지가 낮은 조건도 단계적으로 완화합니다.
- 최종적으로 추천 의도에서는 가능한 한 빈 `product_card`를 반환하지 않고, 관련성이 낮아지더라도 일반 추천 상품을 최대 5개까지 확보합니다.

## 현재 상태
- `health_concern` 필터 때문에 후보가 0개가 되는 경우에는 재검색 시 `health_concern` 값을 비우는 fallback이 반영되어 있습니다.
- `/api/recommend/` 직접 호출도 graph 경로와 동일하게 1회 재검색을 수행합니다.
- 다중 `health_concern` 검색의 PostgreSQL array overlap cast 문제는 `varchar[]` 캐스팅으로 수정되어 있습니다.

현재 한계:
- `filter_relaxation_count`가 현재는 사실상 0 또는 1 단계만 표현합니다.
- 현재 retry 조건은 `relaxation < 1`이라 최초 검색 이후 최대 1번만 재검색합니다.
- `health_concern`과 일부 `subcategory` 완화만 처리하므로, 여러 세부 분류가 동시에 걸린 경우에는 여전히 후보가 0개가 될 수 있습니다.
- 검색어에는 원래 분류값이 계속 포함될 수 있어, hard filter를 제거해도 벡터/키워드 검색 쿼리 자체가 너무 좁게 남을 수 있습니다.

변경 후 목표:
- 최대 retry 횟수는 4번입니다.
- 최초 strict 검색까지 포함하면 총 5번까지 검색할 수 있습니다.
- 단, 추천 상품이 5개 확보되면 즉시 early stop합니다.
- 5개 미만이면 다음 relaxation 단계로 넘어가고, 마지막 단계에서도 부족하면 확보된 결과만 반환합니다.

## 변경 방향

### 1. 필수 조건과 선호 조건 분리
추천 검색 조건을 다음처럼 분리합니다.

필수 hard filter:
- `pet_type`: 강아지/고양이처럼 종이 명확한 경우
- `category`: 사용자가 명시한 큰 상품군. 예: 사료, 간식, 모래
- 시스템 조건: 판매 가능, 삭제 제외, 허용된 `goods_id` 범위 등

완화 가능한 soft condition:
- `health_concern`
- `subcategory`
- `age_group`
- `breed`
- `food_preferences`
- 기타 query-derived 세부 태그

주의:
- `brand`는 사용자가 명시한 경우 구매 의도가 강하므로 기본적으로 hard filter로 유지합니다.
- 다만 브랜드 필터 때문에 결과가 0개인 케이스를 별도로 완화할지는 정책 결정을 한 번 더 해야 합니다.
- `allowed_goods_ids`는 refinement 범위이므로 fallback 중에도 유지해야 합니다.

### 2. 단계적 filter relaxation ladder 추가
추천 후보가 0개이거나 rerank 결과가 최소 기준보다 부족하면 아래 순서로 재검색합니다.

| 단계 | 유지 조건 | 제거/완화 조건 | 목적 |
| --- | --- | --- | --- |
| 최초 검색 | 0 | `pet_type`, `category`, `subcategory`, `health_concern`, `age_group`, `brand` | 없음 | 가장 엄격한 검색 |
| retry 1 | 1 | `pet_type`, `category`, `subcategory`, `age_group`, `brand` | `health_concern` hard filter 및 검색어 힌트 제거 | 건강관심사 데이터 공백 대응 |
| retry 2 | 2 | `pet_type`, `category`, `age_group`, `brand` | `subcategory` 제거 | 세부 카테고리 과분류 대응 |
| retry 3 | 3 | `pet_type`, `category`, `brand` | `age_group`, `breed` 검색 힌트와 연령 필터 제거 | 생애 단계/품종 과제약 대응 |
| retry 4 | 4 | `pet_type`, `category`, `brand` | 남은 선택 조건 제거 | 일반식/일반상품 5개 확보 |

기본 정책:
- `pet_type`과 `category`는 가능한 끝까지 유지합니다.
- `health_concern`은 hard filter에서 제거되더라도 rerank boost에는 남깁니다.
- `subcategory`, `age_group`, `breed`도 hard filter/검색어에서는 제거할 수 있지만, 점수 boost나 설명용 메타데이터로는 보존합니다.
- `brand`는 구매 의도가 강하므로 우선 모든 단계에서 유지합니다. 브랜드 때문에 0개가 나는 케이스는 별도 정책으로 분리합니다.

### 3. 검색어 생성도 relaxation 단계와 동기화
현재는 `query_service`에서 검색어를 만들 때 건강관심사, 소분류, 연령대 등을 조합합니다.

변경 후에는 `filter_relaxation_count` 또는 명시적인 relaxation policy에 따라 검색어도 같이 넓힙니다.

예:
- 단계 0: `강아지 말티즈 사료 요로 퍼피`
- 단계 1: `강아지 말티즈 사료 퍼피`
- 단계 2: `강아지 사료 퍼피`
- 단계 3: `강아지 사료`
- 단계 4: `강아지 사료`

목적:
- hard filter만 제거하고 검색어는 그대로 좁게 남는 불일치를 줄입니다.
- fallback 단계가 올라갈수록 실제 후보군이 넓어지도록 보장합니다.

### 4. rerank retry 기준 확장
현재 `rerank_service`는 결과가 없거나 unique top 결과가 부족할 때 1회만 retry합니다.

변경 후:
- 최대 relaxation 단계 수를 상수로 관리합니다.
- 결과가 0개면 다음 단계로 즉시 retry합니다.
- 결과가 1~4개처럼 5개 미만이면 다음 단계로 retry해서 최대 5개 확보를 시도합니다.
- 결과가 5개가 되면 즉시 retry를 중단합니다.
- 최종 단계에서도 부족하면 확보된 결과만 반환하되, 빈 결과를 줄이는 방향으로 동작합니다.

예상 상수:
```python
MIN_RECOMMENDATION_RESULTS = 5
MAX_FILTER_RELAXATION_COUNT = 4
```

### 5. 응답 meta와 로그 보강
추천 응답과 로그에 어떤 단계까지 완화했는지 남깁니다.

추가 후보:
- `filter_relaxation_count`
- `filter_relaxation_stage`
- `relaxed_filters`
- `original_filters`
- `effective_filters`
- `candidate_count_by_stage`

목적:
- 배포환경에서 어떤 필터 때문에 후보가 죽었는지 바로 추적합니다.
- 하네스 결과에서도 strict 검색과 fallback 검색을 분리해서 확인합니다.

## 구현 과정

1. 현재 추천 검색 경로의 상태값을 정리합니다.
   - `filters`
   - `health_concerns`
   - `age_group`
   - `pet_profile.breed`
   - `brand`
   - `allowed_goods_ids`

2. relaxation policy helper를 추가합니다.
   - 입력: 원본 state, 현재 `filter_relaxation_count`
   - 출력: 검색에 사용할 effective filters, effective query hints, relaxed filter names

3. `query_service`에서 relaxation 단계에 맞게 검색어 구성 요소를 제거합니다.
   - strict 단계에서는 기존과 동일하게 조합합니다.
   - fallback 단계에서는 건강관심사, 세부 분류, 연령/품종 힌트를 단계적으로 제외합니다.

4. `search_service`에서 effective filters만 hard filter로 전달합니다.
   - `health_concern`은 단계 1부터 hard filter에서 제외합니다.
   - `subcategory`는 단계 2부터 제외합니다.
   - `allowed_goods_ids`는 refinement 범위라 항상 유지합니다.

5. `rerank_service`에서 retry 최대 단계를 1에서 정책 상수로 확장합니다.
   - 결과 부족 기준을 `MIN_RECOMMENDATION_RESULTS` 기준으로 판단합니다.
   - retry 시 `filter_relaxation_count`를 증가시킵니다.

6. `/api/recommend/` 직접 호출도 graph와 동일한 최대 단계만큼 반복합니다.
   - 현재 2회 반복을 policy 기반 반복으로 변경합니다.
   - 추천 결과가 5개 확보되면 early stop합니다.
   - 최대 반복 횟수는 최초 검색 1회 + retry 4회입니다.

7. 테스트와 하네스 fixture를 추가합니다.
   - 세부 조건이 과하게 추출되어 strict 결과가 0개인 케이스
   - 단일 `health_concern` 데이터 공백 케이스
   - 다중 `health_concern` 케이스
   - `subcategory` 과분류 케이스
   - 연령대 힌트 때문에 결과가 부족한 케이스
   - refinement에서 `allowed_goods_ids`가 fallback 중에도 유지되는 케이스

8. 배포환경에서 실제 질문으로 검증합니다.
   - 등록 pet의 건강관심사가 하나만 있고 질문이 `사료추천해줘`인 케이스
   - 건강관심사가 여러 개 등록된 pet의 `사료추천해줘` 케이스
   - query에서 건강관심사/세부 카테고리/연령대가 동시에 잡힌 케이스

## 이번 구현 결과

반영된 동작:
- retry 최대 횟수를 1회에서 4회로 확장했습니다.
- 최초 strict 검색까지 포함해 최대 5번 검색합니다.
- `reranked_results` 기준 추천 상품이 5개 확보되면 즉시 early stop합니다.
- 5개 미만이면 다음 relaxation 단계로 넘어갑니다.
- 마지막 단계까지 5개가 안 나오면 가장 많이 확보된 결과를 반환합니다.
- direct `/api/recommend/` 경로와 LangGraph chat 경로, recommendation harness 경로가 같은 retry 정책을 사용합니다.
- `original_filters`, `effective_filters`, `relaxed_filters`, `candidate_count_by_stage`를 남겨 배포환경 로그/응답 meta에서 어떤 조건이 완화됐는지 추적할 수 있게 했습니다.

실제 relaxation 순서:
- `0`: strict 검색
- `1`: `health_concern` 제거
- `2`: `subcategory` 제거
- `3`: `age_group`, `breed` 제거 및 연령 필터 비활성화
- `4`: `pet_type`, `category`, `brand` 중심 검색

보존 정책:
- `pet_type`과 `category`는 모든 단계에서 유지합니다.
- `brand`는 명시적 구매 의도가 강하므로 모든 단계에서 유지합니다.
- `allowed_goods_ids`는 refinement 범위이므로 모든 단계에서 유지합니다.
- 알러지 제외 조건은 안전 조건이므로 완화하지 않습니다.

## 변경될 파일

### FastAPI submodule

이번 변경 파일:
- `services/fastapi/final_ai/domain/recommendation/filter_relaxation.py`
  - relaxation 단계, retry 조건, target count 계산 helper 추가

- `services/fastapi/final_ai/domain/recommendation/query_service.py`
  - relaxation 단계별 검색어 구성 요소 제거
  - `health_concern`, `subcategory`, `age_group`, `breed` 힌트 포함 여부 조정

- `services/fastapi/final_ai/domain/recommendation/search_service.py`
  - relaxation 단계별 effective hard filter 적용
  - `health_concern`, `subcategory`, 연령/품종 조건 완화
  - stage별 로그 보강

- `services/fastapi/final_ai/domain/recommendation/rerank_service.py`
  - retry 최대 횟수 확장
  - 결과 부족 기준 상수화
  - retry pending 판단을 relaxation ladder 기준으로 변경
  - 5개 미만 fallback 중 이전 단계 결과가 더 많으면 best result로 보존

- `services/fastapi/final_ai/application/recommendation/service.py`
  - `/api/recommend/` 직접 호출의 반복 횟수를 policy 기반으로 변경
  - 응답 meta에 relaxation 관련 정보 추가

- `services/fastapi/final_ai/domain/recommendation/constants.py`
  - `MIN_RECOMMENDATION_RESULTS`
  - `MAX_FILTER_RELAXATION_COUNT`
  - `RECOMMENDATION_TOP_K`

- `services/fastapi/final_ai/application/chat/dto.py`
  - chat graph 초기 state에 relaxation runtime metadata 추가

- `services/fastapi/final_ai/graph/builder.py`
  - local `chat()` 초기 state에 relaxation runtime metadata 추가

- `services/fastapi/final_ai/graph/state.py`
  - relaxation runtime metadata 타입 추가

- `services/fastapi/final_ai/harness/recommendation_runner.py`
  - production과 동일하게 최대 5번 검색 루프 적용
  - query snapshot에 original/effective/relaxed filter 정보 추가

검증/테스트 변경 파일:
- `services/fastapi/final_ai/tests/domain/test_query_service.py`
  - relaxation 단계별 검색어 구성 테스트

- `services/fastapi/final_ai/tests/domain/test_search_service.py`
  - 단계별 hard filter 완화 테스트

- `services/fastapi/final_ai/tests/domain/test_rerank_service.py`
  - retry count와 부족 결과 판단 테스트

- `services/fastapi/final_ai/tests/application/test_recommendation_service.py`
  - `/api/recommend/` 직접 호출이 여러 fallback 단계를 수행하는지 테스트

- `services/fastapi/final_ai/tests/graph/test_chat_graph.py`
  - graph retry routing이 여러 단계 fallback을 수행하는지 테스트

- `services/fastapi/final_ai/tests/fixtures/recommendation_cases.jsonl`
  - 일반 추천 fallback 케이스 추가

- `services/fastapi/final_ai/tests/fixtures/recommendation_regression_cases.jsonl`
  - product_card 빈 결과 방지 회귀 케이스 추가

### WEB 루트

문서 변경:
- `docs/planning/15_recommendation_filter_relaxation_plan.md`
  - 본 변경 계획 문서

상위 repo 변경 가능성:
- FastAPI submodule PR이 merge된 뒤 Web repo에서 `services/fastapi` submodule pointer가 변경될 수 있습니다.

## 검증 계획

단위 테스트:
```bash
cd services/fastapi
.venv/bin/python -m unittest \
  final_ai.tests.domain.test_query_service \
  final_ai.tests.domain.test_search_service \
  final_ai.tests.domain.test_rerank_service \
  final_ai.tests.application.test_recommendation_service \
  final_ai.tests.graph.test_chat_graph
```

전체 테스트:
```bash
cd services/fastapi
.venv/bin/python -m unittest discover final_ai/tests
```

하네스:
```bash
cd /home/playdata/SKN22-Final-2Team-WEB
services/fastapi/.venv/bin/python scripts/run_recommendation_harness.py
```

배포환경 확인 질문:
- `사료추천해줘`
- `강아지 요로 사료 추천`
- `강아지 관절 피부 사료 추천`
- `6개월 강아지 요로 사료 추천`
- 등록 pet에 건강관심사 1개만 있는 상태에서 `사료추천해줘`
- 등록 pet에 건강관심사 여러 개가 있는 상태에서 `사료추천해줘`

성공 기준:
- 추천 의도에서 `product_cards`가 가능한 한 빈 배열로 끝나지 않습니다.
- strict 단계에서 결과가 없으면 fallback 단계가 실행됩니다.
- 최종 응답 meta/log에서 어떤 필터가 완화되었는지 확인할 수 있습니다.
- `pet_type`, `category`, `allowed_goods_ids` 같은 핵심 범위는 의도 없이 풀리지 않습니다.

현재 검증 결과:
```bash
cd /home/playdata/SKN22-Final-2Team-WEB/services/fastapi
.venv/bin/python -m unittest discover final_ai/tests
```

결과:
- `69` tests passed

## 리스크와 결정 필요 사항

- `brand`를 어느 단계에서 완화할지 결정이 필요합니다.
  - 브랜드 명시 질문은 구매 의도가 강하므로 기본은 유지가 안전합니다.
  - 다만 브랜드 상품이 없는 경우 일반 추천 5개 확보를 우선할지 정책 선택이 필요합니다.

- `category`를 최종 단계에서도 유지할지 결정이 필요합니다.
  - `사료추천해줘`에서 간식이 나오는 것은 UX상 부정확하므로 기본은 유지가 맞습니다.

- 알러지 제외 조건은 fallback 대상이 아닙니다.
  - 안전 조건이므로 결과가 부족해도 제거하지 않는 편이 맞습니다.

- 결과가 5개 미만일 때 계속 완화할지, 3개 이상이면 멈출지 기준이 필요합니다.
  - 운영 UX 기준은 5개 확보가 좋지만, 관련성 손실을 줄이려면 3개 이상에서 멈추는 정책도 가능합니다.
