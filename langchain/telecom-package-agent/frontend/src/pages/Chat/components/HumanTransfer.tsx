import React, { useState } from "react";
import { Alert, Button, Input, Modal } from "antd";

interface Props {
  visible: boolean;
  onTransfer: (reason: string) => Promise<void>;
}

const HumanTransfer: React.FC<Props> = ({ visible, onTransfer }) => {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState(
    "我希望由人工客服进一步确认套餐或账单问题。"
  );
  const [loading, setLoading] = useState(false);

  const handleClick = () => {
    setOpen(true);
  };

  const handleOk = async () => {
    if (!reason.trim()) return;
    setLoading(true);
    try {
      await onTransfer(reason.trim());
      setOpen(false);
    } finally {
      setLoading(false);
    }
  };

  if (!visible) return null;

  return (
    <>
      <Alert
        className="mt-3"
        type="info"
        message="如果你觉得机器人无法解决当前问题，可以申请转接人工客服。"
        action={
          <Button size="small" onClick={handleClick}>
            转人工
          </Button>
        }
      />
      <Modal
        title="转接人工客服"
        open={open}
        onOk={handleOk}
        onCancel={() => setOpen(false)}
        confirmLoading={loading}
        okText="提交转接"
        cancelText="取消"
      >
        <p className="mb-2 text-sm text-gray-600">
          请简单说明你希望人工客服协助解决的问题，便于我们为你分配合适的专席：
        </p>
        <Input.TextArea
          autoSize={{ minRows: 3, maxRows: 6 }}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
      </Modal>
    </>
  );
};

export default HumanTransfer;

