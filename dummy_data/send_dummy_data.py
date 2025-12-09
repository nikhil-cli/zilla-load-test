import time
import random
import datetime
from kafka import KafkaProducer

BROKERS = [
    "kafka1:9092",
    "kafka2:9092",
    "kafka3:9092"
]
TOPIC = "ohlc_test"  # Updated to the new topic for load testing
KEYS = [f"test_{i}" for i in range(1, 501)]  # Generate keys test_1 to test_500

def get_minute_timestamp():
    now = datetime.datetime.utcnow()
    minute = now.replace(second=0, microsecond=0)
    return int(minute.timestamp() * 1000)

def generate_ohlc_data():
    open_price = round(random.uniform(0.5, 1.5), 4)
    high_price = round(open_price + random.uniform(0, 0.1), 4)
    low_price = round(open_price - random.uniform(0, 0.1), 4)
    close_price = round(random.uniform(low_price, high_price), 4)
    buy = random.randint(0, 100)
    sell = random.randint(0, 100)
    total_volume = buy + sell
    return open_price, high_price, low_price, close_price, buy, sell, total_volume

def build_csv_value(ts, open_, high, low, close, buy, sell, total_volume):
    return f"{ts},{open_},{high},{low},{close},{buy},{sell},{total_volume},"

def main():
    producer = KafkaProducer(
        bootstrap_servers=BROKERS,
        value_serializer=lambda v: v.encode("utf-8"),
        key_serializer=lambda k: k
    )
    print("Starting dummy data producer. Press Ctrl+C to stop.")
    try:
        while True:
            batch = []
            ts = get_minute_timestamp()
            for key in KEYS:
                open_, high, low, close, buy, sell, total_volume = generate_ohlc_data()
                value = build_csv_value(ts, open_, high, low, close, buy, sell, total_volume)
                batch.append((key.encode(), value))
            
            # Send all messages in the batch
            for key, value in batch:
                producer.send(TOPIC, key=key, value=value)
            
            print(f"Sent batch of {len(batch)} messages to topic {TOPIC}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        producer.close()

if __name__ == "__main__":
    main()