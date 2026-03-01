import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ApiPackage,
  ApiPackageUpsertPayload,
  createPackage,
  deletePackage,
  getPackageDetail,
  getPackagesPage,
  updatePackage,
} from "@/services/api";

const PAGE_SIZE = 10;

type ModalMode = "create" | "edit" | "detail" | null;

interface PackageFormState {
  name: string;
  description: string;
  monthly_fee: number;
  data_quota_gb: number;
  validity_days: number;
  is_active: boolean;
}

const emptyForm: PackageFormState = {
  name: "",
  description: "",
  monthly_fee: 39,
  data_quota_gb: 10,
  validity_days: 30,
  is_active: true,
};

const toForm = (pkg: ApiPackage): PackageFormState => ({
  name: pkg.name,
  description: pkg.description ?? "",
  monthly_fee: pkg.monthly_fee,
  data_quota_gb: pkg.data_quota_gb,
  validity_days: pkg.validity_days,
  is_active: pkg.is_active,
});

const toPayload = (form: PackageFormState): ApiPackageUpsertPayload => ({
  name: form.name.trim(),
  description: form.description.trim() || undefined,
  monthly_fee: form.monthly_fee,
  data_quota_gb: form.data_quota_gb,
  validity_days: form.validity_days,
  is_active: form.is_active,
});

const getErrorMessage = (error: any, fallback: string) =>
  error?.response?.data?.detail ?? error?.message ?? fallback;

interface UsePackageManagementOptions {
  onChanged?: () => void | Promise<void>;
}

export const usePackageManagement = (options: UsePackageManagementOptions = {}) => {
  const { onChanged } = options;
  const [packages, setPackages] = useState<ApiPackage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [keyword, setKeyword] = useState("");
  const [includeInactive, setIncludeInactive] = useState(true);

  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [form, setForm] = useState<PackageFormState>(emptyForm);
  const [detailPackage, setDetailPackage] = useState<ApiPackage | undefined>(
    undefined
  );
  const [editingPackageId, setEditingPackageId] = useState<number | undefined>(
    undefined
  );
  const [submitting, setSubmitting] = useState(false);
  const [deletingId, setDeletingId] = useState<number | undefined>(undefined);

  const totalPages = useMemo(
    () => Math.max(1, Math.ceil(total / PAGE_SIZE)),
    [total]
  );

  const fetchPage = useCallback(
    async (nextPage: number, nextKeyword: string, nextIncludeInactive: boolean) => {
      setLoading(true);
      setError(undefined);
      try {
        const data = await getPackagesPage({
          page: nextPage,
          page_size: PAGE_SIZE,
          keyword: nextKeyword || undefined,
          include_inactive: nextIncludeInactive,
        });
        setPackages(data.items);
        setPage(data.page);
        setTotal(data.total);
      } catch (err: any) {
        setError(getErrorMessage(err, "加载套餐管理列表失败"));
      } finally {
        setLoading(false);
      }
    },
    []
  );

  useEffect(() => {
    void fetchPage(1, keyword, includeInactive);
  }, [fetchPage, includeInactive]);

  const search = useCallback(
    async (nextKeyword: string) => {
      setKeyword(nextKeyword.trim());
      await fetchPage(1, nextKeyword.trim(), includeInactive);
    },
    [fetchPage, includeInactive]
  );

  const refresh = useCallback(async () => {
    await fetchPage(page, keyword, includeInactive);
  }, [fetchPage, includeInactive, keyword, page]);

  const openCreate = () => {
    setEditingPackageId(undefined);
    setDetailPackage(undefined);
    setForm(emptyForm);
    setModalMode("create");
  };

  const openEdit = (pkg: ApiPackage) => {
    setEditingPackageId(pkg.id);
    setDetailPackage(undefined);
    setForm(toForm(pkg));
    setModalMode("edit");
  };

  const openDetail = async (packageId: number) => {
    setSubmitting(true);
    try {
      const detail = await getPackageDetail(packageId);
      setDetailPackage(detail);
      setModalMode("detail");
    } catch (err: any) {
      setError(getErrorMessage(err, "加载套餐详情失败"));
    } finally {
      setSubmitting(false);
    }
  };

  const closeModal = () => {
    setModalMode(null);
    setDetailPackage(undefined);
    setEditingPackageId(undefined);
    setSubmitting(false);
  };

  const submitForm = async () => {
    if (!form.name.trim()) {
      setError("套餐名称不能为空");
      return;
    }

    setSubmitting(true);
    setError(undefined);
    try {
      const payload = toPayload(form);
      if (modalMode === "create") {
        await createPackage(payload);
      } else if (modalMode === "edit" && editingPackageId) {
        await updatePackage(editingPackageId, payload);
      }
      closeModal();
      await fetchPage(page, keyword, includeInactive);
      await onChanged?.();
    } catch (err: any) {
      setError(getErrorMessage(err, "保存套餐失败"));
    } finally {
      setSubmitting(false);
    }
  };

  const remove = async (packageId: number) => {
    const confirmed = window.confirm("确认删除该套餐？此操作不可撤销。");
    if (!confirmed) return;

    setDeletingId(packageId);
    setError(undefined);
    try {
      await deletePackage(packageId);
      const expectedItems = Math.max(0, packages.length - 1);
      const nextPage = expectedItems === 0 && page > 1 ? page - 1 : page;
      await fetchPage(nextPage, keyword, includeInactive);
      await onChanged?.();
    } catch (err: any) {
      setError(getErrorMessage(err, "删除套餐失败"));
    } finally {
      setDeletingId(undefined);
    }
  };

  return {
    packages,
    loading,
    error,
    page,
    total,
    totalPages,
    pageSize: PAGE_SIZE,
    keyword,
    includeInactive,
    setIncludeInactive,
    search,
    goToPage: (nextPage: number) =>
      void fetchPage(Math.min(Math.max(nextPage, 1), totalPages), keyword, includeInactive),
    refresh,
    modalMode,
    form,
    setForm: (patch: Partial<PackageFormState>) =>
      setForm((prev) => ({ ...prev, ...patch })),
    detailPackage,
    submitting,
    deletingId,
    openCreate,
    openEdit,
    openDetail: (packageId: number) => void openDetail(packageId),
    closeModal,
    submitForm: () => void submitForm(),
    remove: (packageId: number) => void remove(packageId),
  };
};
