# Realtime (WebSocket & SSE)

SnackBase provides real-time event broadcasting for data changes via WebSocket and Server-Sent Events (SSE). This enables your applications to react instantly to database changes without polling.

---

## Overview

The realtime system broadcasts events when records are created, updated, or deleted in collections. Clients can subscribe to specific collections and receive push notifications as changes occur.

### Key Features

- **Dual Protocol Support**: WebSocket and Server-Sent Events (SSE)
- **Per-Collection Subscriptions**: Subscribe only to the collections you care about
- **Operation Filtering**: Subscribe to specific operations (create, update, delete)
- **JWT Authentication**: Secure using existing access tokens
- **Heartbeat Messages**: Keep connections alive with 30-second heartbeat
- **Account Isolation**: Events only broadcast within the same account

### Event Format

All realtime events follow this structure:

```json
{
  "type": "posts.create",
  "timestamp": "2026-01-17T12:34:56.789Z",
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title": "New Post",
    "status": "published",
    "created_at": "2026-01-17T12:34:56.789Z"
  }
}
```

- `type`: `{collection}.{operation}` - The event type
- `timestamp`: ISO 8601 timestamp of when the event occurred
- `data`: The full record data after the operation

---

## WebSocket

WebSocket provides full-duplex communication with the server, allowing you to send messages and receive events in real-time.

### Connecting

Connect to the WebSocket endpoint with your JWT access token:

```javascript
const token = "your_jwt_access_token";
const ws = new WebSocket(`ws://localhost:8000/api/v1/realtime/ws?token=${token}`);

ws.onopen = () => {
  console.log("Connected to SnackBase realtime");
};

ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};

ws.onclose = () => {
  console.log("Disconnected from SnackBase realtime");
};
```

### Subscribing to Collections

Send a subscription message to receive events for a collection:

```javascript
ws.send(JSON.stringify({
  action: "subscribe",
  collection: "posts",
  operations: ["create", "update", "delete"]  // Optional: defaults to all
}));
```

The server will respond with a confirmation:

```json
{
  "status": "subscribed",
  "collection": "posts"
}
```

### Receiving Events

Listen for incoming events:

```javascript
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  // Handle heartbeat messages
  if (message.type === "heartbeat") {
    console.log("Heartbeat received at", message.timestamp);
    return;
  }

  // Handle data events
  if (message.type === "posts.create") {
    console.log("New post created:", message.data);
    // Update your UI
  }

  if (message.type === "posts.update") {
    console.log("Post updated:", message.data);
    // Update your UI
  }

  if (message.type === "posts.delete") {
    console.log("Post deleted:", message.data);
    // Remove from your UI
  }
};
```

### Unsubscribing

Stop receiving events for a collection:

```javascript
ws.send(JSON.stringify({
  action: "unsubscribe",
  collection: "posts"
}));
```

### Ping/Pong

The server responds to ping messages with pong:

```javascript
ws.send(JSON.stringify({ action: "ping" }));
// Response: { "type": "pong" }
```

### Connection Limits

- Maximum 100 active subscriptions per WebSocket connection
- Heartbeat sent every 30 seconds
- Connection automatically closed if authentication fails

### Complete WebSocket Example

```javascript
class SnackBaseRealtime {
  constructor(token) {
    this.token = token;
    this.ws = null;
    this.subscriptions = new Set();
    this.handlers = {};
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(`ws://localhost:8000/api/v1/realtime/ws?token=${this.token}`);

      this.ws.onopen = () => {
        console.log("Connected to SnackBase realtime");
        resolve();
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        reject(error);
      };

      this.ws.onclose = () => {
        console.log("Disconnected from SnackBase realtime");
      };

      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);

        if (message.type === "heartbeat" || message.type === "pong") {
          return; // Ignore system messages
        }

        // Call registered handlers
        const [collection, operation] = message.type.split(".");
        const eventType = `${collection}.${operation}`;
        if (this.handlers[eventType]) {
          this.handlers[eventType](message.data);
        }
      };
    });
  }

  subscribe(collection, operations = ["create", "update", "delete"], handler) {
    return new Promise((resolve, reject) => {
      if (this.subscriptions.size >= 100) {
        reject(new Error("Maximum subscriptions reached (100)"));
        return;
      }

      this.ws.send(JSON.stringify({
        action: "subscribe",
        collection,
        operations
      }));

      // Register handler
      operations.forEach(op => {
        this.handlers[`${collection}.${op}`] = handler;
      });

      this.subscriptions.add(collection);
      resolve();
    });
  }

  unsubscribe(collection) {
    this.ws.send(JSON.stringify({
      action: "unsubscribe",
      collection
    }));

    // Remove handlers
    ["create", "update", "delete"].forEach(op => {
      delete this.handlers[`${collection}.${op}`];
    });

    this.subscriptions.delete(collection);
  }

  disconnect() {
    this.ws.close();
  }
}

// Usage
const realtime = new SnackBaseRealtime(token);
await realtime.connect();

await realtime.subscribe("posts", ["create", "update"], (data) => {
  console.log("Post event:", data);
  // Update your UI
});
```

---

## Server-Sent Events (SSE)

SSE provides a simpler, one-way communication channel that's easier to integrate in some environments.

### Connecting

Connect to the SSE endpoint with your JWT token:

```javascript
const token = "your_jwt_access_token";
const eventSource = new EventSource(
  `http://localhost:8000/api/v1/realtime/subscribe?token=${token}&collection=posts`
);

eventSource.onopen = () => {
  console.log("Connected to SnackBase SSE");
};

eventSource.onerror = (error) => {
  console.error("SSE error:", error);
};
```

### Subscribing via Query Parameters

For SSE, subscriptions are specified via query parameters:

```javascript
// Single collection
new EventSource(`/api/v1/realtime/subscribe?token=${token}&collection=posts`);

// Multiple collections
new EventSource(`/api/v1/realtime/subscribe?token=${token}&collection=posts&collection=comments`);
```

### Receiving Events

Listen for message events:

```javascript
eventSource.addEventListener("message", (event) => {
  const message = JSON.parse(event.data);

  if (message.event === "heartbeat") {
    console.log("Heartbeat received");
    return;
  }

  console.log("Event received:", message);
  // Update your UI
});
```

### Disconnecting

Close the SSE connection:

```javascript
eventSource.close();
```

### Complete SSE Example

```javascript
class SnackBaseSSE {
  constructor(token) {
    this.token = token;
    this.eventSource = null;
    this.handlers = {};
  }

  connect(collections) {
    const params = new URLSearchParams({
      token: this.token,
      ...collections.reduce((acc, col) => ({
        ...acc,
        collection: col
      }), {})
    });

    // Build query string with multiple collections
    const url = `http://localhost:8000/api/v1/realtime/subscribe?${collections.map(c => `collection=${encodeURIComponent(c)}`).join("&")}`;

    this.eventSource = new EventSource(url + `&token=${this.token}`);

    this.eventSource.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);

      if (message.event === "heartbeat") {
        return;
      }

      const [collection, operation] = message.type.split(".");
      const eventType = `${collection}.${operation}`;

      if (this.handlers[eventType]) {
        this.handlers[eventType](message.data);
      }
    });

    this.eventSource.onerror = (error) => {
      console.error("SSE error:", error);
    };
  }

  on(eventType, handler) {
    this.handlers[eventType] = handler;
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
    }
  }
}

// Usage
const sse = new SnackBaseSSE(token);
sse.connect(["posts", "comments"]);
sse.on("posts.create", (data) => {
  console.log("New post:", data);
});
```

---

## Authentication

Both WebSocket and SSE require authentication via JWT access token.

### Authentication Methods

**Via Query Parameter** (recommended for WebSocket):
```
ws://localhost:8000/api/v1/realtime/ws?token=your_jwt_token
```

**Via Query Parameter** (SSE):
```
http://localhost:8000/api/v1/realtime/subscribe?token=your_jwt_token&collection=posts
```

**Via Authorization Header** (SSE only):
```
Authorization: Bearer your_jwt_token
```

**Via WebSocket Subprotocol**:
```
Sec-WebSocket-Protocol: your_jwt_token
```

### Token Expiration

When your access token expires (after 1 hour), the connection will be closed. Use your refresh token to obtain a new access token and reconnect.

---

## Hook Integration

The realtime system integrates with SnackBase's hook system, allowing you to react to realtime events in custom code.

### Realtime Hook Events

| Event | Description |
|-------|-------------|
| `on_realtime_connect` | Fired when a client connects |
| `on_realtime_disconnect` | Fired when a client disconnects |
| `on_realtime_subscribe` | Fired when a client subscribes to a collection |
| `on_realtime_unsubscribe` | Fired when a client unsubscribes |
| `on_realtime_message` | Fired when a message is received (WebSocket only) |

### Example: Logging Realtime Connections

```python
@app.hook.on_realtime_connect()
async def log_realtime_connection(connection_id, user_id, account_id):
    logger.info(
        "Realtime connection established",
        connection_id=connection_id,
        user_id=user_id,
        account_id=account_id
    )

@app.hook.on_realtime_subscribe()
async def log_subscription(connection_id, user_id, collection):
    logger.info(
        "User subscribed to collection",
        connection_id=connection_id,
        user_id=user_id,
        collection=collection
    )
```

---

## Best Practices

### 1. Handle Reconnections

Network connections can drop. Always implement reconnection logic:

```javascript
class ReconnectingRealtime {
  constructor(token) {
    this.token = token;
    this.reconnectDelay = 1000;
    this.maxReconnectDelay = 30000;
  }

  connect() {
    this.ws = new WebSocket(`ws://localhost:8000/api/v1/realtime/ws?token=${this.token}`);

    this.ws.onclose = () => {
      setTimeout(() => {
        this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
        this.connect();
      }, this.reconnectDelay);
    };

    this.ws.onopen = () => {
      this.reconnectDelay = 1000; // Reset delay on successful connection
      // Resubscribe to collections
    };
  }
}
```

### 2. Filter Events on the Server

Use the `operations` parameter to filter events server-side:

```javascript
// Only listen for create events
ws.send(JSON.stringify({
  action: "subscribe",
  collection: "posts",
  operations: ["create"]
}));
```

### 3. Use SSE for Simple Use Cases

If you only need to receive events (not send messages), SSE is simpler:

- Automatic reconnection handled by browser
- One-way communication (simpler API)
- Built-in heartbeat support

### 4. Monitor Connection Health

Handle heartbeat messages to detect stale connections:

```javascript
let lastHeartbeat = Date.now();

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  if (message.type === "heartbeat") {
    lastHeartbeat = Date.now();
    return;
  }

  // Process data events
};

// Check for stale connection every 60 seconds
setInterval(() => {
  if (Date.now() - lastHeartbeat > 60000) {
    console.warn("No heartbeat received, connection may be stale");
    ws.close();
    this.connect();
  }
}, 60000);
```

### 5. Limit Subscriptions

Stay within the 100 subscription limit per connection:

```javascript
const subscriptions = [];

function subscribe(collection) {
  if (subscriptions.length >= 100) {
    console.error("Maximum subscriptions reached");
    return;
  }

  ws.send(JSON.stringify({
    action: "subscribe",
    collection
  }));

  subscriptions.push(collection);
}
```

---

## API Endpoints

### WebSocket Endpoint

```
WS /api/v1/realtime/ws
```

Connect to this endpoint for WebSocket-based realtime updates.

### SSE Endpoint

```
GET /api/v1/realtime/subscribe
```

Query Parameters:
- `token` (required): JWT access token
- `collection` (optional): Collection to subscribe to (can be specified multiple times)

---

## Security Considerations

1. **Token Security**: Always use HTTPS in production to protect tokens
2. **Account Isolation**: Events never cross account boundaries
3. **Permission Validation**: While realtime broadcasts to all subscribers, your application should validate permissions on the client side
4. **Token Expiration**: Handle token expiration gracefully and reconnect with a new token

---

## Troubleshooting

### Connection Refused

- Verify your token is valid and not expired
- Check that the server is running and the realtime feature is enabled
- Ensure CORS is configured correctly for your domain

### No Events Received

- Verify you've successfully subscribed to the collection
- Check that records are being modified in the subscribed collection
- Ensure you're authenticated with the correct account

### Frequent Disconnections

- Check your network stability
- Verify your token isn't expiring (1 hour lifetime)
- Implement reconnection logic in your client

### Subscription Errors

- Ensure you haven't exceeded the 100 subscription limit
- Verify the collection name is valid
- Check that you have permission to access the collection

---

## Comparison: WebSocket vs SSE

| Feature | WebSocket | SSE |
|---------|-----------|-----|
| **Communication** | Full-duplex (bidirectional) | One-way (server to client) |
| **Protocol** | Custom protocol | HTTP/1.1 |
| **Reconnection** | Manual implementation | Automatic (browser) |
| **Browser Support** | Excellent | Excellent |
| **Message Types** | Any (JSON, binary, etc.) | Text only |
| **Complexity** | Higher | Lower |
| **Use Case** | Interactive apps | Simple updates |

**Choose WebSocket when:**
- You need bidirectional communication
- You need to send messages to the server
- You're building interactive features (chat, collaboration)

**Choose SSE when:**
- You only need to receive updates
- You want simpler implementation
- You're building notifications or live updates
