# 🏥 Query Classification Agent

A multi-agent Streamlit application that classifies clinical trial site responses to data queries using Cortex AI. Designed for CDAs and DMs to rapidly triage high volumes of query data at the study level.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [How It Works](#how-it-works)
- [Classification Categories](#classification-categories)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Usage Guide](#usage-guide)
- [Expected CSV Format](#expected-csv-format)
- [Architecture](#architecture)
- [Analytics and Insights](#analytics-and-insights)
- [Setting Up for Your Own Study](#setting-up-for-your-own-study)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Data Safety](#data-safety)
- [References](#references)
- [Team](#team)

---

## Overview

Clinical trial Data Managers (DMs) and Clinical Data Associates (CDAs) review thousands of site responses to data queries. Manually reading and categorizing each response is time-consuming, inconsistent across reviewers, and makes it easy to miss important patterns like recurring site confusion or medically relevant responses buried in large datasets.

This tool automates that classification. A DM or CDA uploads their **Query Detail Listing** (a CSV they already pull manually — it does not come from CLUWE) and the AI classifies each site response into one of four categories. The result is a classified dataset that allows the team to quickly filter, prioritize, and analyze query responses at scale.

**This is a local, study-level tool — not an enterprise solution.** The Query Analytics team is working on a larger-scale platform separately. This tool is designed to be simple enough for any CDA or DM to set up and use for their own study with minimal technical overhead.

---

## Features

| Feature | Description |
|---------|-------------|
| **CSV Upload** | Drag-and-drop interface. No database or system integration needed. |
| **3-Agent Pipeline** | Validate → Classify → Summarize, all powered by Cortex AI. |
| **4 Categories** | Affirmative, Confused, Medically Related, Miscellaneous. |
| **Analytics Dashboard** | Charts for category distribution, CRF confusion analysis, study breakdown. |
| **Human Feedback (RHF)** | Review and correct low-confidence classifications to validate the model. |
| **CSV Export** | Download full classified dataset or filtered by individual category. |
| **Built-in Guide** | In-app tab explains usage so other CDAs/DMs can self-serve. |

---

## How It Works

```
┌──────────────────────────────┐
│  DM / CDA uploads CSV        │   Query Detail Listing
│  (drag and drop)             │   (manually pulled from study)
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  🕵️ Agent 1: Validator       │   Filters out blank, gibberish,
│  (Cortex API)                │   and non-response entries
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  🤖 Agent 2: Classifier      │   Classifies each response:
│  (Cortex API)                │     ✅ Affirmative
│                              │     ❓ Confused
│                              │     🏥 Medically Related
│                              │     📋 Miscellaneous
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  📝 Agent 3: Summarizer      │   Generates insights and
│  (Cortex API)                │   actionable recommendations
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  📊 Results & Analytics      │   Dashboard, charts, filters
│  🔍 Human Review (RHF)       │   Correct misclassifications
│  💾 Export CSV                │   Download classified data
└──────────────────────────────┘
```

---

## Classification Categories

| Category | Icon | Description | Examples |
|----------|------|-------------|----------|
| **Affirmative** | ✅ | Site confirms correction or update was made | "corrected", "updated", "done", "date entered" |
| **Confused** | ❓ | Site is unsure, asks for help, or can't complete the action | "I can't enter a date", "where is this item?", "field is locked" |
| **Medically Related** | 🏥 | Response contains clinical information or medical judgment | "not clinically significant", "medication ongoing", "AE resolved" |
| **Miscellaneous** | 📋 | Doesn't clearly fit above — ambiguous, partial, or unrelated | "see attached", "pending", "N/A", "will follow up" |

### Important Notes

- **"Updated" does not mean data changed.** An Affirmative classification means the site *said* they updated. The DM must still verify via the audit trail whether the data actually changed and whether the new value is correct.
- **CRF Item name does not determine category.** A medically relevant CRF Item (e.g., "AE Term") may have a non-medical response (e.g., "done"). Classification is based on the **site response text**, not the form or field name.
- **Confused responses reveal training gaps.** High confusion on specific CRF items suggests the query wording, CRF design, or site training materials may need improvement.

---

## Project Structure

```
query-classification-agent/
├── .gitignore                      # Blocks data files, secrets, caches
├── .env.example                    # Template for environment variables
├── .streamlit/
│   └── config.toml                 # Streamlit theme and server config
├── app.py                          # Main Streamlit app (3-agent pipeline)
├── requirements.txt                # Python dependencies
├── manifest.json                   # Deployment manifest
├── run.bat                         # Windows launcher
├── README.md                       # This file
├── CONTRIBUTING.md                 # Branching strategy, how to extend
├── CHANGELOG.md                    # Version history
└── tests/
    └── test_classification.py      # Unit tests (pytest)
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Access to Cortex API (`api.cortex.lilly.com`)
- `light-client` library configured for Cortex authentication

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/query-classification-agent.git
cd query-classification-agent

# Create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Running the App

**Option 1: Using run.bat (Windows)**

```bash
run.bat
```

**Option 2: Manual**

```bash
python -m streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Usage Guide

### Step 1: Upload CSV

Go to the **📤 Upload & Classify** tab. Drag and drop your Query Detail Listing CSV.

### Step 2: Map Columns

In the **sidebar**, verify that the column names match your CSV. Different studies may use different headers. Update them if needed:

| Setting | Default Value | What It Maps To |
|---------|---------------|-----------------|
| Site Response Column | `Site Response` | The column containing site reply text |
| CRF Item Column | `CRF Item` | The CRF form/field name |
| Query ID Column | `Query ID` | Unique query identifier |
| Study Alias Column | `Study Alias` | Study or protocol identifier |
| Original Query Column | `Original Query` | The DM's original query text |

### Step 3: Classify

Click **🚀 Classify Queries**. The three agents will run in sequence:

1. **Agent 1** validates each response (filters blanks and invalid entries)
2. **Agent 2** classifies each valid response into one of four categories
3. **Agent 3** generates a summary with insights and recommendations

Typical processing time: **1-3 minutes per 1,000 queries**, depending on batch size.

### Step 4: Review Results

- **📊 Results tab** — Full classified dataset with filters by category, confidence, and CRF item.
- **📈 Analytics tab** — Charts showing classification distribution, CRF confusion analysis, study-level breakdown, and medically related responses for MRL supplement.

### Step 5: Human Feedback (RHF)

Go to the **🔍 Review & Correct** tab. This is the validation step:

1. Low-confidence classifications are flagged automatically
2. Expand any row to see the response, CRF item, and agent reasoning
3. Change the classification if incorrect
4. Click **Apply Corrections** to update the dataset

This feedback loop is critical for validating the model's accuracy and building confidence in the results.

### Step 6: Export

Go to the **💾 Export** tab:

- **Download Full CSV** — The entire classified dataset with `LLM_Classification`, `Confidence`, `Reasoning`, and `Human_Reviewed` columns appended.
- **Download by Category** — Individual CSVs for Affirmative, Confused, Medically Related, or Miscellaneous.

---

## Expected CSV Format

Your CSV should have at minimum these columns (names are configurable in the sidebar):

| Query ID | Study Alias | CRF Item | Site Response |
|----------|-------------|----------|---------------|
| 11798 | ABC-XY-1234 | Dispensed Amount | corrected |
| 84789 | XYZ-AB-4321 | Subject Status | I was unable to complete this |
| 179664 | XXX-ZZ-YYYY | AE Term | surgery was due to a pre-existing condition |
| 10124 | GBNS-BQ-SDBK | Interruption Reason | please clarify what needs to be updated |
| 70158 | HKBC-GJ-GRHI | Conmed End Date | Medication is ongoing |

Additional columns (Subject ID, Site, Visit, etc.) are preserved in the output but are not required for classification.

---

## Architecture

### Agent 1: Validator

**Purpose:** Filter out rows that cannot be meaningfully classified.

- Checks for blank, empty, or null responses
- Identifies gibberish or numeric-only entries via Cortex
- Marks invalid rows as `INVALID` — they are excluded from classification but preserved in the export

### Agent 2: Classifier

**Purpose:** Classify each valid site response into one of four categories.

- Processes rows in configurable batches (default: 15 rows per API call)
- Uses a detailed system prompt with category definitions, examples, and rules
- Returns structured JSON with classification, confidence score (0.0-1.0), and reasoning
- Falls back to `Miscellaneous` with confidence `0.0` if API call fails (ensures no data is lost)

### Agent 3: Summarizer

**Purpose:** Generate a human-readable summary of the classification results.

- Receives category counts and top confused CRF items
- Produces a markdown report with patterns, concerns, and recommendations

---

## Analytics and Insights

The **📈 Analytics** tab provides:

| Analysis | What It Shows | Why It Matters |
|----------|---------------|----------------|
| Classification Distribution | Bar chart of category counts | Quick overview of response patterns |
| Confidence Distribution | Histogram of confidence scores | Identifies how certain the model is |
| CRF Confusion Analysis | Top 15 CRF items with confused responses | Reveals training gaps and CRF design issues |
| Study Breakdown | Stacked bar by study and category | Compare response patterns across studies |
| Medical Responses | Table of medically related responses | Supplements Medical Review Listings (MRLs) |

### Key Questions This Tool Helps Answer

- Which CRF items or queries do sites have the most difficulty answering?
- Are there potential gaps in site training material?
- Which sites are consistently confused vs. responsive?
- Are there medically relevant responses that should be flagged for medical review?
- For "Affirmative" responses, did a data change actually occur? (requires audit trail follow-up)

---

## Setting Up for Your Own Study

This tool is study-agnostic. Any DM or CDA can use it for their own study:

1. **Clone or copy this project** to your local machine
2. **Install dependencies** per the Getting Started section above
3. **Pull your Query Detail Listing** CSV from your study
4. **Run the app** with `python -m streamlit run app.py`
5. **Update column mapping** in the sidebar to match your CSV headers
6. **Classify, review, and export**

No database setup, no CLUWE connection, no enterprise infrastructure required. It runs entirely locally.

---

## Configuration

### Changing the AI Model

Open `app.py` and modify the `CORTEX_CONFIG` dictionary:

```python
CORTEX_CONFIG = {
    "base_url": "https://api.cortex.lilly.com",
    "config": "md3-raw",
    "model": "gpt-5",    # ← Change this to your preferred model
}
```

### Adding New Categories

1. Add an entry to the `CATEGORIES` dictionary in `app.py`:

```python
"Your New Category": {
    "description": "When this category applies",
    "examples": "example response 1, example response 2",
    "icon": "🆕",
    "color": "#hexcolor",
    "note": "Important caveat.",
},
```

2. Update the `get_classification_prompt()` function to include the new category definition and examples in the system prompt.

3. Test with sample data to verify classification accuracy.

### Adjusting Batch Size

In the sidebar under **Agent Settings**, use the slider to change how many rows are sent per Cortex API call:

| Batch Size | Tradeoff |
|------------|----------|
| 5-10 | More reliable, slower, more API calls |
| 15-20 | Balanced (default: 15) |
| 25-30 | Faster, but may hit token limits on long responses |

---

## Testing

Run the test suite:

```bash
python -m pytest tests/ -v
```

Tests cover:

- Validation logic (Agent 1)
- Category definitions and required fields
- Prompt construction for all three agents
- JSON output parsing (including edge cases like markdown fences)
- Human feedback correction flow
- CSV loading and column mapping

---

## Troubleshooting

| Issue | Likely Cause | Fix |
|-------|-------------|-----|
| "Failed to initialize Cortex client" | `light-client` not configured | Verify Cortex authentication setup |
| Column not found warning | CSV headers don't match defaults | Update column names in the sidebar |
| Many rows classified as Miscellaneous with 0.0 confidence | Cortex API errors or rate limiting | Reduce batch size, check API access |
| App is slow on large CSVs (10k+ rows) | Too many API calls | Increase batch size, or sample a subset first |
| JSON parse error in logs | LLM returned unexpected format | Agent falls back to Miscellaneous automatically — review flagged rows manually |

---

## Data Safety

**CRITICAL: Never commit clinical trial data to version control.**

- The `.gitignore` file blocks all `.csv`, `.xlsx`, `.db`, and data directory files
- Do NOT remove or modify these rules
- If you need sample data for testing, use fully synthetic/fake data only
- No real patient IDs, site names, investigator names, or study aliases should appear in code, comments, or commits
- All data processing happens locally — nothing is stored permanently by the app

---

## References

- Petukhova, A., Matos-Carvalho, J.P., & Fachada, N. (2024). *Text Clustering with Large Language Model Embeddings.* International Journal of Cognitive Computing in Engineering.
- González-Carvajal, S., & Garrido-Merchán, E. C. (2020). *Comparing BERT against traditional machine learning text classification.*
- Sabiri, B., Khtira, A., El Asri, B., & Rhanoui, M. (2023). *Analyzing BERT's Performance Compared to Traditional Text Classification Models.* ICEIS 2023.

---

## Team

| Name | Role |
|------|------|
| *Your Name* | Senior Clinical Data Associate |
| *Intern 1* | CDA Intern — Development |
| *Intern 2* | CDA Intern — Testing & Guide |

---

## License

Internal use only. Not for distribution outside the organization.
