'use client';

import { useRef, useEffect, useCallback, useState, MouseEvent } from 'react';
import { cn } from '@/lib/cn';
import { EditorState, EditorDispatch } from './useEditorState';

export interface SpriteSheet {
  id: string;
  name: string;
  src: string;
  image: HTMLImageElement | null;
  tileWidth: number;
  tileHeight: number;
}

export interface EditorCanvasProps {
  state: EditorState;
  dispatch: EditorDispatch;
  spriteSheets: SpriteSheet[];
  zoom: number;
  className?: string;
}

/**
 * Main canvas component for the tilemap editor
 * Handles rendering and mouse interaction
 */
export function EditorCanvas({
  state,
  dispatch,
  spriteSheets,
  zoom,
  className,
}: EditorCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isPainting, setIsPainting] = useState(false);
  const [lastPaintPos, setLastPaintPos] = useState<{ x: number; y: number } | null>(null);

  const scaledTileSize = state.tileSize * zoom;
  const canvasWidth = state.width * scaledTileSize;
  const canvasHeight = state.height * scaledTileSize;

  // Get sprite sheet image by ID
  const getSpriteSheet = useCallback((id: string) => {
    return spriteSheets.find(s => s.id === id);
  }, [spriteSheets]);

  // Render the canvas
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;

    // Clear canvas
    ctx.fillStyle = '#1a1410';
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);

    // Enable pixel-perfect rendering
    ctx.imageSmoothingEnabled = false;

    // Draw grid
    ctx.strokeStyle = '#3d352d';
    ctx.lineWidth = 1;
    for (let x = 0; x <= state.width; x++) {
      ctx.beginPath();
      ctx.moveTo(x * scaledTileSize, 0);
      ctx.lineTo(x * scaledTileSize, canvasHeight);
      ctx.stroke();
    }
    for (let y = 0; y <= state.height; y++) {
      ctx.beginPath();
      ctx.moveTo(0, y * scaledTileSize);
      ctx.lineTo(canvasWidth, y * scaledTileSize);
      ctx.stroke();
    }

    // Draw layers (from back to front)
    for (const layer of state.layers) {
      if (!layer.visible) continue;

      ctx.globalAlpha = layer.opacity;

      for (let y = 0; y < state.height; y++) {
        for (let x = 0; x < state.width; x++) {
          const cell = layer.cells[y]?.[x];
          if (!cell?.tile) continue;

          const spriteSheet = getSpriteSheet(cell.tile.spriteSheetId);
          if (!spriteSheet?.image) continue;

          ctx.drawImage(
            spriteSheet.image,
            cell.tile.spriteX,
            cell.tile.spriteY,
            cell.tile.spriteWidth,
            cell.tile.spriteHeight,
            x * scaledTileSize,
            y * scaledTileSize,
            scaledTileSize,
            scaledTileSize
          );
        }
      }

      ctx.globalAlpha = 1;
    }

    // Draw selection
    if (state.selection) {
      const { startX, startY, endX, endY } = state.selection;
      const minX = Math.min(startX, endX);
      const maxX = Math.max(startX, endX);
      const minY = Math.min(startY, endY);
      const maxY = Math.max(startY, endY);

      ctx.strokeStyle = '#fbf236';
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 5]);
      ctx.strokeRect(
        minX * scaledTileSize,
        minY * scaledTileSize,
        (maxX - minX + 1) * scaledTileSize,
        (maxY - minY + 1) * scaledTileSize
      );
      ctx.setLineDash([]);

      // Semi-transparent fill
      ctx.fillStyle = 'rgba(251, 242, 54, 0.1)';
      ctx.fillRect(
        minX * scaledTileSize,
        minY * scaledTileSize,
        (maxX - minX + 1) * scaledTileSize,
        (maxY - minY + 1) * scaledTileSize
      );
    }

    // Highlight active layer indicator
    const activeLayer = state.layers.find(l => l.id === state.activeLayerId);
    if (activeLayer?.locked) {
      ctx.fillStyle = 'rgba(172, 50, 50, 0.1)';
      ctx.fillRect(0, 0, canvasWidth, canvasHeight);
    }
  }, [state, canvasWidth, canvasHeight, scaledTileSize, getSpriteSheet]);

  // Re-render when state or sprite sheets change
  useEffect(() => {
    render();
  }, [render, spriteSheets]);

  // Convert mouse position to tile coordinates
  const getTileCoords = useCallback((e: MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return null;

    const rect = canvas.getBoundingClientRect();
    const x = Math.floor((e.clientX - rect.left) / scaledTileSize);
    const y = Math.floor((e.clientY - rect.top) / scaledTileSize);

    if (x < 0 || x >= state.width || y < 0 || y >= state.height) return null;
    return { x, y };
  }, [scaledTileSize, state.width, state.height]);

  // Handle paint action
  const paint = useCallback((x: number, y: number) => {
    if (state.tool === 'paint' && state.selectedTile) {
      dispatch({ type: 'SET_TILE', layerId: state.activeLayerId, x, y, tile: state.selectedTile });
    } else if (state.tool === 'erase') {
      dispatch({ type: 'SET_TILE', layerId: state.activeLayerId, x, y, tile: null });
    }
  }, [state.tool, state.selectedTile, state.activeLayerId, dispatch]);

  // Handle fill action
  const fill = useCallback((x: number, y: number) => {
    if (state.tool === 'fill') {
      dispatch({
        type: 'FILL_AREA',
        layerId: state.activeLayerId,
        startX: x,
        startY: y,
        tile: state.selectedTile,
      });
    }
  }, [state.tool, state.selectedTile, state.activeLayerId, dispatch]);

  // Handle eyedropper
  const eyedrop = useCallback((x: number, y: number) => {
    const activeLayer = state.layers.find(l => l.id === state.activeLayerId);
    const tile = activeLayer?.cells[y]?.[x]?.tile;
    if (tile) {
      dispatch({ type: 'SET_SELECTED_TILE', tile });
      dispatch({ type: 'SET_TOOL', tool: 'paint' });
    }
  }, [state.layers, state.activeLayerId, dispatch]);

  // Mouse event handlers
  const handleMouseDown = useCallback((e: MouseEvent<HTMLCanvasElement>) => {
    const coords = getTileCoords(e);
    if (!coords) return;

    if (state.tool === 'select') {
      dispatch({ type: 'SET_SELECTION', selection: { startX: coords.x, startY: coords.y, endX: coords.x, endY: coords.y } });
    } else if (state.tool === 'paint' || state.tool === 'erase') {
      setIsPainting(true);
      setLastPaintPos(coords);
      paint(coords.x, coords.y);
    } else if (state.tool === 'fill') {
      fill(coords.x, coords.y);
    } else if (state.tool === 'eyedropper') {
      eyedrop(coords.x, coords.y);
    }
  }, [getTileCoords, state.tool, dispatch, paint, fill, eyedrop]);

  const handleMouseMove = useCallback((e: MouseEvent<HTMLCanvasElement>) => {
    const coords = getTileCoords(e);
    if (!coords) return;

    if (state.tool === 'select' && state.selection && e.buttons === 1) {
      dispatch({
        type: 'SET_SELECTION',
        selection: { ...state.selection, endX: coords.x, endY: coords.y },
      });
    } else if (isPainting && (state.tool === 'paint' || state.tool === 'erase')) {
      // Line drawing between last position and current
      if (lastPaintPos && (lastPaintPos.x !== coords.x || lastPaintPos.y !== coords.y)) {
        // Bresenham's line algorithm for smooth line drawing
        const dx = Math.abs(coords.x - lastPaintPos.x);
        const dy = Math.abs(coords.y - lastPaintPos.y);
        const sx = lastPaintPos.x < coords.x ? 1 : -1;
        const sy = lastPaintPos.y < coords.y ? 1 : -1;
        let err = dx - dy;
        let x = lastPaintPos.x;
        let y = lastPaintPos.y;

        while (true) {
          paint(x, y);
          if (x === coords.x && y === coords.y) break;
          const e2 = 2 * err;
          if (e2 > -dy) {
            err -= dy;
            x += sx;
          }
          if (e2 < dx) {
            err += dx;
            y += sy;
          }
        }
      }
      setLastPaintPos(coords);
    }
  }, [getTileCoords, state.tool, state.selection, isPainting, lastPaintPos, dispatch, paint]);

  const handleMouseUp = useCallback(() => {
    setIsPainting(false);
    setLastPaintPos(null);
  }, []);

  const handleMouseLeave = useCallback(() => {
    setIsPainting(false);
    setLastPaintPos(null);
  }, []);

  return (
    <div
      ref={containerRef}
      className={cn(
        'overflow-auto',
        'border border-border rounded-lg',
        'bg-bg-dark',
        className
      )}
    >
      <canvas
        ref={canvasRef}
        width={canvasWidth}
        height={canvasHeight}
        className="cursor-crosshair"
        style={{
          imageRendering: 'pixelated',
        }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseLeave}
      />
    </div>
  );
}
