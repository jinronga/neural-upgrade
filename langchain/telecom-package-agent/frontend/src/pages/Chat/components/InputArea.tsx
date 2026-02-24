import React, { useState } from "react";
import { Button, Input } from "antd";
import { SendOutlined } from "@ant-design/icons";

interface Props {
  loading: boolean;
  onSend: (content: string) => Promise<void> | void;
}

const InputArea: React.FC<Props> = ({ loading, onSend }) => {
  const [value, setValue] = useState("");

  const handleSend = async () => {
    const text = value.trim();
    if (!text || loading) return;
    setValue("");
    await onSend(text);
  };

  const handleKeyDown: React.KeyboardEventHandler<HTMLTextAreaElement> = (
    e
  ) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  return (
    <div className="flex items-end gap-2 mt-3">
      <Input.TextArea
        autoSize={{ minRows: 1, maxRows: 4 }}
        placeholder="请输入你的问题，例如：帮我看看当前流量情况，并推荐一个更合适的套餐。"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      <Button
        type="primary"
        icon={<SendOutlined />}
        loading={loading}
        onClick={() => void handleSend()}
      >
        发送
      </Button>
    </div>
  );
};

export default InputArea;

