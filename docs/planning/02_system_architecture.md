# 시스템 구성

> **프로젝트**: SKN22 Final Project · 2팀
> **작성일**: 2026-03-06

---

## 0. 전체 시스템 아키텍처 (Mermaid)

```mermaid
flowchart TD
    USER(["👤 사용자 / 게스트"])

    subgraph FRONTEND["🖥️ Frontend"]
        direction LR
        FE["Django Template (MVT)<br>3-패널 레이아웃"]
        OAUTH["OAuth<br>Google · Kakao · Naver"]
    end

    NGINX["⚡ Nginx<br>리버스 프록시 / LB"]

    subgraph BACKEND["⚙️ Backend"]
        direction LR
        DJANGO["Django<br>Auth · User · Pet<br>Order · Admin"]
        FASTAPI["FastAPI<br>챗봇 · 추천 · 상품 API"]
    end

    subgraph AI["🤖 AI / LLM"]
        direction LR
        LANGGRAPH["LangGraph<br>멀티 에이전트"]
        LLM["LLM<br>Claude API / OpenAI GPT"]
    end

    subgraph MULTIMODAL["🎙️ Multimodal"]
        direction LR
        YOLO["YOLO<br>체중 추정"]
        STT["STT / TTS<br>음성 입출력 (TBD)"]
    end

    subgraph DB["🗄️ Database & Storage"]
        direction LR
        PG[("PostgreSQL<br>user · pet · order<br>goods · review")]
        QDRANT[("Qdrant<br>Vector DB<br>Hybrid Search + RRF")]
    end

    subgraph PIPELINE["🔄 Data Pipeline"]
        direction LR
        ABOUTPET["어바웃펫<br>aboutpet.co.kr"]
        PW["Playwright<br>크롤링"]
        PREPROCESS["전처리 파이프라인<br>Bronze → Silver → Gold"]
    end

    CICD["🔧 GitHub Actions<br>CI/CD → AWS EC2 (EB)"]

    %% 사용자 → 프론트 → 백엔드
    USER --> FE
    FE <--> OAUTH
    FE --> NGINX
    NGINX --> DJANGO
    NGINX --> FASTAPI

    %% 백엔드 → DB / AI
    DJANGO --> PG
    FASTAPI --> PG
    FASTAPI --> LANGGRAPH
    FASTAPI --> MULTIMODAL
    LANGGRAPH --> QDRANT
    LANGGRAPH --> LLM

    %% 데이터 파이프라인
    PW --> ABOUTPET
    PW --> PREPROCESS
    PREPROCESS --> PG
    PREPROCESS --> QDRANT

    %% CI/CD
    CICD --> NGINX

    %% 스타일
    classDef frontend fill:#3B82F6,stroke:#1D4ED8,color:#fff
    classDef backend fill:#10B981,stroke:#047857,color:#fff
    classDef ai fill:#8B5CF6,stroke:#6D28D9,color:#fff
    classDef multimodal fill:#F59E0B,stroke:#B45309,color:#fff
    classDef db fill:#F97316,stroke:#C2410C,color:#fff
    classDef pipeline fill:#06B6D4,stroke:#0E7490,color:#fff
    classDef monitoring fill:#EF4444,stroke:#B91C1C,color:#fff
    classDef infra fill:#6B7280,stroke:#374151,color:#fff
    classDef user fill:#1F2937,stroke:#111827,color:#fff

    class USER user
    class FE,OAUTH frontend
    class NGINX infra
    class DJANGO,FASTAPI backend
    class LANGGRAPH,LLM ai
    class YOLO,STT multimodal
    class PG,QDRANT db
    class ABOUTPET,PW,PREPROCESS pipeline
    class CICD infra
```

---

## 1. 전체 아키텍처

```
[사용자 / 게스트]
      │
      ▼
[Frontend]  Django Template (MVT) + Vanilla JS
  OAuth (Google / Kakao / Naver)
      │
      ▼
[Nginx]  리버스 프록시 / 로드 밸런싱
      │
      ├──► [Django]   Auth · User · Pet · Order · Admin API
      │         └── JWT 인증 / PostgreSQL
      │
      └──► [FastAPI]  챗봇 · 추천 · 상품 마이크로서비스 (RESTful)
                │
                ├── [LangGraph]  멀티 에이전트 오케스트레이션
                │       ├── 의도 분류 에이전트
                │       ├── 상품 검색 에이전트  ──► Qdrant (Hybrid Search + RRF)
                │       ├── 추천 에이전트
                │       └── 응답 생성 에이전트  ──► LLM (Claude API / OpenAI GPT)
                │
                ├── [PostgreSQL]  관계형 데이터
                │       user · pet · order · goods · review
                │
                └── [Qdrant]  Vector DB
                        Dense + Sparse Hybrid Search + RRF
```

---

## 2. 데이터 파이프라인

```
[어바웃펫 크롤링]
  Playwright
      │
      ▼
[Bronze]  원시 크롤링 데이터 (로컬 Parquet)
      │
      ▼
[Silver]  정제 · 정규화 (HTML 제거, 인코딩, 중복 제거)
      │
      ▼
[Gold]    분석 및 추천 신호 파생
  (OCR, 감성 분석, ABSA, popularity_score, 건강 관심사 태그)
      │
      ├──► PostgreSQL  (관계형 서빙 DB)
      └──► Qdrant      (벡터 임베딩 인덱싱)
```

---

## 3. Infra / DevOps

```
[AWS]
  ├── EC2                앱 서버 (Elastic Beanstalk로 프로비저닝)
  └── IAM                최소 권한 원칙

[Docker Compose 서비스 구성]
  ├── django       Django 백엔드 + Template 렌더링
  ├── fastapi      FastAPI 마이크로서비스
  ├── nginx        리버스 프록시 / LB
  ├── postgres     PostgreSQL 16
  └── qdrant       Vector DB

[CI/CD]  GitHub Actions
  └── PR → main: Build & Test
  └── push → main: DockerHub push → AWS EC2 (Elastic Beanstalk) 배포
```

---

## 4. Multimodal

```
[이미지 입력]
  MIME Type 검증 (프론트) → YOLO 분석 (체중 추정)  ※ S3 연동 미구현 (TBD)

[음성 입력 / 출력]  (구현 여부 TBD)
  STT: 마이크 입력 → 텍스트 변환 → 챗봇 전달
  TTS: LLM 응답 → 음성 출력
```
