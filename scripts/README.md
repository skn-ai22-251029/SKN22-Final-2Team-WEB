# scripts/ 사용 가이드

## DB 관리 스크립트

로컬 개발 환경의 PostgreSQL(pgvector) DB를 관리하는 스크립트입니다.

### 사전 조건

- Docker Desktop 실행 중
- `deploy/local/.env` 설정 완료 (`deploy/local/.env.example` 복사 후 `POSTGRES_PASSWORD` 등 입력)

---

### setup_db.sh — 로컬 DB 셋업 / 복원

덤프 파일로부터 로컬 DB를 셋업합니다.

```bash
# 기본: backup/ 폴더에서 최신 .dump 파일 자동 선택
bash scripts/setup_db.sh

# 특정 덤프 파일 지정
bash scripts/setup_db.sh backup/tailtalk_db_20260324_150000.dump

# 데이터만 리셋 (스키마 유지, 테이블 truncate 후 데이터 복원)
bash scripts/setup_db.sh --data-only backup/tailtalk_db_20260324_150000.dump

# 덤프 내용 목록만 확인
bash scripts/setup_db.sh --list backup/tailtalk_db_20260324_150000.dump
```

**동작 순서 (기본 모드)**:
1. postgres 컨테이너 기동 + health check 대기
2. 기존 DB DROP → CREATE
3. pgvector 확장 설치
4. pg_restore로 풀 복원 (스키마 + 데이터 + 인덱스)
5. 테이블 현황 출력

**복원 후 반드시 실행**:
```bash
cd services/django
python manage.py migrate --fake
```
> 덤프에는 `django_migrations` 데이터가 포함되어 있지 않습니다.
> `migrate --fake`는 현재 코드의 migration 파일을 기준으로 "이미 적용됨"으로 등록합니다.

---

### dump_db.sh — DB 덤프 생성

현재 로컬 DB를 덤프 파일로 저장합니다.

```bash
# 타임스탬프 파일명 자동 생성 (backup/tailtalk_db_20260324_153000.dump)
bash scripts/dump_db.sh

# 파일명 직접 지정
bash scripts/dump_db.sh backup/my_backup.dump
```

**참고**:
- `django_migrations` 테이블은 구조만 포함, 데이터는 제외됩니다
- 덤프 형식: PostgreSQL custom format (`-Fc`, 압축됨)
- 덤프 파일은 `.gitignore`에 포함하여 Git에 올리지 않습니다

---

### AWS Test RDS를 DBeaver로 확인

테스트 RDS는 private 이므로 직접 접속이 아니라 EB 인스턴스 경유 SSH 터널이 필요합니다.

```bash
# 접속 정보만 출력
PRINT_ONLY=1 bash scripts/aws/start_test_rds_dbeaver_tunnel.sh

# 실제 터널 열기
bash scripts/aws/start_test_rds_dbeaver_tunnel.sh
```

상세 사용법은 `docs/infra/08_dbeaver_rds_tunnel.md` 문서를 참고합니다.

---

## 팀원 온보딩 (처음 셋업)

```bash
# 1. 코드 pull
git pull origin develop

# 2. 환경변수 설정
cp deploy/local/.env.example deploy/local/.env
# deploy/local/.env 에서 POSTGRES_PASSWORD 등 입력

# 3. DB 셋업 (backup/ 에 덤프 파일이 공유되어 있어야 함)
bash scripts/setup_db.sh backup/tailtalk_db_20260324_150000.dump

# 4. Django migration 동기화
cd services/django
python manage.py migrate --fake
```

---

## 데이터 파이프라인 스크립트

Gold parquet 데이터를 PostgreSQL에 적재하는 스크립트입니다.
덤프 파일이 이미 있다면 위 `setup_db.sh`로 충분하며, 아래는 직접 적재할 때 사용합니다.

### ingest_postgres.py — 상품 + 리뷰 + 벡터 적재

```bash
# 전체 적재 (상품 → 벡터 → 리뷰)
POSTGRES_HOST=localhost python scripts/ingest_postgres.py

# 상품만 (벡터 포함)
POSTGRES_HOST=localhost python scripts/ingest_postgres.py --only goods

# 리뷰만
POSTGRES_HOST=localhost python scripts/ingest_postgres.py --only reviews

# 벡터/tsvector만 재생성 (상품 메타 스킵)
POSTGRES_HOST=localhost python scripts/ingest_postgres.py --only vectors

# 기존 데이터 삭제 후 재적재
POSTGRES_HOST=localhost python scripts/ingest_postgres.py --truncate
```

### domain/ingest_domain_postgres.py — 도메인 QnA + 품종 메타 적재

```bash
# 전체 (QnA + 품종 메타)
POSTGRES_HOST=localhost python scripts/domain/ingest_domain_postgres.py --table all

# 개별
POSTGRES_HOST=localhost python scripts/domain/ingest_domain_postgres.py --table qna
POSTGRES_HOST=localhost python scripts/domain/ingest_domain_postgres.py --table breed

# 기존 데이터 삭제 후 재적재
POSTGRES_HOST=localhost python scripts/domain/ingest_domain_postgres.py --table all --truncate
```

### domain/convert_domain_data.py — 도메인 Excel → Parquet 변환

```bash
# domain-data/*.xlsx → output/domain/*.parquet
python scripts/domain/convert_domain_data.py
```

---

## 디렉토리 구조

```
scripts/
├── setup_db.sh                     # 로컬 DB 셋업/복원
├── dump_db.sh                      # DB 덤프 생성
├── aws/
│   └── start_test_rds_dbeaver_tunnel.sh  # Test RDS용 SSH 터널
├── ingest_postgres.py              # 상품/리뷰/벡터 적재
├── config.py                       # ETL 공통 설정
├── domain/
│   ├── convert_domain_data.py      # Excel → Parquet 변환
│   └── ingest_domain_postgres.py   # 도메인 QnA/품종 적재
├── bronze/                         # Bronze ETL
├── silver/                         # Silver ETL
├── gold/                           # Gold ETL
└── eda/                            # 탐색적 데이터 분석
```
