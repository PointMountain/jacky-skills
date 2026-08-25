/**
 * Adapted from React Bits BlurText.
 * Copyright (c) 2026 David Haz.
 * Source revision: 4e0e030193b563be6be33d928f77d0d01cefe237.
 * License: MIT + Commons Clause; see THIRD_PARTY_NOTICES.md.
 */
import { motion } from 'motion/react';

export function BlurText({
  as: Element = 'p',
  className = '',
  disabled = false,
  text,
}) {
  const words = text.split(' ');
  return (
    <Element className={className}>
      {words.map((word, index) => (
        <motion.span
          className="blur-word"
          key={`${word}-${index}`}
          initial={disabled ? false : { filter: 'blur(10px)', opacity: 0, y: 18 }}
          animate={disabled ? undefined : { filter: 'blur(0px)', opacity: 1, y: 0 }}
          transition={{
            duration: 0.48,
            delay: index * 0.055,
            ease: [0.22, 1, 0.36, 1],
          }}
        >
          {word}{index < words.length - 1 ? '\u00a0' : ''}
        </motion.span>
      ))}
    </Element>
  );
}
