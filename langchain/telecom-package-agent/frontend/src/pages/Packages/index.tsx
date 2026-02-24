import React from "react";

import { usePackages } from "./hooks/usePackages";
import PackageCard from "./components/PackageCard";
import PackageDetail from "./components/PackageDetail";
import PackageFilter from "./components/PackageFilter";
import PackageCompare from "./components/PackageCompare";

const PackagesPage: React.FC = () => {
  const {
    loading,
    error,
    packages,
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
  } = usePackages();

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3">
        <h1 className="text-2xl font-bold text-gray-900">流量套餐列表</h1>
        <p className="mt-1 text-sm text-gray-500">
          浏览并筛选适合你的手机套餐，也可以配合聊天页的智能助手一起选择更合适的方案。
        </p>
      </div>

      <PackageFilter
        keyword={keyword}
        targetGroup={targetGroup}
        maxPrice={maxPrice}
        onKeywordChange={setKeyword}
        onTargetGroupChange={setTargetGroup}
        onMaxPriceChange={setMaxPrice}
      />

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

