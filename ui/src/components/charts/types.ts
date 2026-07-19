/**
 * Shared chart prop types
 */

export interface TimeSeriesDatum {
  date: string;
  count: number;
  [key: string]: string | number;
}

export interface NamedSeries {
  key: string;
  label: string;
  color?: string;
}

export interface CategoryValueDatum {
  name: string;
  value: number;
  color?: string;
}

export interface RankedBarDatum {
  name: string;
  value: number;
  color?: string;
}

export interface StackedBarDatum {
  /** Category axis key (e.g. date) */
  name: string;
  [seriesKey: string]: string | number;
}
