import httpx
import time

print("Testing httpx SSE stream...")
start = time.time()

client = httpx.Client(http2=True, verify=False, timeout=None)

with client.stream(
    'GET',
    'https://localhost:7114/events/ohlc_test/test_1',
    headers={'Accept': 'text/event-stream'}
) as response:
    print(f"Connected: {response.status_code} {response.http_version}")
    
    count = 0
    for line in response.iter_lines():
        print(f"{count}: {repr(line)}")
        count += 1
        
        if count >= 20:
            print("Got 20 lines, stopping...")
            break
        
        if time.time() - start > 5:
            print("Timeout after 5s")
            break

print(f"Done in {time.time()-start:.1f}s, received {count} lines")
