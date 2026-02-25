import React from "react";

interface Props {
  suggestions: string[];
  onClick: (content: string) => void;
}

const SuggestionChips: React.FC<Props> = ({ suggestions, onClick }) => {
  if (!suggestions.length) return null;

  return (
    <div className="mt-2 flex flex-wrap gap-2">
      {suggestions.map((text, idx) => (
        <button
          key={`${text}-${idx}`}
          type="button"
          onClick={() => onClick(text)}
          className="rounded-full bg-blue-50 px-3 py-1 text-xs text-blue-700 ring-1 ring-inset ring-blue-200 transition hover:bg-blue-100 hover:text-blue-800"
        >
          {text}
        </button>
      ))}
    </div>
  );
};

export default SuggestionChips;

