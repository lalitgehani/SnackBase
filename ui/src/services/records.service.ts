/**
 * Records API service
 */
import type { SnackBaseClient } from '@snackbase/sdk';
import { createServiceHook } from '@/lib/snackbase/createServiceHook';
import { bindService } from '@/lib/snackbase/bindService';
import type {
  RecordDetail,
  RecordData,
  GetRecordsParams,
  ListResponse,
  BatchUpdateItem,
  BatchCreateResponse,
  BatchUpdateResponse,
  BatchDeleteResponse,
  AggregationRequest,
  AggregationResponse,
} from '@/types/records.types';

export type { RecordData, RecordListItem } from '@/types/records.types';

export function createRecordsService(client: SnackBaseClient) {
  return {
    getRecords: (params: GetRecordsParams): Promise<ListResponse> => {
      const { collection, ...queryParams } = params;
      return client.records.list(collection, queryParams);
    },
    getRecordById: (collection: string, recordId: string): Promise<RecordDetail> =>
      client.records.get(collection, recordId),
    createRecord: (collection: string, data: RecordData): Promise<RecordDetail> =>
      client.records.create(collection, data),
    updateRecord: (collection: string, recordId: string, data: RecordData): Promise<RecordDetail> =>
      client.records.update(collection, recordId, data),
    patchRecord: (collection: string, recordId: string, data: Partial<RecordData>): Promise<RecordDetail> =>
      client.records.patch(collection, recordId, data),
    deleteRecord: async (collection: string, recordId: string) => {
      await client.records.delete(collection, recordId);
    },
    batchCreateRecords: (collection: string, records: RecordData[]): Promise<BatchCreateResponse> =>
      client.records.batchCreate(collection, records),
    batchUpdateRecords: (collection: string, updates: BatchUpdateItem[]): Promise<BatchUpdateResponse> =>
      client.records.batchUpdate(collection, updates),
    batchDeleteRecords: (collection: string, ids: string[]): Promise<BatchDeleteResponse> =>
      client.records.batchDelete(collection, ids),
    aggregateRecords: (collection: string, params: AggregationRequest): Promise<AggregationResponse> =>
      client.records.aggregate(collection, params),
  };
}

export const useRecordsService = createServiceHook(createRecordsService);

const recordsService = bindService(createRecordsService);
export const getRecords = recordsService.getRecords;
export const getRecordById = recordsService.getRecordById;
export const createRecord = recordsService.createRecord;
export const updateRecord = recordsService.updateRecord;
export const patchRecord = recordsService.patchRecord;
export const deleteRecord = recordsService.deleteRecord;
export const batchCreateRecords = recordsService.batchCreateRecords;
export const batchUpdateRecords = recordsService.batchUpdateRecords;
export const batchDeleteRecords = recordsService.batchDeleteRecords;
export const aggregateRecords = recordsService.aggregateRecords;
