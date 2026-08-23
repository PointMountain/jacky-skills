/**
 * Adapted from React Bits SpotlightCard.
 * Copyright (c) 2026 David Haz.
 * Source revision: 4e0e030193b563be6be33d928f77d0d01cefe237.
 * License: MIT + Commons Clause; see THIRD_PARTY_NOTICES.md.
 */
import { useRef } from 'react';

export function SpotlightCard({
  as: Element = 'div',
  children,
  className = '',
  disabled = false,
  spotlightColor = 'rgba(0, 255, 136, 0.14)',
  ...props
}) {
  const elementRef = useRef(null);

  function handlePointerMove(event) {
    if (disabled || event.pointerType === 'touch' || !elementRef.current) return;
    const bounds = elementRef.current.getBoundingClientRect();
    elementRef.current.style.setProperty('--mouse-x', `${event.clientX - bounds.left}px`);
    elementRef.current.style.setProperty('--mouse-y', `${event.clientY - bounds.top}px`);
    elementRef.current.style.setProperty('--spotlight-color', spotlightColor);
  }

  return (
    <Element
      ref={elementRef}
      className={`card-spotlight ${disabled ? 'is-motion-disabled' : ''} ${className}`.trim()}
      onPointerMove={handlePointerMove}
      {...props}
    >
      {children}
    </Element>
  );
}
