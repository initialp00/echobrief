"""Kafka producer used by the API (brief creation) and worker (stage handoff)."""
import json
import logging
from typing import Any

from kafka import KafkaProducer
from kafka.errors import KafkaError

from app.config import settings

logger = logging.getLogger("echobrief.producer")

_producer: KafkaProducer | None = None


def get_producer() -> KafkaProducer:
    """Lazily create a singleton KafkaProducer."""
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            retries=5,
            linger_ms=10,
        )
    return _producer


def publish(topic: str, payload: dict[str, Any], key: str | None = None) -> None:
    """Publish a message and block briefly to confirm delivery."""
    producer = get_producer()
    future = producer.send(topic, value=payload, key=key)
    # Block so callers get a real ack (surfaces broker errors immediately).
    future.get(timeout=10)
    logger.info("Published to %s key=%s", topic, key)


def check_kafka() -> bool:
    """Lightweight connectivity check for the health endpoint.

    We rely on a metadata fetch (partitions_for) rather than
    bootstrap_connected(): kafka-python closes the initial bootstrap
    connection once it has real broker metadata, so bootstrap_connected()
    can report False even while the cluster is fully reachable.
    """
    try:
        producer = get_producer()
        # A non-None result means we reached the cluster and got metadata.
        # (Auto-create is enabled, so the topic resolves on first request.)
        parts = producer.partitions_for(settings.kafka_topic_transcribe)
        if parts is not None:
            return True
        return producer.bootstrap_connected()
    except KafkaError as exc:  # noqa: BLE001
        logger.warning("Kafka health check failed: %s", exc)
        return False


def close_producer() -> None:
    global _producer
    if _producer is not None:
        _producer.flush()
        _producer.close()
        _producer = None
