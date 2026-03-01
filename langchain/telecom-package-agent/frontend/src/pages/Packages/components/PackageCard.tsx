import React from "react";

import type { Package } from "../types";

interface Props {
  pkg: Package;
  selectedForCompare: boolean;
  onViewDetail: () => void;
  onToggleCompare: () => void;
}

const PackageCard: React.FC<Props> = ({
  pkg,
  selectedForCompare,
  onViewDetail,
  onToggleCompare,
}) => {
  return (
    <div className="flex flex-col rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md">
      <div className="mb-1 flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-900">
          {pkg.name}
        </h3>
        <span className="rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-600">
          {pkg.targetGroup === "student"
            ? "学生专享"
            : pkg.targetGroup === "business"
            ? "商务人士"
            : pkg.targetGroup === "elder"
            ? "长辈关怀"
            : "通用套餐"}
        </span>
      </div>
      <p className="mb-2 line-clamp-2 text-xs text-gray-500">
        {pkg.description}
      </p>
      <div className="mb-2 flex items-baseline gap-2">
        <span className="text-xl font-bold text-blue-600">
          ¥{pkg.price.toFixed(0)}
        </span>
        <span className="text-xs text-gray-400">/月</span>
      </div>
      <div className="mb-3 flex flex-wrap gap-3 text-xs text-gray-600">
        <span>流量 {pkg.dataGb}GB</span>
        <span>语音 {pkg.voiceMinutes} 分钟</span>
        <span>短信 {pkg.smsCount} 条</span>
        <span>有效期 {pkg.validityDays} 天</span>
      </div>
      <div className="mb-3 flex flex-wrap gap-1">
        {pkg.tags.slice(0, 4).map((tag) => (
          <span
            key={tag}
            className="rounded-full bg-gray-100 px-2 py-0.5 text-[11px] text-gray-600"
          >
            {tag}
          </span>
        ))}
      </div>
      <div className="mt-auto flex items-center justify-between gap-2 pt-2">
        <span
          className={`rounded-full px-2 py-0.5 text-[11px] ${
            pkg.isActive
              ? "bg-emerald-50 text-emerald-700"
              : "bg-gray-100 text-gray-500"
          }`}
        >
          {pkg.isActive ? "在售" : "已下架"}
        </span>
        <button
          type="button"
          onClick={onViewDetail}
          className="rounded-full border border-blue-500 px-3 py-1 text-xs font-medium text-blue-600 transition hover:bg-blue-50"
        >
          查看详情
        </button>
        <button
          type="button"
          onClick={onToggleCompare}
          className={`rounded-full px-3 py-1 text-xs font-medium transition ${
            selectedForCompare
              ? "bg-emerald-500 text-white hover:bg-emerald-600"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          {selectedForCompare ? "已加入对比" : "加入对比"}
        </button>
      </div>
    </div>
  );
};

export default PackageCard;
