# 🏥 Query Classification Agent

A multi-agent Streamlit app that classifies clinical trial site responses to data queries using Cortex AI. Based on [Nick Fuller's SCDM 2025 framework](https://scdm.org) — Amplifying Query Analytics with LLM Classification.

**Workflow:** CSV Upload → Validate → Classify → Analyze → Export

---

## 📋 Features

* **Drag-and-Drop CSV Upload:** Upload your manually pulled Query Detail Listing — no database or CLUWE integration needed.
* **3-Agent Pipeline:**
  * **Agent 1 (Validator):** Filters out empty/invalid responses before classification
  * **Agent 2 (Classifier):** Classifies each site response into 4 categories (Affirmative, Confused, Medically Related, Miscellaneous)
  * **Agent 3 (Summarizer):** Generates insights and recommendations for the DM team
* **Analytics Dashboard:** Visual breakdown by category, CRF item confusion analysis, study-level comparisons
* **Human Feedback Loop (RHF):** Review and correct low-confidence classifications to validate the model
* **JIRA Integration:** Auto-creates tickets when high confusion rates are detected
* **Export:** Download classified CSVs (full or filtered by category)

---

## 🏗️ How It Works

```
┌─────────────────────────┐
│  DM/CDA uploads CSV     │   Query Detail Listing
│  (Query Detail Listing) │   (manually pulled)
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  🕵️ Agent 1: Validator  │   Filters blanks, gibberish,
│  (Cortex API)           │   non-responses
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  🤖 Agent 2: Classifier │   Classifies into:
│  (Cortex API)           │   ✅ Affirmative
│                         │   ❓ Confused
│                         │   🏥 Medically Related
│                         │   📋 Miscellaneous
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  📝 Agent 3: Summarizer │   Generates insights &
│  (Cortex API)           │   recommendations
└───────────┬─────────────┘
            ▼
┌─────────────────────────┐
│  📊 Results + Analytics │   Dashboard, CRF confusion
│  🔍 Human Review (RHF)  │   analysis, export
│  💾 Export CSV           │
└─────────────────────────┘
```

---

## 📂 Classification Categories

| Category | Icon | Description | Example |
|----------|------|-------------|---------|
| Affirmative | ✅ | Site confirms correction/update | "corrected", "updated", "done" |
| Confused | ❓ | Site is unsure or needs help | "I can't enter a date", "where is this?" |
| Medically Related | 🏥 | Response has clinical content | "not clinically significant", "medication ongoing" |
| Miscellaneous | 📋 | Doesn't fit above categories | "see attached", "pending", "N/A" |

**Important Notes:**
- "Updated" ≠ data actually changed (verify via audit trail)
- Medically relevant CRF Item ≠ medically related response (classify on response text)
- Confused responses reveal CRF design and site training gaps

---

## 🗂️ Project Files

| File | Description |
|------|-------------|
| `app.py` | Main Streamlit application (entry point) |
| `requirements.txt` | Python dependencies |
| `run.bat` | Windows batch file to set env vars and launch app |
| `README.md` | This file |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11+
- Access to Cortex API (`api.cortex.lilly.com`)
- Access to JIRA (optional, for auto-ticket creation)
- A Query Detail Listing CSV from your study

### Installation

```bash
# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Running the App

**Option 1: Using run.bat (Windows)**
1. Edit `run.bat` with your JIRA credentials
2. Double-click `run.bat` or run from terminal:
```bash
run.bat
```

**Option 2: Manual**
```bash
# Set JIRA env vars (optional)
set JIRA_SERVER="https://jira.lilly.com"
set JIRA_PROJECT="BIOBOT"
set JIRA_USER="your-service-account@lilly.com"
set JIRA_TOKEN="your-api-token"

# Launch
python -m streamlit run app.py
```

### Using the App
1. Open browser to `http://localhost:8501`
2. Upload your Query Detail Listing CSV
3. Check sidebar — make sure column names match your CSV
4. Click **"Classify Queries"**
5. Review results across the tabs
6. Correct any mistakes in the Review tab
7. Export classified CSV

---

## 📊 Expected CSV Format

Your CSV should have at minimum these columns (names configurable in sidebar):

| Query ID | Study Alias | CRF Item | Site Response |
|----------|-------------|----------|---------------|
| 11798 | ABC-XY-1234 | Dispensed Amount | corrected |
| 84789 | XYZ-AB-4321 | Subject Status | I was unable to complete... |
| 179664 | XXX-ZZ-YYYY | AE Term | surgery was due to... |

Additional columns (Original Query, Site, Subject, etc.) are preserved but not required.

---

## 🔄 Setting Up for Your Own Study

This tool is designed to be study-agnostic. Any DM or CDA can use it:

1. **Clone this project** to your local machine
2. **Install dependencies** per instructions above
3. **Pull your Query Detail Listing** CSV from your study
4. **Run the app** and upload your CSV
5. **Adjust column mapping** in the sidebar to match your CSV headers
6. **Classify, review, export**

No database, no CLUWE, no enterprise setup needed. It runs locally.

---

## 📚 References

- Nick Fuller, Meghna Godbole, Vina Ro. *Amplifying Query Analytics with LLM Classification.* SCDM 2025 Annual Conference, Baltimore, MD.
- Petukhova et al. (2024). *Text Clustering with Large Language Model Embeddings.*
- González-Carvajal & Garrido-Merchán (2020). *Comparing BERT against traditional ML text classification.*
