# Changelog

All notable changes to the Query Classification Agent will be documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.1.0] - 2026-02-23

### Added
- Initial proof of concept
- 3-agent pipeline (Validator → Classifier → Summarizer)
- CSV drag-and-drop upload for Query Detail Listings
- 4 classification categories: Affirmative, Confused, Medically Related, Miscellaneous
- Analytics dashboard with CRF confusion analysis
- Reinforcement via Human Feedback (RHF) review tab
- CSV export (full and per-category)
- JIRA integration for high confusion rate alerts
- Guide tab for CDAs and DMs
- Cortex LIGHTClient integration (gpt-5)

### Architecture
- Based on BIO Bot multi-agent pattern
- Uses Cortex LIGHTClient with 3-agent pipeline (Validator → Classifier → Summarizer)
