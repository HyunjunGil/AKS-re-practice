<template>
  <div id="app">
    <h1>K8s 마이크로서비스 데모</h1>
    
    <!-- 로그인/회원가입 섹션 -->
    <div class="section" v-if="!isLoggedIn">
      <div v-if="!showRegister">
        <h2>로그인</h2>
        <input v-model="username" placeholder="사용자명">
        <input v-model="password" type="password" placeholder="비밀번호">
        <button @click="login">로그인</button>
        <button @click="showRegister = true" class="register-btn">회원가입</button>
      </div>
      <div v-else>
        <h2>회원가입</h2>
        <input v-model="registerUsername" placeholder="사용자명">
        <input v-model="registerPassword" type="password" placeholder="비밀번호">
        <input v-model="confirmPassword" type="password" placeholder="비밀번호 확인">
        <button @click="register">가입하기</button>
        <button @click="showRegister = false">로그인으로 돌아가기</button>
      </div>
    </div>

    <div v-else>
      <div class="user-info">
        <span>안녕하세요, {{ currentUser }}님</span>
        <button @click="logout">로그아웃</button>
      </div>

      <div class="container">
        <div class="section">
          <h2>MariaDB 메시지 관리</h2>
          <input v-model="dbMessage" placeholder="저장할 메시지 입력">
          <button @click="saveToDb">DB에 저장</button>
          <button @click="getFromDb">DB에서 조회</button>
          <button @click="insertSampleData" class="sample-btn">샘플 데이터 저장</button>
          <div v-if="loading" class="loading-spinner">
            <p>데이터를 불러오는 중...</p>
          </div>
          <div v-if="dbData.length && !loading">
            <h3>저장된 메시지:</h3>
            <ul>
              <li v-for="item in dbData" :key="item.id">{{ item.message }} ({{ formatDate(item.created_at) }})</li>
            </ul>
          </div>
        </div>

        <div class="section">
          <h2>Redis 로그</h2>
          <button @click="getRedisLogs">로그 조회</button>
          <div v-if="redisLogs.length">
            <h3>API 호출 로그:</h3>
            <ul>
              <li v-for="(log, index) in redisLogs" :key="index">
                [{{ formatDate(log.timestamp) }}] {{ log.action }}: {{ log.details }}
              </li>
            </ul>
          </div>
        </div>

        <div class="section">
          <h2>Kafka 연결 상태</h2>
          <div class="kafka-controls">
            <button @click="testKafkaConnectionSimple" :disabled="kafkaSimpleTesting" class="kafka-simple-btn">
              {{ kafkaSimpleTesting ? '테스트 중...' : '단순 연결 테스트' }}
            </button>
            <button @click="testKafkaConnection" :disabled="kafkaTesting" class="kafka-test-btn">
              {{ kafkaTesting ? '테스트 중...' : '종합 연결 테스트' }}
            </button>
            <button @click="getKafkaStatus" :disabled="kafkaStatusLoading" class="kafka-status-btn">
              {{ kafkaStatusLoading ? '상태 확인 중...' : '상태 조회' }}
            </button>
            <button @click="getKafkaLogs" :disabled="kafkaLogsLoading" class="kafka-logs-btn">
              {{ kafkaLogsLoading ? '로그 조회 중...' : 'Kafka 로그' }}
            </button>
          </div>

          <!-- Kafka 단순 연결 테스트 결과 -->
          <div v-if="kafkaSimpleTestResult" class="kafka-test-result">
            <h3>단순 연결 테스트 결과:</h3>
            <div class="test-status" :class="kafkaSimpleTestResult.status">
              <strong>전체 상태:</strong> 
              <span v-if="kafkaSimpleTestResult.status === 'success'" class="status-success">✅ 성공</span>
              <span v-else-if="kafkaSimpleTestResult.status === 'partial_success'" class="status-partial">⚠️ 부분 성공</span>
              <span v-else class="status-error">❌ 실패</span>
            </div>
            
            <div class="test-details">
              <h4>세부 테스트 결과:</h4>
              <div v-for="(test, name) in kafkaSimpleTestResult.tests" :key="name" class="test-item">
                <div class="test-name">{{ getSimpleTestName(name) }}</div>
                <div class="test-status" :class="test.status">
                  <span v-if="test.status === 'success'" class="status-success">✅</span>
                  <span v-else class="status-error">❌</span>
                  {{ test.message }}
                </div>
              </div>
            </div>
            
            <div class="test-timestamp">
              <small>테스트 시간: {{ formatDate(kafkaSimpleTestResult.timestamp) }}</small>
            </div>
          </div>

          <!-- Kafka 종합 테스트 결과 -->
          <div v-if="kafkaTestResult" class="kafka-test-result">
            <h3>연결 테스트 결과:</h3>
            <div class="test-status" :class="kafkaTestResult.status">
              <strong>전체 상태:</strong> 
              <span v-if="kafkaTestResult.status === 'success'" class="status-success">✅ 성공</span>
              <span v-else-if="kafkaTestResult.status === 'partial_success'" class="status-partial">⚠️ 부분 성공</span>
              <span v-else class="status-error">❌ 실패</span>
            </div>
            
            <div class="test-details">
              <h4>세부 테스트 결과:</h4>
              <div v-for="(test, name) in kafkaTestResult.tests" :key="name" class="test-item">
                <div class="test-name">{{ getTestName(name) }}</div>
                <div class="test-status" :class="test.status">
                  <span v-if="test.status === 'success'" class="status-success">✅</span>
                  <span v-else class="status-error">❌</span>
                  {{ test.message }}
                </div>
                <!-- 디버깅용: 실제 데이터 구조 표시 -->
                <div class="debug-data">
                  <small>Debug: status={{ test.status }}, message={{ test.message }}</small>
                </div>
              </div>
            </div>
            
            <div class="test-timestamp">
              <small>테스트 시간: {{ formatDate(kafkaTestResult.timestamp) }}</small>
            </div>
          </div>

          <!-- Kafka 상태 정보 -->
          <div v-if="kafkaStatus" class="kafka-status">
            <h3>클러스터 상태:</h3>
            <div class="status-grid">
              <div class="status-item">
                <strong>브로커 수:</strong> {{ kafkaStatus.cluster_info.broker_count }}
              </div>
              <div class="status-item">
                <strong>토픽 수:</strong> {{ kafkaStatus.topics.length }}
              </div>
              <div class="status-item">
                <strong>보안 프로토콜:</strong> {{ kafkaStatus.kafka_config.security_protocol }}
              </div>
              <div class="status-item">
                <strong>SASL 메커니즘:</strong> {{ kafkaStatus.kafka_config.sasl_mechanism }}
              </div>
            </div>
            
            <div v-if="kafkaStatus.cluster_info.brokers.length" class="broker-list">
              <h4>브로커 정보:</h4>
              <table class="broker-table">
                <thead>
                  <tr>
                    <th>Node ID</th>
                    <th>Host</th>
                    <th>Port</th>
                    <th>Rack</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="broker in kafkaStatus.cluster_info.brokers" :key="broker.node_id">
                    <td>{{ broker.node_id }}</td>
                    <td>{{ broker.host }}</td>
                    <td>{{ broker.port }}</td>
                    <td>{{ broker.rack || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            
            <div v-if="kafkaStatus.topics.length" class="topic-list">
              <h4>토픽 목록:</h4>
              <div class="topic-tags">
                <span v-for="topic in kafkaStatus.topics" :key="topic" class="topic-tag">
                  {{ topic }}
                </span>
              </div>
            </div>
          </div>

          <!-- Kafka 로그 -->
          <div v-if="kafkaLogs.length" class="kafka-logs">
            <h3>Kafka 로그 ({{ kafkaLogs.length }}개):</h3>
            <table class="kafka-logs-table">
              <thead>
                <tr>
                  <th>시간</th>
                  <th>엔드포인트</th>
                  <th>메서드</th>
                  <th>상태</th>
                  <th>사용자</th>
                  <th>메시지</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="log in kafkaLogs" :key="log.timestamp + log.user_id" class="log-row">
                  <td>{{ formatDate(log.timestamp) }}</td>
                  <td>{{ log.endpoint }}</td>
                  <td>{{ log.method }}</td>
                  <td>
                    <span :class="'status-' + log.status" class="status-badge">
                      {{ log.status }}
                    </span>
                  </td>
                  <td>{{ log.user_id }}</td>
                  <td>{{ log.message }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="section">
          <h2>메시지 검색</h2>
          <div class="search-section">
            <input v-model="searchQuery" placeholder="메시지 검색">
            <button @click="searchMessages">검색</button>
            <button @click="getAllMessages" class="view-all-btn">전체 메시지 보기</button>
          </div>
          
          <!-- 디버깅 정보 표시 -->
          <div v-if="debugInfo" class="debug-info">
            <h4>디버깅 정보:</h4>
            <p><strong>데이터 출처:</strong> {{ debugInfo.source }}</p>
            <p><strong>결과 개수:</strong> {{ debugInfo.count }}</p>
            <p><strong>응답 상태:</strong> {{ debugInfo.status }}</p>
          </div>
          
          <div v-if="searchResults.length > 0" class="search-results">
            <h3>검색 결과 ({{ searchResults.length }}개):</h3>
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>메시지</th>
                  <th>생성 시간</th>
                  <th>사용자</th>
                  <th>출처</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="result in searchResults" :key="result.id">
                  <td>{{ result.id }}</td>
                  <td>{{ result.message }}</td>
                  <td>{{ formatDate(result.created_at) }}</td>
                  <td>{{ result.user_id || '없음' }}</td>
                  <td>{{ result.source || 'database' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios';

// nginx 프록시를 통해 요청하도록 수정
const API_BASE_URL = '/api';

export default {
  name: 'App',
  data() {
    return {
      username: '',
      password: '',
      isLoggedIn: false,
      searchQuery: '',
      dbMessage: '',
      dbData: [],
      redisLogs: [],
      sampleMessages: [
        '안녕하세요! 테스트 메시지입니다.',
        'K8s 데모 샘플 데이터입니다.',
        '마이크로서비스 테스트 중입니다.',
        '샘플 메시지 입니다.'
      ],
      offset: 0,
      limit: 20,
      loading: false,
      hasMore: true,
      showRegister: false,
      registerUsername: '',
      registerPassword: '',
      confirmPassword: '',
      currentUser: null,
      searchResults: [],
      debugInfo: null,
      // Kafka 관련 변수들
      kafkaSimpleTesting: false,
      kafkaTesting: false,
      kafkaStatusLoading: false,
      kafkaLogsLoading: false,
      kafkaSimpleTestResult: null,
      kafkaTestResult: null,
      kafkaStatus: null,
      kafkaLogs: []
    }
  },
  methods: {
    // 날짜를 사용자 친화적인 형식으로 변환
    formatDate(dateString) {
      const date = new Date(dateString);
      const baseTime = date.toLocaleString();
      
      // 마이크로초 부분 추출 (예: "2025-08-30T13:22:51.913501" -> "913")
      const microsecondMatch = dateString.match(/\.(\d{6})/);
      if (microsecondMatch) {
        const milliseconds = microsecondMatch[1].substring(0, 3);
        return `${baseTime}.${milliseconds}`;
      }
      
      return baseTime;
    },
    
    // MariaDB에 메시지 저장
    async saveToDb() {
      try {
        await axios.post(`${API_BASE_URL}/db/message`, {
          message: this.dbMessage
        });
        this.dbMessage = '';
        this.getFromDb();
        this.getRedisLogs();
      } catch (error) {
        console.error('DB 저장 실패:', error);
      }
    },

    // MariaDB에서 메시지 조회 (페이지네이션 적용)
    async getFromDb() {
      try {
        this.loading = true;
        const response = await axios.get(`${API_BASE_URL}/db/messages?offset=${this.offset}&limit=${this.limit}`);
        
        // 새로운 응답 형식 처리
        if (response.data.status === 'success' && response.data.results) {
          this.dbData = response.data.results;
          this.hasMore = response.data.results.length === this.limit;
          console.log(`메시지 조회 성공: ${response.data.source}에서 ${response.data.count}개 로드`);
        } else {
          // 기존 형식 호환성 유지
          this.dbData = response.data;
          this.hasMore = response.data.length === this.limit;
        }
        
        // 디버깅 정보 저장
        this.debugInfo = {
          source: response.data.source || 'legacy',
          count: response.data.count || response.data.length || 0,
          status: response.data.status || 'success'
        };
      } catch (error) {
        console.error('DB 조회 실패:', error);
      } finally {
        this.loading = false;
      }
    },

    // 샘플 데이터를 DB에 저장
    async insertSampleData() {
      const randomMessage = this.sampleMessages[Math.floor(Math.random() * this.sampleMessages.length)];
      try {
        await axios.post(`${API_BASE_URL}/db/message`, {
          message: randomMessage
        });
        this.getFromDb();
        this.getRedisLogs();
      } catch (error) {
        console.error('샘플 데이터 저장 실패:', error);
      }
    },

    // Redis에 저장된 API 호출 로그 조회
    async getRedisLogs() {
      try {
        const response = await axios.get(`${API_BASE_URL}/logs/redis`);
        this.redisLogs = response.data;
      } catch (error) {
        console.error('Redis 로그 조회 실패:', error);
      }
    },

    // 사용자 로그인 처리
    async login() {
      try {
        const response = await axios.post(`${API_BASE_URL}/login`, {
          username: this.username,
          password: this.password
        });
        
        if (response.data.status === 'success') {
          this.isLoggedIn = true;
          this.currentUser = this.username;
          this.username = '';
          this.password = '';
        } else {
          alert(response.data.message || '로그인에 실패했습니다.');
        }
      } catch (error) {
        console.error('로그인 실패:', error);
        alert(error.response && error.response.data 
          ? error.response.data.message 
          : '로그인에 실패했습니다.');
      }
    },
    
    // 로그아웃 처리
    async logout() {
      try {
        await axios.post(`${API_BASE_URL}/logout`);
        this.isLoggedIn = false;
        this.username = '';
        this.password = '';
      } catch (error) {
        console.error('로그아웃 실패:', error);
      }
    },

    // 메시지 검색 기능
    async searchMessages() {
      try {
        this.loading = true;
        const response = await axios.get(`${API_BASE_URL}/db/messages/search`, {
          params: { q: this.searchQuery }
        });
        
        // 새로운 응답 형식 처리
        if (response.data.status === 'success' && response.data.results) {
          this.searchResults = response.data.results;
          console.log(`검색 성공: ${response.data.source}에서 ${response.data.count}개 발견`);
        } else {
          // 기존 형식 호환성 유지
          this.searchResults = response.data;
        }
        
        // 디버깅 정보 저장
        this.debugInfo = {
          source: response.data.source || 'legacy',
          count: response.data.count || response.data.length || 0,
          status: response.data.status || 'success'
        };
      } catch (error) {
        console.error('검색 실패:', error);
        alert('검색에 실패했습니다.');
      } finally {
        this.loading = false;
      }
    },

    // 전체 메시지 조회
    async getAllMessages() {
      try {
        this.loading = true;
        const response = await axios.get(`${API_BASE_URL}/db/messages`);
        
        // 새로운 응답 형식 처리
        if (response.data.status === 'success' && response.data.results) {
          this.searchResults = response.data.results;
          console.log(`전체 메시지 로드 성공: ${response.data.source}에서 ${response.data.count}개 로드`);
        } else {
          // 기존 형식 호환성 유지
          this.searchResults = response.data;
        }
        
        // 디버깅 정보 저장
        this.debugInfo = {
          source: response.data.source || 'legacy',
          count: response.data.count || response.data.length || 0,
          status: response.data.status || 'success'
        };
      } catch (error) {
        console.error('전체 메시지 로드 실패:', error);
      } finally {
        this.loading = false;
      }
    },

    // 페이지네이션을 위한 추가 데이터 로드
    async loadMore() {
      this.offset += this.limit;
      await this.getFromDb();
    },

    // 회원가입 처리
    async register() {
      if (this.registerPassword !== this.confirmPassword) {
        alert('비밀번호가 일치하지 않습니다');
        return;
      }
      
      try {
        const response = await axios.post(`${API_BASE_URL}/register`, {
          username: this.registerUsername,
          password: this.registerPassword
        });
        
        if (response.data.status === 'success') {
          alert('회원가입이 완료되었습니다. 로그인해주세요.');
          this.showRegister = false;
          this.registerUsername = '';
          this.registerPassword = '';
          this.confirmPassword = '';
        }
      } catch (error) {
        console.error('회원가입 실패:', error);
        alert(error.response && error.response.data && error.response.data.message 
          ? error.response.data.message 
          : '회원가입에 실패했습니다.');
      }
    },

    // Kafka 단순 연결 테스트
    async testKafkaConnectionSimple() {
      try {
        this.kafkaSimpleTesting = true;
        this.kafkaSimpleTestResult = null;
        
        const response = await axios.get(`${API_BASE_URL}/kafka/connect`);
        this.kafkaSimpleTestResult = response.data;
        
        console.log('Kafka 단순 연결 테스트 완료:', response.data);
      } catch (error) {
        console.error('Kafka 단순 연결 테스트 실패:', error);
        this.kafkaSimpleTestResult = {
          status: 'error',
          message: (error.response && error.response.data && error.response.data.message) || '단순 연결 테스트에 실패했습니다.',
          timestamp: new Date().toISOString()
        };
      } finally {
        this.kafkaSimpleTesting = false;
      }
    },

    // Kafka 종합 연결 테스트
    async testKafkaConnection() {
      try {
        this.kafkaTesting = true;
        this.kafkaTestResult = null;
        
        const response = await axios.get(`${API_BASE_URL}/kafka/test`);
        this.kafkaTestResult = response.data;
        
        console.log('Kafka 종합 연결 테스트 완료:', response.data);
        console.log('테스트 결과 구조:', JSON.stringify(response.data.tests, null, 2));
        
        // 각 테스트 결과의 status 확인
        Object.keys(response.data.tests).forEach(testName => {
          const test = response.data.tests[testName];
          console.log(`${testName} 테스트:`, test);
          console.log(`${testName} status:`, test.status);
        });
        
      } catch (error) {
        console.error('Kafka 종합 연결 테스트 실패:', error);
        this.kafkaTestResult = {
          status: 'error',
          message: (error.response && error.response.data && error.response.data.message) || '종합 연결 테스트에 실패했습니다.',
          timestamp: new Date().toISOString()
        };
      } finally {
        this.kafkaTesting = false;
      }
    },

    // Kafka 상태 조회
    async getKafkaStatus() {
      try {
        this.kafkaStatusLoading = true;
        this.kafkaStatus = null;
        
        const response = await axios.get(`${API_BASE_URL}/kafka/status`);
        this.kafkaStatus = response.data;
        
        console.log('Kafka 상태 조회 완료:', response.data);
      } catch (error) {
        console.error('Kafka 상태 조회 실패:', error);
        alert('Kafka 상태 조회에 실패했습니다.');
      } finally {
        this.kafkaStatusLoading = false;
      }
    },

    // Kafka 로그 조회
    async getKafkaLogs() {
      try {
        this.kafkaLogsLoading = true;
        this.kafkaLogs = [];
        
        const response = await axios.get(`${API_BASE_URL}/logs/kafka`);
        this.kafkaLogs = response.data;
        
        console.log('Kafka 로그 조회 완료:', response.data);
      } catch (error) {
        console.error('Kafka 로그 조회 실패:', error);
        alert('Kafka 로그 조회에 실패했습니다.');
      } finally {
        this.kafkaLogsLoading = false;
      }
    },

    // 테스트 이름을 한글로 변환
    getTestName(testName) {
      const testNames = {
        'producer': 'Producer 연결',
        'consumer': 'Consumer 연결',
        'topic_creation': '토픽 생성',
        'message_flow': '메시지 흐름'
      };
      return testNames[testName] || testName;
    },

    // 단순 테스트 이름을 한글로 변환
    getSimpleTestName(testName) {
      const testNames = {
        'basic_connection': '기본 연결',
        'producer_creation': 'Producer 생성',
        'consumer_creation': 'Consumer 생성'
      };
      return testNames[testName] || testName;
    }
  }
}
</script>

<style>
.container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.section {
  margin-bottom: 30px;
  padding: 20px;
  border: 1px solid #ddd;
  border-radius: 5px;
}

input {
  margin-right: 10px;
  padding: 5px;
  width: 300px;
}

button {
  margin-right: 10px;
  padding: 5px 10px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

button:hover {
  background-color: #0056b3;
}

.sample-btn {
  background-color: #28a745;
}

.sample-btn:hover {
  background-color: #218838;
}

ul {
  list-style-type: none;
  padding: 0;
}

li {
  margin: 5px 0;
  padding: 5px;
  border-bottom: 1px solid #eee;
}

.pagination {
  text-align: center;
  margin-top: 10px;
}

.pagination button {
  padding: 5px 10px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

.pagination button:hover {
  background-color: #0056b3;
}

.pagination button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.loading-spinner {
  text-align: center;
  margin-top: 20px;
  font-size: 16px;
  color: #555;
}

.user-info {
  text-align: right;
  padding: 10px;
  margin-bottom: 20px;
}

.search-section {
  margin: 10px 0;
}

.search-section input {
  width: 200px;
  margin-right: 10px;
}

.register-btn {
  background-color: #6c757d;
}

.register-btn:hover {
  background-color: #5a6268;
}

.search-results {
  margin-top: 20px;
}

.search-results table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}

.search-results th,
.search-results td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

.search-results th {
  background-color: #f8f9fa;
  font-weight: bold;
}

.search-results tr:hover {
  background-color: #f5f5f5;
}

.view-all-btn {
  background-color: #6c757d;
}

.view-all-btn:hover {
  background-color: #5a6268;
}

.debug-info {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 5px;
  padding: 15px;
  margin: 15px 0;
  font-size: 14px;
}

.debug-info h4 {
  margin-top: 0;
  color: #495057;
}

.debug-info p {
  margin: 5px 0;
  color: #6c757d;
}

.debug-info strong {
  color: #495057;
}

/* Kafka 관련 스타일 */
.kafka-controls {
  margin-bottom: 20px;
}

.kafka-simple-btn {
  background-color: #28a745;
}

.kafka-simple-btn:hover {
  background-color: #218838;
}

.kafka-test-btn {
  background-color: #17a2b8;
}

.kafka-test-btn:hover {
  background-color: #138496;
}

.kafka-status-btn {
  background-color: #6f42c1;
}

.kafka-status-btn:hover {
  background-color: #5a32a3;
}

.kafka-logs-btn {
  background-color: #fd7e14;
}

.kafka-logs-btn:hover {
  background-color: #e8690b;
}

.kafka-test-result {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 5px;
  padding: 20px;
  margin: 20px 0;
}

.test-status {
  margin-bottom: 15px;
  padding: 10px;
  border-radius: 5px;
}

.test-status.success {
  background-color: #d4edda;
  border: 1px solid #c3e6cb;
  color: #155724;
}

.test-status.partial_success {
  background-color: #fff3cd;
  border: 1px solid #ffeaa7;
  color: #856404;
}

.test-status.error {
  background-color: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
}

.test-details {
  margin: 20px 0;
}

.test-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  margin: 5px 0;
  background-color: white;
  border-radius: 3px;
  border: 1px solid #dee2e6;
}

.test-name {
  font-weight: bold;
  color: #495057;
}

.test-status {
  display: flex;
  align-items: center;
  gap: 5px;
}

.test-status .status-success {
  color: #28a745;
}

.test-status .status-error {
  color: #dc3545;
}

.test-timestamp {
  text-align: right;
  color: #6c757d;
  font-style: italic;
}

.kafka-status {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 5px;
  padding: 20px;
  margin: 20px 0;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin: 20px 0;
}

.status-item {
  background-color: white;
  padding: 15px;
  border-radius: 5px;
  border: 1px solid #dee2e6;
}

.broker-table {
  width: 100%;
  border-collapse: collapse;
  margin: 15px 0;
}

.broker-table th,
.broker-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #dee2e6;
}

.broker-table th {
  background-color: #e9ecef;
  font-weight: bold;
}

.topic-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 15px 0;
}

.topic-tag {
  background-color: #007bff;
  color: white;
  padding: 5px 10px;
  border-radius: 15px;
  font-size: 12px;
}

.kafka-logs-table {
  width: 100%;
  border-collapse: collapse;
  margin: 15px 0;
}

.kafka-logs-table th,
.kafka-logs-table td {
  padding: 8px;
  text-align: left;
  border-bottom: 1px solid #dee2e6;
  font-size: 14px;
}

.kafka-logs-table th {
  background-color: #e9ecef;
  font-weight: bold;
}

.log-row:hover {
  background-color: #f5f5f5;
}

.status-badge {
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: bold;
  text-transform: uppercase;
}

.status-success {
  background-color: #d4edda;
  color: #155724;
}

.status-error {
  background-color: #f8d7da;
  color: #721c24;
}

/* 반응형 디자인 */
@media (max-width: 768px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
  
  .kafka-controls button {
    display: block;
    width: 100%;
    margin-bottom: 10px;
  }
  
  .test-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style> 