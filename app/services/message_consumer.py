# app/services/message_consumer.py

import json
import logging

def process_message(ch, method, properties, body):
    try:
        message = json.loads(body)
        resume = message.get("resume")
        # status = message.get("status")
        logging.info(f"Received message for resume {resume[:30]}")
        # Process the message as needed for career_docs
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode message: {e}")
    except Exception as e:
        logging.error(f"Error processing message: {e}")
