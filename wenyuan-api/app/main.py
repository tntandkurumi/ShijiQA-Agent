import json
import time
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .auth import create_access_token, get_current_user, hash_password, verify_password
from .config import settings
from .database import SessionLocal, get_db, init_db
from .models import AgentRun, Conversation, Message, ModelConfig, RetrievalChunk, User
from .schemas import (
    AgentRunResponse,
    ChatStreamRequest,
    ConversationCreateRequest,
    ConversationResponse,
    LoginRequest,
    MessageResponse,
    ModelResponse,
    QuoteResponse,
    RegisterRequest,
    RetrievalChunkResponse,
    TokenResponse,
    UserResponse,
)
from .seed import CLASSIC_QUOTES, seed_model_configs
from .services.agent_service import build_agent_result, split_answer

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _dt(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def _conversation_response(row: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=row.id,
        title=row.title,
        selected_model=row.selected_model,
        created_at=_dt(row.created_at),
        updated_at=_dt(row.updated_at),
    )


def _message_response(row: Message) -> MessageResponse:
    return MessageResponse(
        id=row.id,
        conversation_id=row.conversation_id,
        role=row.role,
        content=row.content,
        model_name=row.model_name,
        created_at=_dt(row.created_at),
    )


def _run_response(row: AgentRun, chunks: list[RetrievalChunk], assistant_message_id: int | None = None) -> AgentRunResponse:
    try:
        process_blocks = json.loads(row.process_log)
    except json.JSONDecodeError:
        process_blocks = []
    return AgentRunResponse(
        id=row.id,
        conversation_id=row.conversation_id,
        user_message_id=row.user_message_id,
        assistant_message_id=assistant_message_id,
        model_name=row.model_name,
        process_blocks=process_blocks,
        retrieval_chunks=[
            RetrievalChunkResponse(
                id=chunk.id,
                source_type=chunk.source_type,
                title=chunk.title,
                content=chunk.content,
                score=chunk.score,
                rank=chunk.rank,
                rationale=chunk.rationale,
            )
            for chunk in chunks
        ],
        created_at=_dt(row.created_at),
    )


def _sse(event_type: str, payload: dict) -> str:
    body = {"type": event_type, **payload}
    return "data: " + json.dumps(body, ensure_ascii=False) + "\n\n"


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    db = SessionLocal()
    try:
        seed_model_configs(db)
    finally:
        db.close()


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "database": "sqlite" if settings.using_sqlite else "mysql-or-custom",
        "llm_enabled": settings.llm_enabled,
    }


@app.post("/api/auth/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户名不能为空。")
    exists = db.query(User).filter(User.username == username).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在。")
    user = User(username=username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    token = create_access_token(subject=user.username)
    return TokenResponse(access_token=token, username=user.username)


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.username == payload.username.strip()).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误。")
    token = create_access_token(subject=user.username)
    return TokenResponse(access_token=token, username=user.username)


@app.get("/api/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=current_user.id, username=current_user.username)


@app.get("/api/models", response_model=list[ModelResponse])
def list_models(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[ModelResponse]:
    rows = db.query(ModelConfig).filter(ModelConfig.enabled.is_(True)).order_by(ModelConfig.id.asc()).all()
    return [
        ModelResponse(
            name=row.name,
            provider=row.provider,
            display_name=row.display_name,
            enabled=row.enabled,
            is_mock=row.is_mock,
        )
        for row in rows
    ]


@app.get("/api/quotes", response_model=list[QuoteResponse])
def list_quotes() -> list[QuoteResponse]:
    return [QuoteResponse(**item) for item in CLASSIC_QUOTES]


@app.get("/api/conversations", response_model=list[ConversationResponse])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConversationResponse]:
    rows = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
        .all()
    )
    return [_conversation_response(row) for row in rows]


@app.post("/api/conversations", response_model=ConversationResponse)
def create_conversation(
    payload: ConversationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConversationResponse:
    title = (payload.title or "新会话").strip() or "新会话"
    row = Conversation(user_id=current_user.id, title=title, selected_model=payload.selected_model)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _conversation_response(row)


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在。")

    runs = db.query(AgentRun).filter(AgentRun.conversation_id == conversation.id).all()
    for run in runs:
        db.query(RetrievalChunk).filter(RetrievalChunk.agent_run_id == run.id).delete()
    db.query(AgentRun).filter(AgentRun.conversation_id == conversation.id).delete()
    db.query(Message).filter(Message.conversation_id == conversation.id).delete()
    db.delete(conversation)
    db.commit()
    return {"status": "deleted", "conversation_id": conversation_id}


@app.get("/api/conversations/{conversation_id}/messages", response_model=list[MessageResponse])
def list_messages(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[MessageResponse]:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在。")
    rows = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc(), Message.id.asc())
        .all()
    )
    return [_message_response(row) for row in rows]


@app.get("/api/conversations/{conversation_id}/agent-runs", response_model=list[AgentRunResponse])
def list_agent_runs(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AgentRunResponse]:
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == current_user.id)
        .first()
    )
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在。")

    runs = (
        db.query(AgentRun)
        .filter(AgentRun.conversation_id == conversation.id)
        .order_by(AgentRun.created_at.desc(), AgentRun.id.desc())
        .all()
    )
    responses = []
    for run in runs:
        chunks = (
            db.query(RetrievalChunk)
            .filter(RetrievalChunk.agent_run_id == run.id)
            .order_by(RetrievalChunk.rank.asc(), RetrievalChunk.id.asc())
            .all()
        )
        assistant_message = (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation.id,
                Message.role == "assistant",
                Message.id > run.user_message_id,
            )
            .order_by(Message.id.asc())
            .first()
        )
        responses.append(_run_response(run, chunks, assistant_message.id if assistant_message else None))
    return responses


@app.post("/api/chat/stream")
def chat_stream(
    payload: ChatStreamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    query = payload.message.strip()
    if not query:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="消息不能为空。")

    if payload.conversation_id is None:
        title = query[:30] + ("..." if len(query) > 30 else "")
        conversation = Conversation(user_id=current_user.id, title=title, selected_model=payload.model_name)
        db.add(conversation)
        db.flush()
    else:
        conversation = (
            db.query(Conversation)
            .filter(Conversation.id == payload.conversation_id, Conversation.user_id == current_user.id)
            .first()
        )
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在。")
        conversation.selected_model = payload.model_name
        conversation.updated_at = datetime.utcnow()

    existing_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(8)
        .all()
    )
    history_messages = [
        {"role": message.role, "content": message.content}
        for message in reversed(existing_messages)
        if message.role in {"user", "assistant"}
    ]
    history_count = db.query(Message).filter(Message.conversation_id == conversation.id).count()
    user_message = Message(conversation_id=conversation.id, role="user", content=query, model_name=None)
    db.add(user_message)
    db.flush()

    selected_model_config = db.query(ModelConfig).filter(ModelConfig.name == payload.model_name).first()
    model_config_payload = None
    if selected_model_config:
        model_config_payload = {
            "provider": selected_model_config.provider,
            "base_url": selected_model_config.base_url,
            "is_mock": selected_model_config.is_mock,
        }
    agent_result = build_agent_result(
        query=query,
        model_name=payload.model_name,
        history_count=history_count,
        model_config=model_config_payload,
        history_messages=history_messages,
    )
    process_blocks = agent_result["process_blocks"]
    retrieval_chunks = agent_result["retrieval_chunks"]
    answer = agent_result["answer"]

    run = AgentRun(
        conversation_id=conversation.id,
        user_message_id=user_message.id,
        model_name=payload.model_name,
        process_log=json.dumps(process_blocks, ensure_ascii=False),
    )
    db.add(run)
    db.flush()

    for chunk in retrieval_chunks:
        db.add(
            RetrievalChunk(
                agent_run_id=run.id,
                source_type=chunk["source_type"],
                title=chunk["title"],
                content=chunk["content"],
                score=chunk["score"],
                rank=chunk["rank"],
                rationale=chunk["rationale"],
            )
        )

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer,
        model_name=payload.model_name,
    )
    db.add(assistant_message)
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(conversation)
    db.refresh(assistant_message)

    events = []
    events.append(
        _sse(
            "conversation",
            {
                "conversation": _conversation_response(conversation).model_dump(),
            },
        )
    )
    for block in process_blocks:
        events.append(_sse(block.get("type", "process"), {"block": block}))
    for chunk in retrieval_chunks:
        events.append(_sse("retrieval_chunk", {"chunk": chunk}))
    events.append(_sse("answer_start", {"message_id": assistant_message.id}))
    for delta in split_answer(answer):
        events.append(_sse("answer_delta", {"content": delta}))
    events.append(
        _sse(
            "done",
            {
                "conversation_id": conversation.id,
                "message_id": assistant_message.id,
            },
        )
    )

    def event_stream():
        for event in events:
            yield event
            time.sleep(0.02)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
