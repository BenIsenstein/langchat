import os
from dotenv import load_dotenv
load_dotenv()

if "ANTHROPIC_API_KEY" not in os.environ:
    raise RuntimeError("ANTHROPIC_API_KEY must be set")

if "E2B_API_KEY" not in os.environ:
    raise RuntimeError("E2B_API_KEY must be set")

import json
import uuid
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from app.agent import agent

# In-memory storage for staging streams.
# Messages need to be added via POST, but Server Sent Events connections need to be GET requests.
# So the common flow involves sending a POST to add a message, then opening a GET SSE connection to stream the tokens.
# So we stage the streams here keyed by a stream_id.
streams = {}

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:8080",
    os.environ.get("FRONTEND_URL", "http://localhost:5173"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status":"ok"}

@app.post("/chats/{chat_id}/messages")
def add_message(chat_id: str, body: dict):
    message = body.get("message", "")
    stream = {"chat_id": chat_id, "message": message}
    stream_id = str(uuid.uuid4())
    streams[stream_id] = stream
    return {"stream_id": stream_id}

@app.get("/chats/{chat_id}/streams/{stream_id}")
async def chat(chat_id: str, stream_id: str):
    payload = streams.get(stream_id, None)

    if payload is None:
        return StreamingResponse(
            iter([f"event: error\ndata: {json.dumps({'error': 'stream not found'})}\n\n"]),
            media_type="text/event-stream",
        )
    
    stream = agent.astream(
        {"messages": [{"role": "user", "content": payload.get("message", "")}]},
        config={"configurable": {"thread_id": payload.get("chat_id", "")}},
        stream_mode=["messages", "updates"]
    )

    # Since each node invocation in the agent graph doesn't have a unique id, just incrementing numbers,
    # I'll create a uuid4 for each node invocation to track it in the frontend as "message_id".
    # This helps immensely with rendering messages separately.
    async def event_generator():
        langgraph_step = None
        message_id = None

        async for event in stream:
            try:
                type, data = event

                if type == "messages":
                    message_chunk, metadata = data

                    if len(message_chunk.content_blocks) == 0:
                        continue

                    if langgraph_step != metadata.get("langgraph_step", None):
                        langgraph_step = metadata.get("langgraph_step", None)
                        message_id = str(uuid.uuid4())
                    
                    block = message_chunk.content_blocks[-1]
                    payload = {
                        "message_id": message_id,
                        "type": block["type"],
                        "data": None
                    }

                    if "name" in block and block["name"] is not None:
                        payload["name"] = block["name"]

                    if block["type"] == "text":
                        payload["data"] = block["text"]
                    elif block["type"] == "tool_call_chunk":
                        payload["data"] = block["args"]

                # elif type == "updates":
                #     if "model" in data:
                #         messages = data["model"]["messages"][-1].__dict__
                #     elif "tools" in data:
                #         messages = data["tools"]["messages"][-1].__dict__
                #     else:
                #         print("There was an 'updates' event that wasn't 'model' or 'tools'. See here --> ", data)

                yield f"data: {json.dumps(payload)}\n\n"
            except Exception as e:
                error_payload = {
                    "type": "error",
                    "data": str(e)
                }
                yield f"data: {json.dumps(error_payload)}\n\n"

        yield "event: closedConnection\ndata: Stream finished\n\n"
        del streams[stream_id]
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
