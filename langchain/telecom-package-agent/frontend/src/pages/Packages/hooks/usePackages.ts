import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiPackage,
  getPackages,
  recommendPackages,
} from "@/services/api";
import type { Package } from "../types";

interface RecommendForm {
  monthlyBudget?: number;
  minDataGb?: number;
  limit: number;
}

interface UsePackagesState {
  packages: Package[];
  loading: boolean;
  error?: string;
  keyword: string;
  targetGroup?: Package["targetGroup"] | "all";
  maxPrice?: number;
  compareIds: string[];
  selectedPackage?: Package;
  recommendationForm: RecommendForm;
  recommendationLoading: boolean;
  recommendationError?: string;
  recommendationPackages: Package[];
}

const extractTargetGroup = (source: string): Package["targetGroup"] => {
  if (/学生|校园/.test(source)) return "student";
  if (/商务|企业/.test(source)) return "business";
  if (/长辈|老人|老年/.test(source)) return "elder";
  return "general";
};

const buildTags = (pkg: ApiPackage): string[] => {
  const tags: string[] = [];
  if (pkg.data_quota_gb >= 80) tags.push("超大流量");
  else if (pkg.data_quota_gb >= 40) tags.push("大流量");
  else if (pkg.data_quota_gb <= 10) tags.push("轻量使用");

  if (pkg.monthly_fee <= 39) tags.push("高性价比");
  if (pkg.monthly_fee >= 99) tags.push("高端套餐");
  if (pkg.validity_days > 30) tags.push(`有效期${pkg.validity_days}天`);

  return Array.from(new Set(tags));
};

const mapPackage = (pkg: ApiPackage): Package => {
  const matchText = `${pkg.name}${pkg.description ?? ""}`;
  return {
    packageId: String(pkg.id),
    rawId: pkg.id,
    name: pkg.name,
    description: pkg.description ?? "暂无套餐描述",
    price: pkg.monthly_fee,
    dataGb: pkg.data_quota_gb,
    voiceMinutes: Math.round(pkg.monthly_fee * 8 + pkg.data_quota_gb * 2),
    smsCount: Math.round(pkg.monthly_fee * 3 + pkg.data_quota_gb),
    validityDays: pkg.validity_days,
    isActive: pkg.is_active,
    benefits: [],
    targetGroup: extractTargetGroup(matchText),
    tags: buildTags(pkg),
    status: pkg.is_active ? "active" : "inactive",
  };
};

export const usePackages = () => {
  const [state, setState] = useState<UsePackagesState>({
    packages: [],
    loading: false,
    keyword: "",
    targetGroup: "all",
    maxPrice: undefined,
    compareIds: [],
    recommendationForm: {
      monthlyBudget: 79,
      minDataGb: 30,
      limit: 3,
    },
    recommendationLoading: false,
    recommendationPackages: [],
  });

  const fetchPackages = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: undefined }));
    try {
      const data = await getPackages();
      const mapped = data.map(mapPackage);
      setState((prev) => ({
        ...prev,
        loading: false,
        packages: mapped,
      }));
    } catch (error: any) {
      const msg =
        error?.response?.data?.detail ??
        error?.message ??
        "获取套餐列表失败，请稍后重试。";
      setState((prev) => ({
        ...prev,
        loading: false,
        error: msg,
      }));
    }
  }, []);

  useEffect(() => {
    void fetchPackages();
  }, [fetchPackages]);

  const filteredPackages = useMemo(() => {
    const { packages, keyword, targetGroup, maxPrice } = state;
    return packages.filter((pkg) => {
      if (targetGroup && targetGroup !== "all" && pkg.targetGroup !== targetGroup) {
        return false;
      }
      if (typeof maxPrice === "number" && pkg.price > maxPrice) {
        return false;
      }
      if (!keyword.trim()) {
        return true;
      }
      const key = keyword.trim().toLowerCase();
      return (
        pkg.name.toLowerCase().includes(key) ||
        pkg.description.toLowerCase().includes(key) ||
        pkg.tags.some((tag) => tag.toLowerCase().includes(key))
      );
    });
  }, [state]);

  const toggleCompare = (packageId: string) => {
    setState((prev) => {
      const exists = prev.compareIds.includes(packageId);
      const compareIds = exists
        ? prev.compareIds.filter((id) => id !== packageId)
        : [...prev.compareIds, packageId].slice(-3);
      return { ...prev, compareIds };
    });
  };

  const comparePackages = useMemo(
    () =>
      state.compareIds
        .map((id) => state.packages.find((pkg) => pkg.packageId === id))
        .filter(Boolean) as Package[],
    [state.compareIds, state.packages]
  );

  const runRecommendation = useCallback(async () => {
    setState((prev) => ({
      ...prev,
      recommendationLoading: true,
      recommendationError: undefined,
    }));
    try {
      const data = await recommendPackages({
        monthly_budget: state.recommendationForm.monthlyBudget,
        min_data_gb: state.recommendationForm.minDataGb,
        limit: state.recommendationForm.limit,
      });
      const mapped = data.recommendations.map(mapPackage);
      setState((prev) => ({
        ...prev,
        recommendationLoading: false,
        recommendationPackages: mapped,
      }));
    } catch (error: any) {
      const msg =
        error?.response?.data?.detail ??
        error?.message ??
        "推荐套餐失败，请稍后重试。";
      setState((prev) => ({
        ...prev,
        recommendationLoading: false,
        recommendationError: msg,
      }));
    }
  }, [state.recommendationForm.limit, state.recommendationForm.minDataGb, state.recommendationForm.monthlyBudget]);

  return {
    loading: state.loading,
    error: state.error,
    packages: filteredPackages,
    rawPackages: state.packages,
    keyword: state.keyword,
    targetGroup: state.targetGroup,
    maxPrice: state.maxPrice,
    compareIds: state.compareIds,
    selectedPackage: state.selectedPackage,
    comparePackages,
    recommendationForm: state.recommendationForm,
    recommendationLoading: state.recommendationLoading,
    recommendationError: state.recommendationError,
    recommendationPackages: state.recommendationPackages,
    setKeyword: (keyword: string) => setState((prev) => ({ ...prev, keyword })),
    setTargetGroup: (targetGroup: UsePackagesState["targetGroup"]) =>
      setState((prev) => ({ ...prev, targetGroup })),
    setMaxPrice: (maxPrice?: number) => setState((prev) => ({ ...prev, maxPrice })),
    toggleCompare,
    selectPackage: (selectedPackage?: Package) =>
      setState((prev) => ({ ...prev, selectedPackage })),
    refreshPackages: fetchPackages,
    setRecommendationForm: (next: Partial<RecommendForm>) =>
      setState((prev) => ({
        ...prev,
        recommendationForm: {
          ...prev.recommendationForm,
          ...next,
        },
      })),
    runRecommendation,
    clearRecommendation: () =>
      setState((prev) => ({
        ...prev,
        recommendationPackages: [],
        recommendationError: undefined,
      })),
  };
};
