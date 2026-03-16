# Bronze Reviews 데이터 품질 이슈 보고서

> **작성일**: 2026-03-10
> **대상 파일**: `output/bronze/reviews/20260310_reviews.parquet`
> **전체 리뷰**: 131,147건 / 고유 상품: 1,726개 / 고유 작성자: 19,923명
> **수집 대상**: 3,618개 (canonical, GP 제외)

---

## 개요

Bronze reviews EDA 과정에서 발견된 데이터 품질 이슈 4건을 정리한다.

---

## 이슈 1 — GO 상품 리뷰 수집 실패 (235개)

### 현상

`goods_id`별 리뷰 수를 goods 목록 API의 `review_count_raw`와 비교했을 때:

- goods API에 `review_count > 0`이지만 수집된 리뷰가 0건인 상품 **235개**
- 이 중 **GO 상품이 집중적으로** 포함됨

```
GO251026172 | review_count=6  | 쓰리잘비 길이조절형 3color
GO251026178 | review_count=16 | 쓰리잘비 기본형 2color
GO251031424 | review_count=9  | [무료배송] 도그웨그 방수 쿠션 넥카라
GO251048775 | review_count=31 | 바잇미 논슬립 실리콘 배변매트
```

- 리뷰 정상 없는 상품: 1,657개 (goods API도 0개 → 정상)
- **수집 실패 의심 상품: 235개** (goods API에 리뷰 있음)

### 원인 추정

GO는 색상/사이즈 선택형 상품이다. `getGoodsEntireCommentList` API 호출 시
`goodsCstrtTpCd="ITEM"` 파라미터가 GO 상품에는 적용되지 않거나 다른 값이 필요할 가능성이 있다.
또는 GO 리뷰는 `optGoodsId`에 특정 옵션 ID를 지정해야 반환되는 구조일 수 있다.

### ETL 대응

- **Silver**: 235개 상품의 `review_count`는 goods 목록 API 값을 그대로 사용하되 `review_collected = False` 플래그 추가
- **Phase 2**: GO 상품에 대해 `optGoodsId` 지정 방식으로 재수집 시도

---

## 이슈 2 — 5점 리뷰 77% 극단적 편향

### 현상

| 점수 | 건수 | 비율 |
|------|------|------|
| 5.0  | 101,046 | **77.0%** |
| 4.5  | 11,984  | 9.1%  |
| 4.0  | 8,966   | 6.8%  |
| 3.5  | 3,151   | 2.4%  |
| 3.0  | 2,573   | 2.0%  |
| 2.5↓ | 3,427   | 2.6%  |

전체 리뷰의 77%가 5점, 93%가 4점 이상.

### 원인

한국 e-커머스 리뷰 문화 특성 + 리뷰 작성 시 포인트 지급 구조.
만족한 고객만 리뷰를 남기는 **자기선택 편향**이 주요 원인이다.

### ETL/추천 대응

- **`score_raw` 단독 사용 금지**: 점수 분포가 거의 의미가 없어 `rating` 기반 랭킹은 변별력이 낮음
- **감성 분석 의존**: `sentiment_score`를 리뷰 텍스트 기반으로 추출하는 것이 실질적인 품질 지표
- **`popularity_score` 계산 시**: `log(review_count + 1) × rating` 대신 `log(review_count + 1) × sentiment_score` 가중 방식 고려
- **감성 분석 모델 학습 시**: 5점 클래스 오버샘플링 또는 클래스 가중치 조정 필요

---

## 이슈 3 — pet_gender 빈 문자열 파싱 버그 (3,275건)

### 현상

`pet_gender` 컬럼에 `None`이 아닌 `""` (빈 문자열)로 저장된 레코드 **3,275건**.
`pet_name`, `pet_age_raw`는 정상적으로 채워져 있음.

```
goods_id      pet_name  pet_gender  pet_age_raw
GI251017375   라비        ""          15살
GI251017384   만두        ""          7개월
GI251018928   봄이        ""          14살
```

### 원인

`bronze_reviews.py` 파싱 로직:

```python
gender_el = spec.select_one("em.b > i.g")
pet_gender = gender_el.get_text(strip=True) if gender_el else None
pet_name   = name_el.get_text(strip=True).replace(f"({pet_gender})", "").strip()
```

`gender_el`이 없으면 `pet_gender = None`인데, 일부 리뷰에서 `i.g` 태그가 없는 대신
성별 정보 자체가 빈 텍스트로 렌더링되어 `get_text(strip=True)` 결과가 `""` 반환.

### ETL 대응

- **Silver**: `pet_gender == ""` → `NULL` 변환
  ```python
  df["pet_gender"] = df["pet_gender"].replace("", None)
  ```
- `bronze_reviews.py` 파서도 수정 필요:
  ```python
  pet_gender = gender_el.get_text(strip=True) or None
  ```

---

## 이슈 4 — PI 상품 리뷰 수 (이슈 없음, 검증 완료)

### 현상

PI 상품당 평균 리뷰 229.2개 (GI 39.7개 대비 5.8배). GP 이슈 2와 유사한 패턴으로 집계 과다를 의심했다.

### 검증 결과

**PI는 정상이다.** 수집된 리뷰 수와 goods 목록 API의 `review_count_raw`가 거의 일치한다:

| goods_id | 수집 | goods API | 상품명 |
|----------|------|-----------|--------|
| PI000003245 | 19,982 | 20,258 | 캐츠랑 전연령 20kg |
| PI000006085 | 2,726 | 2,751 | 런치 보니또 오리지널 참치 20g |
| PI000006087 | 2,439 | 2,457 | 런치 보니또 가쓰오부시맛 20g |

GP(`optGoodsId=""` 집계)와 달리 PI는 **단품 리뷰가 실제로 많은 구독 인기 상품**이다.
`review_count_source = direct`로 유지한다.

---

## 종합 ETL 대응 우선순위

| 우선순위 | 이슈 | 적용 단계 | 영향 범위 |
|---------|------|---------|---------|
| **P0** | 5점 편향 → 감성 분석 의존 | Gold | popularity_score, 추천 품질 |
| **P1** | pet_gender 빈 문자열 | Silver | 펫 프로필 필터링 정확도 |
| **P2** | GO 리뷰 수집 실패 235개 | Bronze 재수집 | 임베딩 커버리지 |
| **확인** | PI 리뷰 과다 집계 의심 | — | 이슈 없음, 정상 확인 |
