export interface Package {
  id: number;
  name: string;
  description?: string;
  price: number;
  dataLimit: number; // 单位：GB
}

export interface Benefit {
  id: number;
  name: string;
  description?: string;
}

export interface UsageSummary {
  usedData: number;
  remainingData: number;
}

