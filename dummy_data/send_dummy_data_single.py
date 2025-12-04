import time
import random
import datetime
from kafka import KafkaProducer

BROKERS = [
    "jpr-cp-broker1.corp.hertshtengroup.com:9092",
    "jpr-cp-broker2.corp.hertshtengroup.com:9092",
    "jpr-cp-broker3.corp.hertshtengroup.com:9092"
]
TOPIC = "ohlc_1"  # Changed to your requested topic name
KEY = b"test"

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
            ts = get_minute_timestamp()
            open_, high, low, close, buy, sell, total_volume = generate_ohlc_data()
            value = build_csv_value(ts, open_, high, low, close, buy, sell, total_volume)
            future = producer.send(TOPIC, key=KEY, value=value)
            result = future.get(timeout=10)
            print(f"Sent: key={KEY.decode()} value={value} to partition={result.partition} offset={result.offset}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("Stopped by user.")
    finally:
        producer.close()

if __name__ == "__main__":
    main()