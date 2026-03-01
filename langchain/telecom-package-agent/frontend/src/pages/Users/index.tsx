import React, { useCallback, useEffect, useMemo, useState } from "react";

import { useUser } from "@/contexts/UserContext";
import {
  ApiUser,
  ApiUserUpsertPayload,
  createUser,
  deleteUser,
  getUsersPage,
  updateUser,
} from "@/services/api";

const PAGE_SIZE = 10;

type ModalMode = "create" | "edit" | null;

interface UserFormState {
  phone_number: string;
  name: string;
  email: string;
  status: "active" | "inactive";
}

const emptyForm: UserFormState = {
  phone_number: "",
  name: "",
  email: "",
  status: "active",
};

const getErrorMessage = (error: any, fallback: string) =>
  error?.response?.data?.detail ?? error?.message ?? fallback;

const toPayload = (form: UserFormState): ApiUserUpsertPayload => ({
  phone_number: form.phone_number.trim(),
  name: form.name.trim() || undefined,
  email: form.email.trim() || undefined,
  status: form.status,
});

const formatTime = (value?: string | null) => {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
};

const PhoneManagementPage: React.FC = () => {
  const { userId } = useUser();
  const [users, setUsers] = useState<ApiUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);
  const [keyword, setKeyword] = useState("");
  const [keywordInput, setKeywordInput] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [editingUserId, setEditingUserId] = useState<number | undefined>(undefined);
  const [form, setForm] = useState<UserFormState>(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<number | undefined>(undefined);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(total / PAGE_SIZE)),
    [total]
  );

  const fetchUsers = useCallback(
    async (nextPage: number, nextKeyword: string) => {
      setLoading(true);
      setError(undefined);
      try {
        const data = await getUsersPage({
          page: nextPage,
          page_size: PAGE_SIZE,
          keyword: nextKeyword || undefined,
        });
        setUsers(data.items);
        setPage(data.page);
        setTotal(data.total);
      } catch (err: any) {
        setError(getErrorMessage(err, "手机号列表加载失败"));
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    void fetchUsers(1, keyword);
  }, [fetchUsers, keyword]);

  const dispatchUsersChanged = () => {
    window.dispatchEvent(new Event("telecom-users-updated"));
  };

  const openCreate = () => {
    setEditingUserId(undefined);
    setForm(emptyForm);
    setModalMode("create");
    setError(undefined);
  };

  const openEdit = (user: ApiUser) => {
    setEditingUserId(user.id);
    setForm({
      phone_number: user.phone_number ?? "",
      name: user.name ?? "",
      email: user.email ?? "",
      status: user.status === "inactive" ? "inactive" : "active",
    });
    setModalMode("edit");
    setError(undefined);
  };

  const closeModal = () => {
    setModalMode(null);
    setEditingUserId(undefined);
    setForm(emptyForm);
  };

  const submitForm = async () => {
    if (!form.phone_number.trim()) {
      setError("手机号不能为空");
      return;
    }
    if (form.phone_number.trim().length < 5) {
      setError("手机号格式不合法");
      return;
    }

    setSubmitting(true);
    setError(undefined);
    try {
      const payload = toPayload(form);
      if (modalMode === "create") {
        await createUser(payload);
      } else if (modalMode === "edit" && editingUserId) {
        await updateUser(editingUserId, payload);
      }
      closeModal();
      await fetchUsers(page, keyword);
      dispatchUsersChanged();
    } catch (err: any) {
      setError(getErrorMessage(err, "保存手机号失败"));
    } finally {
      setSubmitting(false);
    }
  };

  const removeUser = async (id: number) => {
    const isCurrentSelected = Number(userId) === id;
    const confirmed = window.confirm(
      isCurrentSelected
        ? "该手机号是当前选中用户，删除后需重新选择用户，确认删除？"
        : "确认删除该手机号？此操作不可撤销。"
    );
    if (!confirmed) return;

    setDeletingId(id);
    setError(undefined);
    try {
      await deleteUser(id);
      const expectedItems = Math.max(0, users.length - 1);
      const nextPage = expectedItems === 0 && page > 1 ? page - 1 : page;
      await fetchUsers(nextPage, keyword);
      dispatchUsersChanged();
    } catch (err: any) {
      setError(getErrorMessage(err, "删除手机号失败"));
    } finally {
      setDeletingId(undefined);
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-slate-800 to-cyan-800 p-5 text-white shadow-xl">
        <div className="text-[11px] uppercase tracking-[0.2em] text-cyan-200/90">
          Number Center
        </div>
        <h1 className="mt-1 text-2xl font-black">手机号管理</h1>
        <p className="mt-1 text-xs text-cyan-100/80">
          维护用户手机号资料，支持分页查询、新增、编辑和删除。
        </p>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <input
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  const next = keywordInput.trim();
                  setKeyword(next);
                  void fetchUsers(1, next);
                }
              }}
              placeholder="按手机号/用户名搜索"
              className="h-9 w-72 rounded-xl border border-slate-300 px-3 text-sm outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
            />
            <button
              type="button"
              onClick={() => {
                const next = keywordInput.trim();
                setKeyword(next);
                void fetchUsers(1, next);
              }}
              className="h-9 rounded-xl bg-slate-900 px-4 text-xs font-medium text-white hover:bg-slate-700"
            >
              查询
            </button>
            <button
              type="button"
              onClick={() => void fetchUsers(page, keyword)}
              className="h-9 rounded-xl border border-slate-300 px-4 text-xs text-slate-700 hover:bg-slate-50"
            >
              刷新
            </button>
          </div>
          <button
            type="button"
            onClick={openCreate}
            className="h-9 rounded-xl bg-emerald-600 px-4 text-xs font-medium text-white hover:bg-emerald-700"
          >
            新增手机号
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
                <th className="px-3 py-2 font-medium">手机号</th>
                <th className="px-3 py-2 font-medium">用户名</th>
                <th className="px-3 py-2 font-medium">邮箱</th>
                <th className="px-3 py-2 font-medium">状态</th>
                <th className="px-3 py-2 font-medium">注册时间</th>
                <th className="px-3 py-2 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {loading && users.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-3 py-8 text-center text-slate-500">
                    加载中...
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-3 py-8 text-center text-slate-500">
                    暂无手机号数据
                  </td>
                </tr>
              ) : (
                users.map((item) => (
                  <tr key={item.id} className="border-t border-slate-100">
                    <td className="px-3 py-2 text-slate-600">{item.id}</td>
                    <td className="px-3 py-2 font-medium text-slate-900">
                      {item.phone_number}
                    </td>
                    <td className="px-3 py-2 text-slate-700">{item.name || "-"}</td>
                    <td className="px-3 py-2 text-slate-700">{item.email || "-"}</td>
                    <td className="px-3 py-2">
                      <span
                        className={`rounded-full px-2 py-0.5 ${
                          item.status === "active"
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {item.status === "active" ? "正常" : "停用"}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-700">
                      {formatTime(item.registered_at)}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        <button
                          type="button"
                          onClick={() => openEdit(item)}
                          className="rounded-full border border-cyan-300 px-2 py-0.5 text-[11px] text-cyan-700 hover:bg-cyan-50"
                        >
                          编辑
                        </button>
                        <button
                          type="button"
                          onClick={() => void removeUser(item.id)}
                          disabled={deletingId === item.id}
                          className="rounded-full border border-red-300 px-2 py-0.5 text-[11px] text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {deletingId === item.id ? "删除中" : "删除"}
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
            共 {total} 条，每页 {PAGE_SIZE} 条，当前第 {page}/{totalPages} 页
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void fetchUsers(page - 1, keyword)}
              disabled={page <= 1 || loading}
              className="rounded-full border border-slate-300 px-3 py-1 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              上一页
            </button>
            <button
              type="button"
              onClick={() => void fetchUsers(page + 1, keyword)}
              disabled={page >= totalPages || loading}
              className="rounded-full border border-slate-300 px-3 py-1 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              下一页
            </button>
          </div>
        </div>
      </div>

      {modalMode ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40">
          <div className="w-full max-w-lg rounded-2xl bg-white p-5 shadow-xl">
            <h3 className="mb-3 text-base font-semibold text-slate-900">
              {modalMode === "create" ? "新增手机号" : "编辑手机号"}
            </h3>

            <div className="grid gap-2 text-xs">
              <label className="flex flex-col gap-1">
                手机号
                <input
                  value={form.phone_number}
                  onChange={(e) => setForm((prev) => ({ ...prev, phone_number: e.target.value }))}
                  className="h-9 rounded-lg border border-slate-300 px-3 outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
                />
              </label>
              <label className="flex flex-col gap-1">
                用户名
                <input
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  className="h-9 rounded-lg border border-slate-300 px-3 outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
                />
              </label>
              <label className="flex flex-col gap-1">
                邮箱
                <input
                  value={form.email}
                  onChange={(e) => setForm((prev) => ({ ...prev, email: e.target.value }))}
                  className="h-9 rounded-lg border border-slate-300 px-3 outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
                />
              </label>
              <label className="flex flex-col gap-1">
                状态
                <select
                  value={form.status}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      status: e.target.value === "inactive" ? "inactive" : "active",
                    }))
                  }
                  className="h-9 rounded-lg border border-slate-300 px-3 outline-none focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
                >
                  <option value="active">正常</option>
                  <option value="inactive">停用</option>
                </select>
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
                onClick={() => void submitForm()}
                disabled={submitting}
                className="rounded-full bg-slate-900 px-4 py-1.5 text-xs font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitting ? "保存中..." : "保存"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default PhoneManagementPage;
