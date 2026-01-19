/**
 * Todo list component
 * Main container for the todo app
 */

import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { useAuthStore } from '@/stores/auth.store';
import { Button } from '@/components/ui/button';
import TodoItem from './TodoItem';
import TodoForm from './TodoForm';
import { Plus, Loader2, LogOut, CheckCircle, Circle, List } from 'lucide-react';
import * as todosService from '@/services/todos.service';
import type { Todo, TodoInput } from '@/types';

type Filter = 'all' | 'active' | 'completed';

export default function TodoList() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();

  const [todos, setTodos] = useState<Todo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingTodo, setEditingTodo] = useState<Todo | undefined>(undefined);
  const [filter, setFilter] = useState<Filter>('all');
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');

  const fetchTodos = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await todosService.getTodos();
      setTodos(response.items);
    } catch (error) {
      console.error('Failed to fetch todos:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTodos();
  }, [fetchTodos]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleCreateTodo = async (data: TodoInput) => {
    await todosService.createTodo(data);
    await fetchTodos();
  };

  const handleUpdateTodo = async (data: TodoInput) => {
    if (editingTodo) {
      await todosService.updateTodo(editingTodo.id, data);
      await fetchTodos();
      setEditingTodo(undefined);
    }
  };

  const handleToggleTodo = async (id: string, completed: boolean) => {
    await todosService.toggleTodoComplete(id, completed);
    await fetchTodos();
  };

  const handleDeleteTodo = async (id: string) => {
    await todosService.deleteTodo(id);
    await fetchTodos();
  };

  const handleEditClick = (todo: Todo) => {
    setEditingTodo(todo);
    setFormMode('edit');
    setIsFormOpen(true);
  };

  const handleCreateClick = () => {
    setEditingTodo(undefined);
    setFormMode('create');
    setIsFormOpen(true);
  };

  const filteredTodos = todos.filter((todo) => {
    if (filter === 'active') return !todo.completed;
    if (filter === 'completed') return todo.completed;
    return true;
  });

  const activeCount = todos.filter((t) => !t.completed).length;
  const completedCount = todos.filter((t) => t.completed).length;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">My Todos</h1>
            <p className="text-sm text-gray-600">Welcome, {user?.email}</p>
          </div>
          <Button variant="outline" onClick={handleLogout}>
            <LogOut className="h-4 w-4 mr-2" />
            Logout
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-3xl mx-auto px-4 py-8">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
            <p className="text-2xl font-bold text-gray-900">{todos.length}</p>
            <p className="text-sm text-gray-600">Total</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
            <p className="text-2xl font-bold text-blue-600">{activeCount}</p>
            <p className="text-sm text-gray-600">Active</p>
          </div>
          <div className="bg-white rounded-lg border border-gray-200 p-4 text-center">
            <p className="text-2xl font-bold text-green-600">{completedCount}</p>
            <p className="text-sm text-gray-600">Completed</p>
          </div>
        </div>

        {/* Action Bar */}
        <div className="flex items-center justify-between mb-6">
          {/* Filters */}
          <div className="flex items-center gap-2">
            <Button
              variant={filter === 'all' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilter('all')}
            >
              <List className="h-4 w-4 mr-1" />
              All
            </Button>
            <Button
              variant={filter === 'active' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilter('active')}
            >
              <Circle className="h-4 w-4 mr-1" />
              Active
            </Button>
            <Button
              variant={filter === 'completed' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilter('completed')}
            >
              <CheckCircle className="h-4 w-4 mr-1" />
              Completed
            </Button>
          </div>

          {/* Add Button */}
          <Button onClick={handleCreateClick}>
            <Plus className="h-4 w-4 mr-2" />
            Add Todo
          </Button>
        </div>

        {/* Todo List */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
          </div>
        ) : filteredTodos.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-lg text-gray-600">
              {filter === 'all'
                ? 'No todos yet. Create your first todo!'
                : filter === 'active'
                ? 'No active todos.'
                : 'No completed todos yet.'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredTodos.map((todo) => (
              <TodoItem
                key={todo.id}
                todo={todo}
                onToggle={handleToggleTodo}
                onEdit={handleEditClick}
                onDelete={handleDeleteTodo}
              />
            ))}
          </div>
        )}
      </main>

      {/* Todo Form Dialog */}
      <TodoForm
        open={isFormOpen}
        onOpenChange={setIsFormOpen}
        onSubmit={formMode === 'create' ? handleCreateTodo : handleUpdateTodo}
        todo={editingTodo}
        mode={formMode}
      />
    </div>
  );
}
