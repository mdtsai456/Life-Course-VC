---
date: 2026-03-30
topic: voice-recorder-race-condition
---

# Voice Recorder Race Condition Fix

## Problem Frame

When a user stops a voice recording and immediately starts a new one, the old recorder's `onstop` handler fires after `handleStartRecording` has already cleared `chunksRef.current`. The stale `onstop` closure reads the empty (or new-recording's) chunks array, creates an empty blob, and clears chunks again — causing the new recording to lose its audio data.

This is a timing-dependent bug that surfaces under quick stop-then-record interactions.

## Requirements

- R1. When a superseded recorder's `onstop` fires, it must not clear `chunksRef.current`, create a blob, or call `setAudioBlob`
- R2. When a superseded recorder's `ondataavailable` fires, it must not push data into `chunksRef.current`
- R3. Both guards should compare `mediaRecorderRef.current !== recorder` using the closure-captured `recorder` local variable in `handleStartRecording`

## Success Criteria

- Rapidly stopping and restarting a recording produces valid audio from the new session, not an empty blob
- Normal single-session recording behavior is unchanged

## Scope Boundaries

- No changes to the recording UI, timer logic, or audio upload flow
- No refactoring of the chunk collection pattern beyond the guards
- Inactive-recorder edge case (recorder transitions to `inactive` before `stop()` is called, leaking the mic stream) is out of scope for this fix

## Next Steps

→ `/ce:plan` for structured implementation planning, or proceed directly to work given the lightweight scope
