/**
 * SIH26034 — Tactile Haptic & Audio Feedback Engine
 * Emulates the instant affirmative chime and vibration of mobile payment apps (Paytm, GPay).
 * 
 * Provides:
 * 1. navigator.vibrate() haptic pulse for mobile devices
 * 2. Web Audio API synthesized affirmative chime (works on desktop & mobile, 100% offline, zero lag)
 */

let audioCtx: AudioContext | null = null;

function getAudioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  try {
    if (!audioCtx) {
      const AudioCtxClass =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      if (AudioCtxClass) {
        audioCtx = new AudioCtxClass();
      }
    }
    if (audioCtx && audioCtx.state === "suspended") {
      audioCtx.resume().catch(() => {});
    }
  } catch {
    // AudioContext not supported
  }
  return audioCtx;
}

/**
 * Trigger Paytm / GPay style affirmative two-tone beep and haptic vibration.
 */
export function playScanSuccessFeedback() {
  // 1. Haptic Vibration (Crisp double pulse like Paytm QR scan)
  try {
    if (typeof navigator !== "undefined" && "vibrate" in navigator) {
      // 70ms pulse, 40ms pause, 90ms confirmation pulse
      navigator.vibrate([70, 40, 90]);
    }
  } catch {
    // Vibration not supported or blocked by OS
  }

  // 2. Synthesized Two-Tone Affirmative Chime (Paytm/GPay style melodic ding)
  try {
    const ctx = getAudioContext();
    if (!ctx) return;

    const now = ctx.currentTime;

    // Tone 1: High crisp frequency (880Hz - A5)
    const osc1 = ctx.createOscillator();
    const gain1 = ctx.createGain();
    osc1.type = "sine";
    osc1.frequency.setValueAtTime(880, now);
    osc1.frequency.exponentialRampToValueAtTime(1320, now + 0.08);

    gain1.gain.setValueAtTime(0.25, now);
    gain1.gain.exponentialRampToValueAtTime(0.01, now + 0.12);

    osc1.connect(gain1);
    gain1.connect(ctx.destination);

    osc1.start(now);
    osc1.stop(now + 0.12);

    // Tone 2: Harmonic resolution chime (1760Hz - A6)
    const osc2 = ctx.createOscillator();
    const gain2 = ctx.createGain();
    osc2.type = "sine";
    osc2.frequency.setValueAtTime(1760, now + 0.09);

    gain2.gain.setValueAtTime(0.3, now + 0.09);
    gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.32);

    osc2.connect(gain2);
    gain2.connect(ctx.destination);

    osc2.start(now + 0.09);
    osc2.stop(now + 0.32);
  } catch {
    // Audio context failed or blocked by autoplay policy
  }
}
