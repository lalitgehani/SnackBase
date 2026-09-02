/**
 * Client-side cron sanity check shared by the backup settings form (F6.1).
 * The authoritative validation happens server-side with the parser.
 */
export function isPlausibleCron(expr: string): boolean {
  const fields = expr.trim().split(/\s+/);
  if (fields.length !== 5) return false;
  const ranges: [number, number][] = [
    [0, 59],
    [0, 23],
    [1, 31],
    [1, 12],
    [0, 7],
  ];
  const atom = (part: string, min: number, max: number): boolean => {
    const value = Number(part);
    return Number.isInteger(value) && value >= min && value <= max;
  };
  return fields.every((field, index) => {
    const [lo, hi] = ranges[index];
    const options = field.split(',');
    return options.every((option) => {
      let body = option;
      if (body === '*') return true;
      if (body.startsWith('*/')) {
        body = body.slice(2);
        return /^\d+$/.test(body) && Number(body) >= 1;
      }
      if (body.includes('-')) {
        const [a, b] = body.split('-');
        return atom(a, lo, hi) && atom(b, lo, hi);
      }
      return /^\d+$/.test(body) ? atom(body, lo, hi) : /^[A-Za-z]{3}$/.test(body);
    });
  });
}
