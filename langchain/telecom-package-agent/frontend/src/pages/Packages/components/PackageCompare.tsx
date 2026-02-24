import React from "react";

import type { Package } from "../types";

interface Props {
  packages: Package[];
}

const PackageCompare: React.FC<Props> = ({ packages }) => {
  if (!packages.length) return null;

  return (
    <div className="mt-4 rounded-2xl bg-white p-3 shadow-sm ring-1 ring-gray-100">
      <div className="mb-2 flex items-center justify-between text-xs text-gray-600">
        <span>套餐对比（最多 3 个）</span>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {packages.map((p) => (
          <div
            key={p.packageId}
            className="rounded-xl border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700"
          >
            <div className="mb-1 text-sm font-semibold text-gray-900">
              {p.name}
            </div>
            <div className="mb-1 text-gray-500">
              月费 ¥{p.price.toFixed(0)}
            </div>
            <div className="mb-1 flex flex-wrap gap-2">
              <span>流量 {p.dataGb}GB</span>
              <span>语音 {p.voiceMinutes} 分钟</span>
              <span>短信 {p.smsCount} 条</span>
            </div>
            <div className="mt-1 text-[11px] text-gray-500">
              {p.description}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PackageCompare;

