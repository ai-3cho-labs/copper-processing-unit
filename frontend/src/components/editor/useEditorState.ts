import { useCallback, useReducer, useRef } from 'react';

// ============================================================================
// Types
// ============================================================================

export interface Tile {
  spriteSheetId: string;
  spriteX: number;
  spriteY: number;
  spriteWidth: number;
  spriteHeight: number;
}

export interface LayerCell {
  tile: Tile | null;
}

export interface Layer {
  id: string;
  name: string;
  visible: boolean;
  locked: boolean;
  opacity: number;
  cells: LayerCell[][]; // [y][x]
}

export interface Selection {
  startX: number;
  startY: number;
  endX: number;
  endY: number;
}

export interface EditorState {
  // Canvas dimensions (in tiles)
  width: number;
  height: number;
  tileSize: number;

  // Layers
  layers: Layer[];
  activeLayerId: string;

  // Current tool
  tool: 'select' | 'paint' | 'erase' | 'fill' | 'eyedropper';

  // Selected tile from palette
  selectedTile: Tile | null;

  // Selection rectangle
  selection: Selection | null;

  // Clipboard for copy/paste
  clipboard: { tiles: (Tile | null)[][]; width: number; height: number } | null;

  // History for undo/redo
  historyIndex: number;
}

type EditorAction =
  | { type: 'SET_TILE'; layerId: string; x: number; y: number; tile: Tile | null }
  | { type: 'SET_TILES'; layerId: string; tiles: { x: number; y: number; tile: Tile | null }[] }
  | { type: 'FILL_AREA'; layerId: string; startX: number; startY: number; tile: Tile | null }
  | { type: 'SET_TOOL'; tool: EditorState['tool'] }
  | { type: 'SET_SELECTED_TILE'; tile: Tile | null }
  | { type: 'SET_SELECTION'; selection: Selection | null }
  | { type: 'ADD_LAYER'; layer: Layer }
  | { type: 'REMOVE_LAYER'; layerId: string }
  | { type: 'SET_ACTIVE_LAYER'; layerId: string }
  | { type: 'TOGGLE_LAYER_VISIBILITY'; layerId: string }
  | { type: 'TOGGLE_LAYER_LOCK'; layerId: string }
  | { type: 'SET_LAYER_OPACITY'; layerId: string; opacity: number }
  | { type: 'RENAME_LAYER'; layerId: string; name: string }
  | { type: 'REORDER_LAYERS'; layerIds: string[] }
  | { type: 'COPY_SELECTION' }
  | { type: 'PASTE'; x: number; y: number }
  | { type: 'DELETE_SELECTION' }
  | { type: 'CLEAR_LAYER'; layerId: string }
  | { type: 'RESIZE_CANVAS'; width: number; height: number }
  | { type: 'LOAD_STATE'; state: Partial<EditorState> };

// ============================================================================
// Helpers
// ============================================================================

function createEmptyLayer(id: string, name: string, width: number, height: number): Layer {
  const cells: LayerCell[][] = [];
  for (let y = 0; y < height; y++) {
    const row: LayerCell[] = [];
    for (let x = 0; x < width; x++) {
      row.push({ tile: null });
    }
    cells.push(row);
  }
  return {
    id,
    name,
    visible: true,
    locked: false,
    opacity: 1,
    cells,
  };
}

function cloneLayer(layer: Layer): Layer {
  return {
    ...layer,
    cells: layer.cells.map(row => row.map(cell => ({ tile: cell.tile ? { ...cell.tile } : null }))),
  };
}

function floodFill(
  cells: LayerCell[][],
  startX: number,
  startY: number,
  newTile: Tile | null,
  width: number,
  height: number
): { x: number; y: number; tile: Tile | null }[] {
  const changes: { x: number; y: number; tile: Tile | null }[] = [];
  const targetTile = cells[startY]?.[startX]?.tile;

  // If target is same as new tile, nothing to do
  if (JSON.stringify(targetTile) === JSON.stringify(newTile)) {
    return changes;
  }

  const visited = new Set<string>();
  const stack: [number, number][] = [[startX, startY]];

  while (stack.length > 0) {
    const [x, y] = stack.pop()!;
    const key = `${x},${y}`;

    if (visited.has(key)) continue;
    if (x < 0 || x >= width || y < 0 || y >= height) continue;

    const currentTile = cells[y]?.[x]?.tile;
    if (JSON.stringify(currentTile) !== JSON.stringify(targetTile)) continue;

    visited.add(key);
    changes.push({ x, y, tile: newTile });

    stack.push([x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]);
  }

  return changes;
}

// ============================================================================
// Reducer
// ============================================================================

function editorReducer(state: EditorState, action: EditorAction): EditorState {
  switch (action.type) {
    case 'SET_TILE': {
      const layerIndex = state.layers.findIndex(l => l.id === action.layerId);
      const layer = state.layers[layerIndex];
      if (layerIndex === -1 || !layer) return state;

      if (layer.locked) return state;
      if (action.x < 0 || action.x >= state.width || action.y < 0 || action.y >= state.height) return state;

      const newLayers = [...state.layers];
      const cloned = cloneLayer(layer);
      cloned.cells[action.y]![action.x] = { tile: action.tile };
      newLayers[layerIndex] = cloned;

      return { ...state, layers: newLayers };
    }

    case 'SET_TILES': {
      const layerIndex = state.layers.findIndex(l => l.id === action.layerId);
      const layer = state.layers[layerIndex];
      if (layerIndex === -1 || !layer) return state;

      if (layer.locked) return state;

      const newLayers = [...state.layers];
      const cloned = cloneLayer(layer);

      for (const { x, y, tile } of action.tiles) {
        if (x >= 0 && x < state.width && y >= 0 && y < state.height) {
          cloned.cells[y]![x] = { tile };
        }
      }
      newLayers[layerIndex] = cloned;

      return { ...state, layers: newLayers };
    }

    case 'FILL_AREA': {
      const layerIndex = state.layers.findIndex(l => l.id === action.layerId);
      const layer = state.layers[layerIndex];
      if (layerIndex === -1 || !layer) return state;

      if (layer.locked) return state;

      const changes = floodFill(
        layer.cells,
        action.startX,
        action.startY,
        action.tile,
        state.width,
        state.height
      );

      if (changes.length === 0) return state;

      const newLayers = [...state.layers];
      const cloned = cloneLayer(layer);

      for (const { x, y, tile } of changes) {
        cloned.cells[y]![x] = { tile };
      }
      newLayers[layerIndex] = cloned;

      return { ...state, layers: newLayers };
    }

    case 'SET_TOOL':
      return { ...state, tool: action.tool };

    case 'SET_SELECTED_TILE':
      return { ...state, selectedTile: action.tile };

    case 'SET_SELECTION':
      return { ...state, selection: action.selection };

    case 'ADD_LAYER':
      return { ...state, layers: [...state.layers, action.layer], activeLayerId: action.layer.id };

    case 'REMOVE_LAYER': {
      if (state.layers.length <= 1) return state;
      const newLayers = state.layers.filter(l => l.id !== action.layerId);
      const firstLayer = newLayers[0];
      const newActiveId = state.activeLayerId === action.layerId && firstLayer
        ? firstLayer.id
        : state.activeLayerId;
      return { ...state, layers: newLayers, activeLayerId: newActiveId };
    }

    case 'SET_ACTIVE_LAYER':
      return { ...state, activeLayerId: action.layerId };

    case 'TOGGLE_LAYER_VISIBILITY': {
      const newLayers = state.layers.map(l =>
        l.id === action.layerId ? { ...l, visible: !l.visible } : l
      );
      return { ...state, layers: newLayers };
    }

    case 'TOGGLE_LAYER_LOCK': {
      const newLayers = state.layers.map(l =>
        l.id === action.layerId ? { ...l, locked: !l.locked } : l
      );
      return { ...state, layers: newLayers };
    }

    case 'SET_LAYER_OPACITY': {
      const newLayers = state.layers.map(l =>
        l.id === action.layerId ? { ...l, opacity: action.opacity } : l
      );
      return { ...state, layers: newLayers };
    }

    case 'RENAME_LAYER': {
      const newLayers = state.layers.map(l =>
        l.id === action.layerId ? { ...l, name: action.name } : l
      );
      return { ...state, layers: newLayers };
    }

    case 'REORDER_LAYERS': {
      const layerMap = new Map(state.layers.map(l => [l.id, l]));
      const newLayers = action.layerIds
        .map(id => layerMap.get(id))
        .filter((l): l is Layer => l !== undefined);
      return { ...state, layers: newLayers };
    }

    case 'COPY_SELECTION': {
      if (!state.selection) return state;

      const activeLayer = state.layers.find(l => l.id === state.activeLayerId);
      if (!activeLayer) return state;

      const { startX, startY, endX, endY } = state.selection;
      const minX = Math.min(startX, endX);
      const maxX = Math.max(startX, endX);
      const minY = Math.min(startY, endY);
      const maxY = Math.max(startY, endY);

      const width = maxX - minX + 1;
      const height = maxY - minY + 1;
      const tiles: (Tile | null)[][] = [];

      for (let y = 0; y < height; y++) {
        const row: (Tile | null)[] = [];
        for (let x = 0; x < width; x++) {
          const cellY = minY + y;
          const cellX = minX + x;
          row.push(activeLayer.cells[cellY]?.[cellX]?.tile ?? null);
        }
        tiles.push(row);
      }

      return { ...state, clipboard: { tiles, width, height } };
    }

    case 'PASTE': {
      if (!state.clipboard) return state;

      const layerIndex = state.layers.findIndex(l => l.id === state.activeLayerId);
      const layer = state.layers[layerIndex];
      if (layerIndex === -1 || !layer) return state;

      if (layer.locked) return state;

      const newLayers = [...state.layers];
      const cloned = cloneLayer(layer);

      for (let y = 0; y < state.clipboard.height; y++) {
        for (let x = 0; x < state.clipboard.width; x++) {
          const targetX = action.x + x;
          const targetY = action.y + y;
          if (targetX >= 0 && targetX < state.width && targetY >= 0 && targetY < state.height) {
            const clipboardTile = state.clipboard.tiles[y]?.[x] ?? null;
            cloned.cells[targetY]![targetX] = { tile: clipboardTile };
          }
        }
      }
      newLayers[layerIndex] = cloned;

      return { ...state, layers: newLayers };
    }

    case 'DELETE_SELECTION': {
      if (!state.selection) return state;

      const layerIndex = state.layers.findIndex(l => l.id === state.activeLayerId);
      const layer = state.layers[layerIndex];
      if (layerIndex === -1 || !layer) return state;

      if (layer.locked) return state;

      const { startX, startY, endX, endY } = state.selection;
      const minX = Math.min(startX, endX);
      const maxX = Math.max(startX, endX);
      const minY = Math.min(startY, endY);
      const maxY = Math.max(startY, endY);

      const newLayers = [...state.layers];
      const cloned = cloneLayer(layer);

      for (let y = minY; y <= maxY; y++) {
        for (let x = minX; x <= maxX; x++) {
          if (x >= 0 && x < state.width && y >= 0 && y < state.height) {
            cloned.cells[y]![x] = { tile: null };
          }
        }
      }
      newLayers[layerIndex] = cloned;

      return { ...state, layers: newLayers, selection: null };
    }

    case 'CLEAR_LAYER': {
      const layerIndex = state.layers.findIndex(l => l.id === action.layerId);
      const existingLayer = state.layers[layerIndex];
      if (layerIndex === -1 || !existingLayer) return state;

      const newLayers = [...state.layers];
      const cleared = createEmptyLayer(
        action.layerId,
        existingLayer.name,
        state.width,
        state.height
      );
      cleared.visible = existingLayer.visible;
      cleared.locked = existingLayer.locked;
      cleared.opacity = existingLayer.opacity;
      newLayers[layerIndex] = cleared;

      return { ...state, layers: newLayers };
    }

    case 'RESIZE_CANVAS': {
      const newLayers = state.layers.map(layer => {
        const newCells: LayerCell[][] = [];
        for (let y = 0; y < action.height; y++) {
          const row: LayerCell[] = [];
          for (let x = 0; x < action.width; x++) {
            row.push(layer.cells[y]?.[x] ?? { tile: null });
          }
          newCells.push(row);
        }
        return { ...layer, cells: newCells };
      });

      return { ...state, width: action.width, height: action.height, layers: newLayers };
    }

    case 'LOAD_STATE':
      return { ...state, ...action.state };

    default:
      return state;
  }
}

// ============================================================================
// Hook
// ============================================================================

export interface UseEditorStateOptions {
  width?: number;
  height?: number;
  tileSize?: number;
}

export function useEditorState(options: UseEditorStateOptions = {}) {
  const { width = 40, height = 8, tileSize = 16 } = options;

  // History management
  const historyRef = useRef<EditorState[]>([]);
  const historyIndexRef = useRef(-1);

  const initialState: EditorState = {
    width,
    height,
    tileSize,
    layers: [
      createEmptyLayer('layer-5', 'Far Background', width, height),
      createEmptyLayer('layer-4', 'Mid Background', width, height),
      createEmptyLayer('layer-3', 'Main Action', width, height),
      createEmptyLayer('layer-2', 'Near Foreground', width, height),
      createEmptyLayer('layer-1', 'Close Foreground', width, height),
    ],
    activeLayerId: 'layer-3',
    tool: 'paint',
    selectedTile: null,
    selection: null,
    clipboard: null,
    historyIndex: 0,
  };

  const [state, dispatch] = useReducer(editorReducer, initialState);

  // Push state to history
  const pushHistory = useCallback((newState: EditorState) => {
    // Remove any future states if we're not at the end
    historyRef.current = historyRef.current.slice(0, historyIndexRef.current + 1);
    historyRef.current.push(newState);
    historyIndexRef.current = historyRef.current.length - 1;

    // Limit history size
    if (historyRef.current.length > 50) {
      historyRef.current.shift();
      historyIndexRef.current--;
    }
  }, []);

  // Wrapped dispatch that tracks history for undoable actions
  const dispatchWithHistory = useCallback((action: EditorAction) => {
    const undoableActions = ['SET_TILE', 'SET_TILES', 'FILL_AREA', 'PASTE', 'DELETE_SELECTION', 'CLEAR_LAYER'];

    if (undoableActions.includes(action.type)) {
      pushHistory(state);
    }

    dispatch(action);
  }, [state, pushHistory]);

  // Undo
  const undo = useCallback(() => {
    if (historyIndexRef.current >= 0) {
      const previousState = historyRef.current[historyIndexRef.current];
      if (previousState) {
        historyIndexRef.current--;
        dispatch({ type: 'LOAD_STATE', state: previousState });
      }
    }
  }, []);

  // Redo
  const redo = useCallback(() => {
    if (historyIndexRef.current < historyRef.current.length - 2) {
      historyIndexRef.current++;
      const nextState = historyRef.current[historyIndexRef.current + 1];
      if (nextState) {
        dispatch({ type: 'LOAD_STATE', state: nextState });
      }
    }
  }, []);

  // Check if undo/redo is possible
  const canUndo = historyIndexRef.current >= 0;
  const canRedo = historyIndexRef.current < historyRef.current.length - 2;

  // Get active layer
  const activeLayer = state.layers.find(l => l.id === state.activeLayerId) ?? state.layers[0];

  return {
    state,
    dispatch: dispatchWithHistory,
    undo,
    redo,
    canUndo,
    canRedo,
    activeLayer,
  };
}

export type EditorDispatch = ReturnType<typeof useEditorState>['dispatch'];
