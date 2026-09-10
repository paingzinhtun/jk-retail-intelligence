# Real-shop pilot guide

## Phase 1: consent and scope

1. Explain what will be recorded and why.
2. Select 20–50 products with the owner.
3. Do not capture customer names, phone numbers, or other personal data.
4. Agree on who enters sales and who reviews the five-day report.

## Phase 2: establish baselines

Record the current reporting time, known stockouts, current purchasing method, and questions the owner cannot answer reliably.

## Phase 3: replace synthetic data

Keep the same column names used in `data/raw`. Replace synthetic rows with exported pilot records. Back up the original files. Run:

```bash
python src/pipeline.py
python -m unittest discover -s tests -v
```

## Phase 4: five-day review

Discuss only decisions:

- Which products may run out before the next supplier visit?
- Which products generated the most gross profit?
- Which slow products are holding stock?
- What should be purchased, checked, or corrected?

## Phase 5: evidence

Capture actual values in `EVIDENCE_TEMPLATE.md`. Obtain permission before using the shop name, figures, photos, quotations, or screenshots publicly.

