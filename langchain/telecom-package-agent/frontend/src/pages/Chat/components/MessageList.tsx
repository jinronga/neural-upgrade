import React, { useEffect, useRef } from "react";

import type { Message } from "../types";
import MessageItem from "./MessageItem";

interface Props {
  messages: Message[];
}

const MessageList: React.FC<Props> = ({ messages }) => {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 bg-gray-50 rounded-lg border border-gray-200">
      {messages.map((m) => (
        <MessageItem key={m.id} message={m} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
};

export default MessageList;

