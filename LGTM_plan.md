# LGTM 모니터링 시스템 구현 계획

## 프로젝트 개요

**프로젝트명**: AKS Demo (hyunjun-backend, hyunjun-frontend)  
**네임스페이스**: hyunjun  
**백엔드 포트**: 5000  
**프론트엔드 포트**: 80  

## LGTM 스택 구성

**LGTM = Logs, Grafana, Tempo, Metrics**

- **L** (Logs) = **Loki** - 로그 수집 및 저장
- **G** (Grafana) - 시각화 및 대시보드  
- **T** (Tempo) - 분산 추적 (Traces)
- **M** (Metrics) = **Prometheus** - 메트릭 수집 및 저장

## 현재 상황 분석

### 기존 설정
- **백엔드**: Flask 앱 (Python), MariaDB, Redis, Kafka 연동
- **프론트엔드**: Vue.js 2.6.11, Axios HTTP 클라이언트
- **Kubernetes**: hyunjun 네임스페이스에 배포
- **telemetry.py**: OpenTelemetry 설정 템플릿 완성됨

### 모니터링 요구사항
- **자동 계측**: Flask, MySQL, Redis, Kafka 자동 추적
- **수동 계측**: 비즈니스 로직 커스텀 추적
- **간단한 설정**: 환경별 설정 없이 단일 설정
- **telemetry.py 수정 최소화**: 기존 파일 최대한 유지

## 구현 계획

### 1단계: 백엔드 모니터링 통합

#### 1.1 Flask 앱에 OpenTelemetry 통합
- `app.py`에 telemetry import 및 초기화 추가
- Flask 앱 시작 시 `telemetry_manager.setup_telemetry(app)` 호출
- 기존 로깅 시스템과 OpenTelemetry 로깅 통합

#### 1.2 환경 변수 설정
```bash
# backend-deployment.yaml에 추가
- name: TEMPO_ENDPOINT
  value: "http://collector.lgtm.20.249.154.255.nip.io/v1/traces"
- name: OTLP_ENDPOINT
  value: "http://collector.lgtm.20.249.154.255.nip.io"
- name: LOKI_ENDPOINT
  value: "http://collector.lgtm.20.249.154.255.nip.io/loki/api/v1/push"
- name: BACKEND_SERVICE_NAME
  value: "hyunjun-backend"
```

#### 1.3 커스텀 추적 추가
- 사용자 인증 (로그인/로그아웃)
- 데이터베이스 작업 (CRUD)
- Kafka 메시지 처리
- Redis 캐시 작업

### 2단계: 프론트엔드 모니터링 설정

#### 2.1 OpenTelemetry JavaScript 패키지 설치
```bash
cd frontend
npm install @opentelemetry/api @opentelemetry/sdk-trace-web @opentelemetry/instrumentation-document-load @opentelemetry/instrumentation-user-interaction @opentelemetry/instrumentation-fetch
```

#### 2.2 프론트엔드 telemetry.js 생성
- OpenTelemetry Web Tracer 설정
- 자동 계측: Document Load, User Interaction, Fetch
- 수동 계측: 사용자 액션, 페이지 전환, 오류 추적

#### 2.3 main.js에 telemetry 통합
- Vue 앱 시작 시 OpenTelemetry 초기화
- 전역 에러 핸들러에 추적 추가

#### 2.4 환경 변수 설정
```bash
# frontend-deployment.yaml에 추가
- name: VUE_APP_TEMPO_ENDPOINT
  value: "http://collector.lgtm.20.249.154.255.nip.io/v1/traces"
- name: VUE_APP_OTLP_ENDPOINT
  value: "http://collector.lgtm.20.249.154.255.nip.io"
- name: VUE_APP_LOKI_ENDPOINT
  value: "http://collector.lgtm.20.249.154.255.nip.io/loki/api/v1/push"
- name: FRONTEND_SERVICE_NAME
  value: "hyunjun-frontend"
```

### 3단계: Kubernetes 배포 설정

#### 3.1 ConfigMap 생성
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: lgtm-config
  namespace: hyunjun
data:
  TEMPO_ENDPOINT: "http://collector.lgtm.20.249.154.255.nip.io/v1/traces"
  OTLP_ENDPOINT: "http://collector.lgtm.20.249.154.255.nip.io"
  LOKI_ENDPOINT: "http://collector.lgtm.20.249.154.255.nip.io/loki/api/v1/push"
  BACKEND_SERVICE_NAME: "hyunjun-backend"
  FRONTEND_SERVICE_NAME: "hyunjun-frontend"
```

#### 3.2 Deployment 파일 수정
- backend-deployment.yaml에 환경 변수 추가
- frontend-deployment.yaml에 환경 변수 추가
- ConfigMap 참조 설정

### 4단계: 모니터링 대시보드 설정

#### 4.1 Grafana 접속
- **URL**: http://grafana.20.249.154.255.nip.io
- **계정**: admin
- **비밀번호**: New1234!

#### 4.2 대시보드 생성
- **AKS Demo - Overview**: 전체 시스템 상태
- **AKS Demo - Backend Metrics**: 백엔드 성능 지표
- **AKS Demo - Frontend Metrics**: 프론트엔드 사용자 행동
- **AKS Demo - Database Performance**: 데이터베이스 성능
- **AKS Demo - Logs Analysis**: Loki를 통한 로그 분석
- **AKS Demo - Traces & Logs**: Tempo와 Loki 연동 분석

## 수집되는 데이터

### 백엔드 추적
- **HTTP 요청/응답**: 모든 API 엔드포인트
- **데이터베이스 쿼리**: MariaDB 연결 및 쿼리
- **Redis 작업**: 세션, 캐시, 로그 저장
- **Kafka 메시징**: 메시지 발행/구독
- **사용자 세션**: 인증, 권한 관리

### 백엔드 로그 (Loki)
- **구조화된 로그**: JSON 형태의 로그 데이터
- **로그 레벨**: INFO, DEBUG, ERROR, WARN
- **컨텍스트 정보**: 사용자 ID, 요청 ID, 세션 ID
- **비즈니스 로그**: 로그인, 데이터 처리, 오류 상황

### 프론트엔드 추적
- **페이지 로딩**: Vue 컴포넌트 생명주기
- **사용자 인터랙션**: 버튼 클릭, 폼 제출
- **API 호출**: 백엔드 통신
- **오류 추적**: JavaScript 예외

### 프론트엔드 로그 (Loki)
- **사용자 행동 로그**: 페이지 방문, 버튼 클릭, 폼 제출
- **성능 로그**: 페이지 로딩 시간, API 응답 시간
- **오류 로그**: JavaScript 예외, API 오류
- **사용자 컨텍스트**: 사용자 ID, 세션 ID, 페이지 정보

### 메트릭
- **API 호출 횟수**: 엔드포인트별 요청 수
- **응답 시간**: API 응답 시간 분포
- **오류율**: HTTP 상태 코드별 오류 비율
- **사용자 활동**: 로그인, 메시지 저장 등

## 구현 순서

1. **백엔드 telemetry 통합** (app.py 수정)
2. **프론트엔드 telemetry.js 생성**
3. **Kubernetes ConfigMap 생성**
4. **Deployment 파일 수정**
5. **배포 및 테스트**
6. **Grafana 대시보드 설정**

## 예상 결과

- **자동 추적**: Flask, MySQL, Redis, Kafka 모든 작업 자동 추적
- **수동 추적**: 비즈니스 로직별 커스텀 추적
- **통합 모니터링**: 백엔드와 프론트엔드 통합 관찰성
- **실시간 모니터링**: Grafana를 통한 실시간 시스템 상태 확인
- **로그 분석**: Loki를 통한 구조화된 로그 수집 및 분석
- **Traces & Logs 연동**: Tempo의 span과 Loki의 로그 연결 분석

## 주의사항

- **telemetry.py 수정 금지**: 기존 파일 최대한 유지
- **기존 기능 영향 최소화**: 모니터링 추가로 인한 성능 영향 최소화
- **점진적 배포**: 백엔드 → 프론트엔드 순서로 단계별 배포
- **모니터링 확인**: 각 단계별로 추적 데이터 수집 확인
