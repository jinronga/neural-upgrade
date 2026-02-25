import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
} from "axios";

// ---------- 基础配置 ----------

const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  timeout: 15000,
});

// 请求拦截器：注入 token 等
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers = {
        ...config.headers,
        Authorization: `Bearer ${token}`,
      };
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 响应拦截器：统一错误处理 / 日志
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: AxiosError) => {
    // 这里可以根据 error.response?.status 做统一处理（如跳转登录、toast 等）
    // 先简单透传，具体 UI 层再根据 detail 显示。
    console.error("API Error:", error.response ?? error.message);
    return Promise.reject(error);
  }
);

// ---------- 泛型 GET / POST 封装 ----------

export async function get<T = any>(
  url: string,
  config?: AxiosRequestConfig
): Promise<T> {
  const resp = await api.get<T>(url, config);
  return resp.data;
}

export async function post<T = any, B = any>(
  url: string,
  data?: B,
  config?: AxiosRequestConfig
): Promise<T> {
  const resp = await api.post<T>(url, data, config);
  return resp.data;
}

// ---------- 业务类型 ----------

// 根据需要在其它模块复用这些类型
export interface PackageFilter {
  keyword?: string;
  maxPrice?: number;
  targetGroup?: "student" | "business" | "elder" | "general";
}

export interface ChatRequest {
  user_id: string;
  message: string;
  session_id?: string | null;
  channel?: string; // app/mini/web 等
}

export interface HumanTransferRequest {
  session_id: string;
  user_id: string;
  reason: string;
}

// ---------- 用户相关 ----------

export const getUserInfo = (userId: string) =>
  get(`/api/v1/users/${userId}`);

export const getUserPackages = (userId: string) =>
  get(`/api/v1/users/${userId}/packages`);

// ---------- 套餐相关 ----------

export const getPackages = (params?: PackageFilter) =>
  get("/api/v1/packages", { params });

/**
 * 推荐套餐
 *
 * 说明：
 * - 后端 /api/v1/packages/recommend 接受的实际字段为
 *   { monthly_budget?: number; min_data_gb?: number; limit?: number }
 * - 这里将 usageData 中的字段转换为后端期望的格式
 */
export const recommendPackage = (
  userId: string,
  usageData?: {
    monthlyBudget?: number;
    minDataGb?: number;
    limit?: number;
  }
) => {
  const payload = {
    // userId 目前仅用于链路透传，如需可在后端扩展
    monthly_budget: usageData?.monthlyBudget,
    min_data_gb: usageData?.minDataGb,
    limit: usageData?.limit ?? 3,
  };
  return post("/api/v1/packages/recommend", payload);
};

// ---------- 权益相关 ----------

export const getPendingBenefits = (userId: string) =>
  get(`/api/v1/benefits/pending/${userId}`);

export const claimBenefit = (
  userId: string,
  benefitId: string,
  channel: string
) =>
  post("/api/v1/benefits/claim", {
    // 后端当前期望字段为 snake_case
    user_id: Number(userId),
    benefit_id: Number(benefitId),
    channel,
  });

// ---------- 用量相关 ----------

export const getCurrentUsage = (userId: string) =>
  get(`/api/v1/usage/current/${userId}`);

export const getUsageHistory = (userId: string, days: number) =>
  get(`/api/v1/usage/history/${userId}`, {
    params: { days },
  });

// ---------- 聊天相关 ----------

export const sendMessage = (data: ChatRequest) =>
  post("/api/v1/chat", data);

export const transferToHuman = (data: HumanTransferRequest) =>
  post("/api/v1/chat/transfer-human", data);

// 默认导出 axios 实例，方便特殊场景直接使用
export default api;


