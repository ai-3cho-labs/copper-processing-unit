'use client';

import { TilemapEditor } from '@/components/editor';

/**
 * Dev-only tilemap editor page
 * Used for composing tilemap scenes for the dashboard
 *
 * Supports multiple sprite sizes:
 * - Cave tiles: 16×16px
 * - Character sprites: 56×64px
 * - Ores: 32×32px
 *
 * Save: Ctrl+S or Save button (persists to localStorage)
 */
export default function TilemapEditorPage() {
  return (
    <TilemapEditor
      width={12}   // 12 tiles × 16px = 192px base grid
      height={12}  // 12 tiles × 16px = 192px
      tileSize={16}
    />
  );
}
