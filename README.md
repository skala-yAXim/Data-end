# AI 기반 업무 자동화 및 분석 플랫폼 - 데이터 수집

### 📁 디렉토리 구조
```
.
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 애플리케이션 초기화
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints.py        # API 엔드포인트 정의
│   ├── client/
│   │   ├── __init__.py
│   │   ├── github_client.py      # GitHub API 클라이언트
│   │   └── ms_graph_client.py    # Microsoft Graph API 클라이언트
│   ├── common/
│   │   ├── __init__.py
│   │   ├── config.py       # env 환경 변수 설정 파일
│   │   └── utils.py        # 공통 유틸리티 함수
│   ├── extractor/          # 데이터 추출
│   │   ├── __init__.py
│   │   ├── document_extractor.py         
│   │   ├── email_extractor.py
│   │   ├── github_activity_extractor.py
│   │   └── teams_post_extractor.py
│   ├── pipeline/                 # 전체 수집 흐름
│   │   ├── __init__.py
│   │   ├── docs_pipeline.py
│   │   ├── email_pipeline.py
│   │   ├── github_pipeline.py
│   │   └── teams_post_pipeline.py
│   ├── schemas
│   │   ├── __init__.py
│   │   ├── docs_activity.py
│   │   ├── email_activity.py
│   │   ├── github_activity.py
│   │   └── teams_post_activity.py
│   └── vectordb
│       ├── __init__.py
│       ├── client.py
│       ├── schema.py
│       └── uploader.py
├── .env.example                  # 환경 변수 예시 파일
├── requirements.txt              # Python 패키지 의존성
└── README.md                     # 프로젝트 설명 파일
```