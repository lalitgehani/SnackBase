export type ActivityType = 'create' | 'update' | 'delete';

export interface Activity {
  id: string;
  type: ActivityType;
  message: string;
  entity_type: string;
  entity_id?: string;
  user_name: string;
  created_at: string;
}

export interface CreateActivity {
  type: ActivityType;
  message: string;
  entity_type: string;
  entity_id?: string;
  user_name?: string;
}

export interface RealtimeEvent {
  type: string;
  timestamp: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any;
  collection?: string;
  operation?: string;
}

export interface LoginCredentials {
  account: string;
  email: string;
  password: string;
}

export interface AuthResponse {
  token: string;
  user: {
    id: string;
    email: string;
    account_id: string;
  };
}
