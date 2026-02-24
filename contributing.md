# Contributing to Query Classification Agent

## Getting Started

1. Clone the repository
```bash
git clone https://github.com/your-org/query-classification-agent.git
cd query-classification-agent
```

2. Create a virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Run the app
```bash
python -m streamlit run app.py
```

## Project Structure

```
query-classification-agent/
├── app.py                  # Main Streamlit app (3-agent pipeline)
├── requirements.txt        # Python dependencies
├── manifest.json           # Deployment manifest
├── run.bat                 # Windows launcher
├── .env.example            # Template for environment variables
├── .gitignore              # Git ignore rules
├── README.md               # Project documentation
├── CONTRIBUTING.md         # This file
├── CHANGELOG.md            # Version history
└── tests/
    └── test_classification.py  # Unit tests
```

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable, reviewed code only |
| `dev` | Active development and testing |
| `feature/<name>` | New features (branch from `dev`) |
| `bugfix/<name>` | Bug fixes |

### Workflow
1. Create a feature branch from `dev`: `git checkout -b feature/add-new-category dev`
2. Make your changes and test locally
3. Push and open a Pull Request into `dev`
4. After review, merge to `dev`
5. When stable, merge `dev` → `main`

## How to Add a New Classification Category

1. Open `app.py`
2. Find the `CATEGORIES` dictionary near the top
3. Add your new category:
```python
CATEGORIES = {
    # ... existing categories ...
    "Your New Category": {
        "description": "When to use this category",
        "examples": "example response 1, example response 2",
        "icon": "🆕",
        "color": "#hexcolor",
        "note": "Important caveat about this category.",
    },
}
```
4. Update the `get_classification_prompt()` function to include your new category in the Agent 2 system prompt
5. Test with sample data

## How to Change the AI Model

Open `app.py` and find `CORTEX_CONFIG` at the top:

```python
CORTEX_CONFIG = {
    "base_url": "https://api.cortex.lilly.com",
    "config": "md3-raw",
    "model": "gpt-5",    # Change this
}
```

Replace `"gpt-5"` with your preferred model.

## Data Safety

**CRITICAL:** Never commit clinical trial data to git.

- The `.gitignore` blocks all `.csv`, `.xlsx`, `.db` files
- Do NOT remove these rules
- If you need sample data for testing, use fully synthetic/fake data
- No real patient IDs, site names, or study aliases in code or commits

## Code Style

- Follow PEP 8 for Python
- Use descriptive variable names
- Add docstrings to all functions
- Comment any non-obvious logic
- Keep functions focused — one function, one job
