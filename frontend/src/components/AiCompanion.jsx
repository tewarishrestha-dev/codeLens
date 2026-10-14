import { useEffect, useRef, useState } from "react";
import "./AiCompanion.css";

// Suppress an identical message for this many subsequent events so the
// bubble never nags. Measured in aiStatus events, not wall-clock time,
// so the decision stays pure during render.
const REPETITION_EVENTS = 3;
// Completion states settle back to idle after this long. This only
// decays presentation — the state itself was set by a real outcome.
const DECAY_MS = 4500;

// Click reactions cycle so consecutive clicks always show something new.
// Each entry carries its own duration so the class clears exactly when
// the animation ends and the robot returns to idle float.
const REACTIONS = [
  { cls: "react-hop", ms: 950 },
  { cls: "react-stumble", ms: 1050 },
  { cls: "react-tilt", ms: 1000 },
  { cls: "react-sit", ms: 1150 },
];

// Rapid clicks keep navigating, but the reaction animation only restarts
// after this cooldown — otherwise animations thrash from 0% and the robot
// looks frozen at its start pose.
const REACTION_COOLDOWN_MS = 320;

// One-shot spontaneous hop length (matches the CSS ai-hop duration).
const HOP_MS = 1300;
// Spontaneous hops fire at a fresh random delay every time (5.5–14s) so
// the idle loop never reads like a loading spinner.
const HOP_MIN_MS = 5500;
const HOP_JITTER_MS = 8500;

// Short quips shown on every third click, only when the bubble is free.
const QUIPS = [
  "Hello, explorer.",
  "Need a hand?",
  "Boop!",
  "Let's find something.",
  "I'm all eyes.",
  "Ask me anything.",
  "Following along.",
];

// Cursor-proximity radius (px) for the subtle "notice you" glow.
const NEAR_RADIUS = 160;

function isReducedMotion() {
  return (
    window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
    document.documentElement.classList.contains("reduce-motion")
  );
}

// Floating robot companion. States are driven entirely by real application
// events (analysis, ask, search, citation navigation, errors) reported
// through the aiStatus callback — never by timers faking progress.
//
// pointer-events stay disabled on the wrapper, so the companion can never
// block buttons, the file tree, text selection, or graph controls.
export function AiCompanion({
  status = "idle",
  message = "",
  eventKey = 0,
  onActivate,
}) {
  const [bubbleState, setBubbleState] = useState({ text: null, eventKey: 0 });
  const [decayed, setDecayed] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [near, setNear] = useState(false);
  const [reaction, setReaction] = useState("");
  const [hop, setHop] = useState(false);
  const [prevEvent, setPrevEvent] = useState({ status, message, eventKey });
  const [dismissed, setDismissed] = useState(() => new Set());
  const [shownAt, setShownAt] = useState(() => new Map());

  const frameRef = useRef(null);
  const reactionTimerRef = useRef(null);
  const reactionIdxRef = useRef(0);
  const lastReactAtRef = useRef(0);
  const clickCountRef = useRef(0);
  const lastQuipRef = useRef(null);
  const hopDelayRef = useRef(null);
  const hopEndRef = useRef(null);
  // Live mirrors so long-lived hop timers can read current values
  // without re-subscribing (status/reaction change often; the hop loop
  // does not). Synced after commit, never during render.
  const statusRef = useRef(status);
  const reactionRef = useRef(reaction);

  useEffect(() => {
    statusRef.current = status;
    reactionRef.current = reaction;
  });

  // Adjust during render (React's sanctioned alternative to a reset
  // effect): when a new event arrives, show a qualifying message —
  // skipping dismissed texts and recently shown repeats.
  if (
    prevEvent.status !== status ||
    prevEvent.message !== message ||
    prevEvent.eventKey !== eventKey
  ) {
    setPrevEvent({ status, message, eventKey });

    const text = (message || "").trim();

    if (!text) {
      setBubbleState({ text: null, eventKey });
    } else if (!dismissed.has(text)) {
      const last = shownAt.get(text);

      if (last === undefined || eventKey - last >= REPETITION_EVENTS) {
        setShownAt((prev) => new Map(prev).set(text, eventKey));
        setBubbleState({ text, eventKey });
      }
    }

    // Every new event restarts the completion presentation; the decay
    // timer below re-settles success/error back to idle. Real app events
    // also cancel any in-flight idle hop so state animations win.
    setDecayed(false);
    setHop(false);
  }

  // Completion states settle back to idle. The timeout only decays
  // presentation after a real outcome — it never fakes progress.
  useEffect(() => {
    if (status !== "success" && status !== "error") return undefined;

    const timer = setTimeout(() => {
      setDecayed(true);
      setBubbleState({ text: null, eventKey });
    }, DECAY_MS);

    return () => clearTimeout(timer);
  }, [status, eventKey]);

  // Spontaneous idle hop: a one-shot anticipation → airborne → landing
  // squash, scheduled at a fresh random delay every cycle. Skipped while
  // reduced-motion is on, while a busy/AI state is showing, and while a
  // click reaction is playing (reactions own the transform layer).
  useEffect(() => {
    let cancelled = false;

    function canHop() {
      if (isReducedMotion()) return false;
      if (reactionRef.current) return false;

      const s = statusRef.current;

      return s === "idle" || s === "curious";
    }

    function scheduleNext() {
      if (cancelled) return;

      hopDelayRef.current = setTimeout(
        () => {
          if (cancelled) return;

          if (!canHop()) {
            scheduleNext();
            return;
          }

          setHop(true);
          hopEndRef.current = setTimeout(() => {
            if (cancelled) return;
            setHop(false);
            scheduleNext();
          }, HOP_MS);
        },
        HOP_MIN_MS + Math.random() * HOP_JITTER_MS
      );
    }

    scheduleNext();

    return () => {
      cancelled = true;
      clearTimeout(hopDelayRef.current);
      clearTimeout(hopEndRef.current);
    };
  }, []);

  // Cursor awareness: eyes track the pointer, the body leans gently
  // toward it, and the head tilts a few degrees. A proximity flag adds
  // a soft antenna glow when the cursor is close. Skipped on touch
  // devices and when motion is reduced.
  useEffect(() => {
    const finePointer = window.matchMedia(
      "(hover: hover) and (pointer: fine)"
    );

    if (!finePointer.matches) return undefined;

    function onMove(e) {
      if (frameRef.current) return;

      frameRef.current = requestAnimationFrame(() => {
        frameRef.current = null;

        if (isReducedMotion()) {
          setPos((prev) =>
            prev.x === 0 && prev.y === 0 ? prev : { x: 0, y: 0 }
          );
          setNear(false);
          return;
        }

        const cx = window.innerWidth - 70;
        const cy = window.innerHeight - 70;
        const dx = Math.max(-1, Math.min(1, (e.clientX - cx) / 300));
        const dy = Math.max(-1, Math.min(1, (e.clientY - cy) / 300));

        setPos((prev) =>
          prev.x === dx && prev.y === dy ? prev : { x: dx, y: dy }
        );

        const dist = Math.hypot(e.clientX - cx, e.clientY - cy);
        const isNear = dist < NEAR_RADIUS;

        setNear((was) => (was === isNear ? was : isNear));
      });
    }

    window.addEventListener("mousemove", onMove);

    return () => {
      window.removeEventListener("mousemove", onMove);

      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
        frameRef.current = null;
      }
    };
  }, []);

  // Clean up every timer on unmount so a late callback can never set
  // state on a dead component.
  useEffect(
    () => () => {
      clearTimeout(reactionTimerRef.current);
      clearTimeout(hopDelayRef.current);
      clearTimeout(hopEndRef.current);
    },
    []
  );

  function handleActivate() {
    const now = performance.now();

    // Safe interruption with a short cooldown: every click still
    // navigates, but the reaction only restarts when enough time has
    // passed. Cycling guarantees consecutive classes differ, so the new
    // class always restarts its CSS animation; the timer always clears
    // the class, so rapid clicks can never leave the robot frozen.
    if (now - lastReactAtRef.current >= REACTION_COOLDOWN_MS) {
      lastReactAtRef.current = now;

      // A click owns the transform layer — drop any in-flight idle hop.
      setHop(false);
      clearTimeout(hopEndRef.current);

      reactionIdxRef.current = (reactionIdxRef.current + 1) % REACTIONS.length;
      const next = REACTIONS[reactionIdxRef.current];

      clearTimeout(reactionTimerRef.current);
      setReaction(next.cls);
      reactionTimerRef.current = setTimeout(() => setReaction(""), next.ms);
    }

    // Every third click drops a short quip, and only when the bubble is
    // free — a nod, not a flood of chat.
    clickCountRef.current += 1;

    if (clickCountRef.current % 3 === 1 && !bubbleState.text) {
      const pool = QUIPS.filter(
        (quip) => !dismissed.has(quip) && quip !== lastQuipRef.current
      );

      if (pool.length > 0) {
        const quip = pool[Math.floor(Math.random() * pool.length)];
        lastQuipRef.current = quip;
        setShownAt((prev) => new Map(prev).set(quip, eventKey));
        setBubbleState({ text: quip, eventKey });
      }
    }

    onActivate?.();
  }

  function dismissBubble(e) {
    e.stopPropagation();

    if (!bubbleState.text) return;

    const text = bubbleState.text;

    setDismissed((prev) => new Set(prev).add(text));
    setBubbleState({ text: null, eventKey: bubbleState.eventKey });
  }

  // Success/error settle back to idle once the outcome has been shown.
  const visualStatus = decayed ? "idle" : status;
  const celebrate = !decayed && status === "success" ? "celebrate" : "";
  const shake = !decayed && status === "error" ? "shake" : "";

  const leanX = pos.x * 6;
  const leanY = pos.y * 4;
  const lookX = pos.x * 2.5;
  const lookY = pos.y * 2;
  const headTilt = pos.x * 5;

  return (
    <div
      className={`ai-companion status-${visualStatus} ${celebrate} ${shake} ${
        near ? "near" : ""
      }`}
      style={{
        "--lean-x": `${leanX}px`,
        "--lean-y": `${leanY}px`,
        "--look-x": `${lookX}px`,
        "--look-y": `${lookY}px`,
        "--head-tilt": `${headTilt}deg`,
      }}
    >
      {bubbleState.text && (
        <div className="ai-bubble" role="status" aria-live="polite">
          <span className="ai-bubble-text">{bubbleState.text}</span>
          <button
            type="button"
            className="ai-bubble-dismiss"
            onClick={dismissBubble}
            title="Dismiss"
            aria-label="Dismiss message"
          >
            ×
          </button>
        </div>
      )}

      <button
        type="button"
        className={`ai-body ${reaction}${hop ? " hopping" : ""}`}
        onClick={handleActivate}
        title="Ask CodeLens"
        aria-label="Ask CodeLens"
      >
        <span className="ai-antenna" />
        <span className="ai-head">
          <span className="ai-eye left">
            <span className="ai-pupil" />
          </span>
          <span className="ai-eye right">
            <span className="ai-pupil" />
          </span>
        </span>
        <span className="ai-chest">
          <span className="ai-core" />
        </span>
      </button>
    </div>
  );
}
