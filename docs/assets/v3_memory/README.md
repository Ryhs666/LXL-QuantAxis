# V3 Memory System — Screenshot Capture Guide

> Portfolio-quality screenshots for GitHub README and graduate application.

## Preparation

```bash
# Reset demo data to clean state
python scripts/seed_v3_memory.py --reset

# Start web server
python web_modern.py
```

## Capture Settings

| Setting | Value |
|---------|-------|
| Resolution | **1920×1080** |
| Device Pixel Ratio | **2.0** (retina) |
| Browser | Chrome / Edge |
| Theme | Dark (terminal.css default) |
| Format | PNG |
| DevTools | Device Toolbar → Responsive → 1920×1080 |

Chrome DevTools shortcut: `Ctrl+Shift+M` → set to 1920×1080, DPR 2.0.

---

## Screenshot Checklist

### 01 — Memory Timeline

```
File:   01_timeline.png
URL:    http://127.0.0.1:5000/journal
What:   Full journal page with all timeline entries visible
Shows:  5 stat cards, search bar, 16 colored timeline items,
        analytics sidebar with calibration bars
```

### 02 — Search & Filter

```
File:   02_search.png
URL:    http://127.0.0.1:5000/journal
Action: Type "NVIDIA" in search bar → results filter in real-time
Shows:  Search in action, filtered timeline, HTMX live update
```

### 03 — Thesis Detail Modal

```
File:   03_detail.png
URL:    http://127.0.0.1:5000/journal
Action: Click "NVIDIA: Core Beneficiary of AI Infrastructure Buildout"
Shows:  Modal overlay with full thesis content, confidence: 0.80,
        catalysts/risks, target price
```

### 04 — Analytics Sidebar

```
File:   04_analytics.png
URL:    http://127.0.0.1:5000/journal
Action: Scroll right sidebar to show full analytics
Shows:  Memory breakdown, thesis quality (67% hit rate),
        3 calibration bars, insight box, top tags cloud
```

### 05 — Create New Entry

```
File:   05_create.png
URL:    http://127.0.0.1:5000/journal
Action: Click "+ New Thesis" button
Shows:  Creation modal with type=thesis, dynamic form fields
        (confidence, target price appear for thesis type)
```

---

## Post-Processing

After capture, optimize for GitHub:

```bash
# Optional: compress PNGs without quality loss
pngquant --quality=80-95 --ext .png --force 01_timeline.png
```

Do NOT crop or edit content — show the real application UI.
