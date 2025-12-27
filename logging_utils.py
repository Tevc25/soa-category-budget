import contextvars
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

import pika

correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)

_logger: Optional[logging.Logger] = None
_service_name: Optional[str] = None


def get_correlation_id() -> Optional[str]:
    return correlation_id_var.get()


def _rabbit_config():
    return {
        "host": os.getenv("RABBITMQ_HOST", "localhost"),
        "port": int(os.getenv("RABBITMQ_PORT", "5672")),
        "user": os.getenv("RABBITMQ_USER", "guest"),
        "password": os.getenv("RABBITMQ_PASSWORD", "guest"),
        "exchange": os.getenv("RABBITMQ_EXCHANGE", "logs-exchange"),
        "queue": os.getenv("RABBITMQ_QUEUE", "logs-queue"),
        "routing_key": os.getenv("RABBITMQ_ROUTING_KEY", "logs.route"),
    }


class RabbitMQHandler(logging.Handler):
    def __init__(self, service_name: str):
        super().__init__()
        cfg = _rabbit_config()
        credentials = pika.PlainCredentials(cfg["user"], cfg["password"])
        self.connection_params = pika.ConnectionParameters(
            host=cfg["host"],
            port=cfg["port"],
            credentials=credentials,
            heartbeat=0,
        )
        self.exchange = cfg["exchange"]
        self.queue = cfg["queue"]
        self.routing_key = cfg["routing_key"]
        self.service_name = service_name
        self.connection = None
        self.channel = None
        self._connect()

    def _connect(self):
        if self.connection and getattr(self.connection, "is_open", False):
            return
        self.connection = pika.BlockingConnection(self.connection_params)
        self.channel = self.connection.channel()
        self.channel.exchange_declare(
            exchange=self.exchange, exchange_type="direct", durable=True
        )
        self.channel.queue_declare(queue=self.queue, durable=True)
        self.channel.queue_bind(
            queue=self.queue, exchange=self.exchange, routing_key=self.routing_key
        )

    def emit(self, record: logging.LogRecord):
        try:
            self._connect()
            correlation_id = getattr(record, "correlation_id", None) or get_correlation_id()
            url = getattr(record, "url", "") or getattr(record, "path", "")
            timestamp = datetime.now(timezone.utc).isoformat()
            payload = {
                "timestamp": timestamp,
                "level": record.levelname,
                "message": record.getMessage(),
                "service": self.service_name,
                "correlation_id": correlation_id,
                "url": url,
                "method": getattr(record, "method", ""),
                "status_code": getattr(record, "status_code", None),
            }
            payload["formatted"] = (
                f"{timestamp} {record.levelname} {url} "
                f"Correlation:{correlation_id or '-'} [{self.service_name}] - {payload['message']}"
            )
            body = json.dumps(payload).encode("utf-8")
            self.channel.basic_publish(
                exchange=self.exchange,
                routing_key=self.routing_key,
                body=body,
                properties=pika.BasicProperties(
                    content_type="application/json", delivery_mode=2
                ),
            )
        except Exception:
            self.handleError(record)


def setup_logging(service_name: str) -> logging.Logger:
    global _logger, _service_name
    if _logger:
        return _logger

    _service_name = service_name
    logger = logging.getLogger(service_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    class SafeFormatter(logging.Formatter):
        def format(self, record):
            if not hasattr(record, "correlation_id") or record.correlation_id is None:
                record.correlation_id = get_correlation_id()
            if not hasattr(record, "url"):
                record.url = getattr(record, "path", "")
            return super().format(record)

    formatter = SafeFormatter(
        "%(asctime)s %(levelname)s %(url)s Correlation:%(correlation_id)s [%(name)s] - %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    try:
        rabbit_handler = RabbitMQHandler(service_name)
        rabbit_handler.setFormatter(formatter)
        logger.addHandler(rabbit_handler)
    except Exception as e:
        logger.error("Failed to initialize RabbitMQ logger: %s", e)

    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    if _logger:
        return _logger
    if _service_name:
        return logging.getLogger(_service_name)
    return logging.getLogger()


def init_request_logging(app, service_name: str):
    """
    Registers middleware for correlation IDs and request logging.
    """
    logger = setup_logging(service_name)

    @app.middleware("http")
    async def correlation_and_logging_middleware(request, call_next):
        correlation_id = request.headers.get("X-Correlation-Id") or str(uuid4())
        correlation_id_var.set(correlation_id)
        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = time.perf_counter() - start
            logger.exception(
                "Request failed",
                extra={
                    "correlation_id": correlation_id,
                    "url": str(request.url),
                    "path": request.url.path,
                    "method": request.method,
                    "status_code": 500,
                    "duration_ms": int(elapsed * 1000),
                },
            )
            raise

        elapsed = time.perf_counter() - start
        response.headers["X-Correlation-Id"] = correlation_id
        logger.info(
            "Request handled in %.2f ms", elapsed * 1000,
            extra={
                "correlation_id": correlation_id,
                "url": str(request.url),
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
            },
        )
        return response

    return logger
