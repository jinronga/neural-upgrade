import React, { useEffect, useMemo, useState } from "react";

import { useUser } from "@/contexts/UserContext";
import {
  ApiUserPackageRelation,
  assignUserPackage,
  getCurrentUserPackage,
} from "@/services/api";
import type { Package } from "../types";

interface UserPackageBindingProps {
  packages: Package[];
  onAssigned?: () => void | Promise<void>;
}

const formatDateTime = (value?: string | null) => {
  if (!value) return "未设置";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
};

const UserPackageBinding: React.FC<UserPackageBindingProps> = ({
  packages,
  onAssigned,
}) => {
  const { userId, userPhone } = useUser();
  const [selectedPackageId, setSelectedPackageId] = useState<string>("");
  const [currentPackage, setCurrentPackage] =
    useState<ApiUserPackageRelation | undefined>(undefined);
  const [loadingCurrent, setLoadingCurrent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);
  const [success, setSuccess] = useState<string | undefined>(undefined);

  const activePackages = useMemo(
    () => packages.filter((item) => item.isActive),
    [packages]
  );

  const fetchCurrentPackage = async (
    nextUserId: string,
    cancelled?: () => boolean
  ) => {
    setLoadingCurrent(true);
    setError(undefined);
    try {
      const resp = await getCurrentUserPackage(nextUserId);
      if (cancelled?.()) return;
      const current = resp.item ?? undefined;
      setCurrentPackage(current);
      setSelectedPackageId((prev) => {
        if (current) return String(current.package_id);
        if (prev && activePackages.some((item) => item.packageId === prev)) {
          return prev;
        }
        return activePackages[0]?.packageId ?? "";
      });
    } catch (err: any) {
      if (cancelled?.()) return;
      const message =
        err?.response?.data?.detail ??
        err?.message ??
        "加载当前套餐失败，请稍后重试。";
      setError(message);
      setCurrentPackage(undefined);
    } finally {
      if (!cancelled?.()) {
        setLoadingCurrent(false);
      }
    }
  };

  useEffect(() => {
    let isCancelled = false;
    void fetchCurrentPackage(userId, () => isCancelled);

    return () => {
      isCancelled = true;
    };
  }, [activePackages, userId]);

  const remainingDays = useMemo(() => {
    if (!currentPackage?.end_date) return undefined;
    const diffMs = new Date(currentPackage.end_date).getTime() - Date.now();
    return Math.max(0, Math.ceil(diffMs / (1000 * 60 * 60 * 24)));
  }, [currentPackage?.end_date]);

  const handleAssign = async () => {
    if (!selectedPackageId) {
      setError("请先选择一个套餐。");
      return;
    }

    setSubmitting(true);
    setError(undefined);
    setSuccess(undefined);
    try {
      const relation = await assignUserPackage(userId, {
        package_id: Number(selectedPackageId),
      });
      setCurrentPackage(relation);
      setSuccess(
        `已切换为「${relation.package_name}」，到期时间 ${formatDateTime(
          relation.end_date
        )}。`
      );
      await onAssigned?.();
    } catch (err: any) {
      const message =
        err?.response?.data?.detail ?? err?.message ?? "切换套餐失败，请稍后再试。";
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mb-4 rounded-2xl border border-cyan-200 bg-gradient-to-r from-cyan-50 via-white to-sky-50 p-4 shadow-sm">
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-slate-900">手机号套餐绑定</h2>
          <p className="text-xs text-slate-500">
            当前号码：{userPhone ?? "未识别"}（用户ID: {userId}）
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setSuccess(undefined);
            void fetchCurrentPackage(userId);
          }}
          className="rounded-full border border-slate-300 bg-white px-3 py-1 text-xs text-slate-700 hover:bg-slate-50"
        >
          刷新当前状态
        </button>
      </div>

      <div className="grid gap-2 md:grid-cols-[1fr_auto]">
        <select
          value={selectedPackageId}
          onChange={(e) => setSelectedPackageId(e.target.value)}
          className="h-10 rounded-xl border border-cyan-200 bg-white px-3 text-sm text-slate-800 outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
        >
          {activePackages.length === 0 ? (
            <option value="">暂无可选套餐</option>
          ) : (
            activePackages.map((pkg) => (
              <option key={pkg.packageId} value={pkg.packageId}>
                {pkg.name} · ¥{pkg.price}/月 · {pkg.validityDays}天
              </option>
            ))
          )}
        </select>
        <button
          type="button"
          disabled={submitting || loadingCurrent || activePackages.length === 0}
          onClick={() => void handleAssign()}
          className="h-10 rounded-xl bg-slate-900 px-4 text-xs font-medium text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? "切换中..." : "绑定/切换套餐"}
        </button>
      </div>

      {error && (
        <div className="mt-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
          {error}
        </div>
      )}
      {success && (
        <div className="mt-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
          {success}
        </div>
      )}

      <div className="mt-3 rounded-xl border border-slate-200 bg-white/80 p-3 text-xs text-slate-600">
        {loadingCurrent ? (
          <p>正在加载当前套餐信息...</p>
        ) : currentPackage ? (
          <div className="grid gap-1 md:grid-cols-2">
            <p>
              当前套餐：<span className="font-medium text-slate-900">{currentPackage.package_name}</span>
            </p>
            <p>
              月费：<span className="font-medium text-slate-900">¥{currentPackage.monthly_fee}</span>
            </p>
            <p>生效时间：{formatDateTime(currentPackage.start_date)}</p>
            <p>到期时间：{formatDateTime(currentPackage.end_date)}</p>
            <p>有效期：{currentPackage.validity_days} 天</p>
            <p>剩余天数：{remainingDays ?? "未知"} 天</p>
          </div>
        ) : (
          <p>当前手机号尚未绑定生效中的套餐。</p>
        )}
      </div>
    </div>
  );
};

export default UserPackageBinding;
