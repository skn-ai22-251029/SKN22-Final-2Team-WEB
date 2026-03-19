#!/usr/bin/env bash
# backup/qdrant/ 스냅샷 → Qdrant 컬렉션 복원
#
# 사용법:
#   ./scripts/restore_qdrant.sh              # 전체 컬렉션
#   ./scripts/restore_qdrant.sh products     # 단일 컬렉션
#
# 전제조건:
#   - Qdrant 컨테이너 실행 중 (http://localhost:6333)
#   - backup/qdrant/<collection>/*.snapshot 존재

set -euo pipefail

QDRANT_URL="${QDRANT_URL:-http://localhost:6333}"
BACKUP_DIR="$(cd "$(dirname "$0")/../backup/qdrant" && pwd)"

COLLECTIONS=(products domain_qna breed_meta)

# 인자로 특정 컬렉션 지정 가능
if [[ $# -ge 1 ]]; then
  COLLECTIONS=("$@")
fi

for col in "${COLLECTIONS[@]}"; do
  snapshot=$(ls -t "${BACKUP_DIR}/${col}"/*.snapshot 2>/dev/null | head -1)

  if [[ -z "$snapshot" ]]; then
    echo "[SKIP] ${col}: 스냅샷 없음 (${BACKUP_DIR}/${col}/)"
    continue
  fi

  echo "[RESTORE] ${col} ← $(basename "$snapshot")"
  curl -sf -X POST \
    "${QDRANT_URL}/collections/${col}/snapshots/upload?priority=snapshot" \
    -F "snapshot=@${snapshot}" | python3 -c "
import sys, json
r = json.load(sys.stdin)
print('  status:', r.get('status'))
"

  points=$(curl -sf "${QDRANT_URL}/collections/${col}" \
    | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['points_count'])")
  echo "  points_count: ${points}"
done

echo ""
echo "완료"
