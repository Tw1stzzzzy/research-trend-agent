# Research Agent - Academic Paper Research Assistant

## 📖 Project Overview

Research Agent is an intelligent academic paper research assistant system designed to help researchers efficiently track and analyze the latest paper trends from top AI conferences. The system provides personalized academic research reports through automated paper scraping, intelligent filtering, recognition assessment, and trend analysis.

## ✨ Key Features

### 🔍 Multi-Source Paper Scraping
- **OpenReview Conferences**: Top machine learning conferences like ICLR, NeurIPS, ICML
- **CVF Conferences**: Computer vision conferences like CVPR, ECCV  
- **ACL Conferences**: Natural language processing conferences like ACL
- **Time Range Filtering**: Support incremental scraping with specified start dates

### 🎯 Intelligent Paper Filtering
- **Keyword Matching**: Precise filtering based on user-defined keywords
- **AI Abstract Summarization**: Use GPT-4o to condense lengthy abstracts into 2-3 core sentences
- **Multi-dimensional Filtering**: Support filtering by conference, time, decision status, etc.

### 📊 Paper Recognition Assessment
- **Open Source Code Retrieval**: Automatically query PapersWithCode platform for implementations
- **GitHub Impact Analysis**: Obtain metrics like repository stars, creation time, etc.
- **Comprehensive Scoring System**: Calculate paper industry recognition scores based on multiple dimensions

### 📈 Trend Analysis & Reporting
- **Hot Topic Analysis**: Statistics on high-frequency keywords and research trends
- **Conference Distribution Statistics**: Analysis of paper quantity and quality across major conferences
- **Recognition Rankings**: Display most popular papers by score
- **Intelligent Report Generation**: Automatically generate research briefs in Markdown format

### 🤖 Slack Bot Integration
- **Interactive Queries**: Real-time search for papers by specific keywords and years via @Bot commands
- **Real-time Push**: Support automatic report pushing to Slack channels
- **Command Example**: `@Bot search autoregressive 2025`

## 🏗️ System Architecture

```
research_agent/
├── main.py              # Main program entry
├── slack_app.py         # Slack bot service
├── fetchers/            # Paper scraping modules
│   ├── openreview_fetcher.py
│   ├── cvf_fetcher.py
│   ├── acl_fetcher.py
│   ├── pwcode_fetcher.py
│   └── github_fetcher.py
├── processors/          # Data processing modules
│   ├── filter_and_summarize.py
│   ├── scoring.py
│   ├── trend_analyzer.py
│   ├── llm_summary.py
│   └── report_generator.py
└── configs/             # Configuration files
    ├── config.yaml
    └── keywords.txt
```

## 🚀 Quick Start

### System Requirements
- Python 3.8+
- Dependencies: `openreview-py`, `requests`, `beautifulsoup4`, `pyyaml`, `openai`, `slack-bolt`, `flask`

### Installation Steps

1. **Clone the repository**
```bash
git clone <repository-url>
cd research_agent
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configuration setup**

Edit `configs/config.yaml`:
```yaml
# API Configuration
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

#### 1. Batch Processing Mode
```bash
python main.py
```
After completion, check the `output/` directory for:
- `raw_papers.json` - Raw paper data
- `filtered_papers.json` - Filtered papers
- `scored_papers.json` - Scored papers
- `report.md` - Final research report

#### 2. Slack Bot Mode
```bash
# Set environment variables
export SLACK_BOT_TOKEN="your-bot-token"
export SLACK_SIGNING_SECRET="your-signing-secret"

# Start Slack application
python slack_app.py
```

Then use in Slack:
```
@Bot search transformer 2024
```

## 📋 Configuration Guide

### API Key Acquisition
- **OpenAI API**: Visit [OpenAI Platform](https://platform.openai.com/) to obtain
- **PapersWithCode API**: Apply at [PWC API](https://paperswithcode.com/api/v1/docs/)
- **GitHub Token**: Create in GitHub Settings > Developer settings
- **Slack App**: Create application at [Slack API](https://api.slack.com/apps)

### Keyword Configuration
Add one keyword per line in `configs/keywords.txt`. The system performs exact matching (supports regex boundaries).

## 🔧 Extension Development

### Adding New Paper Sources
1. Create a new fetcher class in the `fetchers/` directory
2. Implement the `fetch_papers()` method
3. Integrate the new data source in `main.py`

### Custom Scoring Algorithm
Modify the `calculate_score()` function in `processors/scoring.py` to adjust scoring weights and logic.

### Custom Report Templates
Edit the report generation logic and Markdown templates in `processors/report_generator.py`.

## 📞 Technical Support

For questions or suggestions, please contact us via:
- Create a GitHub Issue
- Email the project maintainers

---

**Note**: Please ensure compliance with API usage terms and rate limits of academic platforms before using this system. 