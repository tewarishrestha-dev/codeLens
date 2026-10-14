import { useEffect, useRef } from "react";

// Lightweight canvas atmosphere: slow-drifting gradient orbs + sparse
// particles. Sits behind all content (pointer-events: none), low contrast,
// pauses under prefers-reduced-motion or the Settings reduce-motion class.
const ORBS = [
  { hue: 222, sat: 80, light: 42, r: 0.42, speed: 0.00012, phase: 0 },
  { hue: 262, sat: 75, light: 48, r: 0.34, speed: 0.00009, phase: 2.1 },
  { hue: 192, sat: 70, light: 40, r: 0.28, speed: 0.00015, phase: 4.2 },
];

const PARTICLE_COUNT = 36;

function buildParticles(width, height) {
  const particles = [];

  for (let i = 0; i < PARTICLE_COUNT; i += 1) {
    particles.push({
      x: Math.random() * width,
      y: Math.random() * height,
      r: 0.6 + Math.random() * 1.4,
      vx: 0.08 + Math.random() * 0.18,
      vy: (Math.random() - 0.5) * 0.06,
      alpha: 0.08 + Math.random() * 0.18,
    });
  }

  return particles;
}

export function Atmosphere() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    const ctx = canvas.getContext("2d");
    if (!ctx) return undefined;

    let raf = 0;
    let width = 0;
    let height = 0;
    let particles = [];
    let running = true;

    const motionQuery = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    );

    function isReduced() {
      return (
        motionQuery.matches ||
        document.documentElement.classList.contains("reduce-motion")
      );
    }

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      particles = buildParticles(width, height);
    }

    function drawStatic() {
      ctx.clearRect(0, 0, width, height);
      // A single still wash so the page never looks empty when motion is off.
      const g = ctx.createRadialGradient(
        width * 0.7,
        height * 0.2,
        0,
        width * 0.7,
        height * 0.2,
        Math.max(width, height) * 0.5
      );
      g.addColorStop(0, "rgba(91, 140, 255, 0.07)");
      g.addColorStop(1, "rgba(91, 140, 255, 0)");
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, width, height);
    }

    function frame(t) {
      if (!running) return;

      if (isReduced()) {
        drawStatic();
        return;
      }

      ctx.clearRect(0, 0, width, height);

      // Drifting gradient orbs (wind / light streaks feel).
      for (const orb of ORBS) {
        const cx =
          width * (0.5 + 0.38 * Math.sin(t * orb.speed + orb.phase));
        const cy =
          height * (0.4 + 0.3 * Math.cos(t * orb.speed * 0.8 + orb.phase));
        const radius = Math.max(width, height) * orb.r;

        const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
        g.addColorStop(
          0,
          `hsla(${orb.hue}, ${orb.sat}%, ${orb.light}%, 0.09)`
        );
        g.addColorStop(1, `hsla(${orb.hue}, ${orb.sat}%, ${orb.light}%, 0)`);
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.fill();
      }

      // Sparse drifting particles.
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;

        if (p.x > width + 4) {
          p.x = -4;
          p.y = Math.random() * height;
        }
        if (p.y < -4) p.y = height + 4;
        if (p.y > height + 4) p.y = -4;

        ctx.beginPath();
        ctx.fillStyle = `rgba(180, 200, 255, ${p.alpha})`;
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fill();
      }

      raf = requestAnimationFrame(frame);
    }

    function onVisibility() {
      if (document.hidden) {
        running = false;
        cancelAnimationFrame(raf);
      } else if (!running) {
        running = true;
        raf = requestAnimationFrame(frame);
      }
    }

    function onMotionChange() {
      cancelAnimationFrame(raf);

      if (isReduced()) {
        drawStatic();
      } else if (running) {
        raf = requestAnimationFrame(frame);
      }
    }

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(document.documentElement);
    resize();

    motionQuery.addEventListener("change", onMotionChange);
    document.addEventListener("visibilitychange", onVisibility);

    if (isReduced()) {
      drawStatic();
    } else {
      raf = requestAnimationFrame(frame);
    }

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      resizeObserver.disconnect();
      motionQuery.removeEventListener("change", onMotionChange);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="atmosphere-canvas"
      aria-hidden="true"
    />
  );
}
