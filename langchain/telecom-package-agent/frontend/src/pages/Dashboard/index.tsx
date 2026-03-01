import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useUser } from "@/contexts/UserContext";
import {
  ApiBenefit,
  ApiUserPackageRelation,
  ApiUsageCurrent,
  ApiUsageHistoryItem,
  ApiUser,
  getCurrentUsage,
  getCurrentUserPackage,
  getPendingBenefits,
  getUsageHistory,
  getUserBenefits,
  getUserInfo,
} from "@/services/api";
import { formatCurrency } from "@/utils";

interface DashboardState {
  loading: boolean;
  error?: string;
  user?: ApiUser;
  currentPackage?: ApiUserPackageRelation;
  currentUsage?: ApiUsageCurrent;
  usageHistory: ApiUsageHistoryItem[];
  pendingBenefits: ApiBenefit[];
  claimedBenefits: ApiBenefit[];
}

const DashboardPage: React.FC = () => {
  const { userId, userPhone } = useUser();
  const [state, setState] = useState<DashboardState>({
    loading: true,
    usageHistory: [],
    pendingBenefits: [],
    claimedBenefits: [],
  });

  useEffect(() => {
    let cancelled = false;

    const fetchDashboard = async () => {
      setState((prev) => ({ ...prev, loading: true, error: undefined }));
      try {
        const user = await getUserInfo(userId);

        const [currentPackageRes, usageRes, historyRes, pendingRes, claimedRes] =
          await Promise.allSettled([
            getCurrentUserPackage(userId),
            getCurrentUsage(userId),
            getUsageHistory(userId),
            getPendingBenefits(userId),
            getUserBenefits(userId),
          ]);

        if (cancelled) return;

        const errors: string[] = [];
        if (currentPackageRes.status === "rejected") {
          errors.push("当前套餐加载失败");
        }
        if (usageRes.status === "rejected") {
          errors.push("当前用量加载失败");
        }
        if (historyRes.status === "rejected") {
          errors.push("历史用量加载失败");
        }
        if (pendingRes.status === "rejected") {
          errors.push("待领权益加载失败");
        }
        if (claimedRes.status === "rejected") {
          errors.push("已领权益加载失败");
        }

        setState({
          loading: false,
          error: errors.length ? `${errors.join("，")}。` : undefined,
          user,
          currentPackage:
            currentPackageRes.status === "fulfilled"
              ? currentPackageRes.value.item ?? undefined
              : undefined,
          currentUsage: usageRes.status === "fulfilled" ? usageRes.value : undefined,
          usageHistory: historyRes.status === "fulfilled" ? historyRes.value : [],
          pendingBenefits:
            pendingRes.status === "fulfilled" ? pendingRes.value : [],
          claimedBenefits:
            claimedRes.status === "fulfilled" ? claimedRes.value : [],
        });
      } catch (error: any) {
        if (cancelled) return;
        const message =
          error?.response?.data?.detail ??
          error?.message ??
          "仪表盘加载失败，请稍后重试。";
        setState((prev) => ({
          ...prev,
          loading: false,
          error: message,
        }));
      }
    };

    void fetchDashboard();

    return () => {
      cancelled = true;
    };
  }, [userId]);

  const currentPackage = state.currentPackage;
  const quotaMb = (currentPackage?.data_quota_gb ?? 0) * 1024;
  const usedMb = state.currentUsage?.total_used_mb ?? 0;
  const usagePercent = quotaMb > 0 ? Math.min(100, (usedMb / quotaMb) * 100) : 0;
  const remainingMb = Math.max(0, quotaMb - usedMb);

  const historyData = useMemo(
    () =>
      state.usageHistory
        .slice(0, 7)
        .reverse()
        .map((item) => ({
          ...item,
          dateLabel: new Date(item.record_time).toLocaleDateString("zh-CN", {
            month: "numeric",
            day: "numeric",
          }),
        })),
    [state.usageHistory]
  );

  const maxHistoryUsage = useMemo(() => {
    if (!historyData.length) return 0;
    return Math.max(...historyData.map((x) => x.used_mb));
  }, [historyData]);
  const userDisplay = userPhone || state.user?.phone_number || `ID:${userId}`;

  return (
    <div className="space-y-4">
      <div className="rounded-3xl bg-gradient-to-r from-slate-900 via-slate-800 to-cyan-800 p-5 text-white shadow-xl">
        <div className="text-[11px] uppercase tracking-[0.2em] text-cyan-200/90">
          User Snapshot
        </div>
        <h1 className="mt-1 text-2xl font-black">业务联调仪表盘</h1>
        <p className="mt-2 text-sm text-cyan-100/90">
          当前用户：{userDisplay}
          {state.user?.name ? ` · ${state.user.name}` : ""}
        </p>
        <p className="mt-1 text-xs text-cyan-100/80">
          页面数据来自 `/users`、`/usage`、`/benefits` 等接口。
        </p>
      </div>

      {state.error && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700">
          {state.error}
        </div>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
          <div className="text-xs text-slate-500">当前套餐</div>
          <div className="mt-1 text-base font-semibold text-slate-900">
            {currentPackage?.package_name ?? "暂无套餐"}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {currentPackage
              ? `${formatCurrency(currentPackage.monthly_fee)} / 月 · ${currentPackage.data_quota_gb} GB`
              : "请先绑定套餐"}
          </div>
        </div>

        <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
          <div className="text-xs text-slate-500">当前流量使用</div>
          <div className="mt-1 text-base font-semibold text-slate-900">
            {(usedMb / 1024).toFixed(2)} GB
          </div>
          <div className="mt-1 text-xs text-slate-500">
            剩余 {(remainingMb / 1024).toFixed(2)} GB
          </div>
        </div>

        <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
          <div className="text-xs text-slate-500">待领取权益</div>
          <div className="mt-1 text-base font-semibold text-slate-900">
            {state.pendingBenefits.length}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            已领取 {state.claimedBenefits.length} 项
          </div>
        </div>

        <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
          <div className="text-xs text-slate-500">最近记录条数</div>
          <div className="mt-1 text-base font-semibold text-slate-900">
            {state.usageHistory.length}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {state.loading ? "数据加载中…" : "来自 /usage/history"}
          </div>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
        <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">流量使用进度</h2>
            <span className="text-xs text-slate-500">
              {quotaMb > 0 ? `${usagePercent.toFixed(1)}%` : "暂无套餐额度"}
            </span>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-slate-100">
            <div
              className={`h-full rounded-full ${
                usagePercent > 85
                  ? "bg-red-500"
                  : usagePercent > 60
                  ? "bg-amber-500"
                  : "bg-emerald-500"
              }`}
              style={{ width: `${usagePercent}%` }}
            />
          </div>
          <div className="mt-2 text-xs text-slate-500">
            已用 {usedMb.toFixed(0)} MB / 总额 {quotaMb.toFixed(0)} MB
          </div>
        </div>

        <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">快捷入口</h2>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <Link
              to="/chat"
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
            >
              去智能咨询
            </Link>
            <Link
              to="/packages"
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
            >
              去看套餐
            </Link>
            <Link
              to="/benefits"
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
            >
              去领权益
            </Link>
            <button
              type="button"
              onClick={() => window.location.assign("/chat")}
              className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-left text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
            >
              人工客服
            </button>
          </div>
        </div>
      </div>

      <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-900">近 7 条用量趋势</h2>
          <span className="text-xs text-slate-500">
            接口：/api/v1/usage/history/{userId}
          </span>
        </div>
        {historyData.length === 0 ? (
          <div className="rounded-xl bg-slate-50 px-3 py-5 text-center text-xs text-slate-500">
            暂无历史用量数据
          </div>
        ) : (
          <div className="grid grid-cols-7 gap-3">
            {historyData.map((item) => {
              const height =
                maxHistoryUsage > 0
                  ? Math.max(12, Math.round((item.used_mb / maxHistoryUsage) * 120))
                  : 12;

              return (
                <div
                  key={item.id}
                  className="flex flex-col items-center justify-end gap-2"
                >
                  <div className="text-[10px] text-slate-400">
                    {Math.round(item.used_mb)}MB
                  </div>
                  <div className="flex h-32 w-full max-w-10 items-end rounded-lg bg-slate-100 p-1">
                    <div
                      className="w-full rounded-md bg-gradient-to-t from-cyan-500 to-sky-300"
                      style={{ height }}
                    />
                  </div>
                  <div className="text-[10px] text-slate-400">{item.dateLabel}</div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;
