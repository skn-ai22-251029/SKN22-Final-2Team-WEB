#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote_plus


DEFAULT_TABLES = ("product", "product_category_tag", "review", "user_interaction")


@dataclass(frozen=True)
class MetricSpec:
    key: str
    label: str
    expression: str
    required_columns: tuple[str, ...]


@dataclass(frozen=True)
class TableSpec:
    name: str
    label: str
    metrics: tuple[MetricSpec, ...]


TABLE_SPECS: dict[str, TableSpec] = {
    "product": TableSpec(
        name="product",
        label="추천 핵심 상품 메타데이터",
        metrics=(
            MetricSpec("goods_name_present", "goods_name", "goods_name IS NOT NULL AND btrim(goods_name) <> ''", ("goods_name",)),
            MetricSpec("brand_name_present", "brand_name", "brand_name IS NOT NULL AND btrim(brand_name) <> ''", ("brand_name",)),
            MetricSpec("pet_type_present", "pet_type", "pet_type IS NOT NULL AND cardinality(pet_type) > 0", ("pet_type",)),
            MetricSpec("category_present", "category", "category IS NOT NULL AND cardinality(category) > 0", ("category",)),
            MetricSpec("subcategory_present", "subcategory", "subcategory IS NOT NULL AND cardinality(subcategory) > 0", ("subcategory",)),
            MetricSpec(
                "health_concern_tags_present",
                "health_concern_tags",
                "health_concern_tags IS NOT NULL AND cardinality(health_concern_tags) > 0",
                ("health_concern_tags",),
            ),
            MetricSpec(
                "main_ingredients_present",
                "main_ingredients",
                "main_ingredients IS NOT NULL AND main_ingredients::text NOT IN ('[]', '{}', 'null')",
                ("main_ingredients",),
            ),
            MetricSpec(
                "ingredient_text_ocr_present",
                "ingredient_text_ocr",
                "ingredient_text_ocr IS NOT NULL AND btrim(ingredient_text_ocr) <> ''",
                ("ingredient_text_ocr",),
            ),
            MetricSpec("popularity_score_present", "popularity_score", "popularity_score IS NOT NULL", ("popularity_score",)),
            MetricSpec("sentiment_avg_present", "sentiment_avg", "sentiment_avg IS NOT NULL", ("sentiment_avg",)),
            MetricSpec("repeat_rate_present", "repeat_rate", "repeat_rate IS NOT NULL", ("repeat_rate",)),
            MetricSpec("embedding_present", "embedding", "embedding IS NOT NULL", ("embedding",)),
            MetricSpec("search_vector_present", "search_vector", "search_vector IS NOT NULL", ("search_vector",)),
        ),
    ),
    "product_category_tag": TableSpec(
        name="product_category_tag",
        label="건강 태그 매핑",
        metrics=(
            MetricSpec("product_id_present", "product_id", "product_id IS NOT NULL", ("product_id",)),
            MetricSpec("tag_present", "tag", "tag IS NOT NULL AND btrim(tag) <> ''", ("tag",)),
        ),
    ),
    "review": TableSpec(
        name="review",
        label="리뷰 / 랭킹 피처 원천",
        metrics=(
            MetricSpec("content_present", "content", "content IS NOT NULL AND btrim(content) <> ''", ("content",)),
            MetricSpec("written_at_present", "written_at", "written_at IS NOT NULL", ("written_at",)),
            MetricSpec("sentiment_score_present", "sentiment_score", "sentiment_score IS NOT NULL", ("sentiment_score",)),
            MetricSpec("absa_result_present", "absa_result", "absa_result IS NOT NULL AND absa_result::text NOT IN ('[]', '{}', 'null')", ("absa_result",)),
            MetricSpec("pet_age_months_present", "pet_age_months", "pet_age_months IS NOT NULL", ("pet_age_months",)),
            MetricSpec("pet_weight_kg_present", "pet_weight_kg", "pet_weight_kg IS NOT NULL", ("pet_weight_kg",)),
            MetricSpec("pet_gender_present", "pet_gender", "pet_gender IS NOT NULL AND btrim(pet_gender) <> ''", ("pet_gender",)),
            MetricSpec("pet_breed_present", "pet_breed", "pet_breed IS NOT NULL AND btrim(pet_breed) <> ''", ("pet_breed",)),
        ),
    ),
    "user_interaction": TableSpec(
        name="user_interaction",
        label="추천 상호작용 로그",
        metrics=(
            MetricSpec("click_count", "click", "interaction_type = 'click'", ("interaction_type",)),
            MetricSpec("cart_count", "cart", "interaction_type = 'cart'", ("interaction_type",)),
            MetricSpec("purchase_count", "purchase", "interaction_type = 'purchase'", ("interaction_type",)),
            MetricSpec("reject_count", "reject", "interaction_type = 'reject'", ("interaction_type",)),
        ),
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare row counts and fill rates between prod and local PostgreSQL databases."
    )
    parser.add_argument("--prod-dsn", default=os.getenv("PROD_DATABASE_URL"), help="Prod DB DSN or PROD_DATABASE_URL")
    parser.add_argument("--local-dsn", default=os.getenv("LOCAL_DATABASE_URL"), help="Local DB DSN or LOCAL_DATABASE_URL")
    parser.add_argument("--prod-label", default="prod", help="Label for the first database")
    parser.add_argument("--local-label", default="local", help="Label for the second database")
    parser.add_argument(
        "--tables",
        default=",".join(DEFAULT_TABLES),
        help=f"Comma-separated subset of tables to compare. Defaults to {', '.join(DEFAULT_TABLES)}",
    )
    parser.add_argument(
        "--local-env-file",
        default="deploy/local/.env",
        help="Fallback env file for building the local DSN when --local-dsn is omitted",
    )
    return parser.parse_args()


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values


def build_dsn_from_parts(prefix: str) -> str | None:
    host = os.getenv(f"{prefix}_HOST")
    port = os.getenv(f"{prefix}_PORT")
    dbname = os.getenv(f"{prefix}_DB")
    user = os.getenv(f"{prefix}_USER")
    password = os.getenv(f"{prefix}_PASSWORD")
    if not all((host, port, dbname, user, password)):
        return None
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{dbname}"


def build_local_dsn_from_env_file(env_file: Path) -> str | None:
    values = parse_env_file(env_file)
    password = values.get("POSTGRES_PASSWORD")
    user = values.get("POSTGRES_USER", "mungnyang")
    dbname = values.get("POSTGRES_DB", "tailtalk_db")
    host = values.get("LOCAL_POSTGRES_HOST", "127.0.0.1")
    port = values.get("LOCAL_POSTGRES_PORT", "5432")
    if not password:
        return None
    return f"postgresql://{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{dbname}"


def resolve_dsn(cli_value: str | None, env_prefix: str, fallback_file: Path | None = None) -> str:
    if cli_value:
        return cli_value
    dsn_from_parts = build_dsn_from_parts(env_prefix)
    if dsn_from_parts:
        return dsn_from_parts
    if fallback_file is not None:
        dsn_from_file = build_local_dsn_from_env_file(fallback_file)
        if dsn_from_file:
            return dsn_from_file
    raise SystemExit(
        f"{env_prefix} 접속 정보가 없습니다. DSN 인자를 넘기거나 {env_prefix}_HOST/{env_prefix}_PORT/{env_prefix}_DB/{env_prefix}_USER/{env_prefix}_PASSWORD 환경변수를 설정하세요."
    )


def parse_table_names(raw_value: str) -> list[str]:
    requested = [name.strip() for name in raw_value.split(",") if name.strip()]
    unknown = [name for name in requested if name not in TABLE_SPECS]
    if unknown:
        raise SystemExit(f"알 수 없는 테이블 비교 대상: {', '.join(unknown)}")
    return requested


def connect(dsn: str):
    try:
        import psycopg2
    except ModuleNotFoundError as exc:
        raise SystemExit("psycopg2 가 설치되어 있지 않습니다. 프로젝트 Python 환경에서 실행하세요.") from exc
    return psycopg2.connect(dsn)


def table_exists(conn, table_name: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass(%s)", (f"public.{table_name}",))
        return cur.fetchone()[0] is not None


def fetch_columns(conn, table_name: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table_name,),
        )
        return {row[0] for row in cur.fetchall()}


def fetch_table_snapshot(conn, spec: TableSpec) -> dict[str, object]:
    snapshot: dict[str, object] = {
        "table_exists": table_exists(conn, spec.name),
        "row_count": None,
        "metrics": {},
        "skipped_metrics": [],
    }
    if not snapshot["table_exists"]:
        return snapshot

    columns = fetch_columns(conn, spec.name)
    enabled_metrics = [metric for metric in spec.metrics if set(metric.required_columns).issubset(columns)]
    skipped_metrics = [
        f"{metric.label} (missing: {', '.join(sorted(set(metric.required_columns) - columns))})"
        for metric in spec.metrics
        if metric not in enabled_metrics
    ]
    snapshot["skipped_metrics"] = skipped_metrics

    select_parts = ["COUNT(*) AS row_count"]
    for metric in enabled_metrics:
        select_parts.append(
            f"SUM(CASE WHEN {metric.expression} THEN 1 ELSE 0 END) AS {metric.key}"
        )

    query = f"SELECT {', '.join(select_parts)} FROM {spec.name}"
    with conn.cursor() as cur:
        cur.execute(query)
        row = cur.fetchone()

    snapshot["row_count"] = row[0]
    metrics = {}
    for index, metric in enumerate(enabled_metrics, start=1):
        metrics[metric.key] = row[index]
    snapshot["metrics"] = metrics
    return snapshot


def format_int(value: object) -> str:
    if value is None:
        return "-"
    return f"{int(value):,}"


def format_count_and_rate(value: object, total: object) -> str:
    if value is None or total in (None, 0):
        return "-"
    ratio = (int(value) / int(total)) * 100
    return f"{int(value):,} ({ratio:5.1f}%)"


def format_delta(left: object, right: object) -> str:
    if left is None or right is None:
        return "-"
    diff = int(left) - int(right)
    if diff == 0:
        return "0"
    return f"{diff:+,}"


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    lines = []
    header_line = "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    separator = "  ".join("-" * widths[index] for index in range(len(headers)))
    lines.append(header_line)
    lines.append(separator)
    for row in rows:
        lines.append("  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)))
    return "\n".join(lines)


def compare_status(left: object, right: object) -> str:
    if left is None or right is None:
        return "MISSING"
    return "OK" if int(left) == int(right) else "DIFF"


def print_connection_summary(prod_label: str, prod_dsn: str, local_label: str, local_dsn: str) -> None:
    print("=== Connection Targets ===")
    print(f"- {prod_label}:  {prod_dsn}")
    print(f"- {local_label}: {local_dsn}")
    print()


def print_table_report(
    spec: TableSpec,
    prod_label: str,
    prod_snapshot: dict[str, object],
    local_label: str,
    local_snapshot: dict[str, object],
) -> int:
    print(f"=== {spec.name} ({spec.label}) ===")

    row_rows = [
        [
            "row_count",
            format_int(prod_snapshot["row_count"]),
            format_int(local_snapshot["row_count"]),
            format_delta(prod_snapshot["row_count"], local_snapshot["row_count"]),
            compare_status(prod_snapshot["row_count"], local_snapshot["row_count"]),
        ]
    ]
    print(render_table(["metric", prod_label, local_label, "delta", "status"], row_rows))
    print()

    metric_rows: list[list[str]] = []
    mismatch_count = 0
    for metric in spec.metrics:
        prod_value = prod_snapshot["metrics"].get(metric.key)
        local_value = local_snapshot["metrics"].get(metric.key)
        status = compare_status(prod_value, local_value)
        if status != "OK":
            mismatch_count += 1
        metric_rows.append(
            [
                metric.label,
                format_count_and_rate(prod_value, prod_snapshot["row_count"]),
                format_count_and_rate(local_value, local_snapshot["row_count"]),
                format_delta(prod_value, local_value),
                status,
            ]
        )

    if metric_rows:
        print(render_table(["fill_metric", prod_label, local_label, "delta", "status"], metric_rows))
        print()

    prod_skipped = prod_snapshot["skipped_metrics"]
    local_skipped = local_snapshot["skipped_metrics"]
    if prod_skipped:
        print(f"- skipped on {prod_label}: {', '.join(prod_skipped)}")
    if local_skipped:
        print(f"- skipped on {local_label}: {', '.join(local_skipped)}")
    if prod_skipped or local_skipped:
        print()

    row_status = compare_status(prod_snapshot["row_count"], local_snapshot["row_count"])
    if row_status != "OK":
        mismatch_count += 1
    return mismatch_count


def main() -> int:
    args = parse_args()
    tables = parse_table_names(args.tables)

    prod_dsn = resolve_dsn(args.prod_dsn, "PROD_POSTGRES")
    local_dsn = resolve_dsn(args.local_dsn, "LOCAL_POSTGRES", Path(args.local_env_file))

    print_connection_summary(args.prod_label, prod_dsn, args.local_label, local_dsn)

    mismatch_count = 0
    try:
        with connect(prod_dsn) as prod_conn, connect(local_dsn) as local_conn:
            for table_name in tables:
                spec = TABLE_SPECS[table_name]
                prod_snapshot = fetch_table_snapshot(prod_conn, spec)
                local_snapshot = fetch_table_snapshot(local_conn, spec)
                mismatch_count += print_table_report(
                    spec,
                    args.prod_label,
                    prod_snapshot,
                    args.local_label,
                    local_snapshot,
                )
    except Exception as exc:
        print(f"DB 비교 중 오류가 발생했습니다: {exc}", file=sys.stderr)
        return 2

    compared_metrics = sum(len(TABLE_SPECS[name].metrics) + 1 for name in tables)
    print("=== Summary ===")
    print(f"- compared tables: {len(tables)}")
    print(f"- compared checks: {compared_metrics}")
    print(f"- mismatches: {mismatch_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
