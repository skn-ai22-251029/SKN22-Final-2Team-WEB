#!/usr/bin/env bash
# backup/*.dump → PostgreSQL 복원
#
# 사용법:
#   ./scripts/restore_postgres.sh                      # 최신 덤프 자동 선택
#   ./scripts/restore_postgres.sh backup/data_20260319.dump  # 파일 직접 지정
#
# 전제조건:
#   - docker compose up -d 실행 중 (migrate 자동 적용됨)
#   - backup/data_*.dump 존재

set -euo pipefail

CONTAINER="${POSTGRES_CONTAINER:-tailtalk-postgres-1}"
PG_USER="${POSTGRES_USER:-mungnyang}"
PG_DB="${POSTGRES_DB:-tailtalk_db}"
BACKUP_DIR="$(cd "$(dirname "$0")/../backup" && pwd)"
DRY_RUN=false

# 인자 파싱
POSITIONAL=()
for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=true ;;
    *) POSITIONAL+=("$arg") ;;
  esac
done

# 덤프 파일 결정
if [[ ${#POSITIONAL[@]} -ge 1 ]]; then
  DUMP_FILE="${POSITIONAL[0]}"
else
  DUMP_FILE=$(ls -t "${BACKUP_DIR}"/data_*.dump 2>/dev/null | head -1)
fi

if [[ -z "$DUMP_FILE" ]]; then
  echo "오류: 덤프 파일 없음 (${BACKUP_DIR}/data_*.dump)"
  exit 1
fi

echo "[RESTORE] PostgreSQL ← $(basename "$DUMP_FILE")${DRY_RUN:+ (dry-run)}"

# 컨테이너에 복사
docker cp "$DUMP_FILE" "${CONTAINER}:/tmp/data_backup.dump"

if [[ "$DRY_RUN" == true ]]; then
  echo ""
  echo "── 덤프 내용 목록 ──"
  docker exec "${CONTAINER}" pg_restore --list /tmp/data_backup.dump
else
  docker exec "${CONTAINER}" pg_restore \
    -U "$PG_USER" -d "$PG_DB" \
    --data-only --disable-triggers \
    /tmp/data_backup.dump

  echo ""
  docker exec "${CONTAINER}" psql -U "$PG_USER" -d "$PG_DB" \
    -c "SELECT 'product' AS table, COUNT(*) FROM product UNION ALL SELECT 'review', COUNT(*) FROM review;"
fi

# 컨테이너 내 임시 파일 삭제
docker exec "${CONTAINER}" rm /tmp/data_backup.dump

echo ""
echo "완료"
