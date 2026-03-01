import React, { useCallback, useEffect, useState } from "react";

import { useUser } from "@/contexts/UserContext";
import {
  ApiBenefit,
  claimBenefit,
  getPendingBenefits,
  getUserBenefits,
} from "@/services/api";

interface BenefitsState {
  loading: boolean;
  claimingId?: number;
  error?: string;
  success?: string;
  pending: ApiBenefit[];
  claimed: ApiBenefit[];
}

const BenefitsPage: React.FC = () => {
  const { userId, userPhone } = useUser();
  const [state, setState] = useState<BenefitsState>({
    loading: true,
    pending: [],
    claimed: [],
  });

  const fetchBenefits = useCallback(async () => {
    setState((prev) => ({
      ...prev,
      loading: true,
      error: undefined,
      success: undefined,
    }));
    try {
      const [pending, claimed] = await Promise.all([
        getPendingBenefits(userId),
        getUserBenefits(userId),
      ]);
      setState((prev) => ({
        ...prev,
        loading: false,
        pending,
        claimed,
      }));
    } catch (error: any) {
      const message =
        error?.response?.data?.detail ??
        error?.message ??
        "权益信息加载失败，请稍后重试。";
      setState((prev) => ({
        ...prev,
        loading: false,
        error: message,
      }));
    }
  }, [userId]);

  useEffect(() => {
    void fetchBenefits();
  }, [fetchBenefits]);

  const handleClaim = async (benefitId: number) => {
    setState((prev) => ({
      ...prev,
      claimingId: benefitId,
      error: undefined,
      success: undefined,
    }));

    try {
      await claimBenefit({
        user_id: Number(userId),
        benefit_id: benefitId,
      });
      const [pending, claimed] = await Promise.all([
        getPendingBenefits(userId),
        getUserBenefits(userId),
      ]);

      setState((prev) => ({
        ...prev,
        claimingId: undefined,
        pending,
        claimed,
        success: `权益 #${benefitId} 领取成功`,
      }));
    } catch (error: any) {
      const message =
        error?.response?.data?.detail ?? error?.message ?? "领取失败，请稍后重试。";
      setState((prev) => ({
        ...prev,
        claimingId: undefined,
        error: message,
      }));
    }
  };
  const userDisplay = userPhone ? userPhone : `ID:${userId}`;

  return (
    <div className="space-y-4">
      <div className="rounded-3xl bg-gradient-to-r from-emerald-700 to-cyan-700 p-5 text-white shadow-xl">
        <div className="text-[11px] uppercase tracking-[0.2em] text-emerald-100/90">
          Benefit Center
        </div>
        <h1 className="mt-1 text-2xl font-black">权益中心</h1>
        <p className="mt-2 text-sm text-emerald-100/90">
          当前用户：{userDisplay}，可在这里领取待发放权益并查看已领取记录。
        </p>
      </div>

      {state.error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
          {state.error}
        </div>
      )}
      {state.success && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
          {state.success}
        </div>
      )}

      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">待领取权益</h2>
            <button
              type="button"
              onClick={() => void fetchBenefits()}
              className="rounded-full border border-slate-200 px-3 py-1 text-[11px] text-slate-500 hover:bg-slate-50"
            >
              刷新
            </button>
          </div>
          {state.loading ? (
            <div className="rounded-xl bg-slate-50 px-3 py-6 text-center text-xs text-slate-500">
              正在加载待领权益…
            </div>
          ) : state.pending.length === 0 ? (
            <div className="rounded-xl bg-slate-50 px-3 py-6 text-center text-xs text-slate-500">
              暂无待领取权益
            </div>
          ) : (
            <div className="space-y-2">
              {state.pending.map((benefit) => (
                <div
                  key={benefit.id}
                  className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium text-slate-900">
                        {benefit.name}
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {benefit.description || "暂无权益描述"}
                      </p>
                      <p className="mt-1 text-[11px] text-slate-400">
                        剩余库存：{benefit.inventory}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => void handleClaim(benefit.id)}
                      disabled={state.claimingId === benefit.id}
                      className={`rounded-full px-3 py-1 text-xs font-medium transition ${
                        state.claimingId === benefit.id
                          ? "cursor-not-allowed bg-slate-300 text-white"
                          : "bg-emerald-600 text-white hover:bg-emerald-700"
                      }`}
                    >
                      {state.claimingId === benefit.id ? "领取中…" : "立即领取"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-100">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-900">已领取权益</h2>
            <span className="text-xs text-slate-500">{state.claimed.length} 项</span>
          </div>
          {state.loading ? (
            <div className="rounded-xl bg-slate-50 px-3 py-6 text-center text-xs text-slate-500">
              正在加载已领权益…
            </div>
          ) : state.claimed.length === 0 ? (
            <div className="rounded-xl bg-slate-50 px-3 py-6 text-center text-xs text-slate-500">
              暂无已领取权益
            </div>
          ) : (
            <div className="space-y-2">
              {state.claimed.map((benefit) => (
                <div
                  key={`claimed-${benefit.id}`}
                  className="rounded-xl border border-emerald-100 bg-emerald-50/60 px-3 py-3"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium text-slate-900">
                        {benefit.name}
                      </div>
                      <p className="mt-1 text-xs text-slate-500">
                        {benefit.description || "暂无权益描述"}
                      </p>
                    </div>
                    <span className="rounded-full bg-emerald-600 px-2 py-0.5 text-[11px] text-white">
                      已领取
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  );
};

export default BenefitsPage;
