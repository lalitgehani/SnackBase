import api from '../lib/api';
import type { Activity, CreateActivity } from '../types';

export const activitiesService = {
  async getActivities(): Promise<Activity[]> {
    const response = await api.get('/records/activities');
    return response.data;
  },

  async createActivity(data: CreateActivity): Promise<Activity> {
    const response = await api.post('/records/activities', data);
    return response.data;
  }
};
