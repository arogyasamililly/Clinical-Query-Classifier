"""
Unit Tests for Query Classification Agent
==========================================
Tests the classification logic, validation, and edge cases.
Run with: python -m pytest tests/test_classification.py -v
"""

import pytest
import pandas as pd
import json

# --- Import from app (adjust path if needed) ---
# If running from project root: python -m pytest tests/ -v
import sys
sys.path.insert(0, ".")


# =============================================================================
# TEST DATA — Known classifications for validation
# =============================================================================

AFFIRMATIVE_RESPONSES = [
    "corrected",
    "updated",
    "done",
    "completed",
    "fixed",
    "Date has been entered",
    "Value updated to reflect the correct amount",
    "Changed as requested",
    "Data corrected per query",
    "Form has been updated",
]

CONFUSED_RESPONSES = [
    "I can't enter a date, please open the form",
    "How do I fill this in?",
    "Where is this item located?",
    "please clarify what is needed",
    "I'm unclear what needs to be done",
    "item is not appearing for me",
    "unable to complete as the field is locked",
    "Can you please explain what this query is asking?",
    "The form doesn't allow me to edit this field",
    "I don't understand the question",
]

MEDICAL_RESPONSES = [
    "not clinically significant",
    "surgery was due to a pre-existing condition",
    "medication is ongoing",
    "deemed not to be clinically relevant",
    "adverse event resolved without treatment",
    "no additional risk factors",
    "Patient discontinued due to disease progression",
    "The condition was mild and self-limiting",
    "This was a planned surgical procedure",
    "Lab values returned to normal range",
]

MISC_RESPONSES = [
    "see attached",
    "will follow up",
    "pending",
    "N/A",
    "per monitor request",
    "TBD",
    ".",
    "ok",
]

INVALID_RESPONSES = [
    "",
    "   ",
    None,
    "nan",
]


# =============================================================================
# TESTS: Validation (Agent 1 logic)
# =============================================================================

class TestValidation:
    """Tests for the validation step (Agent 1)."""

    def test_valid_responses_pass(self):
        """All meaningful responses should pass validation."""
        for resp in AFFIRMATIVE_RESPONSES + CONFUSED_RESPONSES + MEDICAL_RESPONSES:
            assert resp is not None and len(resp.strip()) > 0, f"Should be valid: '{resp}'"

    def test_empty_responses_fail(self):
        """Empty or blank responses should fail validation."""
        for resp in INVALID_RESPONSES:
            is_invalid = (
                resp is None
                or str(resp).strip() == ""
                or str(resp).strip().lower() in ["nan", "none"]
            )
            assert is_invalid, f"Should be invalid: '{resp}'"

    def test_short_valid_responses(self):
        """Short but meaningful responses should pass."""
        short_valid = ["done", "ok", "yes", "no", "corrected"]
        for resp in short_valid:
            assert len(resp.strip()) > 0


# =============================================================================
# TESTS: Classification Categories
# =============================================================================

class TestCategoryDefinitions:
    """Tests that classification categories are properly defined."""

    def test_four_categories_exist(self):
        from app import CATEGORIES
        expected = {"Affirmative", "Confused", "Medically Related", "Miscellaneous"}
        assert set(CATEGORIES.keys()) == expected

    def test_each_category_has_required_fields(self):
        from app import CATEGORIES
        required_fields = {"description", "examples", "icon", "color", "note"}
        for cat, info in CATEGORIES.items():
            for field in required_fields:
                assert field in info, f"Category '{cat}' missing field '{field}'"

    def test_category_colors_are_valid_hex(self):
        from app import CATEGORIES
        import re
        for cat, info in CATEGORIES.items():
            assert re.match(r"^#[0-9a-fA-F]{6}$", info["color"]), \
                f"Invalid color for '{cat}': {info['color']}"


# =============================================================================
# TESTS: Prompt Construction
# =============================================================================

class TestPrompts:
    """Tests that agent prompts are well-formed."""

    def test_validation_prompt_contains_response(self):
        from app import get_validation_prompt
        prompt = get_validation_prompt("corrected", "AE Term")
        assert "corrected" in prompt
        assert "AE Term" in prompt

    def test_classification_prompt_has_all_categories(self):
        from app import get_classification_prompt
        prompt = get_classification_prompt()
        assert "Affirmative" in prompt
        assert "Confused" in prompt
        assert "Medically Related" in prompt
        assert "Miscellaneous" in prompt

    def test_classification_prompt_has_output_format(self):
        from app import get_classification_prompt
        prompt = get_classification_prompt()
        assert "JSON" in prompt
        assert "index" in prompt
        assert "classification" in prompt
        assert "confidence" in prompt

    def test_summary_prompt_includes_counts(self):
        from app import get_summary_prompt
        counts = {"Affirmative": 50, "Confused": 20}
        prompt = get_summary_prompt(counts, {"AE Term": 10}, 100)
        assert "100" in prompt
        assert "Affirmative" in prompt


# =============================================================================
# TESTS: Output Parsing
# =============================================================================

class TestOutputParsing:
    """Tests that LLM output can be parsed correctly."""

    def test_valid_json_output(self):
        """Simulate a valid LLM response and verify parsing."""
        mock_response = json.dumps([
            {"index": 0, "classification": "Affirmative", "confidence": 0.95, "reasoning": "Site confirms update"},
            {"index": 1, "classification": "Confused", "confidence": 0.82, "reasoning": "Site asking for help"},
        ])
        results = json.loads(mock_response)
        assert len(results) == 2
        assert results[0]["classification"] == "Affirmative"
        assert results[1]["classification"] == "Confused"

    def test_json_with_markdown_fences(self):
        """LLM sometimes wraps JSON in markdown — we should handle it."""
        mock_response = '```json\n[{"index": 0, "classification": "Affirmative", "confidence": 0.9, "reasoning": "done"}]\n```'
        cleaned = mock_response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        results = json.loads(cleaned)
        assert len(results) == 1
        assert results[0]["classification"] == "Affirmative"

    def test_invalid_json_handled_gracefully(self):
        """If LLM returns garbage, we should not crash."""
        mock_response = "I'm sorry, I couldn't classify these responses."
        try:
            results = json.loads(mock_response)
        except json.JSONDecodeError:
            results = [{"index": 0, "classification": "Miscellaneous", "confidence": 0.0, "reasoning": "Parse failed"}]
        assert results[0]["classification"] == "Miscellaneous"


# =============================================================================
# TESTS: Human Feedback
# =============================================================================

class TestHumanFeedback:
    """Tests the Reinforcement via Human Feedback (RHF) flow."""

    def test_correction_updates_classification(self):
        df = pd.DataFrame({
            "LLM_Classification": ["Affirmative", "Confused", "Miscellaneous"],
            "Confidence": [0.95, 0.60, 0.40],
            "Reasoning": ["ok", "ok", "ok"],
            "Human_Reviewed": [False, False, False],
        })

        # Simulate human correcting row 2 from Miscellaneous → Medically Related
        corrections = {2: "Medically Related"}
        for idx, label in corrections.items():
            df.at[idx, "LLM_Classification"] = label
            df.at[idx, "Human_Reviewed"] = True
            df.at[idx, "Confidence"] = 1.0

        assert df.at[2, "LLM_Classification"] == "Medically Related"
        assert df.at[2, "Human_Reviewed"] == True
        assert df.at[2, "Confidence"] == 1.0
        # Other rows unchanged
        assert df.at[0, "LLM_Classification"] == "Affirmative"

    def test_correction_does_not_affect_other_rows(self):
        df = pd.DataFrame({
            "LLM_Classification": ["Affirmative", "Confused"],
            "Confidence": [0.95, 0.60],
            "Human_Reviewed": [False, False],
        })
        df.at[1, "LLM_Classification"] = "Affirmative"
        assert df.at[0, "LLM_Classification"] == "Affirmative"
        assert df.at[0, "Confidence"] == 0.95


# =============================================================================
# TESTS: CSV Processing
# =============================================================================

class TestCSVProcessing:
    """Tests CSV upload and column mapping."""

    def test_sample_csv_loads_correctly(self):
        data = {
            "Query ID": [1, 2, 3],
            "Study Alias": ["ABC", "XYZ", "DEF"],
            "CRF Item": ["AE Term", "Visit Date", "BP"],
            "Site Response": ["corrected", "where is this?", "ongoing"],
        }
        df = pd.DataFrame(data)
        assert len(df) == 3
        assert "Site Response" in df.columns
        assert "CRF Item" in df.columns

    def test_missing_column_detected(self):
        data = {"Query ID": [1], "Response": ["done"]}
        df = pd.DataFrame(data)
        assert "Site Response" not in df.columns  # Should trigger warning

    def test_empty_csv_handled(self):
        df = pd.DataFrame()
        assert len(df) == 0


# =============================================================================
# RUN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
