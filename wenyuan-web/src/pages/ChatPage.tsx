import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Bot, Copy, Loader2, Plus, RefreshCcw, ScrollText, Search, Send, Square, Trash2, UserRound } from "lucide-react";
import {
  api,
  streamChat,
  type AgentRun,
  type ChatStreamEvent,
  type Conversation,
  type Message,
  type ModelInfo,
  type ProcessBlock,
  type RetrievalChunk,
} from "../lib/api";
import { useAuth } from "../lib/auth";
import { CollapsibleBlock } from "../components/CollapsibleBlock";

type UiMessage = {
  id: string;
  numericId?: number;
  role: "user" | "assistant";
  content: string;
  model_name?: string | null;
  processBlocks?: ProcessBlock[];
  retrievalChunks?: RetrievalChunk[];
  status?: "streaming" | "done" | "error";
};

export function ChatPage() {
  const { token } = useAuth();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<number | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModel, setSelectedModel] = useState("wenyuan-sim");
  const [input, setInput] = useState("");
  const [conversationSearch, setConversationSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!token) return;
    Promise.all([api.conversations(token), api.models(token)])
      .then(([conversationRows, modelRows]) => {
        setConversations(conversationRows);
        setModels(modelRows);
        if (modelRows[0]) setSelectedModel(modelRows[0].name);
        if (conversationRows[0]) {
          setActiveConversationId(conversationRows[0].id);
          setSelectedModel(conversationRows[0].selected_model);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "初始化失败。"));
  }, [token]);

  useEffect(() => {
    if (!token || !activeConversationId) {
      setMessages([]);
      return;
    }
    loadConversationState(activeConversationId).catch((err) =>
      setError(err instanceof Error ? err.message : "消息读取失败。"),
    );
  }, [activeConversationId, token]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  const activeConversation = useMemo(
    () => conversations.find((item) => item.id === activeConversationId) ?? null,
    [activeConversationId, conversations],
  );

  const filteredConversations = useMemo(() => {
    const keyword = conversationSearch.trim();
    if (!keyword) return conversations;
    return conversations.filter((item) => item.title.includes(keyword));
  }, [conversationSearch, conversations]);

  async function refreshConversations(nextActiveId?: number) {
    if (!token) return;
    const rows = await api.conversations(token);
    setConversations(rows);
    if (nextActiveId) setActiveConversationId(nextActiveId);
  }

  async function loadConversationState(conversationId: number) {
    if (!token) return;
    const [messageRows, runRows] = await Promise.all([
      api.messages(token, conversationId),
      api.agentRuns(token, conversationId),
    ]);
    setMessages(mergeMessagesWithRuns(messageRows, runRows));
  }

  async function createNewConversation() {
    if (!token) return;
    setError("");
    const created = await api.createConversation(token, "新会话", selectedModel);
    setConversations((rows) => [created, ...rows]);
    setActiveConversationId(created.id);
    setMessages([]);
  }

  async function deleteConversation(conversationId: number) {
    if (!token) return;
    const ok = window.confirm("确定删除这个会话吗？该会话的消息和过程记录都会删除。");
    if (!ok) return;
    await api.deleteConversation(token, conversationId);
    const nextRows = conversations.filter((item) => item.id !== conversationId);
    setConversations(nextRows);
    if (activeConversationId === conversationId) {
      const next = nextRows[0];
      setActiveConversationId(next?.id ?? null);
      setMessages([]);
    }
  }

  function stopGeneration() {
    abortRef.current?.abort();
    abortRef.current = null;
    setLoading(false);
    setMessages((rows) =>
      rows.map((message) => (message.status === "streaming" ? { ...message, status: "error" } : message)),
    );
  }

  async function regenerate() {
    const lastUser = [...messages].reverse().find((message) => message.role === "user");
    if (!lastUser) return;
    await sendMessage(lastUser.content);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = input.trim();
    if (!text) return;
    setInput("");
    await sendMessage(text);
  }

  async function sendMessage(text: string) {
    if (!token || loading) return;
    setError("");
    setLoading(true);
    const assistantId = `local-assistant-${Date.now()}`;
    const userMessage: UiMessage = { id: `local-user-${Date.now()}`, role: "user", content: text };
    const assistantMessage: UiMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      model_name: selectedModel,
      processBlocks: [],
      retrievalChunks: [],
      status: "streaming",
    };
    setMessages((rows) => [...rows, userMessage, assistantMessage]);

    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await streamChat(
        token,
        { conversation_id: activeConversationId, message: text, model_name: selectedModel },
        (eventData) => handleStreamEvent(eventData, assistantId),
        controller.signal,
      );
    } catch (err) {
      const aborted = err instanceof DOMException && err.name === "AbortError";
      setError(aborted ? "已停止生成。" : err instanceof Error ? err.message : "发送失败。");
      setMessages((rows) =>
        rows.map((message) =>
          message.id === assistantId
            ? { ...message, content: message.content || "本轮问答未完成。", status: "error" }
            : message,
        ),
      );
    } finally {
      abortRef.current = null;
      setLoading(false);
    }
  }

  function handleStreamEvent(eventData: ChatStreamEvent, assistantId: string) {
    if (eventData.type === "conversation") {
      setActiveConversationId(eventData.conversation.id);
      setConversations((rows) => upsertConversation(rows, eventData.conversation));
      return;
    }
    if ("block" in eventData) {
      setMessages((rows) =>
        rows.map((message) =>
          message.id === assistantId
            ? { ...message, processBlocks: [...(message.processBlocks ?? []), eventData.block] }
            : message,
        ),
      );
      return;
    }
    if (eventData.type === "retrieval_chunk") {
      setMessages((rows) =>
        rows.map((message) =>
          message.id === assistantId
            ? { ...message, retrievalChunks: [...(message.retrievalChunks ?? []), eventData.chunk] }
            : message,
        ),
      );
      return;
    }
    if (eventData.type === "answer_delta") {
      setMessages((rows) =>
        rows.map((message) =>
          message.id === assistantId ? { ...message, content: message.content + eventData.content } : message,
        ),
      );
      return;
    }
    if (eventData.type === "done") {
      setMessages((rows) =>
        rows.map((message) => (message.id === assistantId ? { ...message, status: "done" } : message)),
      );
      void refreshConversations(eventData.conversation_id);
      void loadConversationState(eventData.conversation_id);
    }
  }

  return (
    <section className="chatPage inlineProcess">
      <aside className="conversationRail">
        <button className="newConversation" type="button" onClick={createNewConversation}>
          <Plus size={17} aria-hidden="true" />
          新建会话
        </button>
        <label className="conversationSearch">
          <Search size={15} aria-hidden="true" />
          <input
            value={conversationSearch}
            onChange={(event) => setConversationSearch(event.target.value)}
            placeholder="搜索会话"
          />
        </label>
        <div className="conversationList">
          {filteredConversations.map((conversation) => (
            <div
              className={conversation.id === activeConversationId ? "conversationItem active" : "conversationItem"}
              key={conversation.id}
            >
              <button
                type="button"
                className="conversationOpen"
                onClick={() => {
                  setActiveConversationId(conversation.id);
                  setSelectedModel(conversation.selected_model);
                }}
              >
                <ScrollText size={16} aria-hidden="true" />
                <span>{conversation.title}</span>
              </button>
              <button
                type="button"
                className="conversationDelete"
                onClick={() => void deleteConversation(conversation.id)}
                title="删除会话"
              >
                <Trash2 size={15} aria-hidden="true" />
              </button>
            </div>
          ))}
        </div>
      </aside>

      <div className="chatWorkspace immersive">
        <header className="chatHeader">
          <div>
            <p className="eyebrow">史籍问答</p>
            <h1>{activeConversation?.title ?? "新问未启"}</h1>
          </div>
          <label className="modelSelect">
            <span>模型</span>
            <select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)}>
              {models.map((model) => (
                <option value={model.name} key={model.name}>
                  {model.display_name}
                </option>
              ))}
            </select>
          </label>
        </header>

        {error && <div className="formError">{error}</div>}

        <div className="messageScroll">
          {messages.length === 0 ? (
            <div className="emptyChat">
              <Bot size={38} aria-hidden="true" />
              <h2>请问一则史籍问题</h2>
              <p>例如：陈霸先的谥号和建陈关系是什么？请给出检索依据。</p>
            </div>
          ) : (
            messages.map((message) => <ChatMessageView key={message.id} message={message} onRegenerate={regenerate} />)
          )}
          <div ref={endRef} />
        </div>

        <form className="composer" onSubmit={handleSubmit}>
          <textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="输入你的史籍问题..."
            rows={2}
            disabled={loading}
          />
          <div className="composerActions">
            {loading && (
              <button className="secondaryButton" type="button" onClick={stopGeneration}>
                <Square size={16} aria-hidden="true" />
                停止
              </button>
            )}
            <button className="primaryButton" type="submit" disabled={loading || !input.trim()}>
              {loading ? <Loader2 className="spin" size={18} aria-hidden="true" /> : <Send size={18} aria-hidden="true" />}
              发送
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}

function ChatMessageView({ message, onRegenerate }: { message: UiMessage; onRegenerate: () => void }) {
  const isAssistant = message.role === "assistant";
  const processBlocks = orderProcessBlocks(message.processBlocks ?? []);
  return (
    <article className={`chatMessage ${message.role}`}>
      <div className="messageIcon">
        {message.role === "user" ? <UserRound size={18} aria-hidden="true" /> : <Bot size={18} aria-hidden="true" />}
      </div>
      <div className="messageBubble">
        <div className="messageHeader">
          <span>{message.role === "user" ? "你" : message.model_name ?? "文渊问史"}</span>
          {message.status === "streaming" && <small>生成中</small>}
          {message.status === "error" && <small>已停止/失败</small>}
        </div>
        {isAssistant && (
          <div className="inlineEvidence">
            {processBlocks.map((block, index) => (
              <CollapsibleBlock
                key={`${message.id}-${block.type}-${index}`}
                label={processLabel(block.type)}
                title={block.title}
                content={block.content}
                meta={JSON.stringify(block.metadata)}
                limit={220}
              />
            ))}
            {(message.retrievalChunks ?? []).map((chunk) => (
              <CollapsibleBlock
                key={`${message.id}-${chunk.source_type}-${chunk.rank}`}
                label={`#${chunk.rank} ${chunk.source_type}`}
                title={chunk.title}
                content={chunk.content}
                meta={`score=${chunk.score} · ${chunk.rationale}`}
                limit={220}
              />
            ))}
          </div>
        )}
        {isAssistant ? (
          <section className="finalAnswer">
            <span>最终答案</span>
            <p>{message.content || (message.status === "streaming" ? "等待模型完成工具观察后生成最终答案..." : "")}</p>
          </section>
        ) : (
          <p>{message.content}</p>
        )}
        {isAssistant && (
          <div className="messageTools">
            <button type="button" onClick={() => void navigator.clipboard?.writeText(message.content)}>
              <Copy size={15} aria-hidden="true" />
              复制
            </button>
            <button type="button" onClick={onRegenerate}>
              <RefreshCcw size={15} aria-hidden="true" />
              重新生成
            </button>
          </div>
        )}
      </div>
    </article>
  );
}

function orderProcessBlocks(blocks: ProcessBlock[]) {
  return blocks;
}

function processLabel(type: string) {
  const labels: Record<string, string> = {
    thinking: "thinking",
    action: "action",
    tool_call: "tool_call",
    observation: "observation",
    llm_status: "llm_status",
  };
  return labels[type] ?? type;
}

function messageToUi(message: Message): UiMessage {
  return {
    id: String(message.id),
    numericId: message.id,
    role: message.role,
    content: message.content,
    model_name: message.model_name,
    status: "done",
  };
}

function mergeMessagesWithRuns(messageRows: Message[], runRows: AgentRun[]): UiMessage[] {
  const runByAssistantId = new Map<number, AgentRun>();
  for (const run of runRows) {
    if (run.assistant_message_id) {
      runByAssistantId.set(run.assistant_message_id, run);
    }
  }
  return messageRows.map((message) => {
    const ui = messageToUi(message);
    const run = message.role === "assistant" ? runByAssistantId.get(message.id) : undefined;
    if (run) {
      ui.processBlocks = run.process_blocks;
      ui.retrievalChunks = run.retrieval_chunks;
    }
    return ui;
  });
}

function upsertConversation(rows: Conversation[], conversation: Conversation) {
  const rest = rows.filter((item) => item.id !== conversation.id);
  return [conversation, ...rest];
}
