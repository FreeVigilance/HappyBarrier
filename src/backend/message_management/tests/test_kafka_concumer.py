from unittest.mock import patch

from message_management.constants import KAFKA_SERVERS
from message_management.kafka_consumer import create_consumer


@patch("message_management.kafka_consumer.confluent_kafka.Consumer")
def test_create_consumer(mock_kafka_consumer):
    topic = "sms_configuration"

    consumer_instance = mock_kafka_consumer.return_value
    result = create_consumer(topic)

    mock_kafka_consumer.assert_called_once_with(
        {
            "bootstrap.servers": KAFKA_SERVERS,
            "group.id": f"sms_handler_{topic}_group",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )

    assert result == consumer_instance
