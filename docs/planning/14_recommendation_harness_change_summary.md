# 추천 하네스 및 멀티턴 추천 변경 요약

작성일: 2026-04-09

## 목적
- 추천 로직 회귀를 로컬에서 빠르게 확인할 수 있는 하네스를 추가합니다.
- 채팅 기반 추천에서 이전 추천 결과를 이어받는 멀티턴 refinement를 안정적으로 지원합니다.
- 실제 변경 범위와 현재 검증 상태를 후속 작업자가 바로 이해할 수 있도록 정리합니다.

## 이번 변경의 큰 축

### 1. 추천 하네스 추가
- FastAPI 내부에 추천 하네스 패키지를 추가했습니다.
- 하네스를 두 레이어로 분리했습니다.
  - `state harness`
    - 사용자 발화에서 `intent`, `pet_type`, `category`, `subcategory`, `brand`, `target_pet_id` 같은 상태를 얼마나 정확히 뽑는지 검증
  - `recommendation harness`
    - 구조화된 상태를 입력으로 넣었을 때 실제 추천 결과가 정책에 맞는지 검증

추가된 대표 파일:
- `services/fastapi/final_ai/harness/`
- `services/fastapi/final_ai/tests/harness/`
- `services/fastapi/final_ai/tests/fixtures/chat_state_cases.jsonl`
- `services/fastapi/final_ai/tests/fixtures/recommendation_cases.jsonl`
- `scripts/run_chat_recommend_harness.py`
- `scripts/run_recommendation_harness.py`
- `scripts/compare_harness_reports.py`

### 2. 상태 추출과 추천 fixture 확대
- `state harness` fixture는 현재 `18`개입니다.
- `recommendation harness` fixture는 현재 `17`개입니다.

현재 커버하는 대표 시나리오:
- 기본 추천 질문
- 브랜드 명시 추천
- 문맥 기반 카테고리 전환
- 문맥 기반 펫 타입 전환
- 건강고민 follow-up
- 복합 질문 분해
- 다펫 이름 기반 전환
- 예산 제한
- 알러지 제외
- 프로필 기반 추천
- 이전 추천 결과 refinement

### 3. 브랜드 hard filter 추가
- 현재 턴에서 브랜드를 명시하면 해당 브랜드만 추천 후보로 제한되도록 변경했습니다.
- 예: `로얄캐닌 고양이 사료 추천`

적용 위치:
- `services/fastapi/final_ai/domain/intent/service.py`
- `services/fastapi/final_ai/domain/recommendation/query_service.py`
- `services/fastapi/final_ai/infrastructure/repositories/product_filters.py`
- `services/fastapi/final_ai/infrastructure/search/hybrid_search.py`

### 4. 멀티턴 refinement 지원 추가
- 채팅에서 추천 결과가 생성되면 마지막 추천 상품의 `goods_id` 목록을 메모리에 저장하도록 변경했습니다.
- 다음 턴이 `이 중에서`, `그중에서`, `방금 추천한 것 중` 같은 refinement이면 이전 추천 결과 집합 안에서만 다시 검색하도록 변경했습니다.

핵심 구조:
- `last_recommended_goods_ids`
- `allowed_goods_ids`
- `is_result_refinement`
- `refinement_sort`

적용 위치:
- `services/fastapi/final_ai/application/chat/dto.py`
- `services/fastapi/final_ai/application/chat/memory.py`
- `services/fastapi/final_ai/graph/state.py`
- `services/fastapi/final_ai/graph/builder.py`
- `services/fastapi/final_ai/graph/nodes/merge_node.py`
- `services/fastapi/final_ai/domain/intent/service.py`
- `services/fastapi/final_ai/domain/recommendation/search_service.py`
- `services/fastapi/final_ai/infrastructure/repositories/product_filters.py`

### 5. refinement 조건의 deterministic 정렬 추가
- refinement는 이제 단순히 이전 추천 집합으로만 좁히는 것이 아니라, 그 집합 안에서 정렬 기준도 다시 적용합니다.
- 현재 지원 정렬:
  - `price_low`
  - `price_high`
  - `popularity`
  - `rating`
  - `review_count`

예:
- `이 중에서 더 싼 거로 보여줘` -> `price_low`
- `그중에서 인기 많은 거` -> `popularity`

적용 위치:
- `services/fastapi/final_ai/domain/intent/prompts.py`
- `services/fastapi/final_ai/domain/intent/service.py`
- `services/fastapi/final_ai/domain/recommendation/rerank_service.py`

## refinement 판정 방식
- `is_result_refinement`는 이제 LLM이 1차로 판단합니다.
- 기존 토큰 매칭 규칙은 제거하지 않았지만, 현재는 LLM 응답에 해당 키가 없을 때만 fallback으로 사용합니다.

의도:
- refinement 여부를 문맥 이해 기반으로 판단하게 하되
- 제어 흐름이 완전히 흔들리지 않도록 최소한의 안전장치는 유지

## JSON 출력 개선
- 하네스 결과는 레포 안 `output/harness-runs/` 아래에 저장됩니다.
- 각 실행 결과에는 사람이 바로 읽을 수 있는 `case_summaries`를 포함합니다.
- `state harness`는 다음 정보를 같이 저장합니다.
  - 원문 질문
  - 내부 정규화 질문
  - intent
  - filters
  - health_concerns
  - route
  - refinement 여부
- `recommendation harness`는 다음 정보를 같이 저장합니다.
  - 추천 결과 goods_id
  - allowed scope
  - last recommended goods ids
  - refinement sort
  - policy failure
  - result count

## 테스트 및 검증

### 단위 테스트
실행 통과:
- FastAPI:
  - `final_ai.tests.application.test_chat_service`
  - `final_ai.tests.domain.test_intent_service`
  - `final_ai.tests.domain.test_search_service`
  - `final_ai.tests.domain.test_rerank_service`
  - `final_ai.tests.harness.test_harness`
- Django:
  - `chat.tests.ChatProxyTests.test_session_messages_proxy_persists_user_and_assistant_messages`

의미:
- 이전 추천 결과 `goods_id`가 Django 채팅 세션 메모리에 저장되는지 확인
- refinement 상태가 FastAPI graph 초기 상태로 다시 복원되는지 확인
- refinement 정렬 로직이 기대 순서를 만드는지 확인

### live harness 검증
실행 통과한 대표 결과:
- state refinement:
  - `output/harness-runs/state/chat_state_harness_20260409_171616.json`
- recommendation refinement `price_low`:
  - `output/harness-runs/recommendation/recommendation_harness_20260409_171522.json`
- recommendation refinement `popularity`:
  - `output/harness-runs/recommendation/recommendation_harness_20260409_171618.json`

확인된 내용:
- `이 중에서 더 싼 거로 보여줘`
  - 이전 추천 2개 안에서만 재검색
  - `price_low` 기준 재정렬
- `그중에서 인기 많은 거`
  - 같은 2개 안에서만 재검색
  - `popularity` 기준 재정렬

## Django 쪽 변경
- Django 테스트 더블 응답에 `last_recommended_goods_ids`를 포함시켰습니다.
- 채팅 persistence 테스트에서 해당 값이 실제 `memory.dialog_state`에 저장되는지 검증합니다.

변경 파일:
- `services/django/chat/tests.py`

## 현재 작업트리 기준 주요 변경 파일

### WEB 루트
- `services/django/chat/tests.py`
- `scripts/run_chat_recommend_harness.py`
- `scripts/run_recommendation_harness.py`
- `scripts/compare_harness_reports.py`

### AI 서브모듈
- `final_ai/domain/intent/prompts.py`
- `final_ai/domain/intent/service.py`
- `final_ai/domain/recommendation/query_service.py`
- `final_ai/domain/recommendation/search_service.py`
- `final_ai/domain/recommendation/rerank_service.py`
- `final_ai/application/chat/dto.py`
- `final_ai/application/chat/memory.py`
- `final_ai/graph/state.py`
- `final_ai/graph/builder.py`
- `final_ai/graph/nodes/merge_node.py`
- `final_ai/infrastructure/repositories/product_filters.py`
- `final_ai/infrastructure/search/hybrid_search.py`
- `final_ai/tests/application/test_chat_service.py`
- `final_ai/tests/domain/test_intent_service.py`
- `final_ai/tests/domain/test_search_service.py`
- `final_ai/tests/domain/test_rerank_service.py`
- `final_ai/tests/harness/test_harness.py`

## 남은 작업
- 브라우저 기준 실제 채팅 2턴 HTTP 왕복 E2E 검증
- refinement 조건 확장
  - 예: 성분 제외, 브랜드 재한정, 가격 상한과 refinement 조합
- 실제 서비스 질문 로그 기반 fixture 추가 축적
- baseline/candidate 비교 루틴 고정

## 현재 리스크
- refinement scope와 정렬은 구현됐지만, 실제 사용자 표현은 더 다양할 수 있습니다.
- `ingredient exclusion`처럼 의미 해석이 더 복잡한 refinement는 아직 fixture를 더 쌓아야 합니다.
- 변경사항은 아직 커밋되지 않았습니다.
