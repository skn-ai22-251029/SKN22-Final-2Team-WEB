# TailTalk 🐾

반려동물(강아지/고양이) 맞춤 상품 추천 대화형 챗봇 서비스.
사용자의 반려동물 프로필과 대화 맥락을 기반으로 [어바웃펫](https://www.aboutpet.co.kr) 상품을 추천한다.

## 서비스 구조

```
[Browser]
    │
[Nginx]  ──── /api/chat/*  ────► [FastAPI + LangGraph]
    │                                   │
    └────── 그 외  ────► [Django]    Qdrant Hybrid Search
                            │           │
                        PostgreSQL    LLM (GPT-4o-mini)
```

## 주요 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | Django Template (MVT), Tailwind CSS, Vanilla JS |
| Backend | Django (Auth/User/Pet/Order), FastAPI (챗봇/추천) |
| AI | LangGraph 멀티에이전트, GPT-4o-mini, Qdrant Hybrid Search |
| DB | PostgreSQL 16, Qdrant (Dense + Sparse BM25 + RRF) |
| Infra | Docker Compose, Nginx, AWS EC2, GitHub Actions CI/CD |

## 로컬 실행

```bash
cd infra
docker compose up -d
```

서비스: `http://localhost`

## 프로젝트 구조

```
services/
  django/     # Auth, User, Pet, Order, Template 렌더링
  fastapi/    # 챗봇 · 추천 마이크로서비스 (LangGraph 파이프라인 포함)
infra/        # Docker Compose, Nginx 설정
notebooks/    # 데이터 파이프라인 실험, LangGraph 테스트
scripts/      # ETL, Qdrant 적재 스크립트
docs/         # 기획/설계 문서
```

## 팀

SKN22 Final Project · 2팀
