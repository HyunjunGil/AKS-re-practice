# LGTM (Logs, Grafana, Tempo, Metrics) 설정 가이드

## 개요

이 가이드는 AKS Demo 프로젝트에서 LGTM 스택을 통한 완전한 관찰성(Observability) 설정 방법을 설명합니다.

## LGTM 엔드포인트

### 현재 설정된 엔드포인트
```
HTTP: http://collector.lgtm.20.249.154.255.nip.io
gRPC: http://collector.lgtm.20.249.154.255.nip.io
```

### 세부 엔드포인트
- **Tempo (Traces)**: `http://collector.lgtm.20.249.154.255.nip.io/v1/traces`
- **Prometheus (Metrics)**: `http://collector.lgtm.20.249.154.255.nip.io/v1/metrics`
- **OpenTelemetry Logs**: `http://collector.lgtm.20.249.154.255.nip.io/v1/logs`

## 수집되는 데이터

### 1. Traces (분산 추적) - Tempo

#### 백엔드 추적
- **HTTP 요청/응답**: 모든 API 엔드포인트 호출 추적
- **데이터베이스 쿼리**: MariaDB 연결 및 쿼리 실행 추적
- **Redis 작업**: 세션 저장, 로그 저장, 캐시 작업 추적
- **Kafka 메시징**: 메시지 발행 및 구독 추적
- **사용자 세션**: 로그인/로그아웃 세션 관리 추적

#### 프론트엔드 추적
- **페이지 로드**: Vue 컴포넌트 생명주기 추적
- **사용자 상호작용**: 버튼 클릭, 폼 제출 등 추적
- **API 호출**: 백엔드 API 호출 추적
- **오류 추적**: JavaScript 오류 및 예외 추적

### 2. Metrics (메트릭) - Prometheus

#### 애플리케이션 메트릭
- **API 호출 횟수**: 엔드포인트별 요청 수
- **응답 시간**: API 응답 시간 분포
- **오류율**: HTTP 상태 코드별 오류 비율
- **사용자 활동**: 로그인, 메시지 저장 등 사용자 행동

#### 시스템 메트릭
- **데이터베이스 연결**: MariaDB 연결 상태 및 성능
- **Redis 연결**: Redis 연결 상태 및 작업 성능
- **Kafka 메시징**: 메시지 처리량 및 지연 시간

### 3. Logs (로그) - OpenTelemetry Logs

#### 구조화된 로그
```json
{
  "resource": {
    "attributes": {
      "service.name": "aks-demo-backend"
    }
  },
  "scopeLogs": [{
    "scope": {"name": "backend"},
    "logRecords": [{
      "timeUnixNano": "1705312200000000000",
      "body": {"stringValue": "User user123 logged in successfully"},
      "severityText": "INFO",
      "attributes": {
        "action": "login_success",
        "username": "user123",
        "remote_addr": "192.168.1.100",
        "component": "authentication"
      }
    }]
  }]
}
```

#### 로그 카테고리
- **인증 로그**: 로그인, 로그아웃, 회원가입
- **데이터베이스 로그**: 쿼리 실행, 오류, 성능
- **API 로그**: 요청/응답, 오류, 성능
- **시스템 로그**: 애플리케이션 시작/종료, 설정
- **오류 로그**: 예외, 오류, 경고

## 환경 설정

### 1. 환경 변수 설정

#### 백엔드 환경 변수
```bash
# LGTM Telemetry 설정
TEMPO_ENDPOINT=http://collector.lgtm.20.249.154.255.nip.io/v1/traces
OTLP_ENDPOINT=http://collector.lgtm.20.249.154.255.nip.io
BACKEND_SERVICE_NAME=aks-demo-backend
```

#### 프론트엔드 환경 변수
```bash
# LGTM Telemetry 설정
VUE_APP_TEMPO_ENDPOINT=http://collector.lgtm.20.249.154.255.nip.io/v1/traces
FRONTEND_SERVICE_NAME=aks-demo-frontend
```

### 2. Kubernetes 배포 설정

#### 백엔드 Deployment
```yaml
env:
- name: TEMPO_ENDPOINT
  value: "http://collector.lgtm.20.249.154.255.nip.io/v1/traces"
- name: OTLP_ENDPOINT
  value: "http://collector.lgtm.20.249.154.255.nip.io"
- name: BACKEND_SERVICE_NAME
  value: "aks-demo-backend"
```

#### 프론트엔드 Deployment
```yaml
env:
- name: VUE_APP_TEMPO_ENDPOINT
  value: "http://collector.lgtm.20.249.154.255.nip.io/v1/traces"
- name: FRONTEND_SERVICE_NAME
  value: "aks-demo-frontend"
```

## 배포 방법

### 1. 환경 설정 파일 생성
```bash
# env/.env.lgtm 파일 생성
cp env.example env/.env.lgtm
```

### 2. LGTM 환경 변수 설정
```bash
# env/.env.lgtm 파일에 다음 내용 추가
TEMPO_ENDPOINT=http://collector.lgtm.20.249.154.255.nip.io/v1/traces
OTLP_ENDPOINT=http://collector.lgtm.20.249.154.255.nip.io
LOKI_ENDPOINT=http://collector.lgtm.20.249.154.255.nip.io/loki/api/v1/push
BACKEND_SERVICE_NAME=aks-demo-backend
FRONTEND_SERVICE_NAME=aks-demo-frontend
```

### 3. 배포 실행
```bash
# LGTM 환경으로 배포
./deploy-with-env.sh lgtm
```

## 모니터링 확인

### 1. Grafana 대시보드 접근
- **URL**: LGTM Grafana 대시보드 URL
- **대시보드**: 
  - AKS Demo - Overview
  - AKS Demo - API Metrics
  - AKS Demo - User Activity
  - AKS Demo - System Health

### 2. 로그 쿼리 예시

#### 사용자 로그인 로그
```logql
{service_name="aks-demo-backend"} |= "login_success"
```

#### API 오류 로그
```logql
{service_name="aks-demo-backend"} |= "ERROR"
```

#### 데이터베이스 작업 로그
```logql
{service_name="aks-demo-backend"} |= "database"
```

#### 특정 사용자 활동 로그
```logql
{service_name="aks-demo-backend"} |= "user123"
```

### 3. 메트릭 쿼리 예시

#### API 호출 횟수
```promql
rate(http_requests_total{service="aks-demo-backend"}[5m])
```

#### 응답 시간
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service="aks-demo-backend"}[5m]))
```

#### 오류율
```promql
rate(http_requests_total{service="aks-demo-backend", status_code=~"5.."}[5m]) / rate(http_requests_total{service="aks-demo-backend"}[5m])
```

## 문제 해결

### 1. 연결 확인
```bash
# LGTM 엔드포인트 연결 테스트
curl -X GET http://collector.lgtm.20.249.154.255.nip.io/ready

# Loki 로그 전송 테스트
curl -X POST http://collector.lgtm.20.249.154.255.nip.io/loki/api/v1/push \
  -H "Content-Type: application/json" \
  -d '{
    "streams": [{
      "stream": {"service": "test", "level": "info"},
      "values": [["'$(date +%s%N)'", "Test log message"]]
    }]
  }'
```

### 2. 로그 확인
```bash
# 백엔드 파드 로그 확인
kubectl logs -n aks-demo deployment/aks-demo-backend

# 프론트엔드 파드 로그 확인
kubectl logs -n aks-demo deployment/aks-demo-frontend
```

### 3. 환경 변수 확인
```bash
# 백엔드 환경 변수 확인
kubectl exec -n aks-demo deployment/aks-demo-backend -- env | grep -E "(TEMPO|OTLP|LOKI)"

# 프론트엔드 환경 변수 확인
kubectl exec -n aks-demo deployment/aks-demo-frontend -- env | grep -E "(TEMPO|FRONTEND)"
```

## 성능 최적화

### 1. 배치 처리
- Traces: BatchSpanProcessor 사용으로 네트워크 오버헤드 최소화
- Metrics: PeriodicExportingMetricReader 사용으로 주기적 전송
- Logs: 비동기 전송으로 애플리케이션 성능 영향 최소화

### 2. 샘플링
- 프로덕션 환경에서는 적절한 샘플링 설정으로 데이터 양 조절
- 오류는 100% 수집, 정상 요청은 샘플링

### 3. 리소스 관리
- 메모리 사용량 모니터링
- 네트워크 대역폭 사용량 확인
- 디스크 I/O 최적화

## 보안 고려사항

### 1. 인증
- LGTM 엔드포인트 접근 인증 설정
- API 키 또는 토큰 기반 인증

### 2. 데이터 보호
- 민감한 정보 로깅 제외
- PII(개인식별정보) 마스킹
- 로그 데이터 암호화

### 3. 네트워크 보안
- HTTPS 통신 사용
- 방화벽 규칙 설정
- 네트워크 격리

## 참고 자료

- [OpenTelemetry 공식 문서](https://opentelemetry.io/docs/)
- [Grafana Tempo 문서](https://grafana.com/docs/tempo/)
- [Grafana Loki 문서](https://grafana.com/docs/loki/)
- [Prometheus 문서](https://prometheus.io/docs/)
