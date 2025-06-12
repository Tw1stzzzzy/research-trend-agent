# Research Agent - Academic Paper Research Assistant

## 📖 Project Overview

Research Agent is an intelligent academic paper research assistant system designed to help researchers efficiently track and analyze the latest paper trends from top AI conferences. The system automatically scrapes papers from major AI conferences, filters them based on keywords, assesses their impact and recognition through code repository metrics, and generates comprehensive research trend reports.

## ✨ Key Features

- **🔍 Multi-Source Paper Scraping**: Automatically scrape papers from top AI conferences (ICLR, NeurIPS, ICML, CVPR, ECCV, ACL)
- **🎯 Intelligent Filtering**: Keyword-based filtering with LLM-powered abstract summarization for rapid paper identification
- **📊 Recognition Assessment**: Evaluate paper impact using PapersWithCode and GitHub metrics (stars, forks, etc.)
- **🧠 Smart Repository Matching**: Advanced validation and cleaning process to ensure high-quality paper-repository matches
- **📈 Trend Analysis**: Generate research trend reports with hot topic statistics and conference distribution
- **🤖 Slack Integration**: Push notifications for newly discovered high-impact papers

## 🏗️ System Architecture

```
research_agent/
├── main.py              # Main program entry
├── fetchers/            # Paper scraping modules
│   ├── openreview_fetcher.py  # Fetch from OpenReview (ICLR, NeurIPS, ICML)
│   ├── cvf_fetcher.py         # Fetch from CVF (CVPR, ECCV)
│   ├── acl_fetcher.py         # Fetch from ACL Anthology
│   ├── pwcode_fetcher.py      # PapersWithCode API integration
│   └── github_fetcher.py      # GitHub API integration
├── processors/          # Data processing modules
│   ├── filter_and_summarize.py  # Filter papers by keywords
│   ├── paper_processor.py       # Validate and clean paper-repo matches
│   ├── scoring.py               # Calculate paper scores
│   ├── trend_analyzer.py        # Analyze research trends
│   ├── llm_client.py            # LLM API client
│   ├── llm_summary.py           # Generate paper summaries
│   └── report_generator.py      # Generate markdown reports
└── configs/             # Configuration files
    ├── config.yaml      # API keys and system settings
    └── keywords.txt     # Keywords for paper filtering
```

## 🚀 Quick Start

### System Requirements
- Python 3.8+
- Dependencies: `openreview-py`, `requests`, `beautifulsoup4`, `pyyaml`, `openai`, etc.

### Installation Steps

1. **Clone the repository**
```bash
git clone https://github.com/Tw1stzzzzy/research-trend-agent.git
cd research-trend-agent
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configuration setup**

Edit `configs/config.yaml`:
```yaml
# API Configuration
llm_provider: "openai"  # or "anthropic", etc.
openai:
  api_key: "your-openai-api-key"

paperswithcode:
  api_key: "your-pwc-api-key"

github:
  token: "your-github-token"

slack:
  webhook_url: "your-slack-webhook-url"

# Scraping Configuration
fetch:
  since_date: "2024-01-01"
```

Edit `configs/keywords.txt` and add keywords of interest:
```
transformer
attention
autoregressive
diffusion
...
```

### Usage

```bash
# If you've run the system before and want to keep previous results,
# make sure to backup important files from the output directory first
# mkdir -p backup && cp output/*.json output/report.md backup/

# Clear previous output files before a new run
rm -f output/*.json output/report.md

# Run the system
python main.py
```

After completion, check the `output/` directory for:
- `raw_papers.json` - Raw paper data
- `filtered_papers.json` - Filtered papers
- `scored_papers.json` - Scored papers with repository matches
- `report.md` - Final research report

## 📋 Configuration Guide

### API Key Acquisition
- **OpenAI API**: Visit [OpenAI Platform](https://platform.openai.com/) to obtain
- **PapersWithCode API**: Apply at [PWC API](https://paperswithcode.com/api/v1/docs/)
- **GitHub Token**: Create in GitHub Settings > Developer settings > Personal access tokens
- **Slack Webhook**: Create at [Slack API](https://api.slack.com/messaging/webhooks)

### Keyword Configuration
Add one keyword per line in `configs/keywords.txt`. The system performs exact matching (supports regex boundaries).

## 🔧 Key Components

### Paper Fetchers
The system supports multiple paper sources through dedicated fetcher modules:
- **OpenReview Fetcher**: For ICLR, NeurIPS, ICML papers
- **CVF Fetcher**: For CVPR, ECCV papers
- **ACL Fetcher**: For ACL Anthology papers

### Repository Matching
The system employs a sophisticated algorithm to match papers with their official repositories:
1. First attempts to find through PapersWithCode API
2. Falls back to GitHub search using paper titles and author names
3. Applies validation and cleaning process to ensure high-quality matches

### Paper Processing
- **Filtering**: Keyword-based filtering to identify relevant papers
- **Scoring**: Multi-factor scoring based on GitHub metrics and paper features
- **Trend Analysis**: Identify hot research topics and emerging trends

### Report Generation
Generates comprehensive Markdown reports including:
- Top papers by impact score
- Research trend analysis
- Hot topics statistics
- Detailed paper information with links

## 🛠️ Extension Development

### Adding New Paper Sources
1. Create a new fetcher class in the `fetchers/` directory
2. Implement the `fetch_papers()` method
3. Integrate the new data source in `main.py`

### Custom Scoring Algorithm
Modify the `calculate_score()` function in `processors/scoring.py` to adjust scoring weights and logic.

### Custom Report Templates
Edit the report generation logic and Markdown templates in `processors/report_generator.py`.

---

**Note**: Please ensure compliance with API usage terms and rate limits of academic platforms when using this system. 