import json
import sys

# A hand-written server with none of the SDK's stdout protection.
for line in sys.stdin:
    msg = json.loads(line)
    method, msg_id = msg.get("method"), msg.get("id")
    if method == "initialize":
        # print("debugging", flush=True)  # stray text on the real stdout
        result = {
            "protocolVersion": "2025-11-25",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "raw-bad", "version": "0"},

        }
    elif method == "tools/list":
        result = {"tools": [{"name": "echo", "inputSchema": {"type": "object", "properties":
        {}}}]}
    elif method == "tools/call":
        result = {"content": [{"type": "text", "text": "pong"}], "isError": False}
    else:
        continue  # notifications get no reply
    print(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}), flush=True)
