/**
 * Feature request types
 */

export interface Feature {
  id: string;
  title: string;
  description: string;
  votes: number;
  status: 'open' | 'in-progress' | 'completed';
  created_by: string;
  created_at: string;
  updated_at: string;
  account_id: string;
  voted_by?: string[]; // Array of user IDs who voted
}

export interface FeatureCreate {
  title: string;
  description: string;
}

export interface FeatureUpdate {
  title?: string;
  description?: string;
  status?: 'open' | 'in-progress' | 'completed';
}
