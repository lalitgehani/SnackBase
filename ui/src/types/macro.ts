export interface Macro {
  id: number;
  name: string;
  description: string | null;
  sql_query: string;
  parameters: string; // JSON string from backend
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface MacroCreate {
  name: string;
  description?: string;
  sql_query: string;
  parameters: string[];
}

export interface MacroUpdate {
  name: string;
  description?: string;
  sql_query: string;
  parameters: string[];
}

export interface MacroTestRequest {
  parameters: any[];
}

export interface MacroTestResponse {
  result: string | null;
  execution_time: number;
  rows_affected: number;
}
