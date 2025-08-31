# OpenTelemetry 설정 및 사용 가이드

이 문서는 AKS 데모 프로젝트에서 OpenTelemetry를 설정하고 사용하는 방법을 설명합니다.

## 개요

OpenTelemetry는 분산 추적(Distributed Tracing), 메트릭(Metrics), 로그(Logs)를 수집하기 위한 표준화된 프레임워크입니다. 이 프로젝트에서는 다음과 같은 기능을 제공합니다:

- **분산 추적**: 마이크로서비스 간 요청 흐름 추적
- **메트릭 수집**: 성능 지표 및 비즈니스 메트릭 수집
- **자동 계측**: Flask, MySQL, Redis, Kafka 등 자동 계측
- **커스텀 추적**: 비즈니스 로직에 대한 커스텀 추적

## 아키텍처

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │    Jaeger       │
│   (Vue.js)      │    │   (Flask)       │    │   (UI/Collector)│
│                 │    │                 │    │                 │
│ • Page Load     │    │ • HTTP Requests │    │ • Trace Storage │
│ • User Actions  │    │ • DB Queries    │    │ • Trace Query   │
│ • API Calls     │    │ • Redis Ops     │    │ • Trace UI      │
│ • Component     │    │ • Kafka Msgs    │    │                 │
│   Lifecycle     │    │ • Custom Spans  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   OTLP HTTP     │
                    │   Endpoint      │
                    │  (4318/v1/traces)│
                    └─────────────────┘
```

## 설치 및 설정

### 1. 백엔드 설정

#### 1.1 의존성 설치
```bash
cd backend
pip install -r requirements.txt
```

#### 1.2 환경 변수 설정
`env/.env.local` 또는 `env/.env.dev` 파일에 다음을 추가:

```bash
# OpenTelemetry 설정 (LGTM 스택)
ENVIRONMENT=development
OTLP_ENDPOINT=http://tempo.${K8S_NAMESPACE}.svc.cluster.local:4317
TEMPO_ENDPOINT=http://tempo.${K8S_NAMESPACE}.svc.cluster.local:4317

# Jaeger 설정 (선택적, 기존 호환성)
# JAEGER_HOST=localhost
# JAEGER_PORT=14268
```

#### 1.3 자동 계측 확인
다음 라이브러리들이 자동으로 계측됩니다:
- **Flask**: HTTP 요청/응답 추적
- **MySQL**: 데이터베이스 쿼리 추적
- **Redis**: Redis 작업 추적
- **Kafka**: 메시지 전송 추적

#### 1.4 Tempo 연결 확인
- **OTLP Exporter**: Tempo로 직접 전송
- **Jaeger Exporter**: 선택적 (기존 호환성)
- **포트**: 4317 (Tempo OTLP gRPC)

### 2. 프론트엔드 설정

#### 2.1 의존성 설치
```bash
cd frontend
npm install
```

#### 2.2 환경 변수 설정
프론트엔드 루트에 `.env` 파일 생성:

```bash
VUE_APP_TEMPO_ENDPOINT=http://tempo.${K8S_NAMESPACE}.svc.cluster.local:4317/v1/traces
VUE_APP_OTLP_ENDPOINT=http://tempo.${K8S_NAMESPACE}.svc.cluster.local:4317/v1/traces
```

#### 2.3 자동 계측 확인
다음 기능들이 자동으로 계측됩니다:
- **Document Load**: 페이지 로딩 시간
- **User Interaction**: 사용자 클릭/입력
- **Fetch**: API 호출
- **Vue Lifecycle**: 컴포넌트 생명주기

### 3. LGTM 스택 설치 (Tempo 포함)

#### 3.1 LGTM 스택 설치
```bash
./setup-lgtm.sh
```

#### 3.2 Grafana 접근 (Tempo UI 포함)
```bash
kubectl port-forward -n <namespace> svc/grafana 3000:3000
```
브라우저에서 http://localhost:3000 접속
또는 외부 URL: http://grafana.20.249.154.255.nip.io
로그인: admin / New1234!

### 4. Jaeger 설치 (선택사항)

기존 Jaeger를 사용하려면:
```bash
./setup-jaeger.sh
```

## 사용 방법

### 1. 백엔드에서 커스텀 추적

#### 1.1 기본 Span 생성
```python
from telemetry import telemetry_manager

def my_function():
    tracer = telemetry_manager.get_tracer()
    
    with tracer.start_as_current_span("my_operation") as span:
        span.set_attribute("operation.type", "data_processing")
        span.set_attribute("user.id", user_id)
        
        # 비즈니스 로직 실행
        result = process_data()
        
        span.set_attribute("result.status", "success")
        return result
```

#### 1.2 중첩 Span 생성
```python
def complex_operation():
    tracer = telemetry_manager.get_tracer()
    
    with tracer.start_as_current_span("complex_operation") as parent_span:
        parent_span.set_attribute("operation.complexity", "high")
        
        # 자식 Span 생성
        with tracer.start_as_current_span("data_validation") as child_span:
            child_span.set_attribute("validation.type", "input_check")
            validate_input()
        
        with tracer.start_as_current_span("data_processing") as child_span:
            child_span.set_attribute("processing.type", "batch")
            process_batch()
```

#### 1.3 메트릭 기록
```python
def record_business_metric():
    telemetry_manager.record_metric(
        "orders_processed_total", 
        1, 
        {"order_type": "premium", "status": "completed"}
    )
```

### 2. 프론트엔드에서 커스텀 추적

#### 2.1 사용자 액션 추적
```javascript
import frontendTelemetry from './telemetry'

// 버튼 클릭 추적
function handleButtonClick() {
    frontendTelemetry.trackUserAction('button_click', {
        button_id: 'submit_button',
        page: 'checkout',
        user_type: 'premium'
    })
    
    // 비즈니스 로직 실행
    submitOrder()
}
```

#### 2.2 API 호출 추적
```javascript
async function callApi() {
    const startTime = performance.now()
    
    try {
        const response = await fetch('/api/data')
        const duration = performance.now() - startTime
        
        frontendTelemetry.trackApiCall(
            'GET',
            '/api/data',
            response.status,
            duration
        )
        
        return response.json()
    } catch (error) {
        frontendTelemetry.trackError(error, {
            context: 'api_call',
            endpoint: '/api/data'
        })
        throw error
    }
}
```

#### 2.3 커스텀 Span 생성
```javascript
function customOperation() {
    const span = frontendTelemetry.createSpan('custom_operation', {
        'operation.type': 'data_analysis',
        'data.size': 'large'
    })
    
    try {
        // 비즈니스 로직 실행
        analyzeData()
        span.setAttribute('result.status', 'success')
    } catch (error) {
        span.setAttribute('error', true)
        span.setAttribute('error.message', error.message)
    } finally {
        span.end()
    }
}
```

### 3. Vue 컴포넌트에서 추적

#### 3.1 컴포넌트 생명주기 추적
```javascript
export default {
    name: 'UserProfile',
    mounted() {
        // 자동으로 추적됨 (Vue 믹스인)
        this.loadUserData()
    },
    methods: {
        loadUserData() {
            frontendTelemetry.trackUserAction('load_user_profile', {
                user_id: this.userId
            })
        }
    }
}
```

## 수집되는 데이터

### 1. 백엔드 추적 데이터

#### 1.1 HTTP 요청/응답
- 요청 메서드, URL, 상태 코드
- 요청 지속 시간
- 요청 헤더 정보
- 응답 크기

#### 1.2 데이터베이스 쿼리
- SQL 쿼리문
- 쿼리 실행 시간
- 데이터베이스 연결 정보
- 쿼리 결과 행 수

#### 1.3 Redis 작업
- Redis 명령어
- 키 정보
- 작업 지속 시간
- 연결 정보

#### 1.4 Kafka 메시지
- 토픽명
- 파티션 정보
- 오프셋 정보
- 메시지 크기

### 2. 프론트엔드 추적 데이터

#### 2.1 페이지 로딩
- 페이지 로딩 시간
- DOM 로딩 시간
- 리소스 로딩 시간

#### 2.2 사용자 인터랙션
- 클릭 이벤트
- 입력 이벤트
- 스크롤 이벤트
- 포커스 이벤트

#### 2.3 API 호출
- HTTP 메서드
- 요청 URL
- 응답 상태 코드
- 요청 지속 시간

## 모니터링 및 분석

### 1. Grafana Tempo UI 사용법

#### 1.1 트레이스 검색
1. Grafana 접속 (http://localhost:3000)
2. Tempo 데이터 소스 선택
3. 서비스 선택 (aks-demo-backend 또는 aks-demo-frontend)
4. 검색 조건 설정:
   - 시간 범위
   - 태그 필터
   - 최소 지속 시간
5. "Search" 클릭

#### 1.2 트레이스 분석
- **Timeline View**: 시간 기반 트레이스 시각화
- **Trace Graph**: 서비스 간 호출 관계 시각화
- **Span Details**: 개별 Span의 상세 정보
- **Logs**: Span과 연관된 로그 메시지 (Loki 연동)
- **Metrics**: Span과 연관된 메트릭 (Prometheus 연동)

### 2. 성능 분석

#### 2.1 병목 지점 식별
- 긴 지속 시간을 가진 Span 찾기
- 데이터베이스 쿼리 최적화
- 외부 API 호출 최적화

#### 2.2 오류 분석
- 실패한 요청 추적
- 오류 패턴 분석
- 사용자 영향도 평가

### 3. 비즈니스 인사이트

#### 3.1 사용자 행동 분석
- 가장 많이 사용되는 기능
- 사용자 여정 분석
- 성능이 좋지 않은 페이지 식별

#### 3.2 시스템 성능 모니터링
- API 응답 시간 추이
- 데이터베이스 성능 모니터링
- 캐시 히트율 분석

## 고급 설정

### 1. 샘플링 설정

#### 1.1 백엔드 샘플링
```python
# telemetry.py에서 설정
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

# 10% 샘플링
sampler = TraceIdRatioBased(0.1)
self.trace_provider = TracerProvider(
    resource=resource,
    sampler=sampler
)
```

#### 1.2 프론트엔드 샘플링
```javascript
// telemetry.js에서 설정
const provider = new WebTracerProvider({
    resource: resource,
    sampler: new TraceIdRatioBased(0.1) // 10% 샘플링
})
```

### 2. 배치 처리 설정

#### 2.1 백엔드 배치 설정
```python
# telemetry.py에서 설정
from opentelemetry.sdk.trace.export import BatchSpanProcessor

processor = BatchSpanProcessor(
    exporter,
    max_queue_size=1000,
    max_export_batch_size=512,
    schedule_delay_millis=5000
)
```

### 3. 커스텀 속성 추가

#### 3.1 전역 속성 설정
```python
# telemetry.py에서 설정
resource = Resource.create({
    "service.name": "aks-demo-backend",
    "service.version": "1.0.0",
    "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    "custom.team": "platform",
    "custom.region": "korea"
})
```

## 문제 해결

### 1. 일반적인 문제

#### 1.1 추적이 수집되지 않는 경우
- 환경 변수 확인
- Jaeger 서비스 상태 확인
- 네트워크 연결 확인

#### 1.2 성능 문제
- 샘플링 비율 조정
- 배치 크기 조정
- 불필요한 속성 제거

#### 1.3 메모리 사용량 문제
- 배치 크기 줄이기
- 스팬 보관 기간 조정
- 샘플링 비율 낮추기

### 2. 디버깅

#### 2.1 로그 확인
```bash
# 백엔드 로그
kubectl logs -f deployment/backend

# Tempo 로그
kubectl logs -f deployment/tempo

# Grafana 로그
kubectl logs -f deployment/grafana
```

#### 2.2 환경 변수 확인
```bash
# 백엔드 환경 변수
kubectl exec deployment/backend -- env | grep -E "(OTLP|TEMPO|JAEGER)"
```

## 모범 사례

### 1. Span 네이밍
- 명확하고 일관된 이름 사용
- 동사-명사 형태 권장
- 예: `save_user_data`, `process_order`, `validate_input`

### 2. 속성 설정
- 의미 있는 속성만 추가
- 민감한 정보 제외
- 일관된 키 네이밍 사용

### 3. 오류 처리
- 모든 예외 상황 추적
- 오류 컨텍스트 제공
- 사용자 영향도 평가

### 4. 성능 고려사항
- 적절한 샘플링 비율 설정
- 배치 처리 활용
- 불필요한 추적 제거

## 추가 리소스

- [OpenTelemetry 공식 문서](https://opentelemetry.io/docs/)
- [Jaeger 공식 문서](https://www.jaegertracing.io/docs/)
- [OpenTelemetry Python 가이드](https://opentelemetry.io/docs/instrumentation/python/)
- [OpenTelemetry JavaScript 가이드](https://opentelemetry.io/docs/instrumentation/js/)
