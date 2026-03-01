import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiChatResponse,
  sendMessage as sendChatMessage,
  transferToHuman as transferHumanApi,
} from "@/services/api";
import { useUser } from "@/contexts/UserContext";
import type { ChatResult, Message } from "../types";

interface ChatState {
  messages: Message[];
  loading: boolean;
  sessionId?: string;
  needHuman: boolean;
  lastError?: string;
}

const mapChatResponse = (resp: ApiChatResponse): ChatResult => ({
  sessionId: resp.session_id,
  response: resp.response,
  suggestions: resp.suggestions ?? [],
  quickReplies: resp.quick_replies ?? [],
  needHuman: resp.need_human ?? false,
  humanTransferReason: resp.human_transfer_reason ?? undefined,
});

const newId = () =>
  typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}_${Math.random().toString(16).slice(2)}`;

export const useChat = (): {
  messages: Message[];
  loading: boolean;
  sessionId?: string;
  needHuman: boolean;
  lastError?: string;
  sendMessage: (content: string) => Promise<void>;
  sendQuickReply: (content: string) => Promise<void>;
  transferToHuman: (reason: string) => Promise<void>;
} => {
  const { userId, userPhone } = useUser();
  const [state, setState] = useState<ChatState>({
    messages: [],
    loading: false,
    sessionId: undefined,
    needHuman: false,
  });

  const appendMessage = useCallback((msg: Message) => {
    setState((prev) => ({
      ...prev,
      messages: [...prev.messages, msg],
    }));
  }, []);

  const effectiveUserId = useMemo(() => userId || "1", [userId]);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

      const userMessage: Message = {
        id: newId(),
        type: "user",
        content,
        timestamp: new Date(),
      };

      appendMessage(userMessage);
      setState((prev) => ({ ...prev, loading: true, lastError: undefined }));

      try {
        const data = await sendChatMessage({
          user_id: effectiveUserId,
          message: content,
          session_id: state.sessionId,
          channel: "web",
        });

        const result = mapChatResponse(data);
        const agentMessage: Message = {
          id: newId(),
          type: "agent",
          content: result.response,
          timestamp: new Date(),
          suggestions: result.suggestions,
          quickReplies: result.quickReplies,
        };

        setState((prev) => ({
          ...prev,
          messages: [...prev.messages, agentMessage],
          sessionId: result.sessionId,
          needHuman: result.needHuman,
          lastError: undefined,
        }));
      } catch (error: any) {
        const statusCode = error?.response?.status;
        const message =
          error?.response?.data?.detail ??
          (statusCode === 500
            ? "聊天服务暂不可用，请检查后端 OPENAI_API_KEY / OPENAI_BASE_URL 配置。"
            : undefined) ??
          error?.message ??
          "发送消息失败，请稍后重试。";

        appendMessage({
          id: newId(),
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
        await transferHumanApi({
          session_id: state.sessionId,
          user_id: effectiveUserId,
          reason,
        });

        appendMessage({
          id: newId(),
          type: "human",
          content: "已为你创建人工客服工单，请稍候专席客服联系你。",
          timestamp: new Date(),
        });

        setState((prev) => ({
          ...prev,
          needHuman: true,
        }));
      } catch (error: any) {
        const statusCode = error?.response?.status;
        const message =
          error?.response?.data?.detail ??
          (statusCode === 500
            ? "人工转接服务暂不可用，请稍后重试。"
            : undefined) ??
          error?.message ??
          "转人工失败，请稍后重试。";

        appendMessage({
          id: newId(),
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
    const userDisplay = userPhone ? userPhone : `ID:${effectiveUserId}`;
    const welcome: Message = {
      id: newId(),
      type: "system",
      content: `你好，我是智能流量套餐助手。当前用户是 ${userDisplay}，你可以直接问我套餐、用量或权益问题。`,
      timestamp: new Date(),
    };
    setState({
      messages: [welcome],
      loading: false,
      sessionId: undefined,
      needHuman: false,
      lastError: undefined,
    });
  }, [effectiveUserId, userPhone]);

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
