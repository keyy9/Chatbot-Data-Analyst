export interface QueryLog {
  id: string;
  user: string;
  question: string;
  generatedSql: string;
  executionTimeMs: number;
  status: 'Success' | 'Failed';
  timestamp: string;
  errorDetail?: string;
  aiExplanation?: string;
  resultPreview?: {
    columns: string[];
    rows: Record<string, any>[];
  };
  clarificationHistory?: {
    originalPrompt: string;
    clarificationQuestion: string;
    userResponse: string;
    finalPrompt: string;
  };
  guardrailStatus?: 'Allowed' | 'Blocked';
  guardrailReason?: string;
}

export interface MockProduct {
  product_id: number;
  product_name: string;
  category: string;
  unit_price: number;
  cost: number;
}

export interface MockCustomer {
  customer_id: number;
  name: string;
  city: string;
  tier: 'Gold' | 'Silver' | 'Platinum' | 'Bronze';
  created_at: string;
}

export interface MockOrder {
  order_id: number;
  customer_id: number;
  order_date: string;
  status: 'completed' | 'cancelled' | 'refunded';
  order_total: number;
}
