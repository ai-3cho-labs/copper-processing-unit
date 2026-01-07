'use client';

import { useRef, useEffect, useCallback, useState, MouseEvent } from 'react';
import { cn } from '@/lib/cn';
import { Tile, EditorDispatch } from './useEditorState';
import { SpriteSheet } from './EditorCanvas';

export interface TilePaletteProps {
  spriteSheets: SpriteSheet[];
  selectedTile: Tile | null;
  dispatch: EditorDispatch;
  className?: string;
}

/**
 * Tile palette component
 * Displays sprite sheets and allows selecting tiles
 */
export function TilePalette({
  spriteSheets,
  selectedTile,
  dispatch,
  className,
}: TilePaletteProps) {
  const [activeSheetId, setActiveSheetId] = useState<string>(spriteSheets[0]?.id ?? '');
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hoveredTile, setHoveredTile] = useState<{ x: number; y: number } | null>(null);

  const activeSheet = spriteSheets.find(s => s.id === activeSheetId);
  const scale = 2; // Display scale for palette

  // Calculate palette dimensions
  const paletteWidth = activeSheet?.image?.width ?? 0;
  const paletteHeight = activeSheet?.image?.height ?? 0;
  const scaledWidth = paletteWidth * scale;
  const scaledHeight = paletteHeight * scale;

  // Render palette canvas
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx || !activeSheet?.image) return;

    // Clear
    ctx.fillStyle = '#241c16';
    ctx.fillRect(0, 0, scaledWidth, scaledHeight);

    // Draw sprite sheet
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(activeSheet.image, 0, 0, scaledWidth, scaledHeight);

    // Draw grid
    ctx.strokeStyle = 'rgba(61, 53, 45, 0.5)';
    ctx.lineWidth = 1;

    const tileW = activeSheet.tileWidth * scale;
    const tileH = activeSheet.tileHeight * scale;
    const cols = Math.floor(paletteWidth / activeSheet.tileWidth);
    const rows = Math.floor(paletteHeight / activeSheet.tileHeight);

    for (let x = 0; x <= cols; x++) {
      ctx.beginPath();
      ctx.moveTo(x * tileW, 0);
      ctx.lineTo(x * tileW, scaledHeight);
      ctx.stroke();
    }
    for (let y = 0; y <= rows; y++) {
      ctx.beginPath();
      ctx.moveTo(0, y * tileH);
      ctx.lineTo(scaledWidth, y * tileH);
      ctx.stroke();
    }

    // Highlight hovered tile
    if (hoveredTile) {
      ctx.fillStyle = 'rgba(255, 255, 255, 0.2)';
      ctx.fillRect(
        hoveredTile.x * tileW,
        hoveredTile.y * tileH,
        tileW,
        tileH
      );
    }

    // Highlight selected tile
    if (selectedTile && selectedTile.spriteSheetId === activeSheetId) {
      const selX = selectedTile.spriteX / activeSheet.tileWidth;
      const selY = selectedTile.spriteY / activeSheet.tileHeight;

      ctx.strokeStyle = '#fbf236';
      ctx.lineWidth = 2;
      ctx.strokeRect(
        selX * tileW + 1,
        selY * tileH + 1,
        tileW - 2,
        tileH - 2
      );
    }
  }, [activeSheet, scaledWidth, scaledHeight, paletteWidth, paletteHeight, hoveredTile, selectedTile, activeSheetId, scale]);

  useEffect(() => {
    render();
  }, [render]);

  // Get tile coordinates from mouse position
  const getTileCoords = useCallback((e: MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas || !activeSheet) return null;

    const rect = canvas.getBoundingClientRect();
    const tileW = activeSheet.tileWidth * scale;
    const tileH = activeSheet.tileHeight * scale;

    const x = Math.floor((e.clientX - rect.left) / tileW);
    const y = Math.floor((e.clientY - rect.top) / tileH);

    const cols = Math.floor(paletteWidth / activeSheet.tileWidth);
    const rows = Math.floor(paletteHeight / activeSheet.tileHeight);

    if (x < 0 || x >= cols || y < 0 || y >= rows) return null;
    return { x, y };
  }, [activeSheet, paletteWidth, paletteHeight, scale]);

  const handleMouseMove = useCallback((e: MouseEvent<HTMLCanvasElement>) => {
    const coords = getTileCoords(e);
    setHoveredTile(coords);
  }, [getTileCoords]);

  const handleMouseLeave = useCallback(() => {
    setHoveredTile(null);
  }, []);

  const handleClick = useCallback((e: MouseEvent<HTMLCanvasElement>) => {
    const coords = getTileCoords(e);
    if (!coords || !activeSheet) return;

    const tile: Tile = {
      spriteSheetId: activeSheetId,
      spriteX: coords.x * activeSheet.tileWidth,
      spriteY: coords.y * activeSheet.tileHeight,
      spriteWidth: activeSheet.tileWidth,
      spriteHeight: activeSheet.tileHeight,
    };

    dispatch({ type: 'SET_SELECTED_TILE', tile });
  }, [getTileCoords, activeSheet, activeSheetId, dispatch]);

  return (
    <div className={cn('flex flex-col', className)}>
      {/* Sprite sheet tabs */}
      <div className="flex gap-1 mb-2 overflow-x-auto">
        {spriteSheets.map(sheet => (
          <button
            key={sheet.id}
            onClick={() => setActiveSheetId(sheet.id)}
            className={cn(
              'px-3 py-1.5 text-xs font-medium rounded whitespace-nowrap',
              'transition-colors',
              activeSheetId === sheet.id
                ? 'bg-copper text-bg-dark'
                : 'bg-bg-surface text-text-secondary hover:bg-bg-card'
            )}
          >
            {sheet.name}
          </button>
        ))}
      </div>

      {/* Selected tile preview */}
      {selectedTile && (
        <div className="mb-2 p-2 bg-bg-surface rounded border border-border">
          <div className="text-xxs text-text-muted mb-1">Selected Tile</div>
          <div className="flex items-center gap-2">
            <div
              className="border border-border"
              style={{
                width: 32,
                height: 32,
                backgroundImage: `url(${spriteSheets.find(s => s.id === selectedTile.spriteSheetId)?.src})`,
                backgroundPosition: `-${selectedTile.spriteX * 2}px -${selectedTile.spriteY * 2}px`,
                backgroundSize: `${(spriteSheets.find(s => s.id === selectedTile.spriteSheetId)?.image?.width ?? 0) * 2}px auto`,
                imageRendering: 'pixelated',
              }}
            />
            <div className="text-xxs text-text-muted">
              {selectedTile.spriteX}, {selectedTile.spriteY}
            </div>
          </div>
        </div>
      )}

      {/* Palette canvas */}
      <div className="overflow-auto border border-border rounded bg-bg-dark max-h-[400px]">
        {activeSheet?.image ? (
          <canvas
            ref={canvasRef}
            width={scaledWidth}
            height={scaledHeight}
            className="cursor-pointer"
            style={{ imageRendering: 'pixelated' }}
            onMouseMove={handleMouseMove}
            onMouseLeave={handleMouseLeave}
            onClick={handleClick}
          />
        ) : (
          <div className="p-4 text-text-muted text-sm">
            Loading sprite sheet...
          </div>
        )}
      </div>

      {/* Tile info */}
      {hoveredTile && activeSheet && (
        <div className="mt-1 text-xxs text-text-muted">
          Tile: ({hoveredTile.x}, {hoveredTile.y}) |
          Pos: ({hoveredTile.x * activeSheet.tileWidth}, {hoveredTile.y * activeSheet.tileHeight})
        </div>
      )}
    </div>
  );
}
