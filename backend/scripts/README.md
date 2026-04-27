# Backend Scripts

## ingest_onet.py — O\*NET career database ingestion

Populates the `careers` table from the O\*NET occupational database (~200 filtered occupations).
Run this once after first deploy, and again after each O\*NET version update.

---

### Step 1 — Download the O\*NET database

1. Go to https://www.onetcenter.org/database.html
2. Under **Download**, click the **Text** format link for the latest version
   (e.g. "28.3 Database — Text", ~30 MB zip).
3. Extract the zip. You will get a folder like `db_29_0_text/`.
4. Place the extracted folder at `./data/onet/` relative to the repo root,
   **or** pass any path via `--data-dir`.

The `data/` directory is gitignored — do not commit O\*NET files.

---

### Step 2 — Run ingestion

```bash
# From repo root (uses ./data/onet/ by default):
make ingest-onet

# Custom path:
make ingest-onet ONET_DIR=/path/to/db_29_0_text
```

The script is **idempotent**: running it a second time updates existing rows
instead of duplicating them, identified by `onet_soc_code`.

Expected output:

```
O*NET ingestion complete.
  Added:   198
  Updated: 0
  Skipped: 2  (name conflicts with manual careers)
  Total active careers in DB: 220
```

---

### Filter rules applied

| Rule | Detail |
|---|---|
| SOC suffix | Keep only `.00` codes (base occupations; sub-specialties omitted for clarity) |
| Major groups | 11 (Management), 13 (Business/Financial), 15 (Computer/Math), 17 (Engineering), 19 (Science), 21 (Community/Social), 23 (Legal), 25 (Education), 27 (Arts/Media), 29 (Healthcare), 41 (Sales) |
| Excluded groups | 31, 33, 35, 37, 39, 43, 45, 47, 49, 51, 53 — manual/service/trades occupations unlikely to match Echelon's user base |
| Job Zone | ≥ 3 (medium to high preparation required); Zone 1–2 entries excluded |
| Cap | If > 250 remain, trim alphabetically to 250 |

---

### Work Styles → Big Five mapping

O\*NET Work Styles are **not** Big Five personality traits. The mapping below is a
heuristic approximation — it is explicitly **not** a validated psychometric instrument.

| Big Five trait | O\*NET Work Styles used |
|---|---|
| Conscientiousness | Achievement/Effort, Persistence, Dependability, Attention to Detail |
| Openness | Innovation, Analytical Thinking, Adaptability/Flexibility, Initiative |
| Extraversion | Leadership, Social Orientation |
| Agreeableness | Cooperation, Concern for Others |
| Neuroticism | **Inverted** Self-Control + Stress Tolerance (high self-control = low neuroticism) |

Scores are on O\*NET's 1–5 Importance scale, converted to 0–100 by `(score − 1) / 4 × 100`.
When an occupation has no data for a style group, a category-level default is used.

---

### Growth potential

All O\*NET careers are assigned `growth_potential = "medium"` as a default.
Accurate growth data requires the BLS Employment Projections dataset, which is
a separate download (https://www.bls.gov/emp/). This is a known limitation.

---

### License and attribution

O\*NET is a public-domain resource produced by the U.S. Department of Labor and
licensed under **CC BY 4.0**.

**Required attribution (must appear in any product using this data):**

> "This product uses data from O\*NET OnLine by the U.S. Department of Labor,
> Employment and Training Administration (USDOL/ETA).
> O\*NET® is a trademark of USDOL/ETA."

This attribution appears in:
- The main project `README.md`
- The frontend footer (`/frontend/src/app/layout.tsx`)
