"""
domain-data/ Excel → output/domain/ Parquet 변환

출력:
    output/domain/qna.parquet        -- QnA 6개 파일 통합 (2,412행)
    output/domain/breed_meta.parquet -- 강아지(900행) + 고양이(225행) 통합 (1,125행)

명세: docs/domain/01_domain_preprocessing.md
"""

from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
DOMAIN_DIR = BASE_DIR / "domain-data"
OUTPUT_DIR = BASE_DIR / "output" / "domain"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
# size_class 정규화 매핑
# ──────────────────────────────────────────────

SIZE_MAP = {
    "초소형":   ["XS"],
    "소형":     ["S"],
    "소형/중형": ["S", "M"],
    "중형":     ["M"],
    "S/M/L":   ["S", "M", "L"],
    "중형/대형": ["M", "L"],
    "대형":     ["L"],
    "대형/XL":  ["L", "XL"],
    "초대형":   ["XL"],
    "초대형/XL": ["XL"],
}


def normalize_size_class(val) -> list[str]:
    if pd.isna(val):
        return []
    return SIZE_MAP.get(str(val).strip(), [str(val).strip()])


# ──────────────────────────────────────────────
# QnA
# ──────────────────────────────────────────────

QNA_FILES = [
    ("bemypet_cat_Q&A(완료).xlsx",      "bemypet", "cat"),
    ("bemypet_dog_Q&A(완료).xlsx",      "bemypet", "dog"),
    ("bemypet_product_Q&A(완료).xlsx",  "bemypet", "both"),
    ("biteme_blog_Q&A(완료).xlsx",      "biteme",  "both"),
    ("강아지 질의응답 1000선_완료.xlsx", "manual",  "dog"),
    ("고양이 질의응답 1000선_완료.xlsx", "manual",  "cat"),
]


def build_qna() -> pd.DataFrame:
    frames = []
    for filename, source, species in QNA_FILES:
        df = pd.read_excel(DOMAIN_DIR / filename)
        df["No."] = pd.to_numeric(df["No."], errors="coerce")
        df = df.dropna(subset=["No."]).copy()
        df["No."] = df["No."].astype(int)
        df["source"] = source
        df["species"] = species
        df = df.rename(columns={
            "No.": "no",
            "질문 카테고리": "category",
            "질문": "question",
            "답변": "answer",
            "참고사항": "notes",
        })
        frames.append(df[["no", "species", "source", "category", "question", "answer", "notes"]])
        print(f"  [{filename}] {len(df)}건")

    result = pd.concat(frames, ignore_index=True)
    result["no"] = range(1, len(result) + 1)
    return result


# ──────────────────────────────────────────────
# 품종 메타
# ──────────────────────────────────────────────

DOG_FILE = "강아지 300종 데이터 정보(연령_비만 메타).xlsx"
CAT_FILE = "고양이 75종 데이타 정보(연령_비만 메타).xlsx"
CAT_SHEET = "고양이 연령 & 비만메타"

# 강아지/고양이 공통 출력 컬럼
BREED_COLS = [
    "no", "species", "breed_name", "breed_name_en",
    "group", "size_class", "age_group",
    "general_traits", "health_traits", "care_difficulty",
    "preferred_food", "health_products", "vet_nutrition_desc", "source_ref",
]


def build_breed_meta() -> pd.DataFrame:
    # ── 강아지 ──
    dog = pd.read_excel(DOMAIN_DIR / DOG_FILE)
    dog = dog.rename(columns={
        "No.":                                                   "no",
        "품종명":                                                 "breed_name",
        "그룹":                                                   "group",
        "영문명(English)":                                        "breed_name_en",
        "이미지(체급)":                                           "size_class",
        "연령대":                                                 "age_group",
        "일반 특징":                                              "general_traits",
        "건강 특징":                                              "health_traits",
        "난이도":                                                 "care_difficulty",
        "좋아하는 사료":                                           "preferred_food",
        "건강제품":                                               "health_products",
        "수의 영양학적 메타 디스크립션 (BCS 상세 가이드 포함)":      "vet_nutrition_desc",
        "출처(Reference)":                                        "source_ref",
    })
    dog["species"] = "dog"
    print(f"  [{DOG_FILE}] {len(dog)}행")

    # ── 고양이 ──
    cat = pd.read_excel(DOMAIN_DIR / CAT_FILE, sheet_name=CAT_SHEET)
    cat = cat.rename(columns={
        "No.":                                                   "no",
        "품종명(국문)":                                           "breed_name",
        "그룹":                                                   "group",
        "영문명(English)":                                        "breed_name_en",
        "체급":                                                   "size_class",
        "연령대":                                                 "age_group",
        "일반 특징":                                              "general_traits",
        "건강 특징":                                              "health_traits",
        "난이도":                                                 "care_difficulty",
        "좋아하는 사료":                                           "preferred_food",
        "건강제품":                                               "health_products",
        "수의 영양학적 메타 디스크립션 (BCS 상세 가이드 포함)":      "vet_nutrition_desc",
        "출처(Reference)":                                        "source_ref",
    })
    cat["species"] = "cat"
    print(f"  [{CAT_FILE} / {CAT_SHEET}] {len(cat)}행")

    result = pd.concat([dog, cat], ignore_index=True)

    # no float → int
    result["no"] = pd.to_numeric(result["no"], errors="coerce")
    result = result.dropna(subset=["no"]).copy()
    result["no"] = result["no"].astype(int)

    # size_class 정규화 (str → list)
    result["size_class"] = result["size_class"].apply(normalize_size_class)

    return result[BREED_COLS]


# ──────────────────────────────────────────────
# main
# ──────────────────────────────────────────────

def main():
    print("=== QnA 변환 ===")
    qna = build_qna()
    out_qna = OUTPUT_DIR / "qna.parquet"
    qna.to_parquet(out_qna, index=False)
    print(f"  → {out_qna}  ({len(qna)}건)")

    print("\n=== 품종 메타 변환 ===")
    breed = build_breed_meta()
    out_breed = OUTPUT_DIR / "breed_meta.parquet"
    breed.to_parquet(out_breed, index=False)
    print(f"  → {out_breed}  ({len(breed)}행)")

    print("\n── QnA species 분포 ──")
    print(qna["species"].value_counts().to_string())
    print("\n── QnA category 분포 ──")
    print(qna["category"].value_counts().to_string())
    print("\n── breed group 분포 ──")
    print(breed.drop_duplicates(subset=["no", "species"]).groupby(["species", "group"]).size().to_string())
    print("\n── breed size_class 샘플 ──")
    print(breed[["breed_name", "age_group", "size_class"]].head(6).to_string())


if __name__ == "__main__":
    main()
