import React, { useState } from "react";

interface Props {
  loading: boolean;
  onSend: (content: string) => Promise<void> | void;
}

const InputArea: React.FC<Props> = ({ loading, onSend }) => {
  const [value, setValue] = useState("");
  const [recording, setRecording] = useState(false);

  const isTyping = value.trim().length > 0;

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

  const toggleVoice = () => {
    // 这里可以接入真实语音逻辑，目前只是状态切换示例
    setRecording((prev) => !prev);
  };

  return (
    <div className="mt-3 flex flex-col gap-1">
      <div className="flex items-end gap-2">
        <textarea
          className="min-h-[44px] max-h-32 flex-1 resize-none rounded-2xl border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
          placeholder="请输入你的问题，Enter 发送，Shift+Enter 换行…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="button"
          onClick={toggleVoice}
          className={`flex h-10 w-10 items-center justify-center rounded-full border text-xs transition ${
            recording
              ? "border-red-500 bg-red-50 text-red-600"
              : "border-gray-300 bg-white text-gray-600 hover:border-blue-400 hover:text-blue-500"
          }`}
        >
          语音
        </button>
        <button
          type="button"
          onClick={() => void handleSend()}
          disabled={loading || !isTyping}
          className={`h-10 rounded-full px-5 text-sm font-medium text-white shadow-sm transition ${
            loading || !isTyping
              ? "cursor-not-allowed bg-blue-300"
              : "bg-blue-600 hover:bg-blue-700"
          }`}
        >
          {loading ? "发送中…" : "发送"}
        </button>
      </div>
      <div className="flex justify-between text-[11px] text-gray-400">
        <span>
          {isTyping ? "正在输入…" : "按 Enter 发送，Shift+Enter 换行"}
        </span>
        {recording && (
          <span className="text-red-500">语音录制中…（示例）</span>
        )}
      </div>
    </div>
  );
};

export default InputArea;

