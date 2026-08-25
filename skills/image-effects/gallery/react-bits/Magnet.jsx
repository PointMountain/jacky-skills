/**
 * Adapted from React Bits Magnet.
 * Copyright (c) 2026 David Haz.
 * Source revision: 4e0e030193b563be6be33d928f77d0d01cefe237.
 * License: MIT + Commons Clause; see THIRD_PARTY_NOTICES.md.
 */
import { useState } from 'react';

export function Magnet({
  children,
  disabled = false,
  magnetStrength = 5,
  className = '',
}) {
  const [position, setPosition] = useState({ x: 0, y: 0 });

  function handlePointerMove(event) {
    if (disabled || event.pointerType === 'touch') return;
    const bounds = event.currentTarget.getBoundingClientRect();
    setPosition({
      x: (event.clientX - bounds.left - bounds.width / 2) / magnetStrength,
      y: (event.clientY - bounds.top - bounds.height / 2) / magnetStrength,
    });
  }

  function reset() {
    setPosition({ x: 0, y: 0 });
  }

  return (
    <span
      className={`magnet-shell ${className}`.trim()}
      onPointerMove={handlePointerMove}
      onPointerLeave={reset}
      onBlur={reset}
    >
      <span
        className="magnet-content"
        style={{ transform: `translate3d(${position.x}px, ${position.y}px, 0)` }}
      >
        {children}
      </span>
    </span>
  );
}
