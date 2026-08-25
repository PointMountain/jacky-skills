/**
 * Adapted from React Bits ClickSpark.
 * Copyright (c) 2026 David Haz.
 * Source revision: 4e0e030193b563be6be33d928f77d0d01cefe237.
 * License: MIT + Commons Clause; see THIRD_PARTY_NOTICES.md.
 */
import { useEffect, useRef } from 'react';

export function ClickSpark({
  children,
  disabled = false,
  sparkColor = '#00ff88',
  sparkCount = 7,
  sparkRadius = 20,
  sparkSize = 8,
  duration = 360,
}) {
  const canvasRef = useRef(null);
  const frameRef = useRef(0);
  const sparksRef = useRef([]);

  useEffect(() => () => cancelAnimationFrame(frameRef.current), []);

  function draw(timestamp) {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext('2d');
    context.clearRect(0, 0, canvas.width, canvas.height);

    sparksRef.current = sparksRef.current.filter((spark) => {
      const progress = Math.min(1, (timestamp - spark.startedAt) / duration);
      if (progress >= 1) return false;
      const eased = progress * (2 - progress);
      const distance = eased * sparkRadius;
      const lineLength = sparkSize * (1 - eased);
      const startX = spark.x + distance * Math.cos(spark.angle);
      const startY = spark.y + distance * Math.sin(spark.angle);
      context.strokeStyle = sparkColor;
      context.globalAlpha = 1 - progress;
      context.lineWidth = 1.5;
      context.beginPath();
      context.moveTo(startX, startY);
      context.lineTo(
        startX + lineLength * Math.cos(spark.angle),
        startY + lineLength * Math.sin(spark.angle),
      );
      context.stroke();
      return true;
    });

    context.globalAlpha = 1;
    if (sparksRef.current.length) frameRef.current = requestAnimationFrame(draw);
    else context.clearRect(0, 0, canvas.width, canvas.height);
  }

  function handleClick(event) {
    if (disabled || !canvasRef.current) return;
    const bounds = event.currentTarget.getBoundingClientRect();
    const scale = window.devicePixelRatio || 1;
    const canvas = canvasRef.current;
    canvas.width = Math.max(1, Math.round(bounds.width * scale));
    canvas.height = Math.max(1, Math.round(bounds.height * scale));
    canvas.style.width = `${bounds.width}px`;
    canvas.style.height = `${bounds.height}px`;
    canvas.getContext('2d').setTransform(scale, 0, 0, scale, 0, 0);

    const startedAt = performance.now();
    sparksRef.current = Array.from({ length: sparkCount }, (_, index) => ({
      x: event.clientX - bounds.left,
      y: event.clientY - bounds.top,
      angle: (Math.PI * 2 * index) / sparkCount,
      startedAt,
    }));
    cancelAnimationFrame(frameRef.current);
    frameRef.current = requestAnimationFrame(draw);
  }

  return (
    <span className="click-spark-shell" onClick={handleClick}>
      <canvas ref={canvasRef} className="click-spark-canvas" aria-hidden="true" />
      {children}
    </span>
  );
}
