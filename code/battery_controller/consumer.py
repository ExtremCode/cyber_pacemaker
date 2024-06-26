# implements Kafka topic consumer functionality

import threading
from confluent_kafka import Consumer, OFFSET_BEGINNING
import json
from producer import proceed_to_deliver
import random

CHARGE_LEVEL = 100


def handle_event(id: str, details: dict):    
    # print(f"[debug] handling event {id}, {details}")
    print(f"[info] handling event {id}, {details['source']}->{details['deliver_to']}: {details['operation']}")
    global CHARGE_LEVEL
    try:
        if details['operation'] == 'check_battery':
            CHARGE_LEVEL = max(CHARGE_LEVEL - random.randint(0, 5), 0)
            details['charge_level'] = CHARGE_LEVEL
            details['deliver_to'] = 'query_processor'
            details['operation'] = 'return_battery_stat'
            proceed_to_deliver(id, details)
    except Exception as e:
        print(f"[error] failed to handle request: {e}")

def consumer_job(args, config):
    # Create Consumer instance
    battery_controller_consumer = Consumer(config)

    # Set up a callback to handle the '--reset' flag.
    def reset_offset(battery_controller_consumer, partitions):
        if args.reset:
            for p in partitions:
                p.offset = OFFSET_BEGINNING
            battery_controller_consumer.assign(partitions)

    # Subscribe to topic
    topic = "battery_controller"
    battery_controller_consumer.subscribe([topic], on_assign=reset_offset)

    # Poll for new messages from Kafka and print them.
    try:
        while True:
            msg = battery_controller_consumer.poll(1.0)
            if msg is None:
                # Initial message consumption may take up to
                # `session.timeout.ms` for the consumer group to
                # rebalance and start consuming
                # print("Waiting...")
                pass
            elif msg.error():
                print(f"[error] {msg.error()}")
            else:
                # Extract the (optional) key and value, and print.
                try:
                    id = msg.key().decode('utf-8')
                    details_str = msg.value().decode('utf-8')
                    # print("[debug] consumed event from topic {topic}: key = {key:12} value = {value:12}".format(
                        # topic=msg.topic(), key=id, value=details_str))
                    handle_event(id, json.loads(details_str))
                except Exception as e:
                    print(
                        f"Malformed event received from topic {topic}: {msg.value()}. {e}")
    except KeyboardInterrupt:
        pass
    finally:
        # Leave group and commit final offsets
        battery_controller_consumer.close()


def start_consumer(args, config):
    threading.Thread(target=lambda: consumer_job(args, config)).start()


if __name__ == '__main__':
    start_consumer(None)
