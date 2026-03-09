# 어바웃펫(AboutPet) 크롤링 명세서

## 대상 사이트

- **URL**: https://aboutpet.co.kr
- **대상 카테고리**: 강아지 / 고양이 상품 전체 (소분류 98개 전수 조사 완료)
- **수집 대상 규모**: 소분류 98개 / 상품 합산 18,248개 (중복 제거 전)

---

## 사이트 기술 특성

- **렌더링 방식**: AJAX 기반 동적 렌더링 (서버사이드 HTML 반환)
- **크롤링 도구**: **Playwright** (JS 동적 렌더링 대응, 네트워크 요청 인터셉트 활용)
- **Playwright 활용 방식**:
  - `page.request.post()` / `page.request.get()` 로 API 직접 호출 (browser context 재사용으로 세션/쿠키 유지)
  - 또는 `page.route()` 로 응답 인터셉트
  - HTML 파싱은 `page.evaluate()` 또는 `BeautifulSoup` (응답 text 전달)

---

## 카테고리 구조

- 카테고리는 3단계 (대분류 / 중분류 / 소분류)
- URL 파라미터: `cateCdL`(대분류), `cateCdM`(중분류), `dispClsfNo`(소분류)
- 소분류 전체: **98개**, 전체 상품 수 (소분류 중복 합산): **18,248개**

### 강아지 (cateCdL: 12564)

| 중분류 | dispClsfNo | 소분류 | dispClsfNo | 상품 수 |
|---|---|---|---|---|
| 사료 | 100000374 | 퍼피(1세미만) | 100000377 | 77 |
| 사료 | 100000374 | 어덜트(1~7세) | 100000378 | 219 |
| 사료 | 100000374 | 시니어(7세이상) | 100000379 | 94 |
| 사료 | 100000374 | 전연령 | 100000380 | 440 |
| 사료 | 100000374 | 건식사료 | 100000402 | 625 |
| 사료 | 100000374 | 화식 | 100000403 | 171 |
| 사료 | 100000374 | 소프트사료 | 100000404 | 126 |
| 사료 | 100000374 | 습식사료 | 100000405 | 227 |
| 사료 | 100000374 | 동결건조/에어드라이 | 100000406 | 138 |
| 사료 | 100000374 | 처방식 | 100000408 | 38 |
| 사료 | 100000374 | 눈/눈물 | 100000409 | 24 |
| 사료 | 100000374 | 체중조절 | 100000410 | 44 |
| 사료 | 100000374 | 피부/모질 | 100000411 | 44 |
| 사료 | 100000374 | 위장/소화 | 100000412 | 51 |
| 사료 | 100000374 | 관절 | 100000413 | 51 |
| 사료 | 100000374 | 중성화 | 100000498 | 12 |
| 사료 | 100000374 | 스트레스 완화 | 100000499 | 10 |
| 사료 | 100000374 | 구강/치아(덴탈케어) | 100000500 | 9 |
| 사료 | 100000374 | 견종별 | 100000501 | 42 |
| 사료 | 100000374 | 맛보기 샘플 | 100000414 | 49 |
| 간식 | 100000375 | 덴탈껌 | 100000381 | 354 |
| 간식 | 100000375 | 원물/뼈간식 | 100000382 | 111 |
| 간식 | 100000375 | 캔/파우치 | 100000383 | 131 |
| 간식 | 100000375 | 져키/트릿 | 100000415 | 336 |
| 간식 | 100000375 | 비스킷/쿠키 | 100000416 | 39 |
| 간식 | 100000375 | 사사미 | 100000417 | 168 |
| 간식 | 100000375 | 통살/소시지 | 100000418 | 51 |
| 간식 | 100000375 | 동결/건조간식 | 100000419 | 143 |
| 간식 | 100000375 | 수제간식 | 100000420 | 329 |
| 간식 | 100000375 | 파우더 | 100000421 | 17 |
| 간식 | 100000375 | 음료/분유/우유 | 100000422 | 14 |
| 간식 | 100000375 | 영양/기능 | 100000484 | 106 |
| 용품 | 100000376 | 구강관리 | 100000384 | 123 |
| 용품 | 100000376 | 건강관리 | 100000385 | 368 |
| 용품 | 100000376 | 미용/목욕 | 100000386 | 506 |
| 용품 | 100000376 | 급식/급수기 | 100000387 | 274 |
| 용품 | 100000376 | 장난감/훈련 | 100000388 | 693 |
| 용품 | 100000376 | 의류/악세사리 | 100000497 | 1085 |
| 용품 | 100000376 | 하우스/방석 | 100000390 | 385 |
| 용품 | 100000376 | 이동장/캐리어 | 100000391 | 241 |
| 용품 | 100000376 | 목줄/하네스 | 100000392 | 770 |
| 용품 | 100000376 | 반려인용품 | 100000393 | 76 |
| 배변용품 | 100000394 | 배변패드 | 100000395 | 135 |
| 배변용품 | 100000394 | 배변판 | 100000396 | 36 |
| 배변용품 | 100000394 | 기저귀/팬티 | 100000397 | 51 |
| 배변용품 | 100000394 | 탈취/소독 | 100000398 | 9 |
| 배변용품 | 100000394 | 배변봉투/집게 | 100000399 | 89 |
| 배변용품 | 100000394 | 배변유도제 | 100000400 | 0 |
| 배변용품 | 100000394 | 물티슈/클리너 | 100000401 | 28 |
| 덴탈관 | 100000431 | 수의사인증 | 100000432 | 26 |
| 덴탈관 | 100000431 | 덴탈껌 | 100000433 | 89 |
| 덴탈관 | 100000431 | 칫솔 | 100000434 | 68 |
| 덴탈관 | 100000431 | 치약 | 100000436 | 31 |
| 덴탈관 | 100000431 | 원물/뼈간식 | 100000435 | 31 |

### 고양이 (cateCdL: 12565)

| 중분류 | dispClsfNo | 소분류 | dispClsfNo | 상품 수 |
|---|---|---|---|---|
| 사료 | 100000437 | 키튼(1세미만) | 100000469 | 90 |
| 사료 | 100000437 | 어덜트(1~7세) | 100000470 | 456 |
| 사료 | 100000437 | 시니어(7세이상) | 100000471 | 59 |
| 사료 | 100000437 | 전연령 | 100000472 | 390 |
| 사료 | 100000437 | 주식캔 | 100000473 | 552 |
| 사료 | 100000437 | 건식 | 100000474 | 545 |
| 사료 | 100000437 | 주식파우치 | 100000475 | 337 |
| 사료 | 100000437 | 에어/동결건조 | 100000476 | 34 |
| 사료 | 100000437 | 처방식 | 100000477 | 21 |
| 사료 | 100000437 | 헤어볼 | 100000478 | 26 |
| 사료 | 100000437 | 피부/피모 | 100000479 | 23 |
| 사료 | 100000437 | 위장/소화 | 100000480 | 16 |
| 사료 | 100000437 | 요로기계 | 100000481 | 31 |
| 사료 | 100000437 | 체중조절 | 100000482 | 27 |
| 사료 | 100000437 | 구강/치아(덴탈케어) | 100000502 | 6 |
| 사료 | 100000437 | 면역력 | 100000503 | 22 |
| 사료 | 100000437 | 묘종별 | 100000504 | 15 |
| 사료 | 100000437 | 맛보기 샘플 | 100000483 | 16 |
| 간식 | 100000438 | 간식캔 | 100000459 | 401 |
| 간식 | 100000438 | 간식파우치 | 100000460 | 504 |
| 간식 | 100000438 | 동결/건조간식 | 100000461 | 178 |
| 간식 | 100000438 | 스낵/캔디 | 100000463 | 166 |
| 간식 | 100000438 | 져키/스틱 | 100000464 | 96 |
| 간식 | 100000438 | 통살/소시지 | 100000465 | 98 |
| 간식 | 100000438 | 음료 | 100000466 | 22 |
| 간식 | 100000438 | 파우더/토퍼 | 100000467 | 6 |
| 간식 | 100000438 | 영양/기능 | 100000468 | 179 |
| 용품 | 100000439 | 건강관리 | 100000447 | 115 |
| 용품 | 100000439 | 장난감/캣닢 | 100000450 | 831 |
| 용품 | 100000439 | 스크래쳐/캣타워 | 100000449 | 511 |
| 용품 | 100000439 | 치아관리 | 100000451 | 52 |
| 용품 | 100000439 | 화장실/위생 | 100000452 | 210 |
| 용품 | 100000439 | 미용/목욕 | 100000453 | 378 |
| 용품 | 100000439 | 급식/급수기 | 100000448 | 314 |
| 용품 | 100000439 | 의류/악세사리 | 100000454 | 318 |
| 용품 | 100000439 | 하우스/방석 | 100000455 | 357 |
| 용품 | 100000439 | 이동장/캐리어 | 100000456 | 122 |
| 용품 | 100000439 | 반려인용품 | 100000458 | 39 |
| 모래 | 100000440 | 두부모래 | 100000444 | 79 |
| 모래 | 100000440 | 카사바/천연모래 | 100000445 | 76 |
| 모래 | 100000440 | 벤토나이트 | 100000446 | 286 |
| 모래 | 100000440 | 기타 모래 | 100000488 | 180 |
| 습식관 | 100000441 | 주식캔 | 100000442 | 436 |
| 습식관 | 100000441 | 주식파우치 | 100000443 | 224 |

---

## API 명세

### 1. 상품 목록 조회

**Endpoint:** `POST /shop/getScateGoodsList`

**Request Parameters:**

| 파라미터 | 설명 | 예시 |
|---|---|---|
| `dispClsfNo` | 소분류 코드 | `100000443` |
| `cateCdL` | 대분류 코드 | `12565` |
| `cateCdM` | 중분류 코드 | `100000441` |
| `filters` | 필터 (미사용 시 빈 문자열) | `` |
| `bndNos` | 브랜드 필터 번호 | `` |
| `order` | 정렬 기준 | `APET` (추천순), `SCORE` (평점순), `NEW` (최신순) |
| `page` | 페이지 번호 (**0부터 시작**) | `0` |
| `rows` | 페이지당 상품 수 (기본 20) | `20` |

**Response 형식:** HTML (서버사이드 렌더링)

**총 상품 수 위치:** 응답 스크립트 내 `var goodsCount = '224';`

---

### 2. 상품 상세 정보 조회

**Endpoint:** `GET /goods/getGoodsDetail?goodsId={goodsId}`

**Response 형식:** HTML

**포함 데이터:**
- 상품 설명 이미지 (PC / 모바일)
- 상품 필수 정보 테이블 (원산지, 제조사 등)

---

### 3. 평점 상세 조회

**Endpoint:** `POST /goods/getGoodsCommentScore`

| 파라미터 | 설명 |
|---|---|
| `goodsId` | 상품 ID |

**Response 형식:** HTML

---

### 4. 전체 후기 목록 조회

**Endpoint:** `POST /goods/getGoodsEntireCommentList`

| 파라미터 | 설명 | 예시 |
|---|---|---|
| `goodsId` | 상품 ID | `GP251070972` |
| `goodsCstrtTpCd` | 상품 구성 타입 (필수) | `ITEM` |
| `page` | 페이지 번호 | `1` |
| `sidx` | 정렬 기준 컬럼 | `` (기본) / `SYS_REG_DTM` (최신순) |
| `sord` | 정렬 방향 | `` (기본) / `DESC` |
| `optGoodsId` | 옵션 상품 ID 필터 | `` |
| `detailYn` | 상세 정보 포함 여부 | `Y` |
| `petKindNm`, `petAge`, `petWeight` | 펫 종류/나이/체중 필터 | `` |
| `pageGoodsEstmNo` | 마지막 후기 번호 (페이지 커서) | `` |

> `page=1`부터 시작 (1-based). `goodsCstrtTpCd=ITEM` 누락 시 빈 응답 반환. `page.request.post()` 직접 호출로 수집 가능 (JS 트리거 불필요).

**Response 형식:** HTML

---

### 5. 포토/영상 후기 목록 조회

**Endpoint:** `POST /goods/getGoodsPhotoAndLogComment`

| 파라미터 | 설명 |
|---|---|
| `goodsId` | 상품 ID |
| `rows` | 조회할 수 |

**Response 형식:** JSON

```json
{
  "imgList": [...],
  "so": {
    "totalCount": 0,
    "totalPageCount": 1,
    "goodsId": "GP251070972"
  }
}
```

---

### 6. 베스트 후기 목록 조회

**Endpoint:** `POST /goods/getGoodsBestComment`

| 파라미터 | 설명 |
|---|---|
| `goodsId` | 상품 ID |
| `rows` | 조회할 수 |

**Response 형식:** HTML

---

## 추출 가능 데이터 항목

### 상품 목록 레벨 (getScateGoodsList)

응답 HTML의 `.gd-item` 엘리먼트의 `data-*` 속성에서 추출:

| 필드명 | data 속성 | 타입 | 예시 |
|---|---|---|---|
| 상품 ID | `data-goodsid` | string | `GP251070972` |
| 상품명 | `data-productname` | string | 스텔라앤츄이스 캣 크레이빙스... |
| 브랜드명 | `data-brandname` | string | 스텔라앤츄이스 |
| 브랜드 ID | `data-brandid` | string | `1247` |
| 정가 | `data-price` | int | `3500` |
| 할인가 | `data-discountprice` | int | `3500` |
| 품절 여부 | `data-soldoutyn` | string | `N` / `Y` |
| 리뷰 수 | `data-scorecnt` | int | `347` |
| 평점 (10점 만점) | `data-goodsstarsavgcnt` | float | `9.4` |
| 상품 전시 타입 | `data-disptpnm` | string | `일반` |
| 배송 타입 코드 | `data-dstbtpcd` | string | — |

추가로 HTML 파싱으로 추출:

| 필드명 | CSS 선택자 | 예시 |
|---|---|---|
| 상품 상세 URL | `.gd-link[href]` | `/goods/indexGoodsDetail?goodsId=...` |
| 상품 썸네일 이미지 | `.gd-thumb .thumb-img[src]` | CDN URL |
| 추가 설명 텍스트 | `.gd-body .txt` | `개당 3,317원 (6개 세트 구입시)` |
| 별점 (5점 만점 표시) | `.gd-bottom .rate .star` | `4.7` |

---

### 상품 상세 레벨 (indexGoodsDetail + getGoodsDetail)

**기본 정보** (indexGoodsDetail HTML):

| 필드명 | 위치 | 예시 |
|---|---|---|
| 상품명 | `.pdInfos .names` | 스텔라앤츄이스 캣 크레이빙스... |
| 브랜드명 | `.pdInfos .btn-brand .font-black` | 스텔라앤츄이스 |
| 카테고리 대분류 | JS 변수 `category_name_1depth` | 고양이 |
| 카테고리 중분류 | JS 변수 `category_name_2depth` | 사료 |
| 카테고리 소분류 | JS 변수 `category_name_3depth` | 주식파우치 |
| 판매가 | `.pdInfos .prices .price-txt` | `3,500원` |
| 평점 (5점) | `.pdInfos .starpoint .point` | `4.7` |
| 리뷰 수 | `.pdInfos .starpoint .revew` | `후기 347개` |
| 카테고리 내 순위 | `.pdInfos .store-label` | `고양이 습식관 2위` |
| 최대 적립 포인트 | `.wrap-info .inner em` | `150점` |
| 대표 이미지 URL | `og:image` 메타태그 | CDN URL |

**상품 필수 정보** (getGoodsDetail 응답 테이블):

| 필드명 | 테이블 행 헤더 | 예시 |
|---|---|---|
| 품명 및 모델명 | `품명 및 모델명` | 스텔라앤츄이스 캣 크레이빙스... 80g |
| 원산지 / 제조국 | `제조국 또는 원산지` | 태국 |
| 제조자 / 수입사 | `제조자,수입품의 경우 수입자를 함께 표기` | Stella&Chewys |
| 인증 사항 | `법에 의한 인증,허가 ...` | 상품상세설명 참조 |
| AS 전화번호 | `AS책임자와 전화번호 ...` | 어바웃펫 // 1644-9601 |

---

### 평점 레벨 (getGoodsCommentScore)

| 필드명 | 위치 | 예시 |
|---|---|---|
| 평균 평점 (5점) | `.starpan .ptbox .pnt` | `4.7` |
| 5점 비율 | `.plist li:nth(0) .pct b.p` | `85` (%) |
| 4점 비율 | `.plist li:nth(1) .pct b.p` | `7` (%) |
| 3점 비율 | `.plist li:nth(2) .pct b.p` | `6` (%) |
| 2점 비율 | `.plist li:nth(3) .pct b.p` | `1` (%) |
| 1점 비율 | `.plist li:nth(4) .pct b.p` | `1` (%) |

---

### 후기 레벨 (getGoodsEntireCommentList)

각 후기 항목은 `#entireCommentListUl > li` 구조. 각 `li` 내부에서 추출:

#### 후기 기본 정보

각 후기 항목: `li > div.box[name="estmDataArea"]`

| 필드명 | CSS 선택자 | 설명 |
|---|---|---|
| 후기 번호 | `[data-goods-estm-no]` | 고유 식별자 |
| 상품 ID | `[data-goods-id]` | — |
| 별점 | `.stars.sm` 클래스 `p_X_Y` 파싱 | 1~5점 (예: `p_5_0`=5.0, `p_4_5`=4.5) |
| 후기 내용 | `.msgs` | 텍스트 본문 |
| 작성자 닉네임 | `.writer-info .ids` | — |
| 작성일 | `.writer-info .date` | `YYYY.MM.DD` 형식 |
| 포토 이미지 유무 | `ul.swiper-wrapper.pics .pic` 존재 여부 | 이미지 포함 후기 |

#### 구매 유형 레이블

| 필드명 | CSS 선택자 | 클래스 값 | 비고 |
|---|---|---|---|
| 구매 유형 | `.purchase-label` | `first`=첫구매 / `repeat`=재구매 | **샘플 조사 결과 완구/식품 모두 100% 존재** (항상 노출). 엘리먼트 미존재 시 `null` 처리. |

#### 작성자 반려동물 프로필 (조건부)

리뷰 작성자가 반려동물 프로필을 등록한 경우 표시. **샘플 조사: 완구 80%, 식품 20%**

| 필드명 | CSS 선택자 | 예시 | 비고 |
|---|---|---|---|
| 펫 이름 | `div.spec > em.b` (text, `em.g` 제외) | `초코` | 조건부 |
| 펫 성별 | `div.spec > em.b > i.g` | `수컷` / `암컷` | 조건부 |
| 펫 나이 | `div.spec > em:nth-of-type(2)` | `7개월` / `3살` | 조건부 |
| 펫 체중 | `div.spec > em:nth-of-type(3)` | `2.5kg` | 조건부 |
| 펫 품종 | `div.spec > em:nth-of-type(4)` | `브리티시쇼트헤어` | 조건부 (품종 등록 시에만) |

> 컨테이너: `div.box > div.rhdt > div.tinfo > div.def > div.spec`

#### 후기 상세 정보 (review_info)

컨테이너: `ul.satis` (존재 시). **카테고리 의존 — 식품류는 항목 없음, 완구/용품류에서 확인됨.**

| CSS 선택자 | 필드 | 예시 (완구) |
|---|---|---|
| `ul.satis li .dt` | 항목명 | `사용성` / `내구성` / `디자인` |
| `ul.satis li .dd` | 항목값 | `잘 쓰고 있어요` / `튼튼해요` |

> `review_info`는 `dict` 형태로 저장 (예: `{"사용성": "잘 쓰고 있어요", "내구성": "튼튼해요"}`). 항목 없으면 `{}`. 카테고리별 항목 구성이 상이하므로 유동적으로 수집.

---

## Playwright 크롤링 구현 패턴

```python
import re
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def crawl():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # 세션/쿠키 초기화를 위해 메인 페이지 한 번 방문
        await page.goto("https://www.aboutpet.co.kr/shop/home/", wait_until="networkidle")

        # 상품 목록 수집 (page=0부터 시작)
        list_resp = await page.request.post(
            "https://www.aboutpet.co.kr/shop/getScateGoodsList",
            form={
                "dispClsfNo": "100000443",   # 소분류 dispClsfNo
                "cateCdL": "12565",           # 대분류 (고양이)
                "cateCdM": "100000441",       # 중분류
                "order": "APET",
                "page": "0",                  # 0-based
                "rows": "20",
            }
        )
        list_html = await list_resp.text()
        list_soup = BeautifulSoup(list_html, "html.parser")

        # 총 상품 수: var goodsCount = '224';
        total_match = re.search(r"var goodsCount\s*=\s*'(\d+)'", list_html)
        total_count = int(total_match.group(1)) if total_match else 0

        # 상품 카드: .gd-item[data-goodsid]
        for item in list_soup.select(".gd-item[data-goodsid]"):
            goods_id   = item["data-goodsid"]
            name       = item.get("data-productname", "")
            brand      = item.get("data-brandname", "")
            price      = item.get("data-discountprice", "")
            rating_10  = item.get("data-goodsstarsavgcnt", "")  # 10점 만점
            review_cnt = item.get("data-scorecnt", "")
            sold_out   = item.get("data-soldoutyn", "")
            thumb_url  = item.select_one(".thumb-img")
            thumb      = thumb_url["src"] if thumb_url else ""

        # 후기 수집 (page.request.post 직접 호출 — JS 트리거 불필요)
        review_resp = await page.request.post(
            "https://www.aboutpet.co.kr/goods/getGoodsEntireCommentList",
            form={
                "goodsId": "GP251070972",
                "goodsCstrtTpCd": "ITEM",    # 필수 — 누락 시 빈 응답
                "page": "1",                  # 1-based
                "sidx": "",
                "sord": "",
                "optGoodsId": "",
                "detailYn": "Y",
                "petKindNm": "",
                "petAge": "",
                "petWeight": "",
                "pageGoodsEstmNo": "",
            }
        )
        review_html = await review_resp.text()
        review_soup = BeautifulSoup(review_html, "html.parser")

        # 총 페이지: goodsComment.totalPageCount = 8;
        page_match = re.search(r"totalPageCount\s*=\s*(\d+)", review_html)
        total_pages = int(page_match.group(1)) if page_match else 1

        # 각 후기: div.box[name="estmDataArea"]
        for box in review_soup.select('div[name="estmDataArea"]'):
            estm_no  = box.get("data-goods-estm-no")
            nickname = box.select_one(".writer-info .ids")
            date     = box.select_one(".writer-info .date")
            stars_el = box.select_one(".stars.sm")

            # 별점: class p_X_Y → float (예: p_5_0 → 5.0, p_4_5 → 4.5)
            star_cls = next((c for c in (stars_el.get("class", []) if stars_el else []) if c.startswith("p_")), None)
            rating = float(star_cls[2:].replace("_", ".")) if star_cls else None

            # 구매 유형 (항상 존재)
            pl_el = box.select_one(".purchase-label")
            purchase_label = "first" if pl_el and "first" in pl_el.get("class", []) else "repeat" if pl_el else None

            # 후기 본문
            msg_el = box.select_one(".msgs")
            review_text = msg_el.get_text(strip=True) if msg_el else ""

            # 펫 프로필 (조건부)
            spec = box.select_one("div.spec")
            pet_name = pet_gender = pet_age = pet_weight = pet_breed = None
            if spec:
                name_el = spec.select_one("em.b")
                gender_el = spec.select_one("em.b > i.g")
                ems = spec.select("em")
                pet_gender = gender_el.get_text(strip=True) if gender_el else None
                pet_name   = name_el.get_text(strip=True).replace(f"({pet_gender})", "").strip() if name_el else None
                pet_age    = ems[1].get_text(strip=True) if len(ems) > 1 else None
                pet_weight = ems[2].get_text(strip=True) if len(ems) > 2 else None
                pet_breed  = ems[3].get_text(strip=True) if len(ems) > 3 else None

            # review_info (카테고리 의존 — 식품류는 없음)
            review_info = {}
            for li in box.select("ul.satis li"):
                dt = li.select_one(".dt")
                dd = li.select_one(".dd")
                if dt and dd:
                    review_info[dt.get_text(strip=True)] = dd.get_text(strip=True)

        await browser.close()
```

---

## 크롤링 전략

### 수집 흐름

```
1. 카테고리 목록 정의 (cateCdL + cateCdM + dispClsfNo)
       |
2. getScateGoodsList 반복 호출 (page=1, 2, ... until goodsCount 소진)
       |
3. goodsId 수집 → 중복 제거 (goodsId 기준)
       |
4. 상품별 상세 조회 (병렬 또는 순차):
   ├── getGoodsDetail         (필수 정보 테이블)
   ├── getGoodsCommentScore   (평점 분포)
   └── getGoodsEntireCommentList (후기 목록, 페이지 반복)
           └── 후기별: 기본 정보 + purchase_label + 펫 프로필 + review_info
```

### 주의 사항

- 무한 스크롤 방식이지만 API는 `page` 파라미터 지원 → 순차 페이지 호출로 수집 가능
- 요청 간 딜레이 설정 권장 (서버 부하 방지)
- 평점: 목록 API는 10점 만점(`data-goodsstarsavgcnt`), 상세 페이지는 5점 만점(`.starpoint .point`) — 정규화 필요
- 상품 상세 일부 데이터(영양 성분, 원재료)는 이미지로 제공될 수 있음 → 텍스트 추출 불가, 수집 대상에서 제외
- 소분류 간 상품 중복 존재 → `goodsId` 기준 중복 제거 후 저장
- `purchase_label`은 항상 존재(100%), 펫 프로필은 조건부(20~80%), `review_info`는 카테고리 의존(식품류 없음)
- 리뷰 API: `goodsCstrtTpCd=ITEM` 파라미터 필수 — 누락 시 `totalCount=0` 반환

### 실측 수집 규모

98개 소분류 전수 순회 후 goodsId 기준 dedup 실측 결과 (rows=100 기준):

| 항목 | 수량 | 비고 |
|---|---|---|
| 소분류 카테고리 수 | 98개 | — |
| 전체 상품 수 (소분류 중복 합산) | 18,248개 | 목록 API `goodsCount` 합산 |
| **고유 상품 수 (dedup 후)** | **4,934개** | **goodsId Set 집계 실측값** |
| 중복 비율 | ~73% | 소분류 간 동일 상품 중복 |
| 목록 수집 API 호출 수 | 239회 | rows=100, 소분류당 평균 2.4회 |
| 상품당 후기 수 | 수십 ~ 4,000+개 | 인기 식품 최대 4,000+ |

### 예상 크롤링 소요 시간 (고유 상품 4,934개 기준)

| 작업 | 호출 수 | 0.5s 순차 | 병렬 5개 |
|---|---|---|---|
| 상품 목록 전수집 | 239회 | ~2분 | — |
| 리뷰 수집 (평균 12페이지/상품) | ~59,000회 | ~8시간 | ~1.5시간 |
| 상품 상세 (getGoodsDetail) | 4,934회 | ~40분 | ~10분 |
| **합계** | — | **~9시간** | **~2시간** |

> 리뷰 상한 설정 권장: 상품당 최대 N페이지로 캡을 두면 호출 수 대폭 감소.
