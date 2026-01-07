'use client';

import { cn } from '@/lib/cn';
import { Layer, EditorDispatch } from './useEditorState';

export interface LayerPanelProps {
  layers: Layer[];
  activeLayerId: string;
  dispatch: EditorDispatch;
  className?: string;
}

/**
 * Layer management panel
 * Shows layer list with visibility, lock, and reorder controls
 */
export function LayerPanel({
  layers,
  activeLayerId,
  dispatch,
  className,
}: LayerPanelProps) {
  const handleAddLayer = () => {
    const id = `layer-${Date.now()}`;
    const name = `Layer ${layers.length + 1}`;
    // Create layer with same dimensions - this is handled by the parent
    dispatch({
      type: 'ADD_LAYER',
      layer: {
        id,
        name,
        visible: true,
        locked: false,
        opacity: 1,
        cells: [], // Will be populated by reducer based on canvas size
      },
    });
  };

  const handleMoveLayer = (layerId: string, direction: 'up' | 'down') => {
    const index = layers.findIndex(l => l.id === layerId);
    if (index === -1) return;

    const newIndex = direction === 'up' ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= layers.length) return;

    const newOrder = [...layers.map(l => l.id)];
    // Swap using validated indices (already checked bounds above)
    const temp = newOrder[index]!;
    newOrder[index] = newOrder[newIndex]!;
    newOrder[newIndex] = temp;

    dispatch({ type: 'REORDER_LAYERS', layerIds: newOrder });
  };

  return (
    <div className={cn('flex flex-col', className)}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-copper">Layers</span>
        <button
          onClick={handleAddLayer}
          className="px-2 py-1 text-xs bg-bg-surface hover:bg-copper hover:text-bg-dark rounded transition-colors"
        >
          + Add
        </button>
      </div>

      <div className="flex flex-col gap-1">
        {/* Render layers in reverse order (top layer first in list) */}
        {[...layers].reverse().map((layer, idx) => (
          <div
            key={layer.id}
            onClick={() => dispatch({ type: 'SET_ACTIVE_LAYER', layerId: layer.id })}
            className={cn(
              'flex items-center gap-2 p-2 rounded cursor-pointer',
              'transition-colors',
              layer.id === activeLayerId
                ? 'bg-copper/20 border border-copper/50'
                : 'bg-bg-surface hover:bg-bg-card border border-transparent'
            )}
          >
            {/* Visibility toggle */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                dispatch({ type: 'TOGGLE_LAYER_VISIBILITY', layerId: layer.id });
              }}
              className={cn(
                'w-5 h-5 flex items-center justify-center rounded text-xs',
                layer.visible ? 'text-pixel-green' : 'text-text-muted'
              )}
              title={layer.visible ? 'Hide layer' : 'Show layer'}
            >
              {layer.visible ? '👁' : '○'}
            </button>

            {/* Lock toggle */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                dispatch({ type: 'TOGGLE_LAYER_LOCK', layerId: layer.id });
              }}
              className={cn(
                'w-5 h-5 flex items-center justify-center rounded text-xs',
                layer.locked ? 'text-pixel-red' : 'text-text-muted'
              )}
              title={layer.locked ? 'Unlock layer' : 'Lock layer'}
            >
              {layer.locked ? '🔒' : '○'}
            </button>

            {/* Layer name */}
            <span className="flex-1 text-xs text-text-primary truncate">
              {layer.name}
            </span>

            {/* Opacity indicator */}
            <span className="text-xxs text-text-muted">
              {Math.round(layer.opacity * 100)}%
            </span>

            {/* Move buttons */}
            <div className="flex gap-0.5">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleMoveLayer(layer.id, 'up');
                }}
                disabled={idx === 0}
                className={cn(
                  'w-4 h-4 text-xxs rounded',
                  idx === 0 ? 'text-text-muted/30' : 'text-text-muted hover:text-text-primary'
                )}
                title="Move up"
              >
                ▲
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleMoveLayer(layer.id, 'down');
                }}
                disabled={idx === layers.length - 1}
                className={cn(
                  'w-4 h-4 text-xxs rounded',
                  idx === layers.length - 1 ? 'text-text-muted/30' : 'text-text-muted hover:text-text-primary'
                )}
                title="Move down"
              >
                ▼
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Layer actions */}
      {activeLayerId && (
        <div className="mt-3 pt-3 border-t border-border">
          <div className="text-xxs text-text-muted mb-2">Layer Actions</div>
          <div className="flex flex-wrap gap-1">
            <button
              onClick={() => dispatch({ type: 'CLEAR_LAYER', layerId: activeLayerId })}
              className="px-2 py-1 text-xxs bg-bg-surface hover:bg-pixel-red/20 text-text-secondary hover:text-pixel-red rounded transition-colors"
            >
              Clear
            </button>
            <button
              onClick={() => {
                if (layers.length > 1) {
                  dispatch({ type: 'REMOVE_LAYER', layerId: activeLayerId });
                }
              }}
              disabled={layers.length <= 1}
              className={cn(
                'px-2 py-1 text-xxs rounded transition-colors',
                layers.length <= 1
                  ? 'bg-bg-surface/50 text-text-muted/50 cursor-not-allowed'
                  : 'bg-bg-surface hover:bg-pixel-red/20 text-text-secondary hover:text-pixel-red'
              )}
            >
              Delete
            </button>
          </div>

          {/* Opacity slider */}
          <div className="mt-2">
            <div className="text-xxs text-text-muted mb-1">Opacity</div>
            <input
              type="range"
              min="0"
              max="100"
              value={Math.round((layers.find(l => l.id === activeLayerId)?.opacity ?? 1) * 100)}
              onChange={(e) => {
                dispatch({
                  type: 'SET_LAYER_OPACITY',
                  layerId: activeLayerId,
                  opacity: parseInt(e.target.value) / 100,
                });
              }}
              className="w-full h-1 bg-bg-surface rounded appearance-none cursor-pointer accent-copper"
            />
          </div>
        </div>
      )}
    </div>
  );
}
