'use client';

import { TilemapEditor } from '@/components/editor';

/**
 * Dev-only tilemap editor page
 * Used for composing parallax background layers for the mining scene
 *
 * Default canvas size matches the spec:
 * - Width: 1920px (120 tiles at 16px each)
 * - Height: 400px (25 tiles at 16px each)
 */
export default function TilemapEditorPage() {
  return (
    <TilemapEditor
      width={120}  // 1920px / 16px = 120 tiles
      height={25}  // 400px / 16px = 25 tiles
      tileSize={16}
    />
  );
}
