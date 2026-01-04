"""
Professional HTTP/2 SSE Load Test using Locust with httpx
Tests HTTP/2 multiplexing with 500 unique virtual users
Each user maintains a persistent SSE connection to a unique endpoint
"""
from locust import User, task, between, events
import time
import httpx
import gevent

# =============================================================================
# CONFIGURATION - Modify these settings
# =============================================================================
BASE_URL = "https://localhost:7114"
SSE_ENDPOINT_PATTERN = "/events/ohlc_test/test_{user_id}"
NUM_ENDPOINTS = 500  # Number of unique endpoints (test_1 to test_500)
STREAM_DURATION = 30  # How long each user stays connected (seconds)
MAX_EVENTS_PER_USER = 100  # Limit events per connection for load testing
REPORT_INTERVAL = 10  # Report stats every N events
# =============================================================================


class SSEHTTP2User(User):
    """
    Virtual user for HTTP/2 SSE load testing using httpx
    Each user gets a unique endpoint to test multiplexing
    """
    wait_time = between(1, 3)  # Wait between reconnections
    
    def __init__(self, environment):
        super().__init__(environment)
        # Each VU gets an ID from 1 to NUM_ENDPOINTS
        self.user_id = (id(self) % NUM_ENDPOINTS) + 1
        self.events_received = 0
        self.connection_errors = 0
        self.first_connection = True
        
        # Create httpx client with HTTP/2 support
        self.client = httpx.Client(
            http2=True,
            verify=False,
            timeout=httpx.Timeout(STREAM_DURATION + 10, read=None)
        )
        
        print(f"🚀 User {self.user_id} initialized")
    
    @task
    def connect_sse_stream(self):
        """
        Main task: Connect to SSE endpoint and consume events
        Tests HTTP/2 multiplexing by maintaining long-lived connection
        """
        endpoint = f"{BASE_URL}{SSE_ENDPOINT_PATTERN.format(user_id=self.user_id)}"
        
        headers = {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
        }
        
        start_time = time.time()
        request_meta = {
            "request_type": "GET",
            "name": f"SSE /events/ohlc_test/test_{{id}}",
            "start_time": start_time,
            "response_length": 0,
            "response": None,
            "context": {},
            "exception": None,
        }
        
        try:
            # Stream SSE with httpx
            with self.client.stream(
                'GET',
                endpoint,
                headers=headers,
            ) as response:
                
                connect_time = time.time() - start_time
                
                if response.status_code != 200:
                    request_meta["response_time"] = (time.time() - start_time) * 1000
                    request_meta["exception"] = Exception(f"HTTP {response.status_code}")
                    self.environment.events.request.fire(**request_meta)
                    self.connection_errors += 1
                    print(f"❌ User {self.user_id}: HTTP {response.status_code}")
                    return
                
                # Log first successful connection with HTTP version
                if self.first_connection:
                    http_version = response.http_version
                    print(f"✓ User {self.user_id}: Connected with {http_version} in {connect_time:.3f}s")
                    self.first_connection = False
                
                # Process SSE stream
                events_count = self._process_sse_stream(response, start_time)
                
                request_meta["response_time"] = (time.time() - start_time) * 1000
                request_meta["response_length"] = events_count
                self.environment.events.request.fire(**request_meta)
                
                if events_count > 0:
                    print(f"✅ User {self.user_id}: Completed {events_count} events in {time.time()-start_time:.1f}s")
                    
        except Exception as e:
            request_meta["response_time"] = (time.time() - start_time) * 1000
            request_meta["exception"] = e
            self.environment.events.request.fire(**request_meta)
            
            error_msg = f"{type(e).__name__}: {str(e)[:50]}"
            print(f"❌ User {self.user_id}: {error_msg}")
            self.connection_errors += 1
    
    def _process_sse_stream(self, response, start_time):
        """
        Process SSE stream with manual parsing
        Returns number of events processed
        """
        event_lines = []
        events_count = 0
        last_report = 0
        
        try:
            # Iterate over lines from the stream
            for line in response.iter_lines():
                # Check if we've exceeded max duration
                elapsed = time.time() - start_time
                if elapsed > STREAM_DURATION:
                    break
                
                # Check if we've hit max events
                if events_count >= MAX_EVENTS_PER_USER:
                    break
                
                # Empty line signals end of event
                if line == '':
                    if event_lines:
                        # Parse and count the event
                        if self._parse_sse_event(event_lines):
                            self.events_received += 1
                            events_count += 1
                            
                            # Report progress every N events
                            if events_count - last_report >= REPORT_INTERVAL:
                                print(f"📊 User {self.user_id}: {events_count} events ({elapsed:.1f}s)")
                                last_report = events_count
                        
                        event_lines = []
                else:
                    event_lines.append(line)
                                
        except Exception as e:
            print(f"❌ User {self.user_id} stream error: {str(e)[:50]}")
        
        return events_count
    
    def _parse_sse_event(self, event_lines):
        """
        Parse SSE event from list of lines
        Returns True if valid event with data
        """
        event = {
            'event': None,
            'data': '',
            'id': None,
            'retry': None
        }
        
        for line in event_lines:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith(':'):
                continue
            
            # Parse field: value
            if ':' in line:
                field, value = line.split(':', 1)
                field = field.strip()
                value = value.strip()
                
                if field == 'data':
                    # Data can span multiple lines
                    if event['data']:
                        event['data'] += '\n' + value
                    else:
                        event['data'] = value
                elif field in ['event', 'id', 'retry']:
                    event[field] = value
        
        # Valid event must have data
        return bool(event['data'])
    
    def on_stop(self):
        """Report final statistics when user stops"""
        print(f"\n{'='*60}")
        print(f"User {self.user_id} Final Stats:")
        print(f"  Total events:         {self.events_received}")
        print(f"  Connection errors:    {self.connection_errors}")
        print(f"{'='*60}\n")


# =============================================================================
# Event Listeners - Test lifecycle hooks
# =============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the load test starts"""
    print(f"\n{'='*70}")
    print(f"HTTP/2 SSE Load Test - Starting")
    print(f"{'='*70}")
    print(f"Target:           {BASE_URL}")
    print(f"Endpoint Pattern: {SSE_ENDPOINT_PATTERN}")
    print(f"Unique Users:     {NUM_ENDPOINTS}")
    print(f"Stream Duration:  {STREAM_DURATION}s per user")
    print(f"Max Events:       {MAX_EVENTS_PER_USER} per user")
    print(f"{'='*70}\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the load test stops - print comprehensive statistics"""
    print(f"\n{'='*70}")
    print(f"HTTP/2 SSE Load Test - Complete")
    print(f"{'='*70}\n")
    
    stats = environment.stats
    
    # Overall statistics
    print(f"Overall Statistics:")
    print(f"  Total requests:       {stats.total.num_requests:>10}")
    print(f"  Failed requests:      {stats.total.num_failures:>10}")
    print(f"  Success rate:         {((stats.total.num_requests - stats.total.num_failures) / stats.total.num_requests * 100) if stats.total.num_requests > 0 else 0:>9.2f}%")
    print(f"  Total RPS:            {stats.total.total_rps:>10.2f}")
    
    # Response time statistics
    print(f"\nResponse Time Statistics (ms):")
    print(f"  Average:              {stats.total.avg_response_time:>10.2f}")
    print(f"  Min:                  {stats.total.min_response_time:>10}")
    print(f"  Max:                  {stats.total.max_response_time:>10}")
    print(f"  Median:               {stats.total.median_response_time:>10}")
    print(f"  p95:                  {stats.total.get_response_time_percentile(0.95):>10.2f}")
    print(f"  p99:                  {stats.total.get_response_time_percentile(0.99):>10.2f}")
    
    # Data transfer
    print(f"\nData Transfer:")
    print(f"  Sent:                 {stats.total.total_content_length / 1024 / 1024:>10.2f} MB")
    
    # Breakdown by endpoint if multiple exist
    print(f"\nEndpoint Breakdown:")
    for name, stat in stats.entries.items():
        if stat.num_requests > 0:
            print(f"  {name}:")
            print(f"    Requests:           {stat.num_requests:>10}")
            print(f"    Failures:           {stat.num_failures:>10}")
            print(f"    Avg time:           {stat.avg_response_time:>10.2f}ms")
    
    print(f"\n{'='*70}\n")
