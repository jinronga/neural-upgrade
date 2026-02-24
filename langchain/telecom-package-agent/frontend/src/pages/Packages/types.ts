export interface Benefit {
  benefitId: string;
  name: string;
  type: string;
  icon: string;
}

export interface Package {
  packageId: string;
  name: string;
  description: string;
  price: number;
  dataGb: number;
  voiceMinutes: number;
  smsCount: number;
  benefits: Benefit[];
  targetGroup: "student" | "business" | "elder" | "general";
  tags: string[];
  status: "active" | "inactive";
}

