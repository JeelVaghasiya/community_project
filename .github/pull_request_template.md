## Pull Request Summary

**Area:** (Choose one: `cv` | `hydro` | `gis` | `app` | `repo` | `docs`)
**Team Member:** (P1 / P2 / P3 / P4)

### Description
Provide a concise explanation of what changed in this PR and why.

---

### Team Rules & Monorepo Checklist
- [ ] **Folder boundary:** Changes are made **only** inside your designated folder (`cv/`, `hydro/`, `gis/` + `data/`, or `app/`).
- [ ] **Branch:** PR is created from your role branch (`p1/cv`, `p2/hydro`, `p3/gis`, `p4/app`) into `main`.
- [ ] **Commit message format:** All commits follow `area: what changed` (e.g. `cv: add depth heuristic using pose keypoints`).
- [ ] **No large files:** No DEM tiles, heavy model weights (`.pt`/`.pth`), or raw uncompressed photo datasets committed.
- [ ] **Shared contracts intact:** No changes to Section 4 shared contracts without team consensus.
- [ ] **Linting:** Passes `ruff check .` and `ruff format --check .` locally.
- [ ] **Testing:** Local tests pass (`pytest`).
- [ ] **Peer Review:** At least one teammate has been requested for review.
