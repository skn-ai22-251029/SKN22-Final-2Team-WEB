# 데이터 수집 이슈 정의

> **프로젝트**: SKN22 Final Project · 2팀
> **작성일**: 2026-03-09
> **범위**: 프로토타입 단계 기준

---

## 개요

어바웃펫(aboutpet.co.kr) 상품·리뷰 데이터를 수집하고, S3 Medallion 구조(Bronze → Silver → Gold)로 정제·증강한 뒤 PostgreSQL / Qdrant에 적재하는 파이프라인 전체를 정의한다.

**아키텍처 확장성 원칙**: S3 Medallion 구조와 배치 스크립트 인터페이스를 프로토타입 단계에서 확정하여, Phase 2에서 Airflow DAG 전환 시 아키텍처 변경 없이 자동화만 추가할 수 있도록 한다.

```
크롤링 (Playwright)
    ↓
Bronze  S3 Parquet (원시 데이터)
    ↓
Silver  S3 Parquet (정제·정규화)
    ↓
Gold    S3 Parquet (메타데이터 증강)
    ↓
    ├── PostgreSQL  (관계형 서빙 DB)
    └── Qdrant      (벡터 임베딩 인덱싱)
```

---

## 이슈 목록

### 이슈 1 — 어바웃펫 상품·리뷰 크롤링

**한 줄 설명**: Playwright로 상품 정보 + 리뷰 전수 수집

**배경**

- 대상: aboutpet.co.kr 강아지/고양이 전체 카테고리 (소분류 **106개**, 상품 **18,248개 listed → 4,934개 unique**, 중복률 73%)
- Playwright를 사용하는 이유: AJAX 기반 동적 렌더링 대응 및 세션/쿠키 자동 유지
- 상세 크롤링 스펙: `docs/data/01_crawling_spec.md` 참고

**서브 이슈**

- [ ] 상품 목록·상세 크롤링 구현
  - `getScateGoodsList` (소분류 106개 순회), `getGoodsDetail` 호출
  - `goodsId` 기준 중복 제거 (소분류 간 동일 상품 중복 포함)
  - `indexGoodsDetail` 페이지에서 `detail_image_urls` 수집 (`img[src*='editor/goods_desc/']`, 식품류만 존재)
  - 예상 소요시간: 순차 ~9시간 / 병렬-5 ~2시간
- [ ] 리뷰 크롤링 구현
  - `getGoodsEntireCommentList` 전 페이지 수집 (`goodsCstrtTpCd=ITEM` 필수 파라미터)
  - `purchase_label` (first/repeat): **항상 존재** (100% 확인) — 추천 신호로 활용
  - 펫 프로필 CSS 셀렉터 **확정**: `div.spec > em.b` (이름), `i.g` (성별), `em:nth-of-type(2/3/4)` (나이/체중/품종)
  - `review_info`: **확정** — `ul.satis` 키-값 dict. 완구(사용성·내구성·디자인), 식품(항목 없음), 없으면 `{}`
- [ ] 크롤링 공통 설정
  - 요청 간 딜레이 정책
  - 에러 핸들링 및 재시도 로직

---

### 이슈 2 — ETL 파이프라인 구현 (Bronze → Silver → Gold)

**한 줄 설명**: 수집 데이터를 S3 Medallion 구조로 정제·증강

**배경**

- S3 Medallion 구조를 프로토타입 단계에서 확정하여 추후 Airflow 연동 시 적재 로직 재작성 불필요
- Gold 레이어의 추천 신호는 외부 데이터 없이 크롤링 데이터에서 파생 (리뷰 timestamp, review_count 등)
- LLM 요약은 비용 및 시간 이슈로 Phase 2 이후 적용
- Bronze/Silver/Gold 컬럼 정의 확정: `docs/data/03_medallion_schema.md` 참고

**서브 이슈**

- [ ] Bronze: 원시 크롤링 데이터 S3 Parquet 저장
  - 파티션 구조 설계 (예: `s3://bucket/bronze/goods/`, `s3://bucket/bronze/reviews/`)
  - 스키마 정의 (크롤링 원본 필드 그대로 보존)
- [ ] Silver: 정제·정규화
  - 평점 스케일 통일 (목록 API 10점 → 5점 기준)
  - `goodsId` 기준 중복 상품 제거
  - HTML 태그 제거, 특수문자 정규화, 인코딩 처리
  - 리뷰 중복 필터링
- [ ] Gold: 메타데이터 증강
  - 건강 관심사 매핑 (피부·관절·소화·체중·요로·눈물·헤어볼·치아·면역)
    - 카테고리 소분류명 기반 키워드 매핑으로 구현 (예: `관절` 소분류 → 관절 태그)
  - 성분·알레르기 정보 증강
    - 1차: 상품명에서 주 원료 키워드 추출 (`치킨`, `연어`, `오리`, `소고기` 등)
    - 2차: 상품 상세 이미지(영양 성분표, 원재료 이미지)에 OCR 적용하여 추출 가능한 성분 정보 적재
    - OCR 결과는 품질이 불완전할 수 있음 → Phase 2에서 어드민 수동 수정으로 보완
  - 리뷰 텍스트 감성 점수 (긍정/부정 비율, 한국어 감성 분석 모델 적용)
  - 추천 신호 파생:
    - 인기도 점수: `log(review_count + 1) × rating`
    - 트렌드 가속도: 최근 N일 리뷰 수 / 전체 리뷰 수 (`sysRegDtm` 기준)

---

### 이슈 3 — DB 적재 (PostgreSQL / Qdrant)

**한 줄 설명**: Gold 데이터를 서빙 DB 및 벡터 인덱싱에 적재

**배경**

- PostgreSQL: 관계형 데이터 서빙 (상품, 리뷰, 카테고리 등)
- Qdrant: RAG 파이프라인용 Hybrid Search (Dense + Sparse + RRF)
- ERD 상세: `docs/planning/04_data_model_detail.md` 참고

**서브 이슈**

- [ ] Gold → PostgreSQL 적재
  - 상품, 리뷰, 카테고리 태그, Gold 증강 필드 적재
  - 기존 ERD 스키마(`PRODUCT`, `REVIEW`, `PRODUCT_CATEGORY_TAG`) 와 매핑 확인
- [ ] 임베딩 모델 선정 및 Qdrant 컬렉션 설계
  - 한국어 지원 Dense / Sparse 벡터 모델 선정
  - 컬렉션 구조 및 payload 스키마 정의
  - Hybrid Search (RRF) 파라미터 설정
- [ ] Gold → Qdrant 인덱싱 스크립트 구현
  - 임베딩 대상 텍스트: `상품명 + 카테고리 소분류 + 리뷰 텍스트` 조합
    - 상품 설명이 이미지로 제공될 수 있어 상품 설명 텍스트에 의존하지 않음
    - 리뷰 없는 상품(신상품 등)은 `상품명 + 카테고리`만으로 처리
  - 배치 upsert

---

### 이슈 4 — 배치 스크립트 작성 (Airflow stub)

**한 줄 설명**: Phase 2 Airflow DAG 전환을 위한 수동 실행 스크립트

**배경**

- 프로토타입 단계에서는 자동화(Airflow) 없이 수동 실행
- 스크립트 인터페이스(입력·출력·실행 단위)를 Airflow DAG Task 단위와 일치시켜 추후 전환 비용 최소화

**서브 이슈**

- [ ] 점수 재계산 스크립트 (수동 실행)
  - 인기도 점수·트렌드 가속도 재계산 → PostgreSQL / Qdrant 반영
  - DB 내부 연산이므로 API 호출 없음, 빠른 실행 가능
- [ ] monthly 가중치 갱신 스크립트 (수동 실행)
  - 계절성 가중치 갱신 (날짜 규칙 기반)
  - 추천 가중치 재계산 → PostgreSQL 반영

> 신규 리뷰 수집은 프로토타입 범위 외 (상품 수 대비 API 호출 비용 큼). 필요 시 이슈 1 크롤링 스크립트 재실행으로 대체.
> Phase 2 전환 시 각 스크립트를 Airflow DAG의 PythonOperator Task로 래핑하면 됨.

---

## Phase 구분

| 항목 | 프로토타입 (현재) | Phase 2 |
|---|---|---|
| 크롤링 | Playwright 수동 실행 | Playwright + 스케줄링 |
| ETL | 스크립트 수동 실행 | Airflow DAG 자동화 |
| 성분·알레르기 정보 | 상품명 추출 (1차) + OCR (2차) | 어드민 수동 수정 인터페이스 |
| 신규 리뷰 수집 | 미구현 (전체 재크롤링으로 대체) | Airflow weekly DAG |
| 트렌드 수집 | 미구현 | 네이버 DataLab API 연동 |
| LLM 요약 | 미구현 | Gold 레이어 증강 추가 |
| 모니터링 | 미구현 | Airflow DAG 실행 현황 알림 |
