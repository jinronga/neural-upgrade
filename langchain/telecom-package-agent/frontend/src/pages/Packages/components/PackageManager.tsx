import React, { useEffect, useState } from "react";

import { usePackageManagement } from "../hooks/usePackageManagement";

interface PackageManagerProps {
  onChanged?: () => void | Promise<void>;
}

const PackageManager: React.FC<PackageManagerProps> = ({ onChanged }) => {
  const {
    packages,
    loading,
    error,
    page,
    total,
    totalPages,
    pageSize,
    keyword,
    includeInactive,
    setIncludeInactive,
    search,
    goToPage,
    refresh,
    modalMode,
    form,
    setForm,
    detailPackage,
    submitting,
    deletingId,
    openCreate,
    openEdit,
    openDetail,
    closeModal,
    submitForm,
    remove,
  } = usePackageManagement({ onChanged });
  const [keywordInput, setKeywordInput] = useState(keyword);

  useEffect(() => {
    setKeywordInput(keyword);
  }, [keyword]);

  return (
    <div className="mb-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-slate-900">套餐管理</h2>
          <p className="text-xs text-slate-500">
            支持新增、编辑、删除、分页查询和详情查看，便于维护套餐信息。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={openCreate}
            className="rounded-full bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700"
          >
            新增套餐
          </button>
          <button
            type="button"
            onClick={() => void refresh()}
            className="rounded-full border border-slate-300 px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
          >
            刷新
          </button>
        </div>
      </div>

      <div className="mb-3 grid gap-2 md:grid-cols-[1fr_auto_auto]">
        <input
          value={keywordInput}
          onChange={(e) => setKeywordInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              void search(keywordInput);
            }
          }}
          placeholder="按套餐名称或描述搜索"
          className="h-9 rounded-xl border border-slate-300 px-3 text-sm outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
        />
        <label className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 text-xs text-slate-600">
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={(e) => setIncludeInactive(e.target.checked)}
          />
          包含已下架
        </label>
        <button
          type="button"
          onClick={() => void search(keywordInput)}
          className="h-9 rounded-xl bg-slate-900 px-3 text-xs font-medium text-white hover:bg-slate-700"
        >
          查询
        </button>
      </div>

      {error && (
        <div className="mb-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
          {error}
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-slate-200">
        <table className="min-w-full text-left text-xs">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="px-3 py-2 font-medium">ID</th>
              <th className="px-3 py-2 font-medium">套餐名</th>
              <th className="px-3 py-2 font-medium">月费</th>
              <th className="px-3 py-2 font-medium">流量(GB)</th>
              <th className="px-3 py-2 font-medium">有效期</th>
              <th className="px-3 py-2 font-medium">状态</th>
              <th className="px-3 py-2 font-medium">操作</th>
            </tr>
          </thead>
          <tbody>
            {loading && packages.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-slate-500">
                  加载中...
                </td>
              </tr>
            ) : packages.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-3 py-8 text-center text-slate-500">
                  暂无套餐数据
                </td>
              </tr>
            ) : (
              packages.map((pkg) => (
                <tr key={pkg.id} className="border-t border-slate-100">
                  <td className="px-3 py-2 text-slate-600">{pkg.id}</td>
                  <td className="px-3 py-2 text-slate-900">
                    <div className="font-medium">{pkg.name}</div>
                    <div className="line-clamp-1 text-[11px] text-slate-500">
                      {pkg.description || "暂无描述"}
                    </div>
                  </td>
                  <td className="px-3 py-2 text-slate-700">¥{pkg.monthly_fee}</td>
                  <td className="px-3 py-2 text-slate-700">{pkg.data_quota_gb}</td>
                  <td className="px-3 py-2 text-slate-700">{pkg.validity_days} 天</td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 ${
                        pkg.is_active
                          ? "bg-emerald-50 text-emerald-700"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      {pkg.is_active ? "在售" : "下架"}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      <button
                        type="button"
                        onClick={() => void openDetail(pkg.id)}
                        className="rounded-full border border-slate-300 px-2 py-0.5 text-[11px] text-slate-700 hover:bg-slate-50"
                      >
                        详情
                      </button>
                      <button
                        type="button"
                        onClick={() => openEdit(pkg)}
                        className="rounded-full border border-cyan-300 px-2 py-0.5 text-[11px] text-cyan-700 hover:bg-cyan-50"
                      >
                        编辑
                      </button>
                      <button
                        type="button"
                        onClick={() => void remove(pkg.id)}
                        disabled={deletingId === pkg.id}
                        className="rounded-full border border-red-300 px-2 py-0.5 text-[11px] text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {deletingId === pkg.id ? "删除中" : "删除"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-slate-600">
        <span>
          共 {total} 条，每页 {pageSize} 条，当前第 {page}/{totalPages} 页
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => goToPage(page - 1)}
            disabled={page <= 1 || loading}
            className="rounded-full border border-slate-300 px-3 py-1 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            上一页
          </button>
          <button
            type="button"
            onClick={() => goToPage(page + 1)}
            disabled={page >= totalPages || loading}
            className="rounded-full border border-slate-300 px-3 py-1 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            下一页
          </button>
        </div>
      </div>

      {modalMode === "create" || modalMode === "edit" ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-xl">
            <h3 className="mb-3 text-base font-semibold text-slate-900">
              {modalMode === "create" ? "新增套餐" : "编辑套餐"}
            </h3>

            <div className="grid gap-2 text-xs">
              <label className="flex flex-col gap-1">
                套餐名称
                <input
                  value={form.name}
                  onChange={(e) => setForm({ name: e.target.value })}
                  className="h-9 rounded-lg border border-slate-300 px-3 outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
                />
              </label>
              <label className="flex flex-col gap-1">
                套餐描述
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ description: e.target.value })}
                  rows={3}
                  className="rounded-lg border border-slate-300 px-3 py-2 outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
                />
              </label>
              <div className="grid gap-2 md:grid-cols-3">
                <label className="flex flex-col gap-1">
                  月费(元)
                  <input
                    type="number"
                    min={0}
                    value={form.monthly_fee}
                    onChange={(e) =>
                      setForm({ monthly_fee: Number(e.target.value) || 0 })
                    }
                    className="h-9 rounded-lg border border-slate-300 px-3 outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  流量(GB)
                  <input
                    type="number"
                    min={0}
                    value={form.data_quota_gb}
                    onChange={(e) =>
                      setForm({ data_quota_gb: Number(e.target.value) || 0 })
                    }
                    className="h-9 rounded-lg border border-slate-300 px-3 outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  有效期(天)
                  <input
                    type="number"
                    min={1}
                    value={form.validity_days}
                    onChange={(e) =>
                      setForm({ validity_days: Math.max(1, Number(e.target.value) || 1) })
                    }
                    className="h-9 rounded-lg border border-slate-300 px-3 outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
                  />
                </label>
              </div>
              <label className="mt-1 flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={form.is_active}
                  onChange={(e) => setForm({ is_active: e.target.checked })}
                />
                上架状态
              </label>
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={closeModal}
                className="rounded-full border border-slate-300 px-4 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
              >
                取消
              </button>
              <button
                type="button"
                onClick={submitForm}
                disabled={submitting}
                className="rounded-full bg-slate-900 px-4 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? "保存中..." : "保存"}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {modalMode === "detail" && detailPackage ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-xl">
            <h3 className="mb-3 text-base font-semibold text-slate-900">套餐详情</h3>
            <div className="space-y-2 text-sm text-slate-700">
              <p>
                <span className="text-slate-500">ID：</span>
                {detailPackage.id}
              </p>
              <p>
                <span className="text-slate-500">名称：</span>
                {detailPackage.name}
              </p>
              <p>
                <span className="text-slate-500">描述：</span>
                {detailPackage.description || "暂无描述"}
              </p>
              <p>
                <span className="text-slate-500">月费：</span>¥
                {detailPackage.monthly_fee}
              </p>
              <p>
                <span className="text-slate-500">流量：</span>
                {detailPackage.data_quota_gb} GB
              </p>
              <p>
                <span className="text-slate-500">有效期：</span>
                {detailPackage.validity_days} 天
              </p>
              <p>
                <span className="text-slate-500">状态：</span>
                {detailPackage.is_active ? "在售" : "下架"}
              </p>
            </div>
            <div className="mt-4 flex justify-end">
              <button
                type="button"
                onClick={closeModal}
                className="rounded-full border border-slate-300 px-4 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default PackageManager;
