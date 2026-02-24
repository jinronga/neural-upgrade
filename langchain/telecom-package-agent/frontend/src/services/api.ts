import axios from "axios";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  timeout: 10000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // TODO: 在这里统一处理错误（如弹出提示、上报日志等）
    return Promise.reject(error);
  }
);

export async function get<T>(url: string, params?: unknown) {
  const response = await apiClient.get<T>(url, { params });
  return response.data;
}

export async function post<T, B = unknown>(url: string, data?: B) {
  const response = await apiClient.post<T>(url, data);
  return response.data;
}

export default apiClient;

