'use client';

import { useRef, useEffect, useCallback, useState } from 'react';
import { cn } from '@/lib/cn';

// Pickaxe sprite sheet: 7 columns × 4 rows, each frame 64×64px (448×256 total)
const PICKAXE_FRAME_WIDTH = 64;
const PICKAXE_FRAME_HEIGHT = 64;
const PICKAXE_COLUMNS = 7;

// Idle sprite sheet: 2 columns × 4 rows, each frame 64×64px (128×256 total)
const IDLE_FRAME_WIDTH = 64;
const IDLE_FRAME_HEIGHT = 64;
const IDLE_COLUMNS = 2;

// Ore sprite sheet: 18 columns × 9 rows, each frame 16×16px (288×144 total)
const ORE_SPRITE_PATH = '/sprites/decorations/mining/ores/mining_ores.png';
const ORE_FRAME_SIZE = 16;
// Copper ore position in sprite sheet (0-indexed)
// Per tiles-config.ts: ORE_TILES.COPPER = oreIdx(2, 7)
const COPPER_ORE_ROW = 2; // Row 2 for medium-sized ore nugget
const COPPER_ORE_COL = 7; // Column 7 is copper (matches tiles-config.ts)

// Animation rows in pickaxe sprite sheet
const PICKAXE_ANIMATION_ROWS = {
  mining: 0,       // Mining forward
  miningAlt: 1,    // Mining from different angle
  miningDown: 2,   // Mining downward
} as const;

// Idle sprite sheet layout: 4 directions × 2 frames = 8 sprites
// Row 0: Down, Row 1: Right, Row 2: Up, Row 3: Left
// Each row has 2 frames (columns 0 and 1)
const IDLE_FRAMES = [0, 1];  // Frames to cycle through for idle (col 0 and col 1)
const IDLE_FRAME_ROW = 0;

type AnimationState = 'mining' | 'miningAlt' | 'miningDown' | 'idle';

// Per-frame X offsets to anchor character in place (if needed for sprite drift)
const FRAME_OFFSETS: Record<AnimationState, number[]> = {
  mining:       [0, 0, 0, 0, 0, 0, 0],
  miningAlt:    [0, 0, 0, 0, 0, 0, 0],
  miningDown:   [0, 0, 0, 0, 0, 0, 0],
  idle:         [0, 0],
};

interface PixelMinerProps {
  scale?: number;
  animation?: AnimationState;
  /** Milliseconds per frame for mining animation */
  frameTime?: number;
  /** Milliseconds per frame for idle animation (default: 500) */
  idleFrameTime?: number;
  className?: string;
  /** Flip horizontally */
  flipX?: boolean;
  /** Enable timer-based ore collection cycle */
  autoCollect?: boolean;
  /** Time between ore collections in ms (default: 8000) */
  collectInterval?: number;
  /** How long to show collected ore in ms (default: 2500) */
  collectDuration?: number;
  /** Reward amount to show (default: random 1-3) */
  rewardAmount?: number;
}

// Sprite layer paths (pickaxe animation)
const PICKAXE_SPRITE_LAYERS = [
  '/sprites/character/tools_pickaxe/character_body/character_tools_pickaxe_body_light.png',
  '/sprites/character/tools_pickaxe/clothes/fullbody/overhalls/character_tools_pickaxe_clothes_fullbody_overhalls_blue.png',
  '/sprites/character/tools_pickaxe/hairstyles/radical_curve/character_tools_pickaxe_hairstyles_radical_curve_brown_dark.png',
];

// Sprite layer paths (idle animation)
const IDLE_SPRITE_LAYERS = [
  '/sprites/character/idle/character_body/character_idle_body_light.png',
  '/sprites/character/idle/clothes/full_body/overhalls/character_idle_clothes_fullbody_overhalls_blue.png',
  '/sprites/character/idle/hairstyles/radical_curve/character_idle_hairstyles_radical_curve_brown_dark.png',
];


/**
 * Canvas-based animated pixel miner.
 * Uses requestAnimationFrame for smooth, frame-perfect animation.
 * Supports auto-collect cycle: mining → idle with ore → mining
 */
export function PixelMiner({
  scale = 2,
  animation: externalAnimation = 'mining',
  frameTime = 150, // 150ms per frame (~7 FPS for pickaxe swing effect)
  idleFrameTime = 500, // 500ms per frame (~2 FPS for relaxed idle)
  className,
  flipX = false,
  autoCollect = true,
  collectInterval = 8000,
  collectDuration = 2500,
  rewardAmount,
}: PixelMinerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pickaxeImagesRef = useRef<HTMLImageElement[]>([]);
  const idleImagesRef = useRef<HTMLImageElement[]>([]);
  const oreImageRef = useRef<HTMLImageElement | null>(null);
  const frameRef = useRef(0);
  const lastFrameTimeRef = useRef(0);
  const animationIdRef = useRef<number>(0);

  // Internal animation state for auto-collect cycle
  const [internalAnimation, setInternalAnimation] = useState<AnimationState>(externalAnimation);
  const [showOre, setShowOre] = useState(false);
  const [currentReward, setCurrentReward] = useState(rewardAmount ?? Math.floor(Math.random() * 3) + 1);

  // Reward indicator animation progress (0 to 1)
  const [rewardAnimProgress, setRewardAnimProgress] = useState(0);
  const rewardAnimStartRef = useRef<number>(0);

  // Use external animation if autoCollect is disabled
  const currentAnimation = autoCollect ? internalAnimation : externalAnimation;
  const isIdle = currentAnimation === 'idle';

  // Use appropriate frame dimensions based on animation state
  const frameWidth = isIdle ? IDLE_FRAME_WIDTH : PICKAXE_FRAME_WIDTH;
  const frameHeight = isIdle ? IDLE_FRAME_HEIGHT : PICKAXE_FRAME_HEIGHT;
  const columns = isIdle ? IDLE_COLUMNS : PICKAXE_COLUMNS;

  // Sprite size
  const spriteWidth = Math.floor(frameWidth * scale);
  const spriteHeight = Math.floor(frameHeight * scale);

  // Canvas size - miner with space above for reward indicator
  const rewardSpace = Math.floor(24 * scale); // Extra space at top for floating reward
  const verticalOffset = Math.floor(16 * scale); // Move miner up within canvas
  const width = spriteWidth;
  const height = spriteHeight + rewardSpace;

  // Get current row based on animation state
  const row = isIdle ? IDLE_FRAME_ROW : PICKAXE_ANIMATION_ROWS[currentAnimation as keyof typeof PICKAXE_ANIMATION_ROWS];

  const render = useCallback(() => {
    const canvas = canvasRef.current;
    const images = isIdle ? idleImagesRef.current : pickaxeImagesRef.current;
    const requiredLayers = isIdle ? IDLE_SPRITE_LAYERS.length : PICKAXE_SPRITE_LAYERS.length;

    if (!canvas || images.length < requiredLayers) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Disable smoothing for pixel art
    ctx.imageSmoothingEnabled = false;

    // Use idle frames array for idle, animated frame cycling for mining
    const frame = isIdle
      ? (IDLE_FRAMES[frameRef.current % IDLE_FRAMES.length] ?? 0)
      : (frameRef.current % columns);
    const srcX = frame * frameWidth;
    const srcY = row * frameHeight;

    // Get per-frame offset to prevent sliding
    const frameOffsets = FRAME_OFFSETS[currentAnimation];
    const frameOffsetX = (frameOffsets?.[frame] ?? 0) * scale;

    // Miner position: offset up to be closer to the ore
    const destX = frameOffsetX;
    const destY = rewardSpace - verticalOffset; // Move miner up within canvas

    // Handle flip
    if (flipX) {
      ctx.save();
      ctx.translate(width, 0);
      ctx.scale(-1, 1);
    }

    // Draw each layer in order (body, overalls, hair)
    for (const img of images) {
      if (img.complete && img.naturalWidth > 0) {
        ctx.drawImage(
          img,
          srcX, srcY, frameWidth, frameHeight,  // source
          destX, destY, spriteWidth, spriteHeight  // destination (centered)
        );
      }
    }

    // Draw animated reward indicator (ore sprite + "+X") when showing ore collected
    if (showOre && isIdle && oreImageRef.current) {
      if (flipX) {
        ctx.restore(); // Restore before drawing so it's not flipped
      }

      const oreImg = oreImageRef.current;

      // Animation: float up and fade out
      // Progress 0->0.3: appear and stay, 0.3->1: float up and fade
      const floatDistance = Math.floor(30 * scale);
      const floatOffset = rewardAnimProgress > 0.3
        ? ((rewardAnimProgress - 0.3) / 0.7) * floatDistance
        : 0;
      const opacity = rewardAnimProgress > 0.3
        ? 1 - ((rewardAnimProgress - 0.3) / 0.7)
        : 1;

      // Position: centered above the miner's head
      const oreSize = Math.floor(ORE_FRAME_SIZE * scale * 0.5); // Smaller ore nugget
      const centerX = spriteWidth / 2;
      const baseY = destY + Math.floor(16 * scale); // Start at miner's head
      const rewardY = baseY - floatOffset;

      // Calculate positions for ore + text combo (ore on left, text on right)
      const text = `+${currentReward}`;
      const fontSize = Math.floor(8 * scale);
      ctx.font = `bold ${fontSize}px "Press Start 2P", monospace, sans-serif`;
      const textWidth = ctx.measureText(text).width;
      const gap = Math.floor(1 * scale);
      const totalWidth = oreSize + gap + textWidth;
      const startX = centerX - totalWidth / 2;

      ctx.save();
      ctx.globalAlpha = opacity;

      // Draw ore sprite with outline that wraps the shape
      const oreSrcX = COPPER_ORE_COL * ORE_FRAME_SIZE;
      const oreSrcY = COPPER_ORE_ROW * ORE_FRAME_SIZE;
      const oreX = startX;
      const oreY = rewardY - oreSize / 2;

      // Create outline using offscreen canvas to avoid affecting main canvas
      const outlineOffset = Math.max(1, Math.floor(scale * 0.5));
      const padding = outlineOffset + 1;
      const offscreenWidth = oreSize + padding * 2;
      const offscreenHeight = oreSize + padding * 2;

      const offscreen = document.createElement('canvas');
      offscreen.width = offscreenWidth;
      offscreen.height = offscreenHeight;
      const offCtx = offscreen.getContext('2d');

      if (offCtx) {
        offCtx.imageSmoothingEnabled = false;

        // Draw offset copies for outline
        const offsets: [number, number][] = [
          [-outlineOffset, 0], [outlineOffset, 0],
          [0, -outlineOffset], [0, outlineOffset],
          [-outlineOffset, -outlineOffset], [outlineOffset, -outlineOffset],
          [-outlineOffset, outlineOffset], [outlineOffset, outlineOffset],
        ];

        for (const [ox, oy] of offsets) {
          offCtx.drawImage(
            oreImg,
            oreSrcX, oreSrcY, ORE_FRAME_SIZE, ORE_FRAME_SIZE,
            padding + ox, padding + oy, oreSize, oreSize
          );
        }

        // Tint outline copies white
        offCtx.globalCompositeOperation = 'source-atop';
        offCtx.fillStyle = '#ffffff';
        offCtx.fillRect(0, 0, offscreenWidth, offscreenHeight);

        // Draw actual ore sprite on top
        offCtx.globalCompositeOperation = 'source-over';
        offCtx.drawImage(
          oreImg,
          oreSrcX, oreSrcY, ORE_FRAME_SIZE, ORE_FRAME_SIZE,
          padding, padding, oreSize, oreSize
        );

        // Draw the composed result to main canvas
        ctx.drawImage(offscreen, oreX - padding, oreY - padding);
      }

      // Draw "+X" text next to ore
      const textX = startX + oreSize + gap;
      const textY = rewardY;

      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';

      // Text outline (dark border)
      ctx.strokeStyle = '#1a1a2e';
      ctx.lineWidth = Math.max(2, scale * 0.8);
      ctx.lineJoin = 'round';
      ctx.strokeText(text, textX, textY);

      // Text fill (golden/copper color)
      ctx.fillStyle = '#f59e0b';
      ctx.fillText(text, textX, textY);

      ctx.restore();

      if (flipX) {
        ctx.save();
        ctx.translate(width, 0);
        ctx.scale(-1, 1);
      }
    }

    if (flipX) {
      ctx.restore();
    }
  }, [width, height, spriteWidth, spriteHeight, rewardSpace, verticalOffset, row, flipX, currentAnimation, scale, showOre, isIdle, frameWidth, frameHeight, columns, currentReward, rewardAnimProgress]);

  const animate = useCallback((timestamp: number) => {
    // Calculate time since last frame
    const elapsed = timestamp - lastFrameTimeRef.current;
    // Use slower frame time for idle animation
    const currentFrameTime = isIdle ? idleFrameTime : frameTime;

    if (elapsed >= currentFrameTime) {
      // Advance frame
      frameRef.current = (frameRef.current + 1) % columns;
      lastFrameTimeRef.current = timestamp - (elapsed % currentFrameTime);
      render();
    }

    animationIdRef.current = requestAnimationFrame(animate);
  }, [frameTime, idleFrameTime, isIdle, render, columns]);

  // Load sprite images
  useEffect(() => {
    let mounted = true;

    const loadImage = (src: string): Promise<HTMLImageElement> => {
      return new Promise((resolve, reject) => {
        const img = new Image();
        img.onload = () => resolve(img);
        img.onerror = reject;
        img.src = src;
      });
    };

    // Load pickaxe character sprites
    Promise.all(PICKAXE_SPRITE_LAYERS.map(loadImage))
      .then((loadedImages) => {
        if (mounted) {
          pickaxeImagesRef.current = loadedImages;
          render();
        }
      })
      .catch((err) => {
        console.error('Failed to load pickaxe sprites:', err);
      });

    // Load idle character sprites
    Promise.all(IDLE_SPRITE_LAYERS.map(loadImage))
      .then((loadedImages) => {
        if (mounted) {
          idleImagesRef.current = loadedImages;
          render();
        }
      })
      .catch((err) => {
        console.error('Failed to load idle sprites:', err);
      });

    // Load ore sprite sheet
    loadImage(ORE_SPRITE_PATH)
      .then((img) => {
        if (mounted) {
          oreImageRef.current = img;
          render();
        }
      })
      .catch((err) => {
        console.error('Failed to load ore sprites:', err);
      });

    return () => {
      mounted = false;
    };
  }, [render]);

  // Start animation loop
  useEffect(() => {
    lastFrameTimeRef.current = performance.now();
    animationIdRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
      }
    };
  }, [animate]);

  // Re-render when animation state changes
  useEffect(() => {
    frameRef.current = 0; // Reset to first frame
    render();
  }, [currentAnimation, render]);

  // Auto-collect cycle: mining → idle with ore → mining
  useEffect(() => {
    if (!autoCollect) return;

    let collectTimer: NodeJS.Timeout;
    let resumeTimer: NodeJS.Timeout;

    const startCycle = () => {
      // After collectInterval, transition to idle with ore
      collectTimer = setTimeout(() => {
        // Generate new random reward if not specified
        if (rewardAmount === undefined) {
          setCurrentReward(Math.floor(Math.random() * 3) + 1);
        }
        setInternalAnimation('idle');
        setShowOre(true);
        setRewardAnimProgress(0); // Reset animation

        // After collectDuration, resume mining
        resumeTimer = setTimeout(() => {
          setShowOre(false);
          setInternalAnimation('mining');
          startCycle(); // Restart the cycle
        }, collectDuration);
      }, collectInterval);
    };

    startCycle();

    return () => {
      clearTimeout(collectTimer);
      clearTimeout(resumeTimer);
    };
  }, [autoCollect, collectInterval, collectDuration, rewardAmount]);

  // Animate reward indicator float/fade
  useEffect(() => {
    if (!showOre) {
      setRewardAnimProgress(0);
      return;
    }

    rewardAnimStartRef.current = performance.now();
    let animFrameId: number;

    const animateReward = (timestamp: number) => {
      const elapsed = timestamp - rewardAnimStartRef.current;
      const progress = Math.min(elapsed / collectDuration, 1);
      setRewardAnimProgress(progress);

      if (progress < 1) {
        animFrameId = requestAnimationFrame(animateReward);
      }
    };

    animFrameId = requestAnimationFrame(animateReward);

    return () => {
      if (animFrameId) {
        cancelAnimationFrame(animFrameId);
      }
    };
  }, [showOre, collectDuration]);

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className={cn('pointer-events-none', className)}
      style={{
        imageRendering: 'pixelated',
        // Debug: red border shows canvas bounds
        // border: '1px solid red',
      }}
      role="img"
      aria-label={`Animated pixel miner - ${currentAnimation}${showOre ? ' with ore' : ''}`}
    />
  );
}

// Export types for external use
export type { AnimationState, PixelMinerProps };
