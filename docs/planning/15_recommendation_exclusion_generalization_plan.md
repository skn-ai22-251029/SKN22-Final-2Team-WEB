# 추천 제외 키워드 일반화 및 전후 응답 검증 계획

## 배경
- 현재 추천 파이프라인은 포함 조건 중심으로만 동작합니다.
- 사용자가 `로얄캐닌 제외`, `연어 빼고`, `습식 말고`, `방금 추천한 거 말고 다른 거`처럼 제외 조건을 말해도 추천 결과에서 제대로 제거되지 않습니다.
- 실제 develop 기준에서 `로얄캐닌 제외하고 고양이 사료 추천해줘`는 `brand=로얄캐닌` 포함 필터로 해석되어 로얄캐닌 제품만 추천되는 문제가 재현되었습니다.

## 목표
- 사용자의 제외/삭제/말고/빼고/다른 등의 표현을 구조화된 exclusion 상태로 저장합니다.
- 추천 검색과 fallback retry 전 단계에서 exclusion을 유지합니다.
- 코드 변경 전/후 동일 질문에 대한 응답과 추천 결과를 비교해 개선 여부를 확인합니다.

## 핵심 원칙
1. `filters`는 포함 조건만 유지합니다.
2. 제외 조건은 `exclusions` 상태로 별도 관리합니다.
3. fallback retry에서는 포함 조건만 완화하고 exclusion은 유지합니다.
4. 임시 제외 요청을 `allergies` 같은 영속 사용자 정보와 합치지 않습니다.

## exclusion 구조
- `brands`: 제외 브랜드
- `categories`: 제외 카테고리
- `subcategories`: 제외 서브카테고리
- `health_concerns`: 제외 건강 관심사 태그
- `ingredients`: 제외 성분/원재료
- `keywords`: 위 분류에 정확히 매핑되지 않은 일반 제외 키워드
- `goods_ids`: 직전 추천 결과에서 제외할 상품 ID

## 해석 규칙
- `A 제외`, `A 빼고`, `A 말고`, `A 삭제`, `A 없는`은 exclusion 후보로 해석합니다.
- `다른 거`, `다른 상품`은 직전 추천 결과가 있으면 `goods_ids` exclusion으로 처리합니다.
- `다른 카테고리`는 기존 next-request 흐름을 유지하고 exclusion으로 처리하지 않습니다.
- 분류 우선순위:
  1. 브랜드
  2. 카테고리/서브카테고리
  3. 건강 관심사
  4. 성분
  5. 일반 키워드

## 검색 적용 방식
- 포함 조건:
  - `pet_type`, `category`, `subcategory`, `brand`
- 제외 조건:
  - `brand_name NOT ILIKE`
  - `goods_name NOT ILIKE`
  - `category`/`subcategory` 배열에 대한 NOT EXISTS
  - `health_concern_tags` 배열 제외
  - 필요 시 `main_ingredients`, `ingredient_text_ocr` 기반 제외

## fallback 정책
- 완화 대상:
  - `health_concern`
  - `subcategory`
  - `age_group`
  - `breed`
- 유지 대상:
  - `pet_type`
  - `category`
  - `allowed_goods_ids`
  - 모든 `exclusions`
- early stop:
  - 최종 추천 카드가 5개 이상이면 즉시 종료

## 구현 단계
1. 계약/상태/메모리 구조에 `exclusions` 추가
2. intent prompt와 parser에서 제외 표현 추출
3. query/search/repository 계층에 exclusion 전달
4. fallback retry에서 exclusion 유지
5. 단위 테스트 추가
6. 변경 전/후 응답 비교 검증 수행

## 전후 검증 절차
### 변경 전 기준선 확보
- develop 기준 실제 `/api/chat/` 호출로 아래 질문들을 기록합니다.
- 기록 항목:
  - 입력된 펫정보
  - 사용자질문
  - 추출된 filters/exclusions
  - search_query
  - 추천제품 개수
  - 추천제품 목록
  - 최종 응답

### 변경 후 재검증
- 동일 입력으로 다시 호출합니다.
- 비교 포인트:
  - exclusion이 구조화되었는지
  - 제외 대상 브랜드/키워드가 결과에서 사라졌는지
  - fallback 후에도 exclusion이 유지되는지
  - 응답 문구와 product_cards가 정상 반환되는지

### 우선 검증 케이스
1. `로얄캐닌 제외하고 고양이 사료 추천해줘`
2. `연어 빼고 강아지 사료 추천해줘`
3. `습식 말고 건식 사료 추천해줘`
4. `요로 사료 추천해줘. 로얄캐닌은 제외해줘`
5. `방금 추천한 거 말고 다른 거 보여줘`

## 변경 예정 파일
- `services/fastapi/final_ai/contracts/filters.py`
- `services/fastapi/final_ai/graph/state.py`
- `services/fastapi/final_ai/domain/intent/prompts.py`
- `services/fastapi/final_ai/domain/intent/service.py`
- `services/fastapi/final_ai/domain/recommendation/query_service.py`
- `services/fastapi/final_ai/domain/recommendation/search_service.py`
- `services/fastapi/final_ai/domain/recommendation/filter_relaxation.py`
- `services/fastapi/final_ai/infrastructure/repositories/product_filters.py`
- `services/fastapi/final_ai/infrastructure/repositories/product_repository.py`
- `services/fastapi/final_ai/infrastructure/search/hybrid_search.py`
- `services/fastapi/final_ai/application/chat/dto.py`
- `services/fastapi/final_ai/application/chat/memory.py`
- 관련 테스트 파일

## 리스크
- 일반 키워드 exclusion을 너무 넓게 적용하면 후보군이 과도하게 줄 수 있습니다.
- `다른` 표현은 문맥에 따라 exclusion이 아니라 카테고리 전환일 수 있어 후속 요청 분기가 중요합니다.
- 성분 exclusion은 상품명뿐 아니라 OCR/주원료 데이터 품질 영향을 받습니다.
