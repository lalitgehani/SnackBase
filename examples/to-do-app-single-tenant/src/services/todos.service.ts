/**
 * Todos service
 * Handles all todo CRUD operations
 */

import { apiClient } from '@/lib/api';
import type { Todo, TodoInput, TodosResponse } from '@/types';

export interface GetTodosParams {
  skip?: number;
  limit?: number;
  sort?: string;
  completed?: boolean;
}

/**
 * Get all todos with optional filtering
 */
export const getTodos = async (params?: GetTodosParams): Promise<TodosResponse> => {
  const response = await apiClient.get<TodosResponse>('/records/todos', { params });
  return response.data;
};

/**
 * Get a single todo by ID
 */
export const getTodo = async (id: string): Promise<Todo> => {
  const response = await apiClient.get<Todo>(`/records/todos/${id}`);
  return response.data;
};

/**
 * Create a new todo
 */
export const createTodo = async (data: TodoInput): Promise<Todo> => {
  const response = await apiClient.post<Todo>('/records/todos', data);
  return response.data;
};

/**
 * Update a todo (partial update using PATCH)
 */
export const updateTodo = async (id: string, data: Partial<TodoInput>): Promise<Todo> => {
  const response = await apiClient.patch<Todo>(`/records/todos/${id}`, data);
  return response.data;
};

/**
 * Delete a todo
 */
export const deleteTodo = async (id: string): Promise<void> => {
  await apiClient.delete(`/records/todos/${id}`);
};

/**
 * Toggle todo completion status
 */
export const toggleTodoComplete = async (id: string, completed: boolean): Promise<Todo> => {
  return updateTodo(id, { completed });
};
