'use client';

import { cn } from '@/lib/cn';
import { EditorState, EditorDispatch } from './useEditorState';

export interface ToolbarProps {
  state: EditorState;
  dispatch: EditorDispatch;
  onUndo: () => void;
  onRedo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  zoom: number;
  onZoomChange: (zoom: number) => void;
  onExport: () => void;
  onExportJSON: () => void;
  onImportJSON: () => void;
  className?: string;
}

const TOOLS = [
  { id: 'select', label: 'Select', icon: '⬚', shortcut: 'V' },
  { id: 'paint', label: 'Paint', icon: '🖌', shortcut: 'B' },
  { id: 'erase', label: 'Erase', icon: '⌫', shortcut: 'E' },
  { id: 'fill', label: 'Fill', icon: '🪣', shortcut: 'G' },
  { id: 'eyedropper', label: 'Eyedropper', icon: '💧', shortcut: 'I' },
] as const;

/**
 * Editor toolbar
 * Contains tools, undo/redo, zoom, and export controls
 */
export function Toolbar({
  state,
  dispatch,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  zoom,
  onZoomChange,
  onExport,
  onExportJSON,
  onImportJSON,
  className,
}: ToolbarProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-4 p-2 bg-bg-card border-b border-border',
        className
      )}
    >
      {/* Tool buttons */}
      <div className="flex items-center gap-1">
        {TOOLS.map(tool => (
          <button
            key={tool.id}
            onClick={() => dispatch({ type: 'SET_TOOL', tool: tool.id as EditorState['tool'] })}
            className={cn(
              'w-8 h-8 flex items-center justify-center rounded text-sm',
              'transition-colors',
              state.tool === tool.id
                ? 'bg-copper text-bg-dark'
                : 'bg-bg-surface text-text-secondary hover:bg-bg-dark'
            )}
            title={`${tool.label} (${tool.shortcut})`}
          >
            {tool.icon}
          </button>
        ))}
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-border" />

      {/* Undo/Redo */}
      <div className="flex items-center gap-1">
        <button
          onClick={onUndo}
          disabled={!canUndo}
          className={cn(
            'w-8 h-8 flex items-center justify-center rounded text-sm',
            'transition-colors',
            canUndo
              ? 'bg-bg-surface text-text-secondary hover:bg-bg-dark'
              : 'bg-bg-surface/50 text-text-muted/50 cursor-not-allowed'
          )}
          title="Undo (Ctrl+Z)"
        >
          ↩
        </button>
        <button
          onClick={onRedo}
          disabled={!canRedo}
          className={cn(
            'w-8 h-8 flex items-center justify-center rounded text-sm',
            'transition-colors',
            canRedo
              ? 'bg-bg-surface text-text-secondary hover:bg-bg-dark'
              : 'bg-bg-surface/50 text-text-muted/50 cursor-not-allowed'
          )}
          title="Redo (Ctrl+Y)"
        >
          ↪
        </button>
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-border" />

      {/* Selection actions */}
      {state.selection && (
        <>
          <div className="flex items-center gap-1">
            <button
              onClick={() => dispatch({ type: 'COPY_SELECTION' })}
              className="px-2 py-1 text-xs bg-bg-surface text-text-secondary hover:bg-bg-dark rounded transition-colors"
              title="Copy (Ctrl+C)"
            >
              Copy
            </button>
            <button
              onClick={() => {
                if (state.selection) {
                  dispatch({
                    type: 'PASTE',
                    x: Math.min(state.selection.startX, state.selection.endX),
                    y: Math.min(state.selection.startY, state.selection.endY),
                  });
                }
              }}
              disabled={!state.clipboard}
              className={cn(
                'px-2 py-1 text-xs rounded transition-colors',
                state.clipboard
                  ? 'bg-bg-surface text-text-secondary hover:bg-bg-dark'
                  : 'bg-bg-surface/50 text-text-muted/50 cursor-not-allowed'
              )}
              title="Paste (Ctrl+V)"
            >
              Paste
            </button>
            <button
              onClick={() => dispatch({ type: 'DELETE_SELECTION' })}
              className="px-2 py-1 text-xs bg-bg-surface text-text-secondary hover:bg-pixel-red/20 hover:text-pixel-red rounded transition-colors"
              title="Delete (Del)"
            >
              Delete
            </button>
            <button
              onClick={() => dispatch({ type: 'SET_SELECTION', selection: null })}
              className="px-2 py-1 text-xs bg-bg-surface text-text-secondary hover:bg-bg-dark rounded transition-colors"
              title="Clear selection (Esc)"
            >
              Deselect
            </button>
          </div>
          <div className="w-px h-6 bg-border" />
        </>
      )}

      {/* Zoom */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-text-muted">Zoom:</span>
        <button
          onClick={() => onZoomChange(Math.max(1, zoom - 1))}
          disabled={zoom <= 1}
          className={cn(
            'w-6 h-6 flex items-center justify-center rounded text-xs',
            zoom <= 1
              ? 'bg-bg-surface/50 text-text-muted/50 cursor-not-allowed'
              : 'bg-bg-surface text-text-secondary hover:bg-bg-dark'
          )}
        >
          −
        </button>
        <span className="text-xs text-text-primary w-8 text-center">{zoom}x</span>
        <button
          onClick={() => onZoomChange(Math.min(8, zoom + 1))}
          disabled={zoom >= 8}
          className={cn(
            'w-6 h-6 flex items-center justify-center rounded text-xs',
            zoom >= 8
              ? 'bg-bg-surface/50 text-text-muted/50 cursor-not-allowed'
              : 'bg-bg-surface text-text-secondary hover:bg-bg-dark'
          )}
        >
          +
        </button>
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Canvas info */}
      <div className="text-xs text-text-muted">
        {state.width} × {state.height} tiles ({state.width * state.tileSize} × {state.height * state.tileSize}px)
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-border" />

      {/* Import/Export */}
      <div className="flex items-center gap-1">
        <button
          onClick={onImportJSON}
          className="px-3 py-1.5 text-xs bg-bg-surface text-text-secondary hover:bg-bg-dark rounded transition-colors"
          title="Import tilemap JSON"
        >
          Import
        </button>
        <button
          onClick={onExportJSON}
          className="px-3 py-1.5 text-xs bg-bg-surface text-text-secondary hover:bg-bg-dark rounded transition-colors"
          title="Export tilemap as JSON"
        >
          JSON
        </button>
        <button
          onClick={onExport}
          className="px-3 py-1.5 text-xs bg-copper text-bg-dark hover:bg-copper-glow rounded transition-colors font-medium"
          title="Export as PNG image"
        >
          Export PNG
        </button>
      </div>
    </div>
  );
}
