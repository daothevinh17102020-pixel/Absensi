# Agy task: test-checklist realtime face scan

Use skill: `test-checklist`.

Workspace: `E:\TMU UNIVERSITY\MACHINE LEARNING\SOURCE 1_ƯU TIÊN\Absensi`

Role: draft QC reviewer only. Do not modify files.

Goal: create a concise test checklist outline for the realtime face attendance scanner after these changes:

- Max 10 faces per frame.
- Each face verifies independently by `track_id`.
- First successful recognition still requires 3 independent frames.
- After a face is successfully recorded/duplicated, keep green box pinned/following that track and do not restart verification for the same track while cache is fresh.
- Completed track should avoid repeated ArcFace embedding, anti-spoofing, and DB attendance calls.
- Far/group faces are supported better with smaller min face size and slower embedding refresh.
- UI box label should show student info only when recognized; do not show internal score/calculation text.
- Multiple active schedules, DB outage, duplicate identity, low quality, no face, camera/session errors must be covered.

Output format only:

`[P] [Auto] CHK-realtime-scan-NNN -> {Ref or —} · {one atomic scenario}`

Rules:

- No Given/When/Then.
- No payload/data detail.
- One line per scenario.
- Include core flow, alternate flow, validation/error, BVA, security basic, loading, accessibility basic, responsive, and edge cases.
- Mark automation suitability with `[Yes]` or `[No]`.
- Prioritize risky behavior: 10 faces, completed-track pinning, no rescan, far faces, duplicate identity, tracker exit/re-entry, DB/schedule failures.
- Return findings/checklist only. Do not invent facts beyond the code behavior above.
