/**
 * Migrations API service
 */
import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';

export function createMigrationsService(client: SnackBaseClient) {
  return {
    listMigrations: () => client.migrations.list(),
    getCurrentMigration: () => client.migrations.getCurrent(),
    getMigrationHistory: () => client.migrations.getHistory(),
  };
}

export const useMigrationsService = createServiceHook(createMigrationsService);

const migrationsService = bindService(createMigrationsService);
export const listMigrations = migrationsService.listMigrations;
export const getCurrentMigration = migrationsService.getCurrentMigration;
export const getMigrationHistory = migrationsService.getMigrationHistory;
