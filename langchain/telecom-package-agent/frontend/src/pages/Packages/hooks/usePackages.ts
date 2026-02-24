import { useEffect, useMemo, useState } from "react";

import { get } from "@/services/api";
import type { Package } from "../types";

interface UsePackagesState {
  packages: Package[];
  loading: boolean;
  error?: string;
  keyword: string;
  targetGroup?: Package["targetGroup"] | "all";
  maxPrice?: number;
  compareIds: string[];
  selectedPackage?: Package;
}

export const usePackages = () => {
  const [state, setState] = useState<UsePackagesState>({
    packages: [],
    loading: false,
    keyword: "",
    targetGroup: "all",
    maxPrice: undefined,
    compareIds: [],
  });

  useEffect(() => {
    const fetchPackages = async () => {
      setState((prev) => ({ ...prev, loading: true, error: undefined }));
      try {
        // 后端返回的是简化的套餐结构，这里做一层映射到前端丰富类型
        const data = await get<any[]>("/api/v1/packages");
        const mapped: Package[] = data.map((p) => ({
          packageId: String(p.id ?? p.packageId ?? crypto.randomUUID()),
          name: p.name,
          description: p.description ?? "暂无套餐描述",
          price: p.monthly_fee ?? p.price ?? 0,
          dataGb: p.data_quota_gb ?? p.dataGb ?? 0,
          voiceMinutes: p.voiceMinutes ?? 0,
          smsCount: p.smsCount ?? 0,
          benefits: [],
          targetGroup: (p.targetGroup as Package["targetGroup"]) ?? "general",
          tags: p.tags ?? [],
          status: (p.is_active ?? p.status === "active")
            ? "active"
            : "inactive",
        }));

        setState((prev) => ({
          ...prev,
          packages: mapped,
          loading: false,
        }));
      } catch (error: any) {
        const msg =
          error?.response?.data?.detail ??
          error?.message ??
          "获取套餐列表失败，请稍后重试。";
        setState((prev) => ({
          ...prev,
          error: msg,
          loading: false,
        }));
      }
    };

    void fetchPackages();
  }, []);

  const filtered = useMemo(() => {
    const { packages, keyword, targetGroup, maxPrice } = state;
    return packages.filter((p) => {
      if (targetGroup && targetGroup !== "all" && p.targetGroup !== targetGroup) {
        return false;
      }
      if (typeof maxPrice === "number" && p.price > maxPrice) {
        return false;
      }
      if (keyword.trim()) {
        const k = keyword.trim().toLowerCase();
        return (
          p.name.toLowerCase().includes(k) ||
          p.description.toLowerCase().includes(k) ||
          p.tags.some((t) => t.toLowerCase().includes(k))
        );
      }
      return true;
    });
  }, [state]);

  const toggleCompare = (packageId: string) => {
    setState((prev) => {
      const exists = prev.compareIds.includes(packageId);
      const compareIds = exists
        ? prev.compareIds.filter((id) => id !== packageId)
        : [...prev.compareIds, packageId].slice(-3); // 最多对比 3 个
      return { ...prev, compareIds };
    });
  };

  const selectPackage = (pkg?: Package) => {
    setState((prev) => ({ ...prev, selectedPackage: pkg }));
  };

  const setKeyword = (keyword: string) => {
    setState((prev) => ({ ...prev, keyword }));
  };

  const setTargetGroup = (targetGroup: UsePackagesState["targetGroup"]) => {
    setState((prev) => ({ ...prev, targetGroup }));
  };

  const setMaxPrice = (maxPrice?: number) => {
    setState((prev) => ({ ...prev, maxPrice }));
  };

  const comparePackages = useMemo(
    () =>
      state.compareIds
        .map((id) => state.packages.find((p) => p.packageId === id))
        .filter(Boolean) as Package[],
    [state.compareIds, state.packages]
  );

  return {
    loading: state.loading,
    error: state.error,
    packages: filtered,
    rawPackages: state.packages,
    keyword: state.keyword,
    targetGroup: state.targetGroup,
    maxPrice: state.maxPrice,
    compareIds: state.compareIds,
    selectedPackage: state.selectedPackage,
    setKeyword,
    setTargetGroup,
    setMaxPrice,
    toggleCompare,
    selectPackage,
    comparePackages,
  };
};

