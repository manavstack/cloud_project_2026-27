import boto3
import json
import logging

logger = logging.getLogger(__name__)

class AWSClient:
    def __init__(self, region_name="ap-south-1"):
        # The edge node uses standard boto3 credentials (configured via AWS CLI or IAM roles)
        self.iot_client = boto3.client('iot-data', region_name=region_name)
        
    def send_telemetry_to_cloud(self, topic: str, data: dict):
        """
        Sends prediction and telemetry data to AWS IoT Core MQTT topic.
        """
        try:
            response = self.iot_client.publish(
                topic=topic,
                qos=1,
                payload=json.dumps(data)
            )
            logger.info(f"Successfully published to {topic}")
            return response
        except Exception as e:
            logger.error(f"Failed to publish to AWS: {e}")
            raise
