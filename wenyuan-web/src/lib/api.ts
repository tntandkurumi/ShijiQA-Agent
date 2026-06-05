export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

export type AuthResponse = {
  access_token: string;
  token_type: string;
  username: string;
};

export type Quote = {
  text: string;
  source: string;
};

export type ModelInfo = {
  name: string;
  provider: string;
  display_name: string;
  enabled: boolean;
  is_mock: boolean;
};

export type Conversation = {
  id: number;
  title: string;
  selected_model: string;
  created_at: string;
  updated_at: string;
};

export type Message = {
  id: number;
  conversation_id: number;
  role: "user" | "assistant";
  content: string;
  model_name: string | null;
  created_at: string;
};

export type ProcessBlock = {
  type: string;
  title: string;
  content: string;
  metadata: Record<string, unknown>;
};

export type RetrievalChunk = {
  source_type: string;
  title: string;
  content: string;
  score: number;
  rank: number;
  rationale: string;
};

export type ChatStreamEvent =
  | { type: "conversation"; conversation: Conversation }
  | { type: "process"; block: ProcessBlock }
  | { type: "thinking"; block: ProcessBlock }
  | { type: "action"; block: ProcessBlock }
  | { type: "tool_call"; block: ProcessBlock }
  | { type: "observation"; block: ProcessBlock }
  | { type: "llm_status"; block: ProcessBlock }
  | { type: "retrieval_chunk"; chunk: RetrievalChunk }
  | { type: "answer_start"; message_id: number }
  | { type: "answer_delta"; content: string }
  | { type: "done"; conversation_id: number; message_id: number };

export type AgentRun = {
  id: number;
  conversation_id: number;
  user_message_id: number;
  assistant_message_id: number | null;
  model_name: string;
  process_blocks: ProcessBlock[];
  retrieval_chunks: (RetrievalChunk & { id: number })[];
  created_at: string;
};

async function request<T>(path: string, options: RequestInit = {}, token?: string | null): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let message = "请求失败。";
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export const api = {
  register(username: string, password: string) {
    return request<AuthResponse>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  login(username: string, password: string) {
    return request<AuthResponse>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  me(token: string) {
    return request<{ id: number; username: string }>("/api/auth/me", {}, token);
  },

  quotes() {
    return request<Quote[]>("/api/quotes");
  },

  models(token: string) {
    return request<ModelInfo[]>("/api/models", {}, token);
  },

  conversations(token: string) {
    return request<Conversation[]>("/api/conversations", {}, token);
  },

  createConversation(token: string, title?: string, selected_model = "wenyuan-sim") {
    return request<Conversation>(
      "/api/conversations",
      {
        method: "POST",
        body: JSON.stringify({ title, selected_model }),
      },
      token,
    );
  },

  messages(token: string, conversationId: number) {
    return request<Message[]>(`/api/conversations/${conversationId}/messages`, {}, token);
  },

  deleteConversation(token: string, conversationId: number) {
    return request<{ status: string; conversation_id: number }>(
      `/api/conversations/${conversationId}`,
      { method: "DELETE" },
      token,
    );
  },

  agentRuns(token: string, conversationId: number) {
    return request<AgentRun[]>(`/api/conversations/${conversationId}/agent-runs`, {}, token);
  },
};

export async function streamChat(
  token: string,
  payload: { conversation_id: number | null; message: string; model_name: string },
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
) {
  const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok || !response.body) {
    let message = "流式问答请求失败。";
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";

    for (const part of parts) {
      const line = part.split("\n").find((item) => item.startsWith("data: "));
      if (!line) continue;
      onEvent(JSON.parse(line.slice(6)) as ChatStreamEvent);
    }
  }
}
