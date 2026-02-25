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
    <div className="flex-1 overflow-y-auto rounded-2xl border border-gray-200 bg-gradient-to-b from-gray-50 to-white px-4 py-3">
      {messages.map((m) => (
        <MessageItem key={m.id} message={m} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
};

export default MessageList;

