/** Platform-only code path marker — referenced only inside `if (IS_PLATFORM)` branches. */
import { PLATFORM_SENTINEL } from './__platform_sentinel__';
import { IS_PLATFORM } from './config';

export function getPlatformSentinel(): string | null {
  if (IS_PLATFORM) {
    return PLATFORM_SENTINEL;
  }
  return null;
}
