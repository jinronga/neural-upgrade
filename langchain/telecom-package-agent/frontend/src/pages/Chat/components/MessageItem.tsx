import React from "react";
import ReactMarkdown from "react-markdown";

import type { Message } from "../types";

interface Props {
  message: Message;
}

const MessageItem: React.FC<Props> = ({ message }) => {
  const isUser = message.type === "user";
  const isAgent = message.type === "agent";
  const isSystem = message.type === "system";
  const isHuman = message.type === "human";

  const align = isUser ? "justify-end" : "justify-start";

  const bubbleBase =
    "max-w-[75%] rounded-2xl px-4 py-2 text-sm shadow-sm";
  const bubbleColor = isUser
    ? "bg-blue-600 text-white"
    : isAgent
    ? "bg-white text-gray-900 border border-gray-200"
    : isHuman
    ? "bg-emerald-50 text-emerald-900 border border-emerald-100"
    : "bg-gray-100 text-gray-700";

  const timeText = message.timestamp.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  const nameLabel = isUser
    ? "我"
    : isAgent
    ? "智能助手"
    : isHuman
    ? "人工客服"
    : "系统";

  return (
    <div className={`flex ${align} mb-3`}>
      {!isUser && (
        <div className="mr-2 flex h-8 w-8 items-center justify-center rounded-full bg-gray-200 text-xs text-gray-700">
          {nameLabel[0]}
        </div>
      )}
      <div className="flex flex-col items-start">
        <div className={`${bubbleBase} ${bubbleColor}`}>
          <ReactMarkdown className="prose prose-sm max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1">
            {message.content}
          </ReactMarkdown>
        </div>
        <div className="mt-1 text-[11px] text-gray-400">{timeText}</div>
      </div>
      {isUser && (
        <div className="ml-2 flex h-8 w-8 items-center justify-center rounded-full bg-blue-500 text-xs text-white">
          我
        </div>
      )}
    </div>
  );
};

export default MessageItem;

