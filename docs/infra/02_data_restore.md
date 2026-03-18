# 데이터 복원 가이드

> DB 데이터 적재, 덤프, 복원 절차

---

## 1. 사전 준비

팀 공유 드라이브에서 아래 파일을 받아 레포 루트 `backup/` 디렉토리에 놓는다:

- `data_<날짜>.dump` — PostgreSQL 덤프 (상품 4,902개 / 리뷰 전체)
- `products-<uuid>.snapshot` — Qdrant products 컬렉션 스냅샷 (3,618개)

> `backup/` 디렉토리는 `.gitignore`에 포함되어 있어 커밋되지 않는다.

---

## 2. PostgreSQL 복원

```bash
# 1. DB 컨테이너 실행
cd infra && docker compose up -d postgres

# 2. 마이그레이션 먼저 적용 (테이블 스키마 생성)
docker compose run --rm django python manage.py migrate

# 3. 덤프 파일을 컨테이너에 복사 후 복원
docker cp backup/data_<날짜>.dump tailtalk-postgres-1:/tmp/data_backup.dump
docker exec tailtalk-postgres-1 pg_restore \
  -U mungnyang -d tailtalk_db --data-only --disable-triggers \
  /tmp/data_backup.dump

# 4. 복원 확인
docker compose run --rm django python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
cursor = connection.cursor()
for table in ['product', 'review']:
    cursor.execute(f'SELECT COUNT(*) FROM \"{table}\"')
    print(f'{table}: {cursor.fetchone()[0]}건')
"
```

---

## 3. Qdrant 복원

```bash
# 1. Qdrant 컨테이너 실행
cd infra && docker compose up -d qdrant

# 2. 같은 네트워크의 python 컨테이너로 스냅샷 업로드
SNAPSHOT=backup/products-<uuid>.snapshot
docker run --rm \
  --network tailtalk_default \
  -v "$(pwd)/$SNAPSHOT:/tmp/snapshot.snapshot:ro" \
  python:3.11-slim python -c "
import urllib.request, json
with open('/tmp/snapshot.snapshot', 'rb') as f:
    data = f.read()
boundary = 'FormBoundary'
body = ('--' + boundary + '\r\nContent-Disposition: form-data; name=\"snapshot\"; filename=\"snapshot.snapshot\"\r\nContent-Type: application/octet-stream\r\n\r\n').encode() + data + ('\r\n--' + boundary + '--\r\n').encode()
req = urllib.request.Request('http://qdrant:6333/collections/products/snapshots/upload?priority=snapshot', data=body, headers={'Content-Type': 'multipart/form-data; boundary=' + boundary}, method='POST')
print(json.loads(urllib.request.urlopen(req).read()))
"

# 3. 복원 확인 (points_count: 3618 이면 정상)
docker run --rm --network tailtalk_default python:3.11-slim python -c "
import urllib.request, json
resp = urllib.request.urlopen('http://qdrant:6333/collections/products')
print('points_count:', json.loads(resp.read())['result']['points_count'])
"
```

---

## 4. 덤프 파일 재생성 (데이터 담당자만)

Gold ETL 결과가 변경됐을 때만 재생성한다.

### PostgreSQL 덤프

```bash
docker exec tailtalk-postgres-1 pg_dump \
  -U mungnyang -d tailtalk_db \
  -t product -t product_category_tag -t review \
  --data-only -F c \
  -f /tmp/data_backup.dump
docker cp tailtalk-postgres-1:/tmp/data_backup.dump backup/data_$(date +%Y%m%d).dump
```

### Qdrant 스냅샷

```bash
# 스냅샷 생성 (컨테이너 내부 API 호출)
docker run --rm --network tailtalk_default python:3.11-slim python -c "
import urllib.request, json
resp = urllib.request.urlopen(urllib.request.Request('http://qdrant:6333/collections/products/snapshots', method='POST'))
result = json.loads(resp.read())
print(result['result']['name'])
"
# 출력된 파일명으로 복사
docker cp tailtalk-qdrant-1:/qdrant/snapshots/products/<출력된_파일명> backup/
```

> 재생성 후 팀 공유 드라이브 파일 교체 및 팀 공지 필요.
