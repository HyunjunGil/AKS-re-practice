# Kafka 연결 테스트 문제해결 과정

## 1. 초기 문제 상황

### 1.1 프론트엔드 빌드 에러
**문제**: `npm run build` 과정에서 Vue 컴포넌트 문법 오류 발생
```
ERROR  Failed to compile with 1 error
Module parse failed: Unexpected token (245:34)
```

**원인 분석**:
- `v-for="(test, name)"` 순서가 Vue 2 문법에 맞지 않음
- CSS 클래스 중복 정의 (`.status-success`, `.status-error`)
- JavaScript Optional chaining operator (`?.`) 사용 (Vue 2에서 지원하지 않음)

**해결 과정**:
1. `v-for="(test, name)"` → `v-for="(name, test)"` 순서 수정
2. 중복 CSS 클래스 제거 및 스코프 명확화
3. Optional chaining을 전통적인 AND 연산자로 변경

### 1.2 Kafka 라이브러리 호환성 문제
**문제**: `kafka-python` 라이브러리로 Azure Event Hubs와의 호환성 부족

**해결**: `confluent-kafka` 라이브러리로 교체
- **장점**: 
  - Azure Event Hubs와 완벽한 호환성
  - C 기반으로 빠른 성능
  - 프로덕션 환경에서 검증됨

## 2. confluent-kafka 적용 과정

### 2.1 라이브러리 교체
```bash
# requirements.txt 수정
kafka-python → confluent-kafka
kafka-admin → confluent-kafka (내장)
```

### 2.2 코드 수정
```python
# 기존 kafka-python
from kafka import KafkaProducer, KafkaConsumer
from kafka.admin import KafkaAdminClient

# confluent-kafka로 변경
from confluent_kafka import Producer, Consumer, KafkaError
from confluent_kafka.admin import AdminClient, NewTopic
```

### 2.3 설정 방식 변경
```python
# 기존 kafka-python 방식
producer = KafkaProducer(
    bootstrap_servers=servers,
    security_protocol='SASL_PLAINTEXT',
    sasl_mechanism='PLAIN',
    sasl_plain_username=username,
    sasl_plain_password=password
)

# confluent-kafka 방식
producer = Producer({
    'bootstrap.servers': servers,
    'sasl.mechanism': 'PLAIN',
    'security.protocol': 'SASL_PLAINTEXT',
    'sasl.username': username,
    'sasl.password': password
})
```

## 3. 연결 테스트 구현

### 3.1 단순 연결 테스트 (`/kafka/connect`)
**목적**: 기본적인 Kafka 연결 상태만 확인
**테스트 항목**:
- 기본 연결 (AdminClient로 클러스터 정보 조회)
- Producer 생성 (객체 생성만, 메시지 전송 없음)
- Consumer 생성 (객체 생성만, 메시지 수신 없음)

### 3.2 종합 연결 테스트 (`/kafka/test`)
**목적**: 전체적인 Kafka 기능 검증
**테스트 항목**:
- Producer 연결 (실제 메시지 전송)
- Consumer 연결 (실제 메시지 수신)
- 토픽 생성/삭제
- 메시지 흐름 (전송→수신)

## 4. 주요 문제 해결 과정

### 4.1 `api.version` 설정 오류
**문제**: `KafkaError{code=_INVALID_ARG,val=-186,str="No such configuration property: "api.version""}`
**원인**: confluent-kafka에서는 `api.version` 설정을 지원하지 않음
**해결**: 모든 AdminClient, Producer, Consumer 설정에서 `api.version` 제거

### 4.2 Future 객체 처리
**문제**: AdminClient 메서드들이 Future 객체를 반환
**원인**: confluent-kafka는 비동기 방식으로 동작
**해결**: `.result()` 메서드로 Future 완료 대기
```python
cluster_metadata = admin_client.describe_cluster()
cluster_metadata = cluster_metadata.result()  # Future 완료 대기
```

### 4.3 Producer close() 메서드 오류
**문제**: `'cimpl.Producer' object has no attribute 'close'`
**원인**: confluent-kafka Producer는 `close()` 메서드가 없음
**해결**: `producer.flush()` 사용 또는 가비지 컬렉터에 의존

### 4.4 DescribeClusterResult brokers 접근 오류
**문제**: `'DescribeClusterResult' object has no attribute 'brokers'`
**원인**: confluent-kafka의 `DescribeClusterResult` 객체 구조 파악 필요
**해결**: `cluster_metadata.brokers` 속성으로 직접 접근

## 5. 프론트엔드 UI 구현

### 5.1 Kafka 연결 상태 섹션 추가
- 단순 연결 테스트 버튼 (초록색)
- 종합 연결 테스트 버튼 (파란색)
- 상태 조회 버튼 (보라색)
- Kafka 로그 조회 버튼 (주황색)

### 5.2 테스트 결과 표시
- 전체 상태: 성공/부분 성공/실패
- 세부 테스트 결과: 각 테스트별 성공/실패 상태
- 디버깅 정보: 실제 데이터 구조 표시

### 5.3 Vue 문법 오류 수정
**문제**: `v-for="(name, test)"` 순서 오류
**원인**: Vue 2에서는 `(value, key)` 순서
**해결**: `v-for="(test, name)"` 순서로 수정

## 6. 최종 결과

### 6.1 성공한 기능들
- ✅ 단순 연결 테스트: 기본 연결, Producer/Consumer 생성
- ✅ 종합 연결 테스트: 메시지 전송/수신, 토픽 생성/삭제
- ✅ 상태 조회: 브로커 정보, 토픽 목록
- ✅ Kafka 로그 조회: API 호출 로그

### 6.2 Azure Event Hubs 호환성
- confluent-kafka 사용으로 완벽한 호환성 확보
- 환경 변수만 변경하면 Azure Event Hubs로 마이그레이션 가능
- 보안 프로토콜: `SASL_PLAINTEXT` → `SASL_SSL`
- 포트: `9092` → `9093`

## 7. 교훈 및 주의사항

### 7.1 confluent-kafka 사용 시 주의사항
- `api.version` 설정 사용 금지
- AdminClient 메서드는 Future 객체 반환 → `.result()` 필수
- Producer는 `close()` 메서드 없음 → `flush()` 사용
- 설정 키는 `kafka-python`과 다름 (예: `group.id`, `auto.offset.reset`)

### 7.2 Vue 2 문법 주의사항
- `v-for`에서 객체 순회 시 `(value, key)` 순서
- Optional chaining operator (`?.`) 지원하지 않음
- CSS 클래스 중복 정의 시 스코프 명확화 필요

### 7.3 디버깅 방법
- 브라우저 콘솔에서 API 응답 구조 확인
- 백엔드 로그에서 상세 에러 메시지 확인
- 단계별 테스트로 문제 범위 축소
