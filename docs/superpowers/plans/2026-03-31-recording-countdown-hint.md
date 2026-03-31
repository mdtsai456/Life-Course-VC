# Recording Countdown Hint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a real-time "至少再錄 X 秒" hint while recording is under 3 seconds, so users know how much longer they need before the recording is valid.

**Architecture:** Add a single inline hint element to the existing recording timer area in `VoiceCloner.jsx`. The hint derives from `recordingSeconds` (already tracked) — no new state needed. Reuse the existing `.recording-too-short` CSS class for styling consistency.

**Tech Stack:** React (JSX), CSS

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `frontend/src/components/VoiceCloner.jsx:250-254` | Add countdown hint next to timer during recording |

Only one file changes. No new files, no new state, no new CSS.

---

### Task 1: Add countdown hint during recording

**Files:**
- Modify: `frontend/src/components/VoiceCloner.jsx:250-254`

- [ ] **Step 1: Verify current behavior**

Run the app and start a recording. Confirm:
- The timer shows `00:00`, `00:01`, `00:02`, … while recording
- No hint is shown during recording
- After stopping at < 3s, the error "錄音至少需要 3 秒" appears

```bash
cd frontend && npm run dev
```

- [ ] **Step 2: Add the countdown hint JSX**

In `frontend/src/components/VoiceCloner.jsx`, replace lines 250–254:

**Before:**
```jsx
          {isRecording && (
            <span className="recording-timer" aria-live="polite">
              {formatTime(recordingSeconds)}
            </span>
          )}
```

**After:**
```jsx
          {isRecording && (
            <>
              <span className="recording-timer" aria-live="polite">
                {formatTime(recordingSeconds)}
              </span>
              {recordingSeconds < 3 && (
                <span className="recording-too-short">
                  至少再錄 {3 - recordingSeconds} 秒
                </span>
              )}
            </>
          )}
```

This reuses the existing `recording-too-short` CSS class (red text, 0.875rem) and the existing `recordingSeconds` state. No new state, hooks, or CSS needed.

- [ ] **Step 3: Manually verify the new behavior**

Run the app, start recording, and confirm:
1. At 0s: hint shows "至少再錄 3 秒"
2. At 1s: hint shows "至少再錄 2 秒"
3. At 2s: hint shows "至少再錄 1 秒"
4. At 3s: hint disappears — only the timer remains
5. After stopping at ≥ 3s: no "too short" error shown
6. After stopping at < 3s: the existing "錄音至少需要 3 秒" error still works

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/VoiceCloner.jsx
git commit -m "feat(voice): show countdown hint during recording when under 3 seconds"
```
