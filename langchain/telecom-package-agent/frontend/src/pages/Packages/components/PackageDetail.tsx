import React from "react";

import type { Package } from "../types";

interface Props {
  pkg?: Package;
  open: boolean;
  onClose: () => void;
}

const PackageDetail: React.FC<Props> = ({ pkg, open, onClose }) => {
  if (!open || !pkg) return null;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40">
      <div className="max-h-[80vh] w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3">
          <h2 className="text-base font-semibold text-gray-900">
            套餐详情
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>
        <div className="max-h-[70vh] space-y-3 overflow-y-auto px-5 py-4 text-sm">
          <div className="flex items-baseline justify-between">
            <div>
              <div className="mb-1 text-lg font-semibold text-gray-900">
                {pkg.name}
              </div>
              <div className="text-xs text-gray-500">
                {pkg.targetGroup === "student"
                  ? "适合学生用户，注重流量和性价比"
                  : pkg.targetGroup === "business"
                  ? "适合商务用户，语音与全国漫游友好"
                  : pkg.targetGroup === "elder"
                  ? "适合长辈用户，语音为主、操作简单"
                  : "适合大多数用户的通用套餐"}
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-blue-600">
                ¥{pkg.price.toFixed(0)}
              </div>
              <div className="text-xs text-gray-400">/月</div>
            </div>
          </div>

          <div className="rounded-xl bg-gray-50 px-3 py-2">
            <div className="mb-1 text-xs font-semibold text-gray-700">
              资源配置
            </div>
            <div className="flex flex-wrap gap-3 text-xs text-gray-600">
              <span>流量 {pkg.dataGb} GB</span>
              <span>语音 {pkg.voiceMinutes} 分钟</span>
              <span>短信 {pkg.smsCount} 条</span>
            </div>
          </div>

          {pkg.tags.length > 0 && (
            <div>
              <div className="mb-1 text-xs font-semibold text-gray-700">
                标签
              </div>
              <div className="flex flex-wrap gap-2">
                {pkg.tags.map((tag) => (
                  <span
                    key={tag}
                    className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] text-blue-700"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div>
            <div className="mb-1 text-xs font-semibold text-gray-700">
              套餐说明
            </div>
            <p className="text-xs leading-relaxed text-gray-600">
              {pkg.description || "暂无详细说明，可咨询客服获取更多信息。"}
            </p>
          </div>

          {pkg.benefits.length > 0 && (
            <div>
              <div className="mb-1 text-xs font-semibold text-gray-700">
                含权益
              </div>
              <ul className="space-y-1 text-xs text-gray-600">
                {pkg.benefits.map((b) => (
                  <li
                    key={b.benefitId}
                    className="flex items-center gap-1"
                  >
                    <span className="text-sm">{b.icon}</span>
                    <span className="font-medium">{b.name}</span>
                    <span className="text-gray-400">({b.type})</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
        <div className="flex justify-end gap-3 border-t border-gray-100 px-5 py-3 text-xs">
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-gray-300 px-4 py-1.5 text-gray-700 hover:bg-gray-50"
          >
            关闭
          </button>
          <button
            type="button"
            className="rounded-full bg-blue-600 px-4 py-1.5 font-medium text-white hover:bg-blue-700"
          >
            办理此套餐
          </button>
        </div>
      </div>
    </div>
  );
};

export default PackageDetail;

