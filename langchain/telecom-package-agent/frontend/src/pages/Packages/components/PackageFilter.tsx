import React from "react";

import type { Package } from "../types";

interface Props {
  keyword: string;
  targetGroup?: Package["targetGroup"] | "all";
  maxPrice?: number;
  onKeywordChange: (value: string) => void;
  onTargetGroupChange: (value: Package["targetGroup"] | "all") => void;
  onMaxPriceChange: (value?: number) => void;
}

const PackageFilter: React.FC<Props> = ({
  keyword,
  targetGroup = "all",
  maxPrice,
  onKeywordChange,
  onTargetGroupChange,
  onMaxPriceChange,
}) => {
  return (
    <div className="mb-4 flex flex-wrap items-end gap-3 rounded-2xl bg-white px-4 py-3 shadow-sm ring-1 ring-gray-100">
      <div className="flex min-w-[200px] flex-1 flex-col gap-1">
        <label className="text-xs font-medium text-gray-600">
          关键词
        </label>
        <input
          type="text"
          value={keyword}
          onChange={(e) => onKeywordChange(e.target.value)}
          placeholder="输入套餐名称、标签，如“通用”“学生”“大流量”等…"
          className="h-9 rounded-full border border-gray-300 px-3 text-xs text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        />
      </div>
      <div className="flex w-36 flex-col gap-1">
        <label className="text-xs font-medium text-gray-600">
          适用人群
        </label>
        <select
          value={targetGroup}
          onChange={(e) =>
            onTargetGroupChange(e.target.value as Package["targetGroup"] | "all")
          }
          className="h-9 rounded-full border border-gray-300 bg-white px-3 text-xs text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        >
          <option value="all">全部</option>
          <option value="student">学生</option>
          <option value="business">商务</option>
          <option value="elder">长辈</option>
          <option value="general">通用</option>
        </select>
      </div>
      <div className="flex w-40 flex-col gap-1">
        <label className="text-xs font-medium text-gray-600">
          最高月费（元）
        </label>
        <input
          type="number"
          min={0}
          value={typeof maxPrice === "number" ? maxPrice : ""}
          onChange={(e) => {
            const v = e.target.value;
            onMaxPriceChange(v === "" ? undefined : Number(v));
          }}
          placeholder="不限"
          className="h-9 rounded-full border border-gray-300 px-3 text-xs text-gray-900 shadow-sm outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        />
      </div>
      <div className="ml-auto flex flex-col items-end gap-1 text-[11px] text-gray-400">
        <span>提示：你也可以让聊天页的智能助手根据使用情况帮你推荐套餐。</span>
      </div>
    </div>
  );
};

export default PackageFilter;

