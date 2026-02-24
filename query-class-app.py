import streamlit as st
import pandas as pd
import json
import re
import logging
from light_client import LIGHTClient

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- Configuration Constants ---
CORTEX_CONFIG = {
    "base_url": "https://api.cortex.lilly.com",
    "config": "md3-raw",
    "model": "gpt-5",
}

# --- Classification Categories ---
CATEGORIES = {
    "Affirmative": {
        "description": "Site acknowledged and indicates correction/update was made",
        "examples": "corrected, updated, done, completed, fixed, date entered, value changed",
        "icon": "✅",
        "color": "#22c55e",
        "note": "Just because they say 'updated' doesn't mean the data change actually occurred or was correct.",
    },
    "Confused": {
        "description": "Site is unsure, asks for help, or doesn't understand the query",
        "examples": "I can't enter a date, how do I fill this in, where is this item, please clarify, field is locked",
        "icon": "❓",
        "color": "#f59e0b",
        "note": "These indicate potential gaps in CRF design, site training, or query wording.",
    },
    "Medically Related": {
        "description": "Response contains clinical/medical information or judgment",
        "examples": "not clinically significant, surgery was due to, medication is ongoing, adverse event resolved",
        "icon": "🏥",
        "color": "#3b82f6",
        "note": "Just because a CRF Item is medically relevant doesn't mean the response is.",
    },
    "Miscellaneous": {
        "description": "Doesn't clearly fit above categories — ambiguous, partial, or unrelated",
        "examples": "see attached, will follow up, pending, N/A, per monitor request",
        "icon": "📋",
        "color": "#8b5cf6",
        "note": "Catch-all for responses needing manual review.",
    },
}

# --- Page and UI Configuration ---
st.set_page_config(
    page_title="Query Classification Agent",
    page_icon="🏥",
    layout="wide",
)


# =============================================================================
# CORE FUNCTIONS
# =============================================================================

@st.cache_resource
def initialize_cortex_client():
    """Initializes and caches the Cortex LIGHTClient."""
    try:
        return LIGHTClient()
    except Exception as e:
        st.error(f"Fatal: Failed to initialize Cortex client. Error: {e}")
        return None


def run_cortex_query(client, full_prompt):
    """Generic function to call the Cortex API and handle errors."""
    try:
        logger.info("Calling Cortex API...")
        response = client.post(
            f"{CORTEX_CONFIG['base_url']}/model/ask/{CORTEX_CONFIG['config']}",
            params={"model": CORTEX_CONFIG["model"]},
            data={"q": full_prompt},
        )
        response.raise_for_status()
        result = response.json().get("message", response.text)
        logger.info(f"Cortex response received ({len(result)} chars)")
        return result
    except Exception as e:
        logger.error(f"Cortex API error: {e}")
        st.error(f"An error occurred while calling the Cortex API: {e}")
        return None


def validate_response_local(site_response):
    """
    Local validation — no API call needed.
    Returns True if the response is meaningful enough to classify.
    """
    if not site_response:
        return False
    text = str(site_response).strip().lower()
    if text in ["", "nan", "none", "null", "na"]:
        return False
    if len(text) < 1:
        return False
    # Pure numbers with no context
    if text.replace(".", "").replace("-", "").isdigit():
        return False
    return True


# =============================================================================
# AGENT PROMPTS
# =============================================================================

def get_classification_prompt():
    """
    Agent 2: Classifies site responses into categories.
    This is the core classification prompt for the query classification agent.
    """
    return """
You are an expert clinical trial query classification agent. Your job is to classify 
site responses to data queries in clinical trials.

You must classify each site response into EXACTLY ONE of these categories:

## 1. Affirmative
The site acknowledged the query and indicates they made a correction or update.
Examples: "corrected", "updated", "done", "completed", "fixed", "changed as requested", 
"date has been entered", "value updated to reflect correct amount"
IMPORTANT: Just because they say "updated" does NOT mean the data actually changed. 
Still classify as Affirmative.

## 2. Confused
The site is unsure how to respond, asks for clarification, or indicates they don't 
understand the query or can't complete the action.
Examples: "I can't enter a date please open the form", "How do I fill this in?", 
"Where is this item located?", "please clarify what is needed", 
"item is not appearing for me", "unable to complete as the field is locked"

## 3. Medically Related
The response contains medical or clinical information, clinical judgment, or references 
to medical events, treatments, or diagnoses.
Examples: "not clinically significant", "surgery was due to a pre-existing condition", 
"medication is ongoing", "deemed not to be clinically relevant", 
"adverse event resolved without treatment", "no additional risk factors"
IMPORTANT: Just because the CRF Item name is medically relevant does NOT mean the site 
response is. Classify based on the RESPONSE TEXT, not the CRF Item.

## 4. Miscellaneous
Response doesn't clearly fit the above categories. Ambiguous, partial, or unrelated.
Examples: "see attached", "will follow up", "pending", "N/A", "per monitor request"

---
RULES:
- Classify based primarily on the SITE RESPONSE text
- Use CRF Item as secondary context only — it should NOT override the response text
- Short responses like "done" or "updated" → Affirmative
- Questions or expressions of difficulty → Confused
- Clinical language about conditions, treatments, significance → Medically Related
- Everything else → Miscellaneous

---
OUTPUT FORMAT:
For EACH row, respond with ONLY a JSON array. No other text, no markdown fences.
Each object must have:
- "index": the row number (integer)
- "classification": exactly one of "Affirmative", "Confused", "Medically Related", "Miscellaneous"
- "confidence": float between 0.0 and 1.0
- "reasoning": brief 5-10 word explanation

Example output:
[{"index": 0, "classification": "Affirmative", "confidence": 0.95, "reasoning": "Site confirms correction was made"}, {"index": 1, "classification": "Confused", "confidence": 0.88, "reasoning": "Site asking where to find the item"}]
"""


def get_summary_prompt(classification_counts, confused_crf_items, total_queries):
    """
    Agent 3: Generates a human-readable summary and recommendations.
    """
    return f"""
You are a clinical trial data management analyst. Generate a concise summary report 
based on the following query classification results.

---
Total Queries Classified: {total_queries}

Classification Breakdown:
{json.dumps(classification_counts, indent=2)}

Top CRF Items with Confused Responses:
{json.dumps(confused_crf_items, indent=2)}

---
Instructions:
1. Summarize the classification distribution in 2-3 sentences.
2. Highlight any concerning patterns (e.g., high confusion rate, specific CRF items).
3. Provide 2-3 actionable recommendations for the DM team.
4. Keep the tone professional and concise — this is for a clinical trial audience.
5. Format with clear headers using markdown.
"""


# =============================================================================
# CLASSIFICATION ENGINE
# =============================================================================

def classify_batch(client, rows, batch_size=15):
    """
    Sends rows to Agent 2 (Classification) in batches via Cortex.
    """
    system_prompt = get_classification_prompt()
    all_results = []

    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]

        row_texts = []
        for j, row in enumerate(batch):
            idx = i + j
            row_texts.append(
                f'Row {idx}: CRF_Item="{row["crf_item"]}" | '
                f'Site_Response="{row["site_response"]}"'
            )

        user_message = (
            f"Classify each of these {len(batch)} site responses. "
            f"Return ONLY a JSON array.\n\n" + "\n".join(row_texts)
        )

        full_prompt = f"{system_prompt}\n\n{user_message}"

        try:
            response_text = run_cortex_query(client, full_prompt)

            if not response_text:
                raise Exception("Empty response from Cortex")

            logger.info(f"Raw response: {response_text[:200]}...")

            # Clean markdown fences if present
            cleaned = response_text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                cleaned = cleaned.rsplit("```", 1)[0]

            # Extract JSON array from response
            json_match = re.search(r"\[.*\]", cleaned, re.DOTALL)
            if json_match:
                batch_results = json.loads(json_match.group())
            else:
                raise json.JSONDecodeError("No JSON array found", cleaned, 0)

            # Re-index to match original dataframe positions
            for j, result in enumerate(batch_results):
                result["index"] = i + j
            all_results.extend(batch_results)

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Batch classification failed: {e}")
            # Fallback: mark batch as Miscellaneous
            for j in range(len(batch)):
                all_results.append(
                    {
                        "index": i + j,
                        "classification": "Miscellaneous",
                        "confidence": 0.0,
                        "reasoning": "Classification failed — manual review needed",
                    }
                )

    return all_results


# =============================================================================
# MAIN APPLICATION (ORCHESTRATOR)
# =============================================================================

def main():
    st.header("🏥 Query Classification Agent")
    st.write(
        "Upload a Query Detail Listing CSV → Agent classifies site responses → "
        "Review, analyze, and export."
    )

    client = initialize_cortex_client()
    if not client:
        return

    # --- Sidebar: Settings ---
    with st.sidebar:
        st.header("⚙️ Settings")

        st.subheader("📂 Column Mapping")
        st.caption("Match these to your CSV column names")
        col_site_response = st.text_input("Site Response Column", value="Site Response")
        col_crf_item = st.text_input("CRF Item Column", value="CRF Item")
        col_query_id = st.text_input("Query ID Column", value="Query ID")
        col_study = st.text_input("Study Alias Column", value="Study Alias")
        col_query_text = st.text_input("Original Query Column", value="Original Query")

        st.divider()
        st.subheader("🎛️ Agent Settings")
        batch_size = st.slider("Batch Size", 5, 30, 15,
                               help="Rows per Cortex API call. Lower = more reliable.")
        confidence_threshold = st.slider(
            "Low Confidence Threshold", 0.50, 0.95, 0.70,
            help="Flag rows below this for human review.",
        )

        st.divider()
        st.subheader("📖 Categories")
        for cat, info in CATEGORIES.items():
            with st.expander(f"{info['icon']} {cat}"):
                st.write(info["description"])
                st.caption(f"Examples: {info['examples']}")
                st.caption(f"⚠️ {info['note']}")

    # --- Tabs ---
    tab_upload, tab_results, tab_analytics, tab_review, tab_export, tab_guide = st.tabs(
        ["📤 Upload & Classify", "📊 Results", "📈 Analytics", "🔍 Review & Correct", "💾 Export", "📖 Guide"]
    )

    # =================================================================
    # TAB 1: Upload & Classify
    # =================================================================
    with tab_upload:
        st.subheader("Step 1: Upload Your Query Detail Listing")

        uploaded_file = st.file_uploader(
            "Drag and drop your CSV here", type=["csv"],
            help="The manually pulled Query Detail Listing CSV from your study.",
        )

        if uploaded_file is not None:
            try:
                df_raw = pd.read_csv(uploaded_file)
                st.session_state["df_raw"] = df_raw
                st.success(f"✅ Uploaded **{len(df_raw)}** rows, **{len(df_raw.columns)}** columns")
                st.dataframe(df_raw.head(10), use_container_width=True)

                # Validate columns
                missing = []
                for col_name, col_var in [("Site Response", col_site_response), ("CRF Item", col_crf_item)]:
                    if col_var not in df_raw.columns:
                        missing.append(f"'{col_var}' ({col_name})")
                if missing:
                    st.warning(
                        f"⚠️ Columns not found: {', '.join(missing)}. "
                        f"Available: {list(df_raw.columns)}. Update in sidebar."
                    )
                else:
                    st.success("✅ Required columns found")

            except Exception as e:
                st.error(f"Error reading CSV: {e}")
        else:
            st.info("Upload a CSV to get started. Expected columns: Query ID, Study Alias, CRF Item, Site Response")

        # --- CLASSIFY BUTTON ---
        st.divider()
        if st.button("🚀 Classify Queries", type="primary", use_container_width=True):
            if "df_raw" not in st.session_state:
                st.error("Please upload a CSV first.")
                return
            if col_site_response not in st.session_state["df_raw"].columns:
                st.error(f"Column '{col_site_response}' not found. Update in sidebar.")
                return

            df = st.session_state["df_raw"].copy()

            # ── Agent 1: Validation (LOCAL — no API calls) ────────
            st.subheader("🕵️ Agent 1: Validation")
            logger.info(f"Starting validation for {len(df)} rows...")

            with st.spinner("Agent 1 is validating responses..."):
                df["Is_Valid"] = df[col_site_response].apply(validate_response_local)

            valid_count = df["Is_Valid"].sum()
            invalid_count = len(df) - valid_count
            logger.info(f"Validation complete: {valid_count} valid, {invalid_count} invalid")
            st.success(
                f"✅ Validation complete: **{valid_count}** valid, **{invalid_count}** invalid/empty"
            )

            # ── Agent 2: Classification ─────────────────────────
            st.subheader("🤖 Agent 2: Classification")
            df_valid = df[df["Is_Valid"]].copy()

            if len(df_valid) == 0:
                st.warning("No valid responses to classify.")
                return

            rows_to_classify = []
            for _, row in df_valid.iterrows():
                rows_to_classify.append(
                    {
                        "site_response": str(row.get(col_site_response, "")),
                        "crf_item": str(row.get(col_crf_item, "")),
                    }
                )

            with st.spinner("Agent 2 is classifying responses..."):
                progress2 = st.progress(0, text="Classifying...")
                all_results = []
                total_batches = (len(rows_to_classify) + batch_size - 1) // batch_size
                logger.info(f"Starting classification: {len(rows_to_classify)} rows in {total_batches} batches (batch_size={batch_size})")

                for b_idx in range(0, len(rows_to_classify), batch_size):
                    batch = rows_to_classify[b_idx : b_idx + batch_size]
                    batch_num = (b_idx // batch_size) + 1
                    logger.info(f"Classifying batch {batch_num}/{total_batches} ({len(batch)} rows)...")

                    batch_results = classify_batch(client, batch, batch_size=len(batch))

                    # Re-index to global positions
                    for j, r in enumerate(batch_results):
                        r["index"] = b_idx + j
                    all_results.extend(batch_results)

                    logger.info(f"Batch {batch_num}/{total_batches} complete")
                    progress2.progress(
                        batch_num / total_batches,
                        text=f"Classified {min(b_idx + batch_size, len(rows_to_classify))}/{len(rows_to_classify)}...",
                    )

            # Merge results into valid dataframe
            results_df = pd.DataFrame(all_results)
            df_valid = df_valid.reset_index(drop=True)
            df_valid["LLM_Classification"] = results_df["classification"]
            df_valid["Confidence"] = results_df["confidence"]
            df_valid["Reasoning"] = results_df["reasoning"]
            df_valid["Human_Reviewed"] = False

            # Merge back with invalid rows
            df_invalid = df[~df["Is_Valid"]].copy()
            df_invalid["LLM_Classification"] = "INVALID"
            df_invalid["Confidence"] = None
            df_invalid["Reasoning"] = "Empty or invalid response"
            df_invalid["Human_Reviewed"] = False

            df_final = pd.concat([df_valid, df_invalid], ignore_index=True)
            st.session_state["df_classified"] = df_final

            # ── Agent 3: Summary ────────────────────────────────
            st.subheader("📝 Agent 3: Summary Generation")
            class_counts = df_valid["LLM_Classification"].value_counts().to_dict()
            logger.info(f"Classification counts: {class_counts}")

            confused_crf = {}
            if col_crf_item in df_valid.columns:
                confused_df = df_valid[df_valid["LLM_Classification"] == "Confused"]
                if len(confused_df) > 0:
                    confused_crf = confused_df[col_crf_item].value_counts().head(10).to_dict()

            with st.spinner("Agent 3 is generating summary..."):
                logger.info("Generating summary report...")
                summary_prompt = get_summary_prompt(class_counts, confused_crf, len(df_valid))
                summary_text = run_cortex_query(client, summary_prompt)

            if summary_text:
                st.markdown(summary_text)
            else:
                st.info("Summary generation skipped.")

            st.success("✅ Classification complete! Check the Results and Analytics tabs.")
            logger.info("=== CLASSIFICATION PIPELINE COMPLETE ===")

    # =================================================================
    # TAB 2: Results
    # =================================================================
    with tab_results:
        if "df_classified" not in st.session_state:
            st.info("Upload and classify queries first (Tab 1).")
        else:
            df = st.session_state["df_classified"]
            df_valid_only = df[df["LLM_Classification"] != "INVALID"]

            st.subheader("Classification Results")

            # Summary cards
            cols = st.columns(5)
            total = len(df_valid_only)
            for col, (cat, info) in zip(cols[:4], CATEGORIES.items()):
                count = len(df_valid_only[df_valid_only["LLM_Classification"] == cat])
                pct = (count / total * 100) if total > 0 else 0
                col.metric(f"{info['icon']} {cat}", f"{count}", f"{pct:.1f}%")

            low_conf = len(df_valid_only[df_valid_only["Confidence"] < confidence_threshold])
            cols[4].metric("⚠️ Low Confidence", f"{low_conf}", "Needs Review")

            st.divider()

            # Filters
            f1, f2, f3 = st.columns(3)
            with f1:
                filter_class = st.multiselect(
                    "Classification",
                    list(CATEGORIES.keys()) + ["INVALID"],
                    default=list(CATEGORIES.keys()),
                )
            with f2:
                filter_conf = st.selectbox(
                    "Confidence", ["All", "High (≥0.8)", "Medium (0.6-0.8)", "Low (<0.6)"]
                )
            with f3:
                if col_crf_item in df.columns:
                    crf_opts = ["All"] + sorted(df[col_crf_item].dropna().unique().tolist())
                    filter_crf = st.selectbox("CRF Item", crf_opts)
                else:
                    filter_crf = "All"

            filtered = df[df["LLM_Classification"].isin(filter_class)]
            if filter_conf == "High (≥0.8)":
                filtered = filtered[filtered["Confidence"] >= 0.8]
            elif filter_conf == "Medium (0.6-0.8)":
                filtered = filtered[(filtered["Confidence"] >= 0.6) & (filtered["Confidence"] < 0.8)]
            elif filter_conf == "Low (<0.6)":
                filtered = filtered[filtered["Confidence"] < 0.6]
            if filter_crf != "All" and col_crf_item in filtered.columns:
                filtered = filtered[filtered[col_crf_item] == filter_crf]

            st.dataframe(filtered, use_container_width=True)
            st.caption(f"Showing {len(filtered)} of {len(df)} rows")

    # =================================================================
    # TAB 3: Analytics
    # =================================================================
    with tab_analytics:
        if "df_classified" not in st.session_state:
            st.info("Upload and classify queries first.")
        else:
            df = st.session_state["df_classified"]
            df_v = df[df["LLM_Classification"] != "INVALID"]

            st.subheader("📈 Query Analytics Dashboard")

            # Classification distribution
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Classification Distribution**")
                class_counts = df_v["LLM_Classification"].value_counts()
                chart_df = pd.DataFrame({"Category": class_counts.index, "Count": class_counts.values})
                st.bar_chart(chart_df.set_index("Category"))

            with c2:
                st.markdown("**Confidence Distribution**")
                if "Confidence" in df_v.columns:
                    st.bar_chart(df_v["Confidence"].dropna().value_counts(bins=10).sort_index())

            # Confused CRF Items
            if col_crf_item in df_v.columns:
                st.divider()
                st.subheader("❓ Which CRF Items Cause the Most Confusion?")
                confused = df_v[df_v["LLM_Classification"] == "Confused"]
                if len(confused) > 0:
                    crf_counts = confused[col_crf_item].value_counts().head(15)
                    st.bar_chart(crf_counts)
                    st.info(
                        "💡 These CRF items consistently confuse sites. "
                        "Consider reviewing query wording, CRF design, or site training."
                    )
                else:
                    st.success("No confused responses found.")

            # Study breakdown
            if col_study in df_v.columns:
                st.divider()
                st.subheader("📊 Breakdown by Study")
                study_class = df_v.groupby([col_study, "LLM_Classification"]).size().unstack(fill_value=0)
                st.bar_chart(study_class)

            # Medically Related for MRL
            st.divider()
            st.subheader("🏥 Medically Related Responses (MRL Supplement)")
            medical = df_v[df_v["LLM_Classification"] == "Medically Related"]
            if len(medical) > 0:
                st.write(f"**{len(medical)}** responses could supplement Medical Review Listings.")
                display_cols = [c for c in [col_query_id, col_study, col_crf_item, col_site_response, "Reasoning"]
                                if c in medical.columns]
                st.dataframe(medical[display_cols] if display_cols else medical, use_container_width=True)
            else:
                st.info("No medically related responses found.")

    # =================================================================
    # TAB 4: Review & Correct (Reinforcement via Human Feedback)
    # =================================================================
    with tab_review:
        if "df_classified" not in st.session_state:
            st.info("Upload and classify queries first.")
        else:
            df = st.session_state["df_classified"]
            st.subheader("🔍 Reinforcement via Human Feedback (RHF)")
            st.write(
                "Review low-confidence or incorrect classifications. "
                "Your corrections validate the model and improve future results."
            )

            df_v = df[df["LLM_Classification"] != "INVALID"]
            low_conf = df_v[df_v["Confidence"] < confidence_threshold]

            if len(low_conf) > 0:
                st.warning(f"⚠️ **{len(low_conf)} rows** below {confidence_threshold:.0%} confidence — review these first.")

            review_mode = st.radio("Review:", ["Low Confidence Only", "All Rows"], horizontal=True)
            review_df = low_conf if review_mode == "Low Confidence Only" else df_v

            if len(review_df) == 0:
                st.success("All classifications above confidence threshold!")
            else:
                corrections = {}
                for idx, row in review_df.head(50).iterrows():
                    with st.expander(
                        f"Row {idx} | {row.get('LLM_Classification', '?')} "
                        f"({row.get('Confidence', 0):.0%}) | "
                        f"{str(row.get(col_site_response, ''))[:80]}"
                    ):
                        ca, cb = st.columns([2, 1])
                        with ca:
                            st.markdown(f"**Site Response:** {row.get(col_site_response, 'N/A')}")
                            st.markdown(f"**CRF Item:** {row.get(col_crf_item, 'N/A')}")
                            st.caption(f"Reasoning: {row.get('Reasoning', 'N/A')}")
                        with cb:
                            current = row.get("LLM_Classification", "Miscellaneous")
                            cat_list = list(CATEGORIES.keys())
                            default_idx = cat_list.index(current) if current in cat_list else 3
                            new_class = st.selectbox(
                                "Correct to:",
                                cat_list,
                                index=default_idx,
                                key=f"corr_{idx}",
                            )
                            if new_class != current:
                                corrections[idx] = new_class

                if corrections:
                    st.write(f"**{len(corrections)} corrections** pending.")
                    if st.button("✅ Apply Corrections", type="primary"):
                        for idx, label in corrections.items():
                            df.at[idx, "LLM_Classification"] = label
                            df.at[idx, "Human_Reviewed"] = True
                            df.at[idx, "Confidence"] = 1.0
                            df.at[idx, "Reasoning"] = "Corrected via human review"
                        st.session_state["df_classified"] = df
                        st.success(f"Applied {len(corrections)} corrections!")
                        st.rerun()

    # =================================================================
    # TAB 5: Export
    # =================================================================
    with tab_export:
        if "df_classified" not in st.session_state:
            st.info("Upload and classify queries first.")
        else:
            df = st.session_state["df_classified"]
            st.subheader("💾 Export Classified Data")

            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Full Classified CSV",
                data=csv_data,
                file_name="classified_queries.csv",
                mime="text/csv",
                use_container_width=True,
            )

            st.divider()
            st.subheader("Download by Category")
            for cat, info in CATEGORIES.items():
                cat_df = df[df["LLM_Classification"] == cat]
                if len(cat_df) > 0:
                    st.download_button(
                        f"{info['icon']} {cat} ({len(cat_df)} rows)",
                        data=cat_df.to_csv(index=False).encode("utf-8"),
                        file_name=f"queries_{cat.lower().replace(' ', '_')}.csv",
                        mime="text/csv",
                    )

    # =================================================================
    # TAB 6: Guide for CDAs / DMs
    # =================================================================
    with tab_guide:
        st.subheader("📖 How to Use This Tool — Guide for CDAs and DMs")
        st.markdown("""
### What This Tool Does
Upload your **Query Detail Listing** (CSV) and the AI classifies each site response into:
- ✅ **Affirmative** — Site says they updated/corrected
- ❓ **Confused** — Site is unsure or asking for help  
- 🏥 **Medically Related** — Response contains clinical info
- 📋 **Miscellaneous** — Everything else

### Step-by-Step
1. **Pull your Query Detail Listing** from your study (the CSV you already pull manually)
2. **Upload the CSV** in the Upload tab  
3. **Map your columns** in the sidebar (match to your CSV headers)
4. **Click "Classify Queries"** — the 3 agents will validate, classify, and summarize
5. **Review results** in the Results and Analytics tabs
6. **Correct mistakes** in the Review tab (this validates the model)
7. **Export** the classified CSV

### What the 3 Agents Do
| Agent | Role |
|-------|------|
| 🕵️ Agent 1: Validator | Checks if each response is meaningful enough to classify |
| 🤖 Agent 2: Classifier | Assigns category (Affirmative/Confused/Medical/Misc) |
| 📝 Agent 3: Summarizer | Generates insights and recommendations |

### Tips
- Classification is based on **site response text**, not the CRF item name
- "Updated" responses still need DM verification — check audit trail
- Use the **Confused** category to find CRF design or training gaps
- **Medically Related** responses can supplement MRLs for medical review

### Setting Up for Your Own Study
1. Install: `pip install -r requirements.txt`
2. Run: `python -m streamlit run app.py`
3. Upload your study's Query Detail Listing CSV
        """)


if __name__ == "__main__":
    main()
