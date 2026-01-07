'use client';

import { cn } from '@/lib/cn';
import { CSSProperties } from 'react';

export interface MiningFloorProps {
  /** Floor height in pixels */
  height?: number;
  /** Enable parallax scrolling animation */
  animate?: boolean;
  /** Animation duration in seconds (full scroll cycle) */
  animationDuration?: number;
  /** Additional class names */
  className?: string;
}

/**
 * Sprite sheet configuration for walls_floors.png
 * The sheet contains 4 rows of tiles, each row is a different color variant
 * Row 0 (top): Purple-blue cave tiles - used for mine walls
 */
const SPRITE_CONFIG = {
  // Tile size in the sprite sheet (native)
  tileSize: 16,
  // Scale factor for rendering
  scale: 3,
  // Sprite sheet path
  src: '/assets/mining-bg/sprites/walls_floors.png',
  // Row offsets (y position in sprite sheet)
  rows: {
    purpleBlue: 0,    // Cave/mine tiles
    copperBrown: 1,   // Warm brown tiles
    green: 2,         // Green tiles
    gray: 3,          // Gray stone tiles
  },
  // Column positions for different tile types (approximate x positions)
  cols: {
    solidTile: 0,           // Main solid fill tile
    crossConnector: 80,     // Cross-shaped connector
    cornerPieces: 160,      // Corner variations
    smallSquare: 192,       // Small inner square
    roundedLarge: 256,      // Rounded large tile
    debris: 320,            // Small debris/rocks
  },
};

/**
 * Track sprite configuration for mine_carts.png
 */
const TRACK_CONFIG = {
  src: '/assets/mining-bg/sprites/mine_carts.png',
  // Track rail piece (horizontal straight)
  straightTrack: {
    x: 0,
    y: 48,
    width: 16,
    height: 8,
  },
};

// Calculate scaled tile size
const SCALED_TILE = SPRITE_CONFIG.tileSize * SPRITE_CONFIG.scale; // 48px

/**
 * MiningFloor component
 * Renders a horizontally scrolling mine floor with cave tiles and tracks
 */
export function MiningFloor({
  height = 120,
  animate = true,
  animationDuration = 20,
  className,
}: MiningFloorProps) {
  // Calculate how many tiles we need for seamless loop (2x viewport width)
  const tilesNeeded = Math.ceil((1920 * 2) / SCALED_TILE) + 2;

  return (
    <div
      className={cn(
        'relative overflow-hidden',
        'w-full',
        className
      )}
      style={{ height }}
    >
      {/* Cave floor base layer */}
      <div
        className={cn(
          'absolute inset-0',
          'flex',
          animate && 'animate-scroll-floor'
        )}
        style={{
          '--scroll-duration': `${animationDuration}s`,
          width: `${tilesNeeded * SCALED_TILE}px`,
        } as CSSProperties}
      >
        {/* Render floor tiles */}
        {Array.from({ length: tilesNeeded }).map((_, i) => (
          <FloorTile key={i} index={i} />
        ))}
      </div>

      {/* Track layer - rendered on top of floor */}
      <div
        className={cn(
          'absolute bottom-0 left-0 right-0',
          'flex',
          animate && 'animate-scroll-floor'
        )}
        style={{
          '--scroll-duration': `${animationDuration}s`,
          width: `${tilesNeeded * SCALED_TILE}px`,
          height: SCALED_TILE,
        } as CSSProperties}
      >
        {Array.from({ length: tilesNeeded }).map((_, i) => (
          <TrackSegment key={i} />
        ))}
      </div>

      {/* Dark gradient overlay for depth */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'linear-gradient(to bottom, rgba(26, 20, 16, 0.6) 0%, transparent 40%, transparent 80%, rgba(26, 20, 16, 0.4) 100%)',
        }}
      />
    </div>
  );
}

/**
 * Individual floor tile component
 * Uses CSS background-position to show specific tile from sprite sheet
 */
function FloorTile({ index }: { index: number }) {
  // Alternate between solid tile and variations for visual interest
  const variation = index % 3;

  // Calculate sprite position for purple-blue row
  const spriteY = SPRITE_CONFIG.rows.purpleBlue * (SPRITE_CONFIG.tileSize * 4 + 80); // Approximate row height

  return (
    <div
      className="flex-shrink-0 relative"
      style={{
        width: SCALED_TILE,
        height: SCALED_TILE * 2.5, // 2.5 tiles high for floor depth
      }}
    >
      {/* Main floor tile */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: `url(${SPRITE_CONFIG.src})`,
          backgroundSize: `${660 * SPRITE_CONFIG.scale}px auto`, // Scaled sprite sheet
          backgroundPosition: variation === 0
            ? `${-SPRITE_CONFIG.cols.solidTile * SPRITE_CONFIG.scale}px ${-spriteY}px`
            : variation === 1
            ? `${-SPRITE_CONFIG.cols.roundedLarge * SPRITE_CONFIG.scale}px ${-spriteY}px`
            : `${-SPRITE_CONFIG.cols.solidTile * SPRITE_CONFIG.scale}px ${-spriteY}px`,
          backgroundRepeat: 'repeat',
          imageRendering: 'pixelated',
        }}
      />

      {/* Add some ore deposits randomly */}
      {index % 5 === 0 && (
        <OreDeposit variant={index % 3} />
      )}
    </div>
  );
}

/**
 * Track segment component
 * Renders a straight section of mine track
 */
function TrackSegment() {
  return (
    <div
      className="flex-shrink-0"
      style={{
        width: SCALED_TILE,
        height: SCALED_TILE,
        backgroundImage: `url(${TRACK_CONFIG.src})`,
        backgroundSize: `${252 * SPRITE_CONFIG.scale}px auto`,
        backgroundPosition: `${-TRACK_CONFIG.straightTrack.x * SPRITE_CONFIG.scale}px ${-80 * SPRITE_CONFIG.scale}px`,
        backgroundRepeat: 'no-repeat',
        imageRendering: 'pixelated',
      }}
    />
  );
}

/**
 * Small ore deposit decoration
 */
function OreDeposit({ variant }: { variant: number }) {
  const colors = ['#d4a23a', '#c86449', '#4d9b8c']; // Gold, copper, teal

  return (
    <div
      className="absolute"
      style={{
        width: 12,
        height: 12,
        backgroundColor: colors[variant],
        borderRadius: '2px',
        top: '30%',
        left: '20%',
        boxShadow: `0 0 8px ${colors[variant]}40`,
        imageRendering: 'pixelated',
      }}
    />
  );
}

export default MiningFloor;
