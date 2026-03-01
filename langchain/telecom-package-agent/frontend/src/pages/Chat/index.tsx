import React, { useMemo } from "react";
import { Card, Spin, Typography } from "antd";

import MessageList from "./components/MessageList";
import InputArea from "./components/InputArea";
import SuggestionChips from "./components/SuggestionChips";
import HumanTransfer from "./components/HumanTransfer";
import { useChat } from "./hooks/useChat";
import { useUser } from "@/contexts/UserContext";

const { Title, Text } = Typography;

const ChatPage: React.FC = () => {
  const { userId, userPhone } = useUser();
  const {
    messages,
    loading,
    needHuman,
    lastError,
    sendMessage,
    sendQuickReply,
    transferToHuman,
  } = useChat();

  const latestAgentSuggestions = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      const msg = messages[i];
      if (msg.type === "agent" && msg.suggestions?.length) {
        return msg.suggestions;
      }
    }
    return [] as string[];
  }, [messages]);
  const userDisplay = userPhone ? userPhone : `ID:${userId}`;

  return (
    <div className="h-full flex flex-col">
      <Card className="flex-1 flex flex-col">
        <div className="mb-3">
          <Title level={3} className="!mb-1">
            智能流量套餐助手
          </Title>
          <Text type="secondary">
            当前用户：{userDisplay}。可以查询用量、推荐套餐、领取权益，并在需要时发起人工转接。
          </Text>
        </div>

        <Spin spinning={loading} tip="正在为你思考...">
          <div className="flex flex-col h-[60vh]">
            <MessageList messages={messages} />
            {latestAgentSuggestions.length > 0 && (
              <SuggestionChips
                suggestions={latestAgentSuggestions}
                onClick={(text) => void sendQuickReply(text)}
              />
            )}
            <InputArea loading={loading} onSend={sendMessage} />
            <HumanTransfer visible={needHuman} onTransfer={transferToHuman} />
            {lastError && (
              <div className="mt-2 text-xs text-red-500">{lastError}</div>
            )}
          </div>
        </Spin>
      </Card>
    </div>
  );
};

export default ChatPage;
