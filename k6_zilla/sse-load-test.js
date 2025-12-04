import sse from 'k6/x/sse';
import { sleep } from 'k6';
import { Counter, Gauge, Rate, Trend } from 'k6/metrics';

// Custom Metrics
const sseConnectionsSuccessful = new Counter('sse_connections_successful');
const sseConnectionsFailed = new Counter('sse_connections_failed');
const sseConnectionsBroken = new Counter('sse_connections_broken');
const sseConnectionsActive = new Gauge('sse_connections_active');
const sseMessagesReceived = new Counter('sse_messages_received');
const sseConnectionDuration = new Trend('sse_connection_duration_ms');
const sseMessagesPerConnection = new Trend('sse_messages_per_connection');
const sseSuccessRate = new Rate('sse_success_rate');

const BASE_URL = 'https://api.com/events/key/ohlc_1';
//const BASE_URL = 'https://api.com/events/key/ohlc_test';
const MIN_ID = 1;
const MAX_ID = 500;
const STREAM_DURATION_SEC = 120; // 2 minutes of streaming per connection

export const options = {
  insecureSkipTLSVerify: true,
  stages: [
    { duration: '15s', target: 1000 },  // Ramp up to 1000
    { duration: '15s', target: 3000 },  // Ramp up to 3000
    { duration: '15s', target: 5000 },  // Ramp up to 5000
    { duration: '120s', target: 5000 }, // Maintain 5000 for 2 minutes
  ],
  thresholds: {
    'sse_success_rate': ['rate>0.8'], // At least 80% success rate
  },
};

function getRandomEndpoint() {
  const id = Math.floor(Math.random() * (MAX_ID - MIN_ID + 1)) + MIN_ID;
  return `${BASE_URL}/test_${id}`;
}

export default function () {
  const vuId = __VU;
  const startTime = Date.now();
  
  sseConnectionsActive.add(1);

  const endpoint = getRandomEndpoint();
  const params = {
    method: 'GET',
    headers: {
      'Accept': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  };

  // Connection state tracking - shared between callback and main function
  let connectionState = {
    connected: false,
    messagesReceived: 0,
    streamAlive: true,
    connectionError: null,
    streamBroken: false,
    client: null,
  };

  try {
    // Open SSE connection using callback pattern
    sse.open(endpoint, params, (client) => {
      if (!client) {
        connectionState.streamAlive = false;
        connectionState.connectionError = 'Failed to create SSE client';
        return;
      }

      connectionState.client = client;

      // Set up event handlers
      client.on('open', () => {
        connectionState.connected = true;
        console.log(`[VU ${vuId}] Connected to ${endpoint}`);
      });

      client.on('event', (event) => {
        connectionState.messagesReceived++;
        sseMessagesReceived.add(1);
      });

      client.on('error', (err) => {
        connectionState.streamAlive = false;
        connectionState.streamBroken = true;
        connectionState.connectionError = err ? err.error() : 'Unknown error';
        console.error(`[VU ${vuId}] SSE error: ${connectionState.connectionError}`);
      });

      client.on('close', () => {
        connectionState.streamAlive = false;
        if (connectionState.connected) {
          connectionState.streamBroken = true;
          console.log(`[VU ${vuId}] Connection closed unexpectedly`);
        }
      });
    });

    // Wait for connection to establish (with timeout)
    let connectionWaitTime = 0;
    const maxConnectionWait = 10000; // 10 seconds max wait for connection
    while (!connectionState.connected && connectionWaitTime < maxConnectionWait && connectionState.streamAlive) {
      sleep(0.1);
      connectionWaitTime += 100;
    }

    if (!connectionState.connected) {
      throw new Error(`Connection timeout for VU ${vuId} after ${maxConnectionWait}ms`);
    }

    // Stream for the specified duration (2 minutes)
    const endTime = Date.now() + (STREAM_DURATION_SEC * 1000);
    let lastMessageCount = connectionState.messagesReceived;
    let lastMessageCheckTime = Date.now();
    const maxSilenceDuration = 60000; // 60 seconds without new messages = potentially broken

    while (Date.now() < endTime && connectionState.streamAlive) {
      sleep(1);
      
      // Check if we're still receiving messages
      const currentTime = Date.now();
      if (currentTime - lastMessageCheckTime > 5000) { // Check every 5 seconds
        if (connectionState.messagesReceived === lastMessageCount && connectionState.messagesReceived > 0) {
          // No new messages in the last 5 seconds, but we had messages before
          // This might indicate a problem, but don't break immediately
          const silenceDuration = currentTime - lastMessageCheckTime;
          if (silenceDuration > maxSilenceDuration) {
            console.log(`[VU ${vuId}] No messages for ${(silenceDuration/1000).toFixed(0)}s, marking as potentially broken`);
            connectionState.streamBroken = true;
            break;
          }
        }
        lastMessageCount = connectionState.messagesReceived;
        lastMessageCheckTime = currentTime;
      }
      
      // If stream is broken, exit early
      if (connectionState.streamBroken) {
        break;
      }
    }

    // Close the connection gracefully
    if (connectionState.client) {
      try {
        connectionState.client.close();
      } catch (closeErr) {
        // Ignore close errors
      }
    }

    // Record metrics based on connection outcome
    const connectionDuration = Date.now() - startTime;
    sseConnectionDuration.add(connectionDuration);

    if (connectionState.connected && connectionState.messagesReceived > 0 && !connectionState.streamBroken) {
      // Successful connection that received messages and stayed alive
      sseConnectionsSuccessful.add(1);
      sseSuccessRate.add(1);
      sseMessagesPerConnection.add(connectionState.messagesReceived);
      console.log(`[VU ${vuId}] ✓ Success: ${connectionState.messagesReceived} messages in ${(connectionDuration/1000).toFixed(1)}s`);
    } else if (connectionState.connected && connectionState.streamBroken) {
      // Connection was established but broke during streaming
      sseConnectionsBroken.add(1);
      sseConnectionsFailed.add(1);
      sseSuccessRate.add(0);
      console.log(`[VU ${vuId}] ⚠ Broken: Received ${connectionState.messagesReceived} messages before breaking`);
    } else if (connectionState.connected && connectionState.messagesReceived === 0) {
      // Connected but no messages received
      sseConnectionsFailed.add(1);
      sseSuccessRate.add(0);
      console.log(`[VU ${vuId}] ✗ Failed: Connected but no messages received`);
    } else {
      // Failed to connect
      sseConnectionsFailed.add(1);
      sseSuccessRate.add(0);
      console.log(`[VU ${vuId}] ✗ Failed: Never connected - ${connectionState.connectionError || 'unknown error'}`);
    }

  } catch (err) {
    // Connection failed or error occurred
    sseConnectionsFailed.add(1);
    sseSuccessRate.add(0);
    const connectionDuration = Date.now() - startTime;
    sseConnectionDuration.add(connectionDuration);
    console.error(`[VU ${vuId}] ✗ Exception: ${err.message}`);
  } finally {
    sseConnectionsActive.add(-1);
  }
}

export function handleSummary(data) {
  const successful = data.metrics.sse_connections_successful?.values?.count || 0;
  const failed = data.metrics.sse_connections_failed?.values?.count || 0;
  const broken = data.metrics.sse_connections_broken?.values?.count || 0;
  const totalConnections = successful + failed;
  const successRate = totalConnections > 0 ? (successful / totalConnections) * 100 : 0;
  const totalMessages = data.metrics.sse_messages_received?.values?.count || 0;
  const avgMessagesPerConnection = successful > 0 ? (totalMessages / successful).toFixed(2) : 0;
  
  const avgConnectionDuration = data.metrics.sse_connection_duration_ms?.values?.avg || 0;
  const p95ConnectionDuration = data.metrics.sse_connection_duration_ms?.values?.['p(95)'] || 0;
  const p99ConnectionDuration = data.metrics.sse_connection_duration_ms?.values?.['p(99)'] || 0;

  return {
    stdout: `\n` +
            `╔════════════════════════════════════════════════════════════╗\n` +
            `║              SSE Load Test Summary                         ║\n` +
            `╠════════════════════════════════════════════════════════════╣\n` +
            `║ Connection Statistics:                                     ║\n` +
            `║   ✓ Successful connections:  ${String(successful).padStart(10)} ║\n` +
            `║   ✗ Failed connections:      ${String(failed).padStart(10)} ║\n` +
            `║   ⚠ Broken connections:      ${String(broken).padStart(10)} ║\n` +
            `║   ──────────────────────────────────────────────────────── ║\n` +
            `║   Total connections:         ${String(totalConnections).padStart(10)} ║\n` +
            `║   Success rate:              ${String(successRate.toFixed(2) + '%').padStart(10)} ║\n` +
            `╠════════════════════════════════════════════════════════════╣\n` +
            `║ Message Statistics:                                         ║\n` +
            `║   Total messages received:   ${String(totalMessages).padStart(10)} ║\n` +
            `║   Avg messages/connection:   ${String(avgMessagesPerConnection).padStart(10)} ║\n` +
            `╠════════════════════════════════════════════════════════════╣\n` +
            `║ Connection Duration (ms):                                  ║\n` +
            `║   Average:                   ${String(Math.round(avgConnectionDuration)).padStart(10)} ║\n` +
            `║   p95:                       ${String(Math.round(p95ConnectionDuration)).padStart(10)} ║\n` +
            `║   p99:                       ${String(Math.round(p99ConnectionDuration)).padStart(10)} ║\n` +
            `╚════════════════════════════════════════════════════════════╝\n`,
  };
}

