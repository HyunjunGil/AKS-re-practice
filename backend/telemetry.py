import os
import logging
from opentelemetry import trace
from opentelemetry import metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.mysql import MySQLInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.kafka import KafkaInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelemetryManager:
    """OpenTelemetry 설정 및 관리를 위한 클래스"""
    
    def __init__(self):
        self.tracer = None
        self.meter = None
        self.logger_provider = None
        self.trace_provider = None
        self.meter_provider = None
        
    def setup_telemetry(self, app=None):
        """OpenTelemetry 설정을 초기화합니다."""
        try:
            # 리소스 설정
            service_name = os.getenv('BACKEND_SERVICE_NAME', 'backend')  # 세션을 위한 시크릿 키
            resource = Resource.create({
                "service.name": service_name,
                "service.version": "1.0.0",
                "deployment.environment": "development"
            })
            
            # Trace Provider 설정
            self.trace_provider = TracerProvider(resource=resource)
            
            # Span Exporter 설정
            exporters = self._setup_span_exporters()
            for exporter in exporters:
                self.trace_provider.add_span_processor(BatchSpanProcessor(exporter))
            
            # Trace 설정
            trace.set_tracer_provider(self.trace_provider)
            self.tracer = trace.get_tracer(__name__)
            
            # Meter Provider 설정
            metric_readers = self._setup_metric_readers()
            self.meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
            
            # Metrics 설정
            metrics.set_meter_provider(self.meter_provider)
            self.meter = metrics.get_meter(__name__)
            
            # Logger Provider 설정
            self.logger_provider = LoggerProvider(resource=resource)
            
            # Log Exporter 설정
            log_exporters = self._setup_log_exporters()
            for exporter in log_exporters:
                self.logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
            
            # Logger 설정
            set_logger_provider(self.logger_provider)
            
            # LoggingHandler 설정으로 Python 로깅과 OpenTelemetry 로깅 연결
            handler = LoggingHandler(level=logging.NOTSET, logger_provider=self.logger_provider)
            logging.getLogger().addHandler(handler)
            
            # Flask 앱이 제공된 경우 자동 계측
            if app:
                self._instrument_flask(app)
            
            # 데이터베이스 및 Redis 자동 계측
            self._instrument_databases()
            
            logger.info("✅ OpenTelemetry 설정이 완료되었습니다.")
            
        except Exception as e:
            logger.error(f"❌ OpenTelemetry 설정 오류: {str(e)}")
    
    def _setup_span_exporters(self):
        """Span Exporter들을 설정합니다."""
        exporters = []
        
        # Tempo OTLP Exporter (LGTM 스택)
        tempo_endpoint = os.getenv("TEMPO_ENDPOINT")
        if tempo_endpoint:
            try:
                tempo_exporter = OTLPSpanExporter(endpoint=tempo_endpoint)
                exporters.append(tempo_exporter)
                logger.info(f"Tempo Exporter 설정됨: {tempo_endpoint}")
            except Exception as e:
                logger.error(f"Tempo Exporter 설정 실패: {str(e)}")
        
        return exporters
    
    def _setup_metric_readers(self):
        """Metric Reader들을 설정합니다."""
        readers = []
        
        # OTLP HTTP Metric Exporter
        otlp_endpoint = os.getenv("OTLP_ENDPOINT")
        if otlp_endpoint:
            try:
                otlp_metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint + "/v1/metrics")
                readers.append(PeriodicExportingMetricReader(otlp_metric_exporter))
                logger.info(f"OTLP Metric Exporter 설정됨: {otlp_endpoint}/v1/metrics")
            except Exception as e:
                logger.error(f"OTLP Metric Exporter 설정 실패: {str(e)}")
        
        return readers
    
    def _setup_log_exporters(self):
        """Log Exporter들을 설정합니다."""
        exporters = []
        
        # OTLP Log Exporter (LGTM 스택)
        otlp_endpoint = os.getenv("OTLP_ENDPOINT")
        if otlp_endpoint:
            try:
                # OTLP HTTP Log Exporter를 사용
                from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
                log_exporter = OTLPLogExporter(endpoint=f"{otlp_endpoint}/v1/logs")
                exporters.append(log_exporter)
                logger.info(f"OTLP Log Exporter 설정됨: {otlp_endpoint}/v1/logs")
            except Exception as e:
                logger.error(f"OTLP Log Exporter 설정 실패: {str(e)}")
                # 실패 시 Console Exporter 사용
                exporters.append(ConsoleLogExporter())
                logger.info("Console Log Exporter로 대체됨")
        else:
            # 기본적으로 Console Exporter 사용
            exporters.append(ConsoleLogExporter())
            logger.info("Console Log Exporter 설정됨")
        
        return exporters
    
    def _instrument_flask(self, app):
        """Flask 앱에 자동 계측을 적용합니다."""
        try:
            FlaskInstrumentor().instrument_app(app)
            logger.info("Flask 자동 계측이 적용되었습니다.")
        except Exception as e:
            logger.error(f"Flask 계측 설정 실패: {str(e)}")
    
    def _instrument_databases(self):
        """데이터베이스 및 Redis에 자동 계측을 적용합니다."""
        try:
            # MySQL 계측
            MySQLInstrumentor().instrument()
            logger.info("MySQL 자동 계측이 적용되었습니다.")
        except Exception as e:
            logger.error(f"MySQL 계측 설정 실패: {str(e)}")
        
        try:
            # Redis 계측
            RedisInstrumentor().instrument()
            logger.info("Redis 자동 계측이 적용되었습니다.")
        except Exception as e:
            logger.error(f"Redis 계측 설정 실패: {str(e)}")
        
        try:
            # Kafka 계측
            KafkaInstrumentor().instrument()
            logger.info("Kafka 자동 계측이 적용되었습니다.")
        except Exception as e:
            logger.error(f"Kafka 계측 설정 실패: {str(e)}")
    
    def get_tracer(self):
        """Tracer 인스턴스를 반환합니다."""
        return self.tracer
    
    def get_meter(self):
        """Meter 인스턴스를 반환합니다."""
        return self.meter
    
    def create_span(self, name, attributes=None):
        """새로운 Span을 생성합니다."""
        if self.tracer:
            return self.tracer.start_span(name, attributes=attributes or {})
        return None
    
    def record_metric(self, name, value, attributes=None):
        """메트릭을 기록합니다."""
        if self.meter:
            counter = self.meter.create_counter(name)
            counter.add(value, attributes=attributes or {})
    
    def log_info(self, message, attributes=None):
        """INFO 레벨 로그를 기록합니다."""
        logger.info(f"[LGTM] {message}")
    
    def log_error(self, message, attributes=None):
        """ERROR 레벨 로그를 기록합니다."""
        logger.error(f"[LGTM] {message}")
    
    def log_warn(self, message, attributes=None):
        """WARN 레벨 로그를 기록합니다."""
        logger.warning(f"[LGTM] {message}")
    
    def log_debug(self, message, attributes=None):
        """DEBUG 레벨 로그를 기록합니다."""
        logger.debug(f"[LGTM] {message}")
    
    def shutdown(self):
        """Telemetry 리소스를 정리합니다."""
        try:
            if self.trace_provider:
                self.trace_provider.shutdown()
            if self.meter_provider:
                self.meter_provider.shutdown()
            if self.logger_provider:
                self.logger_provider.shutdown()
            logger.info("OpenTelemetry 리소스가 정리되었습니다.")
        except Exception as e:
            logger.error(f"OpenTelemetry 정리 오류: {str(e)}")

# 전역 Telemetry Manager 인스턴스
telemetry_manager = TelemetryManager()
