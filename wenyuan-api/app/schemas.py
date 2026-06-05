from pydantic import BaseModel, Field
from typing import Any, Dict, Optional


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class UserResponse(BaseModel):
    id: int
    username: str


class ModelResponse(BaseModel):
    name: str
    provider: str
    display_name: str
    enabled: bool
    is_mock: bool


class QuoteResponse(BaseModel):
    text: str
    source: str


class ConversationCreateRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=160)
    selected_model: str = Field(default="wenyuan-sim", max_length=120)


class ConversationResponse(BaseModel):
    id: int
    title: str
    selected_model: str
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    model_name: Optional[str]
    created_at: str


class ChatStreamRequest(BaseModel):
    conversation_id: Optional[int] = None
    message: str = Field(min_length=1, max_length=4000)
    model_name: str = Field(default="wenyuan-sim", max_length=120)


class AgentProcessBlock(BaseModel):
    type: str
    title: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalChunkResponse(BaseModel):
    id: int
    source_type: str
    title: str
    content: str
    score: float
    rank: int
    rationale: str


class AgentRunResponse(BaseModel):
    id: int
    conversation_id: int
    user_message_id: int
    assistant_message_id: int | None = None
    model_name: str
    process_blocks: list[AgentProcessBlock]
    retrieval_chunks: list[RetrievalChunkResponse]
    created_at: str
