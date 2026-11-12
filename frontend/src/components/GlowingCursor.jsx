import { useEffect, useState } from "react";

/**
 * GlowingCursor: An optical glowing spotlight cursor with physics-based spring follow,
 * lens magnification glow, and hover-triggered expansion.
 * Inspired by AW Media's interactive liquid glass cursor.
 */
export function GlowingCursor() {
  const [position, setPosition] = useState({ x: -100, y: -100 });
  const [trailing, setTrailing] = useState({ x: -100, y: -100 });
  const [isHovered, setIsHovered] = useState(false);
  const [isClicking, setIsClicking] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Only enable on desktop pointer devices
    if (window.matchMedia("(pointer: coarse)").matches) {
      return;
    }

    let animationFrameId;
    let targetX = -100;
    let targetY = -100;
    let currentX = -100;
    let currentY = -100;

    const handleMouseMove = (e) => {
      targetX = e.clientX;
      targetY = e.clientY;
      setPosition({ x: e.clientX, y: e.clientY });

      if (!isVisible) setIsVisible(true);

      // Check if hovering over clickable or interactive element
      const target = e.target;
      const interactive = target.closest(
        'button, a, input, select, textarea, [role="button"], .feature-card, .home-card, .flow-step, .nav-item'
      );
      setIsHovered(Boolean(interactive));
    };

    const handleMouseDown = () => setIsClicking(true);
    const handleMouseUp = () => setIsClicking(false);
    const handleMouseLeave = () => setIsVisible(false);

    // Physics interpolation loop (smooth lerp follow)
    const animate = () => {
      // Lerp coefficient for smooth trailing momentum
      const ease = 0.18;
      currentX += (targetX - currentX) * ease;
      currentY += (targetY - currentY) * ease;

      setTrailing({ x: currentX, y: currentY });
      animationFrameId = requestAnimationFrame(animate);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mouseup", handleMouseUp);
    document.addEventListener("mouseleave", handleMouseLeave);

    animationFrameId = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("mouseup", handleMouseUp);
      document.removeEventListener("mouseleave", handleMouseLeave);
      cancelAnimationFrame(animationFrameId);
    };
  }, [isVisible]);

  if (!isVisible) return null;

  return (
    <div className="glowing-cursor-root" aria-hidden="true">
      {/* Ambient optical spotlight illumination (illuminates card borders) */}
      <div
        className="cursor-spotlight-field"
        style={{
          transform: `translate3d(${trailing.x}px, ${trailing.y}px, 0)`,
        }}
      />

      {/* Trailing glass ring with soft glow */}
      <div
        className={`cursor-ring ${isHovered ? "hovered" : ""} ${
          isClicking ? "clicking" : ""
        }`}
        style={{
          transform: `translate3d(${trailing.x}px, ${trailing.y}px, 0)`,
        }}
      />

      {/* Sharp central specular lens point */}
      <div
        className="cursor-dot"
        style={{
          transform: `translate3d(${position.x}px, ${position.y}px, 0)`,
        }}
      />
    </div>
  );
}
