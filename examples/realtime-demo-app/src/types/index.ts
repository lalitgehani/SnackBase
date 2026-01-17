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
  data: any;
  collection?: string;
  operation?: string;
}
