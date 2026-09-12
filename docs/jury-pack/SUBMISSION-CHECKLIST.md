# Submission checklist — Sentinel Command

Portal: https://sentinel.gujarat.gov.in/problems  
Deadline: **15 September 2026**  
On-site: **22–23 September 2026**

## Pack in this folder

| File | Official item |
|---|---|
| `Sentinel-Command-Presentation.pptx` | 1. Solution presentation |
| `Sentinel-Command-HLD.pdf` | 2. High-Level Design |
| `government-feed-output-report.pdf` | 4. Output report (vehicles + timestamps) |
| `hunt-GJ01AB1234.csv` | Hunt evidence / CSV export |
| `coverage-gap-analysis.pdf` | Visual gap report for Gujarat Police (silent / unlocated / no-ANPR) |
| `jury-demo-script.pdf` | Your 8-minute speaking script (not uploaded unless useful) |

Also in the repo: `docs/sentinel-learning.html` (internal briefing), `docs/diagrams/*`.

## You still record (portal rejects mock-ups)

1. **Own-feed video, max 2–3 minutes, unlisted YouTube or Drive “anyone with the link”.**  
   Script: onboard Gate MP4 → Detect → watchlist GJ01AB1234 → Hunt → Export CSV. Real UI, backend running.

2. **Government-feed video + this output report.**  
   Fetch grid → play Camera 4 HLS → Capture → Detect. Attach `government-feed-output-report.pdf`.

3. **GitHub** of source. Do **not** commit `.env` or the grid password.

4. **Submit on the portal:** PPT, HLD PDF, two video links, output report, GitHub URL. Optional hosted UI + test login.

## Rebuild these PDFs after new Detect runs

```bash
source .venv/bin/activate
python docs/jury-pack/build_hld_pdf.py
python docs/jury-pack/build_output_report.py
python docs/jury-pack/build_demo_script.py
# PPT: cd docs/jury-pack && node build-presentation.js
```
