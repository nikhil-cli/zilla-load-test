# Dummy Kafka Data Producer

This project generates and sends dummy OHLC (Open, High, Low, Close) data to your Kafka brokers every 500ms.

## Setup

1. **Create and activate a virtual environment named `zilla`:**

   On Windows:
   ```
   python -m venv zilla
   zilla\Scripts\activate
   ```

   On Linux/Mac:
   ```
   python3 -m venv zilla
   source zilla/bin/activate
   ```

2. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

## Usage

1. **Configure your Kafka topic:**
   - By default, the script uses `test-topic`. Change the `TOPIC` variable in `send_dummy_data.py` to your desired topic name.

2. **Run the producer:**
   ```
   python send_dummy_data.py
   ```

   The script will send a message every 500ms with:
   - Key: `test`
   - Value: `timestamp,open,high,low,close,buy,sell,totalVolume,`
     - `timestamp` is the current minute in Unix ms (UTC).
     - OHLC, buy, sell, and totalVolume are randomly generated.

3. **Stop the producer:**
   - Press `Ctrl+C` to stop.

## Example Message

```
test: 1763769060000,0.6448,0.6448,0.6448,0.6448,0,0,0,
```

Where:
- `1763769060000` = timestamp (current minute, UTC, in ms)
- `0.6448` = open, high, low, close
- `0` = buy
- `0` = sell
- `0` = totalVolume

## Notes

- Ensure your Kafka brokers are reachable from your machine.
- You can adjust the random value ranges in `send_dummy_data.py` as needed.