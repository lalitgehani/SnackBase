import asyncio
import json
import httpx
import websockets
from datetime import datetime

API_URL = "http://localhost:8000/api/v1"
WS_URL = "ws://localhost:8000/api/v1/realtime/ws"

async def verify_realtime():
    print("🚀 Starting Real-Time Verification...")
    
    # 1. Login to get token
    async with httpx.AsyncClient() as client:
        # Assuming we have a test user or superadmin
        # In a real environment, we'd use environment variables
        login_data = {
            "email": "admin@snackbase.io",
            "password": "Password123!",
            "account": "system"
        }
        print(f"Logging in as {login_data['email']}...")
        response = await client.post(f"{API_URL}/auth/login", json=login_data)
        if response.status_code != 200:
            print(f"❌ Login failed: {response.text}")
            return
        
        resp_json = response.json()
        if "token" not in resp_json:
            print(f"❌ Login response missing 'token': {resp_json}")
            return
            
        token = resp_json["token"]
        print("✅ Login successful")

        # 2. Connect to WebSocket
        print(f"Connecting to WebSocket at {WS_URL}...")
        async with websockets.connect(f"{WS_URL}?token={token}") as ws:
            print("✅ WebSocket connected")
            
            # 3. Subscribe to a test collection (e.g., 'tasks')
            # First, make sure the collection exists or create it
            # For this test, let's assume 'tasks' collection exists or create a throwaway one
            collection_name = f"test_col_{int(datetime.now().timestamp())}"
            print(f"Creating test collection '{collection_name}'...")
            col_resp = await client.post(
                f"{API_URL}/collections", 
                json={
                    "name": collection_name,
                    "schema": [{"name": "title", "type": "text"}]
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            if col_resp.status_code >= 400:
                print(f"❌ Collection creation failed: {col_resp.status_code} {col_resp.text}")
                return
            print("✅ Collection created")
            
            print(f"Subscribing to {collection_name}...")
            await ws.send(json.dumps({
                "action": "subscribe",
                "collection": collection_name
            }))
            
            sub_resp = await ws.recv()
            print(f"Subscription response: {sub_resp}")
            
            # 4. Perform a CREATE operation via REST
            print("Creating a record via REST...")
            create_resp = await client.post(
                f"{API_URL}/records/{collection_name}",
                json={"title": "Real-time Test"},
                headers={"Authorization": f"Bearer {token}"}
            )
            print(f"Record created: {create_resp.status_code}")
            
            # 5. Wait for WebSocket event
            print("Waiting for WebSocket event...")
            try:
                # We might get heartbeats or the event
                for _ in range(5):
                    event_data = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    event = json.loads(event_data)
                    print(f"Received event: {event['type']}")
                    if event["type"] == f"{collection_name}.create":
                        print("✅ Success! WebSocket event received.")
                        break
                else:
                    print("❌ Failed: WebSocket event not received within timeout")
            except asyncio.TimeoutError:
                print("❌ Failed: Timeout waiting for WebSocket event")

            # 6. Verify SSE
            print("\nWait, verifying SSE...")
            # SSE is harder to test with a simple script but we can try
            # We'll use a separate task to listen to SSE
            async def listen_sse():
                # Note: SSE endpoint is /api/v1/realtime/subscribe?token=...&collection=...
                async with client.stream(
                    "GET", 
                    f"{API_URL}/realtime/subscribe", 
                    params={"token": token, "collection": collection_name},
                    timeout=None
                ) as response:
                    print("✅ SSE stream opened")
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = json.loads(line[6:])
                            print(f"Received SSE event: {data.get('type')}")
                            if data.get("type") == f"{collection_name}.update":
                                print("✅ Success! SSE event received.")
                                break

            sse_task = asyncio.create_task(listen_sse())
            await asyncio.sleep(1) # Give SSE time to connect
            
            # Trigger UPDATE via REST
            record_id = create_resp.json()["id"]
            print(f"Updating record {record_id} via REST...")
            await client.patch(
                f"{API_URL}/records/{collection_name}/{record_id}",
                json={"title": "Updated Title"},
                headers={"Authorization": f"Bearer {token}"}
            )
            
            try:
                await asyncio.wait_for(sse_task, timeout=5.0)
            except asyncio.TimeoutError:
                print("❌ Failed: Timeout waiting for SSE event")
                sse_task.cancel()

    print("\n🏁 Verification complete.")

if __name__ == "__main__":
    asyncio.run(verify_realtime())
