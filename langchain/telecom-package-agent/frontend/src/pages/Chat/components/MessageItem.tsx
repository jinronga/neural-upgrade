import React from "react";
import { Avatar, Card } from "antd";
import { UserOutlined, RobotOutlined } from "@ant-design/icons";

import type { Message } from "../types";

interface Props {
  message: Message;
}

const MessageItem: React.FC<Props> = ({ message }) => {
  const isUser = message.type === "user";
  const isAgent = message.type === "agent";
  const isSystem = message.type === "system";

  const alignClass = isUser ? "justify-end" : "justify-start";
  const bgClass = isUser
    ? "bg-blue-500 text-white"
    : isSystem
    ? "bg-gray-100 text-gray-700"
    : "bg-white";

  return (
    <div className={`flex ${alignClass} mb-3`}>
      {!isUser && (
        <Avatar
          className="mr-2"
          icon={isAgent ? <RobotOutlined /> : <UserOutlined />}
        />
      )}
      <Card
        size="small"
        className={`${bgClass} max-w-xl shadow-sm`}
        bodyStyle={{ padding: "8px 12px" }}
      >
        <div className="whitespace-pre-wrap break-words">{message.content}</div>
        <div className="mt-1 text-xs text-gray-400">
          {message.timestamp.toLocaleTimeString()}
        </div>
      </Card>
      {isUser && (
        <Avatar className="ml-2" icon={<UserOutlined />} />
      )}
    </div>
  );
};

export default MessageItem;

