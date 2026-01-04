# HTTP/2 SSE Load Test with Locust

Professional load testing for HTTP/2 Server-Sent Events using Locust.

## Features

- ✅ **HTTP/2 Support**: Tests HTTP/2 multiplexing
- ✅ **500 Unique Users**: Each user connects to unique endpoint (test_1 to test_500)
- ✅ **Persistent Connections**: Long-lived SSE streams
- ✅ **Manual SSE Parsing**: No external dependencies for SSE parsing
- ✅ **Comprehensive Metrics**: Response times, RPS, success rates
- ✅ **Configurable**: All settings at top of locustfile.py

## Setup

### 1. Create Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

## Configuration

Edit `locustfile.py` to modify settings at the top:

```python
BASE_URL = "https://localhost:7114"
SSE_ENDPOINT_PATTERN = "/events/ohlc_test/test_{user_id}"
NUM_ENDPOINTS = 500
STREAM_DURATION = 30  # seconds
MAX_EVENTS_PER_USER = 100
```

## Running the Test

### Headless Mode (Command Line)

**500 users, spawn 50/sec, run for 2 minutes:**

```powershell
python -m locust -f locustfile.py --host=https://localhost:7114 --headless --users 500 --spawn-rate 50 --run-time 2m
```

**100 users, spawn 10/sec, run for 1 minute:**

```powershell
python -m locust -f locustfile.py --host=https://localhost:7114 --headless --users 100 --spawn-rate 10 --run-time 1m
```

**100 users for quick test:**

```powershell
python -m locust -f locustfile.py --host=https://localhost:7114 --headless --users 100 --spawn-rate 10 --run-time 30s
```

### Web UI Mode

Start Locust web interface:

```powershell
python -m locust -f locustfile.py --host=https://localhost:7114
```

Then open browser to: http://localhost:8089

Configure users, spawn rate, and duration in the web UI.

## Command Line Options

- `--users N` or `-u N`: Number of concurrent users
- `--spawn-rate R` or `-r R`: Users to spawn per second
- `--run-time T` or `-t T`: Test duration (e.g., 1h, 30m, 60s)
- `--headless`: Run without web UI
- `--host URL`: Target server URL

## Example Output

```
======================================================================
HTTP/2 SSE Load Test - Starting
======================================================================
Target:           https://localhost:7114
Endpoint Pattern: /events/ohlc_test/test_{user_id}
Unique Users:     500
Stream Duration:  30s per user
Max Events:       100 per user
======================================================================

✓ User 1: Connected with HTTP/2.0 in 0.045s
✓ User 2: Connected with HTTP/2.0 in 0.052s
📊 User 1: 10 events (3.2s)
📊 User 2: 10 events (3.5s)
...

======================================================================
HTTP/2 SSE Load Test - Complete
======================================================================

Overall Statistics:
  Total requests:              500
  Failed requests:               0
  Success rate:             100.00%
  Total RPS:                  16.67

Response Time Statistics (ms):
  Average:                  120.50
  Min:                           45
  Max:                         4523
  Median:                      98.0
  p95:                        250.00
  p99:                        450.00
```

## Testing HTTP/2 Multiplexing

Each virtual user maintains a unique SSE connection to endpoints test_1 through test_500. This tests:

1. **Connection Multiplexing**: Multiple streams over single TCP connection
2. **Concurrent Streams**: 500 parallel SSE streams
3. **Stream Management**: Long-lived connections with proper cleanup
4. **Performance**: Response times under load

## Troubleshooting

**"locust not found"**
- Use `python -m locust` instead of just `locust`
- Or add Python Scripts to PATH

**SSL Certificate Errors**
- Locust is configured with `verify=False` for self-signed certs
- Check `urllib3.disable_warnings()` is present

**Connection Refused**
- Ensure Zilla server is running: `docker-compose up`
- Check port 7114 is accessible

**Too Many Open Files**
- Reduce `--users` count
- Increase system file descriptor limit

## Advanced Options

### Master-Worker Mode (Distributed Testing)

Start master:
```powershell
python -m locust -f locustfile.py --master
```

Start workers (on same or different machines):
```powershell
python -m locust -f locustfile.py --worker --master-host=localhost
```

### CSV Output

```powershell
python -m locust -f locustfile.py --headless --csv=results --users 500 --spawn-rate 50 --run-time 2m
```

Generates:
- `results_stats.csv`: Request statistics
- `results_failures.csv`: Failure logs
- `results_stats_history.csv`: Time-series data
