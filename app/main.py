from fastapi import FastAPI
from pydantic import BaseModel
from app.core import SupportEngine

app = FastAPI(title="Claude Customer Support Ops", version="1.0.0")
engine = SupportEngine()

class ChatRequest(BaseModel):
    conversation_id: str
    message: str

@app.get("/health")
def health():
    return {"status": "ok", "service": "claude-customer-support-ops", "mode": "deterministic_demo" if not engine._claude_available() else "claude"}

@app.post("/chat")
def chat(request: ChatRequest):
    return engine.chat(request.conversation_id, request.message)
