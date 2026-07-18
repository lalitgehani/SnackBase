/**
 * Default landing tab when selecting a collection.
 * Data if there are records; otherwise Schema.
 */
export function resolveDefaultTab(recordsCount: number): 'data' | 'schema' {
  return recordsCount > 0 ? 'data' : 'schema'
}
