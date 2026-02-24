import React from "react";
import { Tag } from "antd";

interface Props {
  suggestions: string[];
  onClick: (content: string) => void;
}

const SuggestionChips: React.FC<Props> = ({ suggestions, onClick }) => {
  if (!suggestions.length) return null;

  return (
    <div className="mt-2 space-x-2">
      {suggestions.map((text, idx) => (
        <Tag
          key={`${text}-${idx}`}
          color="blue"
          className="cursor-pointer mb-1"
          onClick={() => onClick(text)}
        >
          {text}
        </Tag>
      ))}
    </div>
  );
};

export default SuggestionChips;

