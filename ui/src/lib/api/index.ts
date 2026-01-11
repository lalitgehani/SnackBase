/**
 * API client configuration with axios
 * Handles authentication, token refresh, and error handling
 */

import axios, { AxiosError, type InternalAxiosRequestConfig, AxiosHeaders } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

// Create axios instance
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Get token from localStorage
    const authState = localStorage.getItem('auth-storage');
    
    if (authState) {
      try {
        const parsedState = JSON.parse(authState);
        const token = parsedState?.state?.token;
        
        if (token) {
          if (!config.headers) {
            config.headers = new AxiosHeaders();
          }

          // Ensure headers is an AxiosHeaders instance or compatible
          if (config.headers instanceof AxiosHeaders) {
            config.headers.set('Authorization', `Bearer ${token}`);
          } else {
            // Fallback for plain object headers
            (config.headers as Record<string, string>).Authorization = `Bearer ${token}`;
          }
          
          // Debug log for development
          if (import.meta.env.DEV) {
            console.log(`[API] Request ${config.method?.toUpperCase()} ${config.url} with token`);
          }
        } else {
          if (import.meta.env.DEV) {
            console.warn(`[API] No token found in auth-storage for ${config.url}`);
          }
        }
      } catch (error) {
        console.error('Failed to parse auth state:', error);
      }
    } else {
      if (import.meta.env.DEV) {
        console.warn(`[API] No auth-storage found in localStorage for ${config.url}`);
      }
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // If error is 401 and we haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Get refresh token from localStorage
        const authState = localStorage.getItem('auth-storage');
        if (!authState) {
          throw new Error('No auth state found');
        }

        const { state } = JSON.parse(authState);
        const refreshToken = state?.refreshToken;

        if (!refreshToken) {
          throw new Error('No refresh token found');
        }

        // Call refresh endpoint
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { token, refresh_token } = response.data;

        // Update tokens in localStorage
        const updatedState = {
          ...state,
          token,
          refreshToken: refresh_token,
        };
        localStorage.setItem('auth-storage', JSON.stringify({ state: updatedState }));

        // Retry original request with new token
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${token}`;
        }
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed, clear auth state and redirect to login
        localStorage.removeItem('auth-storage');
        window.location.href = '/admin/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

/**
 * API error handler
 */
export const handleApiError = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ 
      message?: string; 
      error?: string; 
      detail?: string | unknown[];
      details?: unknown[];
    }>;
    
    // Check for detail field (used by FastAPI for validation errors)
    if (axiosError.response?.data?.detail) {
      const detail = axiosError.response.data.detail;
      
      // If detail is a string, return it directly
      if (typeof detail === 'string') {
        return detail;
      }
      
      // If detail is an array of validation errors, format them
      if (Array.isArray(detail)) {
        const errors = detail.map((item: unknown) => {
          const err = item as string | { message?: string; msg?: string };
          if (typeof err === 'string') return err;
          if (err.message) return err.message;
          if (err.msg) return err.msg;
          return JSON.stringify(err);
        });
        return errors.join(', ');
      }
    }
    
    // Check for details field (used for record validation errors)
    if (axiosError.response?.data?.details) {
      const details = axiosError.response.data.details;
      if (Array.isArray(details)) {
        const errors = details.map((item: unknown) => {
          const err = item as { message?: string; msg?: string };
          return err.message || err.msg || JSON.stringify(err);
        });
        return errors.join(', ');
      }
    }
    
    // Fallback to message or error fields
    if (axiosError.response?.data?.message) {
      return axiosError.response.data.message;
    }
    
    if (axiosError.response?.data?.error) {
      return axiosError.response.data.error;
    }
    
    if (axiosError.message) {
      return axiosError.message;
    }
  }
  
  return 'An unexpected error occurred';
};
