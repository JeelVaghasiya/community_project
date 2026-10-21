# Branch Protection & Monorepo Workflow Guide

This document outlines the branch protection rules and workflow guidelines configured for the **Urban Flood Risk Platform** repository.

---

## 1. Protected Branch: `main`

The `main` branch represents the integration baseline for the platform. Direct pushes to `main` are strictly prohibited. All changes must arrive via reviewed Pull Requests (PRs).

### GitHub Branch Protection Rule Configuration

To configure this on GitHub:
1. Navigate to your repository: `https://github.com/JeelVaghasiya/community_project/settings/branches`.
2. Click **Add branch protection rule** (or use **Settings > Rules > Rulesets**).
3. Set **Branch name pattern** to `main`.
4. Enable the following settings:
   - **Require a pull request before merging**:
     - Check **Require approvals**: Set to at least **1** (at least one teammate must review).
     - Check **Dismiss stale pull request approvals when new commits are pushed**.
     - Check **Require review from Code Owners** (optional, recommended).
   - **Require status checks to pass before merging**:
     - Check **Require branches to be up to date before merging**.
     - In the search bar for status checks, select:
       - `Run Ruff Linter & Formatter Check` (`ruff-lint` job from `lint.yml`)
       - `Run Pytest` (`test` job from `test.yml`)
   - **Do not allow bypassing the above settings**: Ensures all team members (including repo admins) follow PR and lint rules.
   - **Restrict who can push to matching branches**: Prevent direct command-line `git push origin main`.

---

## 2. Team Branch Conventions

Each team member owns a specific area and works on an isolated branch:

| Person | Role | Branch Name | Owned Directory |
| :--- | :--- | :--- | :--- |
| **P1** | Computer Vision Engineer | `p1/cv` | `cv/`, `docs/cv_eval_report.md` |
| **P2** | Hydrology & SWMM Modeller | `p2/hydro` | `hydro/`, `data/risk/swmm_nodes_*.geojson` |
| **P3** | GIS & Data Engineer | `p3/gis` | `gis/`, `data/` |
| **P4** | Integration, Backend & Frontend Lead | `p4/app` | `app/`, repo root files |

> Sub-branches for distinct sub-tasks should follow the pattern `p<num>/<feature>` (e.g. `p1/cv-depth`, `p4/fusion-engine`).

---

## 3. Commit Message Standard

Commits must follow the format:
```text
<area>: <what changed>
```
Examples:
- `cv: add depth heuristic using pose keypoints`
- `hydro: generate 100mmhr design storm hyetograph`
- `gis: clip copernicus DEM for silk board pilot area`
- `app: implement fusion logic and leaflet status markers`
- `repo: configure ruff lint check and branch rules`

---

## 4. Local Pre-PR Checklist

Before opening a pull request, run the following commands locally:

```bash
# 1. Check linting and formatting
ruff check .
ruff format --check .

# 2. Automatically fix formatting / safe lint errors if any:
ruff format .
ruff check --fix .

# 3. Run test suite
pytest -v
```

---

## 5. Large File Policy

- **Never commit large files**:
  - Raw DEM geotiffs (`data/dem/*.tif`)
  - Deep learning model weights (`*.pt`, `*.pth`, `*.onnx`)
  - Large raw photo batches
- **Where they live**: Keep these files on the shared Google Drive folder and document their links in `README.md` and folder READMEs.
- **Allowed in git**: Small outputs like GeoJSON polygons, metadata CSVs, small reference icons, and test stubs.
