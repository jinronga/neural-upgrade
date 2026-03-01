import React from "react";

import { usePackages } from "./hooks/usePackages";
import PackageCard from "./components/PackageCard";
import PackageDetail from "./components/PackageDetail";
import PackageFilter from "./components/PackageFilter";
import PackageCompare from "./components/PackageCompare";
import PackageManager from "./components/PackageManager";
import UserPackageBinding from "./components/UserPackageBinding";

const PackagesPage: React.FC = () => {
  const {
    loading,
    error,
    packages,
    rawPackages,
    keyword,
    targetGroup,
    maxPrice,
    compareIds,
    selectedPackage,
    setKeyword,
    setTargetGroup,
    setMaxPrice,
    toggleCompare,
    selectPackage,
    comparePackages,
    recommendationForm,
    recommendationLoading,
    recommendationError,
    recommendationPackages,
    setRecommendationForm,
    runRecommendation,
    clearRecommendation,
    refreshPackages,
  } = usePackages();

  const handlePackagesChanged = async () => {
    await refreshPackages();
    clearRecommendation();
  };

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3">
        <h1 className="text-2xl font-bold text-gray-900">流量套餐列表</h1>
        <p className="mt-1 text-sm text-gray-500">
          浏览并筛选适合你的手机套餐，也可以配合聊天页的智能助手一起选择更合适的方案。
        </p>
      </div>

      <PackageManager onChanged={handlePackagesChanged} />
      <UserPackageBinding packages={rawPackages} />

      <PackageFilter
        keyword={keyword}
        targetGroup={targetGroup}
        maxPrice={maxPrice}
        onKeywordChange={setKeyword}
        onTargetGroupChange={setTargetGroup}
        onMaxPriceChange={setMaxPrice}
      />

      <div className="mb-4 rounded-2xl border border-cyan-100 bg-gradient-to-r from-cyan-50 to-sky-50 p-4 shadow-sm">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">智能推荐</h2>
            <p className="text-xs text-slate-500">
              根据预算和最低流量需求，调用后端推荐接口返回候选套餐。
            </p>
          </div>
          <button
            type="button"
            onClick={() => void runRecommendation()}
            className="rounded-full bg-slate-900 px-4 py-1.5 text-xs font-medium text-white transition hover:bg-slate-700"
          >
            {recommendationLoading ? "推荐中…" : "开始推荐"}
          </button>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            预算上限（元/月）
            <input
              type="number"
              min={0}
              value={recommendationForm.monthlyBudget ?? ""}
              onChange={(e) =>
                setRecommendationForm({
                  monthlyBudget:
                    e.target.value === "" ? undefined : Number(e.target.value),
                })
              }
              className="h-9 rounded-full border border-cyan-200 bg-white px-3 text-slate-900 outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            最低流量需求（GB）
            <input
              type="number"
              min={0}
              value={recommendationForm.minDataGb ?? ""}
              onChange={(e) =>
                setRecommendationForm({
                  minDataGb:
                    e.target.value === "" ? undefined : Number(e.target.value),
                })
              }
              className="h-9 rounded-full border border-cyan-200 bg-white px-3 text-slate-900 outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-slate-600">
            返回条数
            <input
              type="number"
              min={1}
              max={5}
              value={recommendationForm.limit}
              onChange={(e) =>
                setRecommendationForm({
                  limit: Math.min(5, Math.max(1, Number(e.target.value) || 1)),
                })
              }
              className="h-9 rounded-full border border-cyan-200 bg-white px-3 text-slate-900 outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
            />
          </label>
        </div>
        {recommendationError && (
          <p className="mt-2 text-xs text-red-600">{recommendationError}</p>
        )}
        {recommendationPackages.length > 0 && (
          <div className="mt-3">
            <div className="mb-2 flex items-center justify-between text-xs text-slate-600">
              <span>推荐结果</span>
              <button
                type="button"
                onClick={clearRecommendation}
                className="rounded-full border border-slate-200 px-2 py-0.5 text-[11px] text-slate-500 hover:bg-white"
              >
                清空
              </button>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {recommendationPackages.map((pkg) => (
                <PackageCard
                  key={`recommend-${pkg.packageId}`}
                  pkg={pkg}
                  selectedForCompare={compareIds.includes(pkg.packageId)}
                  onViewDetail={() => selectPackage(pkg)}
                  onToggleCompare={() => toggleCompare(pkg.packageId)}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-2 rounded-xl bg-red-50 px-3 py-2 text-xs text-red-600">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-hidden rounded-2xl border border-gray-200 bg-gray-50 p-4">
        {loading && !packages.length ? (
          <div className="flex h-full items-center justify-center text-sm text-gray-500">
            正在加载套餐数据，请稍候…
          </div>
        ) : packages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-gray-500">
            暂无符合条件的套餐，可以尝试放宽筛选条件或咨询智能助手。
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {packages.map((pkg) => (
              <PackageCard
                key={pkg.packageId}
                pkg={pkg}
                selectedForCompare={compareIds.includes(pkg.packageId)}
                onViewDetail={() => selectPackage(pkg)}
                onToggleCompare={() => toggleCompare(pkg.packageId)}
              />
            ))}
          </div>
        )}
      </div>

      <PackageCompare packages={comparePackages} />

      <PackageDetail
        pkg={selectedPackage}
        open={!!selectedPackage}
        onClose={() => selectPackage(undefined)}
      />
    </div>
  );
};

export default PackagesPage;
