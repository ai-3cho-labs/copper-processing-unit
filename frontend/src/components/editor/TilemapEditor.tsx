'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { cn } from '@/lib/cn';
import { validateTilemapData } from '@/lib/validators';
import { useEditorState } from './useEditorState';
import { EditorCanvas, SpriteSheet } from './EditorCanvas';
import { TilePalette } from './TilePalette';
import { LayerPanel } from './LayerPanel';
import { Toolbar } from './Toolbar';

const STORAGE_KEY = 'copper-tilemap-editor';

// Sprite sheet definitions for the Smallburg Mine Pack
const SPRITE_SHEET_DEFINITIONS: Omit<SpriteSheet, 'image'>[] = [
  // Cave tiles (16x16)
  {
    id: 'walls_floors',
    name: 'Walls & Floors',
    src: '/sprites/walls_and_floors/walls_floors.png',
    tileWidth: 16,
    tileHeight: 16,
  },
  {
    id: 'mine_carts',
    name: 'Mine Carts',
    src: '/sprites/decorations/mine_carts/mine_carts.png',
    tileWidth: 16,
    tileHeight: 16,
  },
  {
    id: 'wall_ores',
    name: 'Wall Ores',
    src: '/sprites/decorations/mining/ores/wall_ores.png',
    tileWidth: 16,
    tileHeight: 16,
  },
  {
    id: 'walls_gems',
    name: 'Wall Gems',
    src: '/sprites/decorations/mining/gems/walls_gems.png',
    tileWidth: 16,
    tileHeight: 16,
  },
  {
    id: 'mine_props',
    name: 'Props',
    src: '/sprites/decorations/props/mine_props.png',
    tileWidth: 16,
    tileHeight: 16,
  },
  {
    id: 'ladders',
    name: 'Ladders',
    src: '/sprites/decorations/props/ladders.png',
    tileWidth: 16,
    tileHeight: 16,
  },
  // Character sprites (56x64)
  {
    id: 'miner_body',
    name: 'Miner Body',
    src: '/sprites/miner-body.png',
    tileWidth: 56,
    tileHeight: 64,
  },
  {
    id: 'miner_overalls',
    name: 'Miner Overalls',
    src: '/sprites/miner-overalls.png',
    tileWidth: 56,
    tileHeight: 64,
  },
  {
    id: 'miner_hair',
    name: 'Miner Hair',
    src: '/sprites/miner-hair.png',
    tileWidth: 56,
    tileHeight: 64,
  },
  // Ores (32x32 for large, variable for others)
  {
    id: 'ores',
    name: 'Ores',
    src: '/sprites/decorations/mining/ores/mining_ores_with_shadows.png',
    tileWidth: 32,
    tileHeight: 32,
  },
];

export interface TilemapEditorProps {
  /** Canvas width in tiles */
  width?: number;
  /** Canvas height in tiles */
  height?: number;
  /** Tile size in pixels */
  tileSize?: number;
  className?: string;
}

/**
 * Main tilemap editor component
 * Combines canvas, palette, layers, and toolbar
 */
export function TilemapEditor({
  width = 120, // 1920px / 16px = 120 tiles (for full scene width)
  height = 25, // 400px / 16px = 25 tiles (for scene height)
  tileSize = 16,
  className,
}: TilemapEditorProps) {
  const [spriteSheets, setSpriteSheets] = useState<SpriteSheet[]>([]);
  const [zoom, setZoom] = useState(3);
  const [isLoading, setIsLoading] = useState(true);
  const exportCanvasRef = useRef<HTMLCanvasElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { state, dispatch, undo, redo, canUndo, canRedo } = useEditorState({
    width,
    height,
    tileSize,
  });

  // Load saved state from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const data = JSON.parse(saved);
        if (validateTilemapData(data)) {
          dispatch({
            type: 'LOAD_STATE',
            state: {
              width: data.width,
              height: data.height,
              tileSize: data.tileSize,
              layers: data.layers,
              activeLayerId: data.layers[0]?.id,
              objects: data.objects || [],
              selectedObjectId: null,
            },
          });
        }
      } catch (err) {
        console.warn('Failed to load saved tilemap:', err);
      }
    }
  }, [dispatch]);

  // Save to localStorage
  const handleSave = useCallback(() => {
    const data = {
      version: 2,
      width: state.width,
      height: state.height,
      tileSize: state.tileSize,
      layers: state.layers.map(layer => ({
        id: layer.id,
        name: layer.name,
        visible: layer.visible,
        locked: layer.locked,
        opacity: layer.opacity,
        cells: layer.cells,
      })),
      objects: state.objects,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }, [state]);

  // Load sprite sheet images
  useEffect(() => {
    const loadSpriteSheets = async () => {
      setIsLoading(true);

      const loaded: SpriteSheet[] = await Promise.all(
        SPRITE_SHEET_DEFINITIONS.map(
          (def) =>
            new Promise<SpriteSheet>((resolve) => {
              const img = new Image();
              img.onload = () => {
                resolve({ ...def, image: img });
              };
              img.onerror = () => {
                console.warn(`Failed to load sprite sheet: ${def.src}`);
                resolve({ ...def, image: null });
              };
              img.src = def.src;
            })
        )
      );

      setSpriteSheets(loaded);
      setIsLoading(false);
    };

    loadSpriteSheets();
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Prevent shortcuts when typing in inputs
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }

      // Tool shortcuts
      if (!e.ctrlKey && !e.metaKey) {
        switch (e.key.toLowerCase()) {
          case 'v':
            dispatch({ type: 'SET_TOOL', tool: 'select' });
            break;
          case 'b':
            dispatch({ type: 'SET_TOOL', tool: 'paint' });
            break;
          case 'e':
            dispatch({ type: 'SET_TOOL', tool: 'erase' });
            break;
          case 'g':
            dispatch({ type: 'SET_TOOL', tool: 'fill' });
            break;
          case 'i':
            dispatch({ type: 'SET_TOOL', tool: 'eyedropper' });
            break;
          case 'o':
            dispatch({ type: 'SET_TOOL', tool: 'object' });
            break;
          case 'escape':
            dispatch({ type: 'SET_SELECTION', selection: null });
            break;
          case 'delete':
          case 'backspace':
            if (state.selection) {
              dispatch({ type: 'DELETE_SELECTION' });
            }
            break;
        }
      }

      // Ctrl/Cmd shortcuts
      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case 'z':
            e.preventDefault();
            if (e.shiftKey) {
              redo();
            } else {
              undo();
            }
            break;
          case 'y':
            e.preventDefault();
            redo();
            break;
          case 's':
            e.preventDefault();
            handleSave();
            break;
          case 'c':
            if (state.selection) {
              e.preventDefault();
              dispatch({ type: 'COPY_SELECTION' });
            }
            break;
          case 'v':
            if (state.clipboard && state.selection) {
              e.preventDefault();
              dispatch({
                type: 'PASTE',
                x: Math.min(state.selection.startX, state.selection.endX),
                y: Math.min(state.selection.startY, state.selection.endY),
              });
            }
            break;
          case 'a':
            e.preventDefault();
            dispatch({
              type: 'SET_SELECTION',
              selection: { startX: 0, startY: 0, endX: state.width - 1, endY: state.height - 1 },
            });
            break;
        }
      }

      // Zoom shortcuts
      if (e.key === '+' || e.key === '=') {
        setZoom(z => Math.min(8, z + 1));
      } else if (e.key === '-') {
        setZoom(z => Math.max(1, z - 1));
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [dispatch, undo, redo, handleSave, state.selection, state.clipboard, state.width, state.height]);

  // Export as PNG
  const handleExportPNG = useCallback(() => {
    const canvas = document.createElement('canvas');
    canvas.width = state.width * state.tileSize;
    canvas.height = state.height * state.tileSize;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.imageSmoothingEnabled = false;

    // Draw all visible layers
    for (const layer of state.layers) {
      if (!layer.visible) continue;

      ctx.globalAlpha = layer.opacity;

      for (let y = 0; y < state.height; y++) {
        for (let x = 0; x < state.width; x++) {
          const cell = layer.cells[y]?.[x];
          if (!cell?.tile) continue;

          const spriteSheet = spriteSheets.find(s => s.id === cell.tile!.spriteSheetId);
          if (!spriteSheet?.image) continue;

          // Draw at actual sprite dimensions
          ctx.drawImage(
            spriteSheet.image,
            cell.tile.spriteX,
            cell.tile.spriteY,
            cell.tile.spriteWidth,
            cell.tile.spriteHeight,
            x * state.tileSize,
            y * state.tileSize,
            cell.tile.spriteWidth,
            cell.tile.spriteHeight
          );
        }
      }

      ctx.globalAlpha = 1;
    }

    // Draw objects (sorted by zIndex)
    const sortedObjects = [...state.objects].sort((a, b) => a.zIndex - b.zIndex);
    for (const obj of sortedObjects) {
      const spriteSheet = spriteSheets.find(s => s.id === obj.sprite.spriteSheetId);
      if (!spriteSheet?.image) continue;

      // Bottom-center anchor
      const drawX = obj.x - obj.sprite.spriteWidth / 2;
      const drawY = obj.y - obj.sprite.spriteHeight;

      ctx.drawImage(
        spriteSheet.image,
        obj.sprite.spriteX,
        obj.sprite.spriteY,
        obj.sprite.spriteWidth,
        obj.sprite.spriteHeight,
        drawX,
        drawY,
        obj.sprite.spriteWidth,
        obj.sprite.spriteHeight
      );
    }

    // Download
    const link = document.createElement('a');
    link.download = `tilemap-${Date.now()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  }, [state, spriteSheets]);

  // Export as JSON
  const handleExportJSON = useCallback(() => {
    const data = {
      version: 2,
      width: state.width,
      height: state.height,
      tileSize: state.tileSize,
      layers: state.layers.map(layer => ({
        id: layer.id,
        name: layer.name,
        visible: layer.visible,
        locked: layer.locked,
        opacity: layer.opacity,
        cells: layer.cells,
      })),
      objects: state.objects,
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    link.download = `tilemap-${Date.now()}.json`;
    link.href = URL.createObjectURL(blob);
    link.click();
    URL.revokeObjectURL(link.href);
  }, [state]);

  // Import from JSON
  const handleImportJSON = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target?.result as string);
        if (validateTilemapData(data)) {
          dispatch({
            type: 'LOAD_STATE',
            state: {
              width: data.width,
              height: data.height,
              tileSize: data.tileSize,
              layers: data.layers,
              activeLayerId: data.layers[0]?.id,
              objects: data.objects || [],
              selectedObjectId: null,
            },
          });
        } else {
          console.error('Invalid tilemap file structure');
        }
      } catch (err) {
        console.error('Failed to parse tilemap JSON:', err);
      }
    };
    reader.readAsText(file);

    // Reset input
    e.target.value = '';
  }, [dispatch]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-bg-dark">
        <div className="text-copper">Loading sprite sheets...</div>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col h-screen bg-bg-dark', className)}>
      {/* Toolbar */}
      <Toolbar
        state={state}
        dispatch={dispatch}
        onUndo={undo}
        onRedo={redo}
        canUndo={canUndo}
        canRedo={canRedo}
        zoom={zoom}
        onZoomChange={setZoom}
        onSave={handleSave}
        onExport={handleExportPNG}
        onExportJSON={handleExportJSON}
        onImportJSON={handleImportJSON}
      />

      {/* Hidden file input for import */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".json"
        className="hidden"
        onChange={handleFileChange}
      />

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar - Tile Palette */}
        <div className="w-72 border-r border-border p-3 overflow-y-auto bg-bg-card">
          <TilePalette
            spriteSheets={spriteSheets}
            selectedTile={state.selectedTile}
            dispatch={dispatch}
          />
        </div>

        {/* Canvas area */}
        <div className="flex-1 overflow-auto p-4">
          <EditorCanvas
            state={state}
            dispatch={dispatch}
            spriteSheets={spriteSheets}
            zoom={zoom}
            className="inline-block"
          />
        </div>

        {/* Right sidebar - Layers */}
        <div className="w-64 border-l border-border p-3 overflow-y-auto bg-bg-card">
          <LayerPanel
            layers={state.layers}
            activeLayerId={state.activeLayerId}
            dispatch={dispatch}
          />

          {/* Help section */}
          <div className="mt-6 pt-4 border-t border-border">
            <div className="text-xs text-text-muted mb-2">Keyboard Shortcuts</div>
            <div className="text-xxs text-text-muted/70 space-y-1">
              <div><span className="text-text-secondary">V</span> Select</div>
              <div><span className="text-text-secondary">B</span> Paint brush</div>
              <div><span className="text-text-secondary">E</span> Eraser</div>
              <div><span className="text-text-secondary">G</span> Fill bucket</div>
              <div><span className="text-text-secondary">I</span> Eyedropper</div>
              <div><span className="text-text-secondary">Ctrl+Z</span> Undo</div>
              <div><span className="text-text-secondary">Ctrl+Y</span> Redo</div>
              <div><span className="text-text-secondary">Ctrl+C</span> Copy</div>
              <div><span className="text-text-secondary">Ctrl+V</span> Paste</div>
              <div><span className="text-text-secondary">+/-</span> Zoom</div>
              <div><span className="text-text-secondary">Esc</span> Deselect</div>
            </div>
          </div>
        </div>
      </div>

      {/* Hidden export canvas */}
      <canvas ref={exportCanvasRef} className="hidden" />
    </div>
  );
}
