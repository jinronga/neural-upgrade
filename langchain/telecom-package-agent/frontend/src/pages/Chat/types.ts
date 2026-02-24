export interface Message {
  id: string;
  type: "user" | "agent" | "system" | "human";
  content: string;
  timestamp: Date;
  suggestions?: string[];
  quickReplies?: string[];
}

export interface ChatResponse {
  sessionId: string;
  response: string;
  suggestions: string[];
  quickReplies: string[];
  needHuman: boolean;
  humanTransferReason?: string;
}

