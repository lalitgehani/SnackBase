import { describe, it, expect } from 'vitest';
import {
    isHookFullBleedPath,
    isFullBleedAdminPath,
    getAdminPageTitle,
} from '@/layouts/adminLayoutHelpers';

describe('AdminLayout hook path helpers', () => {
    it('classifies non-list hooks paths as full-bleed', () => {
        expect(isHookFullBleedPath('/admin/hooks')).toBe(false);
        expect(isHookFullBleedPath('/admin/hooks/new')).toBe(true);
        expect(isHookFullBleedPath('/admin/hooks/abc/edit')).toBe(true);
        expect(isHookFullBleedPath('/admin/hooks/abc')).toBe(true);
    });

    it('includes hooks in isFullBleedAdminPath', () => {
        expect(isFullBleedAdminPath('/admin/hooks')).toBe(false);
        expect(isFullBleedAdminPath('/admin/hooks/new')).toBe(true);
        expect(isFullBleedAdminPath('/admin/collections/posts')).toBe(true);
    });

    it('maps page titles for hooks routes', () => {
        expect(getAdminPageTitle('/admin/hooks')).toBe('Hooks');
        expect(getAdminPageTitle('/admin/hooks/new')).toBe('New Hook');
        expect(getAdminPageTitle('/admin/hooks/hk-1/edit')).toBe('Edit Hook');
        expect(getAdminPageTitle('/admin/hooks/hk-1')).toBe('Hook Overview');
    });
});
