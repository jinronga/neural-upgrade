import { useCallback, useEffect, useMemo, useState } from "react";
import { v4 as uuidv4 } from "uuid";

import { post } from "@/services/api";
import type { ChatResponse, Message } from "../types";

interface UseChatOptions {
  userId?: string;
}

interface ChatState {
  messages: Message[];
  loading: boolean;
  sessionId?: string;
  needHuman: boolean;
  lastError?: string;
}

export const useChat = ({ userId }: UseChatOptions = {}): {
  messages: Message[];
  loading: boolean;
  sessionId?: string;
  needHuman: boolean;
  lastError?: string;
  sendMessage: (content: string) => Promise<void>;
  sendQuickReply: (content: string) => Promise<void>;
  transferToHuman: (reason: string) => Promise<void>;
} => {
  const [state, setState] = useState<ChatState>({
    messages: [],
    loading: false,
    sessionId: undefined,
    needHuman: false,
  });

  const effectiveUserId = useMemo(
    () => userId ?? "10001",
    [userId],
  );

  const appendMessage = useCallback((msg: Message) => {
    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, msg],
    }));
  }, []);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      const id = uuidv4();
      const userMessage: Message = {
        id,
        type: "user",
        content,
        timestamp: new Date(),
      };

      appendMessage(userMessage);
      setState((prev) => ({ ...prev, loading: true, lastError: undefined }));

      try {
        const payload = {
          user_id: effectiveUserId,
          message: content,
          session_id: state.sessionId,
          channel: "web",
        };
        const data = await post<ChatResponse>("/api/v1/chat", payload);

        const agentMessage: Message = {
          id: uuidv4(),
          type: "agent",
          content: data.response,
          timestamp: new Date(),
          suggestions: data.suggestions,
          quickReplies: data.quickReplies,
        };

        setState((prev) => ({
          ...prev,
          messages: [...prev.messages, agentMessage],
          sessionId: data.sessionId,
          needHuman: data.needHuman,
          lastError: undefined,
        }));
      } catch (error: any) {
        const message =
          error?.response?.data?.detail ??
          error?.message ??
          "发送消息失败，请稍后重试。";

        appendMessage({
          id: uuidv4(),
          type: "system",
          content: message,
          timestamp: new Date(),
        });

        setState((prev) => ({
          ...prev,
          lastError: message,
        }));
      } finally {
        setState((prev) => ({ ...prev, loading: false }));
      }
    },
    [appendMessage, effectiveUserId, state.sessionId]
  );

  const sendQuickReply = useCallback(
    async (content: string) => {
      await sendMessage(content);
    },
    [sendMessage]
  );

  const transferToHuman = useCallback(
    async (reason: string) => {
      if (!state.sessionId) return;

      setState((prev) => ({ ...prev, loading: true, lastError: undefined }));

      try {
        await post("/api/v1/chat/transfer-human", {
          session_id: state.sessionId,
          user_id: effectiveUserId,
          reason,
        });

        appendMessage({
          id: uuidv4(),
          type: "human",
          content: "已为你申请转接人工客服，请稍候人工专席的回复。",
          timestamp: new Date(),
        });

        setState((prev) => ({
          ...prev,
          needHuman: true,
        }));
      } catch (error: any) {
        const message =
          error?.response?.data?.detail ??
          error?.message ??
          "转人工失败，请稍后重试。";
        appendMessage({
          id: uuidv4(),
          type: "system",
          content: message,
          timestamp: new Date(),
        });
        setState((prev) => ({ ...prev, lastError: message }));
      } finally {
        setState((prev) => ({ ...prev, loading: false }));
      }
    },
    [appendMessage, effectiveUserId, state.sessionId]
  );

  useEffect(() => {
    const welcome: Message = {
      id: uuidv4(),
      type: "system",
      content: "你好，我是智能流量套餐助手，有什么可以帮你的吗？",
      timestamp: new Date(),
    };
    setState((prev) =>
      prev.messages.length === 0
        ? { ...prev, messages: [welcome] }
        : prev
    );
  }, []);

  return {
    messages: state.messages,
    loading: state.loading,
    sessionId: state.sessionId,
    needHuman: state.needHuman,
    lastError: state.lastError,
    sendMessage,
    sendQuickReply,
    transferToHuman,
  };
};

