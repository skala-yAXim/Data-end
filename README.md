# 개인 업무 관리 AI 서비스 - 데이터 수집 시스템

개인 업무 관리 AI 서비스의 데이터 수집 및 전처리를 담당하는 배치 시스템입니다.

Git, Microsoft Teams, Outlook, SharePoint, OneDrive에서 업무 데이터를 수집하고 전처리하여 VectorDB에 저장합니다.

## 🏗️ 시스템 아키텍처

### 주요 기능
- **다중 플랫폼 데이터 수집**: GitHub, Teams, Outlook, SharePoint, OneDrive 연동
- **자동화된 데이터 파이프라인**: 배치 스케줄러를 통한 자동 실행
- **벡터 데이터베이스 관리**: 수집된 데이터의 벡터화 및 저장
- **통계 데이터 생성**: 주간 업무 통계 RDB 저장
- **Kubernetes 지원**: 컨테이너 기반 배포 및 운영

### 스케줄링
- **일반 배치**: 정기적인 데이터 수집 및 처리
- **토요일**: VectorDB Flush 작업 수행
- **금요일**: RDB에 주간 업무 통계 데이터 저장

## 📁 프로젝트 구조

```sh
Data-and/
├── api/ # REST API 엔드포인트
│ └── endpoints.py
├── client/ # 외부 서비스 클라이언트
│ ├── github_client.py
│ ├── ms_graph_client.py
│ └── utils.py
├── common/ # 공통 유틸리티
│ ├── config.py
│ ├── statics_report.py
│ └── utils.py
├── extractor/ # 데이터 추출기
│ ├── document_extractor.py
│ ├── email_extractor.py
│ ├── github_activity_extractor.py
│ └── teams_post_extractor.py
├── pipeline/ # 데이터 파이프라인
│ ├── docs_pipeline.py
│ ├── email_pipeline.py
│ ├── github_pipeline.py
│ └── teams_post_pipeline.py
├── rdb/ # 관계형 데이터베이스
│ ├── client.py
│ ├── repository.py
│ └── schema.py
├── schemas/ # 데이터 스키마
│ ├── docs_activity.py
│ ├── email_activity.py
│ ├── github_activity.py
│ └── teams_post_activity.py
├── vectordb/ # 벡터 데이터베이스
│ ├── client.py
│ ├── schema.py
│ └── uploader.py
└── main.py # 메인 실행 파일

k8s/ # Kubernetes 배포 설정
├── deploy.yaml
├── service.yaml
└── ingress.yaml
```
## 🚀 설치 및 실행

### 사전 요구사항
- Python 3.8+
- Docker
- Kubernetes (배포 시)

### 저장소 클론
```sh
git clone [repository-url]
cd Data-and
```

### 가상환경 생성 및 활성화
```sh
python -m venv venv
source venv/bin/activate # Linux/Mac
venv\Scripts\activate # Windows
```

### 의존성 설치
```sh
pip install -r requirements.txt # 파이썬 라이브러리 설치
```

### 환경변수 설정
```sh
cp .env.example .env
```

## 🔧 사용법

### 수동 실행
```sh
python data_batch.py # 배치 실행 스크립트
python -m uvicorn app.main:app --host 0.0.0.0 --port 8005 # Fast API 실행 스크립트
```

### 빌드 및 배포 (Docker & k8s)
```sh
./base-build.sh # Docker 이미지 빌드 및 harbor에 배포
cd k8s
kubectl apply -f deploy.yaml ingress.yaml service.yaml
```


## 📊 데이터 플로우

1. **수집 단계**: 각 extractor가 외부 플랫폼에서 데이터 수집
2. **전처리 단계**: pipeline이 수집된 데이터를 정제 및 변환
3. **저장 단계**: 
   - 벡터화된 데이터는 VectorDB에 저장
   - 통계 데이터는 RDB에 저장
4. **스케줄링**: 
   - 토요일: VectorDB Flush 수행
   - 금요일: 주간 통계 데이터 생성

## 🔍 모니터링

### 배치 로그 확인
```sh
tail -f batch.log
```

### Pod 로그 (Kubernetes)
```sh
kubectl logs -f {pod 이름}
```

## 🛠️ 개발
### 코드 구조
- **Client**: 외부 API와의 통신 담당
- **Extractor**: 각 플랫폼별 데이터 추출 로직
- **Pipeline**: 데이터 전처리 및 변환 파이프라인
- **Schema**: 데이터 모델 정의
- **VectorDB/RDB**: 데이터 저장소 인터페이스