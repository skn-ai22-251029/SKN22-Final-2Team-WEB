#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# DB 덤프 생성 스크립트
#
# 사용법:
#   bash scripts/dump_db.sh                          # backup/tailtalk_db_20260324_153000.dump
#   bash scripts/dump_db.sh backup/my_backup.dump    # 파일명 직접 지정
#
# django_migrations 테이블은 구조만 포함, 데이터 제외.
# 복원 후 migrate --fake 로 현재 코드 기준 재등록 필요.
# ──────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INFRA_DIR="$PROJECT_ROOT/infra"
COMPOSE_FILE="$INFRA_DIR/docker-compose.yml"

# .env 로드
if [ -f "$INFRA_DIR/.env" ]; then
    set -a
    source "$INFRA_DIR/.env"
    set +a
else
    echo "ERROR: infra/.env 파일이 없습니다."
    exit 1
fi

DB_NAME="${POSTGRES_DB:-tailtalk_db}"
DB_USER="${POSTGRES_USER:-mungnyang}"

# 출력 파일 결정
DUMP_DIR="$PROJECT_ROOT/backup"
mkdir -p "$DUMP_DIR"

if [ "${1:-}" != "" ]; then
    DUMP_FILE="$1"
else
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    DUMP_FILE="$DUMP_DIR/tailtalk_db_${TIMESTAMP}.dump"
fi

# postgres 컨테이너 확인
if ! docker compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; then
    echo "ERROR: postgres 컨테이너가 실행 중이 아닙니다."
    echo "  docker compose -f infra/docker-compose.yml up -d postgres"
    exit 1
fi

echo "=== DB 덤프 생성 ==="
echo "  DB: $DB_NAME"
echo "  출력: $DUMP_FILE"
echo ""

# 덤프 생성 (django_migrations 데이터 제외)
docker compose -f "$COMPOSE_FILE" exec -T postgres \
    pg_dump -U "$DB_USER" -d "$DB_NAME" \
    -Fc \
    --exclude-table-data=django_migrations \
    > "$DUMP_FILE"

echo "  size: $(du -h "$DUMP_FILE" | cut -f1)"

# 테이블 행 수 요약
echo ""
echo "=== 포함된 테이블 ==="
docker compose -f "$COMPOSE_FILE" exec -T postgres \
    psql -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT t.tablename AS table_name,
               COALESCE(s.n_live_tup, 0) AS row_count
        FROM pg_tables t
        LEFT JOIN pg_stat_user_tables s ON s.relname = t.tablename
        WHERE t.schemaname = 'public'
          AND COALESCE(s.n_live_tup, 0) > 0
        ORDER BY s.n_live_tup DESC;
    "

echo ""
echo "  * django_migrations: 구조만 포함 (데이터 제외)"
echo ""
echo "complete!"
