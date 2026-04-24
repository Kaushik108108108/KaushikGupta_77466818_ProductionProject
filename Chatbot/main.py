import os
import logging
from typing import List, Literal, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from groq import Groq

# Set up simple logging to help you debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ScholarAI-Chat")

load_dotenv()

app = FastAPI(title="ScholarAI Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise RuntimeError("GROQ_API_KEY is missing in environment variables.")

client = Groq(api_key=api_key)

# Default context used ONLY if the Flask side sends nothing
DEFAULT_CONTEXT = """
You are ScholarAI, an intelligent academic and administrative assistant. 
Ground your responses in any provided student context. 
If data is missing, ask for clarification. 
Always aim to provide AT LEAST 3-5 HELPFUL YOUTUBE SEARCH LINKS 
(e.g., `https://www.youtube.com/results?search_query=Khan+Academy+Math+Class+10`) 
instead of direct video IDs to ensure the content remains available.
"""

class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(..., min_length=1)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    history: List[Message] = []
    system_prompt: Optional[str] = None
    temperature: Optional[float] = 0.5 

class ChatResponse(BaseModel):
    reply: str

@app.get("/")
def root():
    return {"message": "ScholarAI Intelligence API is running"}

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    try:
        messages = []

        # 1. Prioritize the Dynamic Data Prompt from your Flask app
        # This contains your real student stats!
        active_prompt = req.system_prompt if req.system_prompt else DEFAULT_CONTEXT
        
        messages.append({
            "role": "system",
            "content": active_prompt
        })

        # 2. Append Chat History (Memory)
        for msg in req.history:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })

        # 3. Append Current User Message
        messages.append({
            "role": "user",
            "content": req.message
        })

        logger.info(f"Processing message with {len(req.history)} previous turns of context.")

        # 4. Generate AI response using Llama 3.3
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=req.temperature if req.temperature is not None else 0.5,
        )

        reply = completion.choices[0].message.content or "Internal AI error."
        return ChatResponse(reply=reply)

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
