import axios, {
  AxiosError,
  AxiosHeaders,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
} from "axios";

const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8005",
  timeout: 15000,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      const headers = AxiosHeaders.from(config.headers);
      headers.set("Authorization", `Bearer ${token}`);
      config.headers = headers;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    console.error("API Error:", error.response ?? error.message);
    return Promise.reject(error);
  }
);

export async function get<T = unknown>(
  url: string,
  config?: AxiosRequestConfig
): Promise<T> {
  const resp = await api.get<T>(url, config);
  return resp.data;
}

export async function post<T = unknown, B = unknown>(
  url: string,
  data?: B,
  config?: AxiosRequestConfig
): Promise<T> {
  const resp = await api.post<T>(url, data, config);
  return resp.data;
}

export async function put<T = unknown, B = unknown>(
  url: string,
  data?: B,
  config?: AxiosRequestConfig
): Promise<T> {
  const resp = await api.put<T>(url, data, config);
  return resp.data;
}

export async function del(
  url: string,
  config?: AxiosRequestConfig
): Promise<void> {
  await api.delete(url, config);
}

export interface ApiUser {
  id: number;
  phone_number: string;
  name?: string | null;
  email?: string | null;
  status: string;
  registered_at?: string | null;
}

export interface ApiUserUpsertPayload {
  phone_number: string;
  name?: string;
  email?: string;
  status?: string;
  registered_at?: string;
}

export interface ApiUserPageResponse {
  items: ApiUser[];
  page: number;
  page_size: number;
  total: number;
}

export interface ApiPackage {
  id: number;
  name: string;
  description?: string | null;
  monthly_fee: number;
  data_quota_gb: number;
  validity_days: number;
  is_active: boolean;
}

export interface ApiPackagePageResponse {
  items: ApiPackage[];
  page: number;
  page_size: number;
  total: number;
}

export interface ApiUserPackageRelation {
  id: number;
  user_id: number;
  phone_number: string;
  package_id: number;
  package_name: string;
  monthly_fee: number;
  data_quota_gb: number;
  validity_days: number;
  start_date: string;
  end_date?: string | null;
  status: string;
  auto_renew: boolean;
  is_current: boolean;
}

export interface ApiUserCurrentPackageResponse {
  item?: ApiUserPackageRelation | null;
}

export interface ApiUserPackageAssignPayload {
  package_id: number;
  effective_from?: string;
  auto_renew?: boolean;
}

export interface ApiUserPackageHistoryPageResponse {
  items: ApiUserPackageRelation[];
  page: number;
  page_size: number;
  total: number;
}

export interface ApiPackageUpsertPayload {
  name: string;
  description?: string;
  monthly_fee: number;
  data_quota_gb: number;
  validity_days: number;
  is_active: boolean;
}

export interface ApiBenefit {
  id: number;
  name: string;
  description?: string | null;
  is_active: boolean;
  inventory: number;
}

export interface ApiUsageCurrent {
  user_id: number;
  total_used_mb: number;
}

export interface ApiUsageHistoryItem {
  id: number;
  record_time: string;
  used_mb: number;
  network_type?: string | null;
  location?: string | null;
}

export interface ApiChatRequest {
  user_id: string;
  message: string;
  session_id?: string;
  channel?: string;
}

export interface ApiChatResponse {
  session_id: string;
  response: string;
  suggestions: string[];
  quick_replies: string[];
  need_human: boolean;
  human_transfer_reason?: string | null;
}

export interface ApiHumanTransferRequest {
  session_id: string;
  user_id: string;
  reason: string;
}

export interface ApiPackageRecommendRequest {
  monthly_budget?: number;
  min_data_gb?: number;
  limit?: number;
}

export interface ApiPackageRecommendResponse {
  recommendations: ApiPackage[];
}

export interface ApiBenefitClaimRequest {
  user_id: number;
  benefit_id: number;
}

export interface ApiBenefitClaimResponse {
  user_id: number;
  benefit_id: number;
  status: string;
}

export interface ApiChatHistoryMessage {
  role: string;
  content: string;
  timestamp: number;
}

export interface ApiChatHistoryResponse {
  history: ApiChatHistoryMessage[];
}

export const getUserInfo = (userId: string | number) =>
  get<ApiUser>(`/api/v1/users/${userId}`);

export const getUsersPage = (params?: {
  page?: number;
  page_size?: number;
  keyword?: string;
}) => get<ApiUserPageResponse>("/api/v1/users/", { params });

export const createUser = (payload: ApiUserUpsertPayload) =>
  post<ApiUser, ApiUserUpsertPayload>("/api/v1/users/", payload);

export const updateUser = (
  userId: string | number,
  payload: Partial<ApiUserUpsertPayload>
) =>
  put<ApiUser, Partial<ApiUserUpsertPayload>>(`/api/v1/users/${userId}`, payload);

export const deleteUser = (userId: string | number) =>
  del(`/api/v1/users/${userId}`);

export const getUserPackages = (userId: string | number) =>
  get<ApiPackage[]>(`/api/v1/users/${userId}/packages`);

export const getCurrentUserPackage = (userId: string | number) =>
  get<ApiUserCurrentPackageResponse>(`/api/v1/users/${userId}/packages/current`);

export const getUserPackageHistory = (
  userId: string | number,
  params?: { page?: number; page_size?: number }
) =>
  get<ApiUserPackageHistoryPageResponse>(
    `/api/v1/users/${userId}/packages/history`,
    { params }
  );

export const assignUserPackage = (
  userId: string | number,
  payload: ApiUserPackageAssignPayload
) =>
  post<ApiUserPackageRelation, ApiUserPackageAssignPayload>(
    `/api/v1/users/${userId}/packages/assign`,
    payload
  );

export const getUserBenefits = (userId: string | number) =>
  get<ApiBenefit[]>(`/api/v1/users/${userId}/benefits`);

export const getPackages = () => get<ApiPackage[]>("/api/v1/packages");

export const getPackagesPage = (params?: {
  page?: number;
  page_size?: number;
  keyword?: string;
  include_inactive?: boolean;
}) => get<ApiPackagePageResponse>("/api/v1/packages/paged", { params });

export const getPackageDetail = (packageId: string | number) =>
  get<ApiPackage>(`/api/v1/packages/${packageId}`);

export const createPackage = (payload: ApiPackageUpsertPayload) =>
  post<ApiPackage, ApiPackageUpsertPayload>("/api/v1/packages", payload);

export const updatePackage = (
  packageId: string | number,
  payload: Partial<ApiPackageUpsertPayload>
) =>
  put<ApiPackage, Partial<ApiPackageUpsertPayload>>(
    `/api/v1/packages/${packageId}`,
    payload
  );

export const deletePackage = (packageId: string | number) =>
  del(`/api/v1/packages/${packageId}`);

export const recommendPackages = (payload: ApiPackageRecommendRequest) =>
  post<ApiPackageRecommendResponse, ApiPackageRecommendRequest>(
    "/api/v1/packages/recommend",
    payload
  );

export const getPendingBenefits = (userId: string | number) =>
  get<ApiBenefit[]>(`/api/v1/benefits/pending/${userId}`);

export const claimBenefit = (payload: ApiBenefitClaimRequest) =>
  post<ApiBenefitClaimResponse, ApiBenefitClaimRequest>(
    "/api/v1/benefits/claim",
    payload
  );

export const getCurrentUsage = (userId: string | number) =>
  get<ApiUsageCurrent>(`/api/v1/usage/current/${userId}`);

export const getUsageHistory = (userId: string | number) =>
  get<ApiUsageHistoryItem[]>(`/api/v1/usage/history/${userId}`);

export const sendMessage = (payload: ApiChatRequest) =>
  post<ApiChatResponse, ApiChatRequest>("/api/v1/chat", payload);

export const transferToHuman = (payload: ApiHumanTransferRequest) =>
  post("/api/v1/chat/transfer-human", payload);

export const getChatHistory = (sessionId: string) =>
  get<ApiChatHistoryResponse>(`/api/v1/chat/history/${sessionId}`);

export default api;
