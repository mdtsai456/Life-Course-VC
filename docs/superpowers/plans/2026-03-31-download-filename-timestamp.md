# Download Filename Timestamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a timestamp to the browser download filename so multiple cloned voice downloads don't overwrite each other (e.g. `clone-20260331-143022.wav`). Timestamp is fixed at clone-success time, not at download-click time.

**Architecture:** Frontend-only change. Add a `cloneFilename()` pure helper and a `resultFilename` state. Set filename once in `onSuccess`, clear it alongside `resultUrl`.

**Tech Stack:** React (JSX)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/components/VoiceCloner.jsx` | Modify | Add helper, state, and wire up download attribute |

---

### Task 1: Add timestamped download filename

**Files:**
- Modify: `frontend/src/components/VoiceCloner.jsx`

- [ ] **Step 1: Add `cloneFilename` pure helper**

Add after `formatTime` (line 34), in the existing "Pure helpers" section:

```javascript
function cloneFilename() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `clone-${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}.wav`
}
```

- [ ] **Step 2: Add `resultFilename` state**

Add after `const [resultUrl, setResultUrl] = useManagedObjectUrl()` (line 67):

```javascript
const [resultFilename, setResultFilename] = useState(null)
```

- [ ] **Step 3: Set filename in `onSuccess`**

Change line 210 from:

```javascript
onSuccess: ({ url }) => setResultUrl(url),
```

to:

```javascript
onSuccess: ({ url }) => { setResultUrl(url); setResultFilename(cloneFilename()) },
```

- [ ] **Step 4: Clear filename alongside `resultUrl`**

There are two places where `setResultUrl(null)` is called. Add `setResultFilename(null)` right after each:

Line 178 (inside `handleStartRecording`):
```javascript
setResultUrl(null)
setResultFilename(null)
```

Line 202 (inside `handleSubmit`):
```javascript
setResultUrl(null)
setResultFilename(null)
```

- [ ] **Step 5: Use `resultFilename` in download attribute**

Change line 346 from:

```jsx
download="cloned-voice.wav"
```

to:

```jsx
download={resultFilename ?? 'cloned-voice.wav'}
```

The fallback `'cloned-voice.wav'` is a safety net — `resultFilename` should always be set when `resultUrl` exists, but the fallback costs nothing and prevents a bare `.wav` download if something unexpected happens.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/VoiceCloner.jsx
git commit -m "feat(frontend): add timestamp to download filename to prevent overwrites"
```
