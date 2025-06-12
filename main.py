import os
import yaml
import json
import time

from fetchers.openreview_fetcher import OpenReviewFetcher
from fetchers.acl_fetcher import ACLFetcher
from fetchers.cvf_fetcher import CVFFetcher
from fetchers.github_fetcher import GitHubFetcher
from fetchers.pwcode_fetcher import PWCodeFetcher

from processors.filter_and_summarize import process_papers
from processors.scoring import calculate_score
from processors.trend_analyzer import analyze_trends
from processors.report_generator import generate_report
from processors.paper_processor import validate_and_clean_matches

import requests
from datetime import datetime

# ── 1. 读取配置 ─────────────────────────────────────────
with open("configs/config.yaml", "r") as f:
    config = yaml.safe_load(f)

# OpenReview 拉取起始日期
since_date = config['fetch']['since_date']

# API Keys
PWC_API_KEY = config['paperswithcode']['api_key']
GITHUB_TOKEN = config['github']['token']
SLACK_WEBHOOK = config['slack'].get('webhook_url', "")

# 初始化 Fetchers
pwcode_fetcher = PWCodeFetcher(PWC_API_KEY)
github_fetcher = GitHubFetcher(GITHUB_TOKEN)

# 会议列表和对应 Fetcher 初始化
# OpenReview 会议 ID (使用2023年数据进行测试)
openreview_confs = [
    "ICLR.cc/2023/Conference",
    # "NeurIPS.cc/2023/Conference",  # 先只测试一个会议
    # "ICML.cc/2023/Conference"
]

# CVF 会议 URL 和 Venue 名称 (使用2023年数据)
cvf_confs = [
    ("https://openaccess.thecvf.com/CVPR2023", "CVPR"),
    # ("https://openaccess.thecvf.com/ECCV2023", "ECCV")  # 先只测试一个会议
]

# ACL 会议设置
acl_year = "2024"
acl_conf = "ACL"

# ── 2. 拉取并合并所有会议论文 ────────────────────────────────
all_papers = []

# 2.1 OpenReview 部分 (暂时跳过，避免API限制)
print("⏭️  OpenReview fetching temporarily skipped (API rate limiting issues)")
# for conf in openreview_confs:
#     fetcher = OpenReviewFetcher(conf)
#     papers = fetcher.fetch_papers(since_date)
#     all_papers.extend(papers)

# 2.2 CVF 部分 (已发表论文)
for url, venue in cvf_confs:
    fetcher = CVFFetcher(url, venue)
    papers = fetcher.fetch_papers(max_papers=300)  # 增加获取数量以找到更多有GitHub的论文
    all_papers.extend(papers)
    print(f"📚 Fetched {len(papers)} papers from {venue}")

# 2.3 ACL 部分 (暂时注释，URL可能有问题)
# acl_fetcher = ACLFetcher(year=acl_year, conference=acl_conf)
# acl_papers = acl_fetcher.fetch_papers()
# all_papers.extend(acl_papers)
print("ACL fetching temporarily skipped (URL needs fixing)")

# 2.4 Save raw fetched data (optional)
os.makedirs("output", exist_ok=True)
with open("output/raw_papers.json", "w", encoding="utf-8") as f:
    json.dump(all_papers, f, indent=2)

print(f"✅ Paper fetching completed: {len(all_papers)} papers collected")

# ── 3. 关键词筛选 & 摘要精简 ────────────────────────────────
filtered_papers = process_papers(all_papers)
with open("output/filtered_papers.json", "w", encoding="utf-8") as f:
    json.dump(filtered_papers, f, indent=2)

print(f"🔍 Keyword filtering completed: {len(filtered_papers)} papers remain")

# 步骤 3：计算每篇论文的分数
print("\n📊 Calculating paper scores...")
scored_papers = calculate_score(filtered_papers, github_fetcher, pwcode_fetcher)

# 步骤 3.5：验证和清理匹配结果，提高匹配质量
print("\n🧹 Validating and cleaning repository matches...")
scored_papers = validate_and_clean_matches(scored_papers)

# 保存结果
with open("output/scored_papers.json", "w", encoding="utf-8") as f:
    json.dump(scored_papers, f, ensure_ascii=False, indent=2)

# ── 5. 趋势统计 & 报告生成 ─────────────────────────────────
stats = analyze_trends("output/scored_papers.json")
report_text = generate_report("output/scored_papers.json", "output")
print("📄 Trend report generated successfully → output/report.md")

# ── 6. Slack 推送（若配置了 webhook） ─────────────────────────
if SLACK_WEBHOOK and SLACK_WEBHOOK != "your-slack-webhook-here":
    try:
        # 准备Slack消息内容
        slack_summary = f"📋 *AI Research Trend Report ({datetime.now().strftime('%Y-%m-%d')})*\n\n"
        slack_summary += f"✨ *Total Papers*: {len(scored_papers)} papers analyzed\n"
        
        # 按星星数排序
        top_papers = sorted(scored_papers, key=lambda x: x.get('stars', 0), reverse=True)
        # 过滤只显示星星数超过500的仓库
        high_star_papers = [p for p in top_papers if p.get('stars', 0) >= 500]
        
        if not high_star_papers:
            slack_summary += "\n*No papers with repositories having 500+ stars were found.*"
        else:
            slack_summary += f"\n*Top {len(high_star_papers[:5])} Recommended Papers*:"
        
        for i, paper in enumerate(high_star_papers[:5], 1):
            title = paper['title']
            # 智能截断：优先保留完整单词，最大80字符
            if len(title) > 80:
                # 在单词边界截断
                words = title.split()
                truncated = ""
                for word in words:
                    if len(truncated + word) > 75:  # 留5个字符给"..."
                        break
                    truncated += word + " "
                title = truncated.strip() + "..."
            
            authors = paper.get('authors', [])
            first_author = authors[0] if authors else "Unknown"
            author_text = f"{first_author} et al." if len(authors) > 1 else first_author
            
            repo_url = paper.get('repo', '')
            stars = paper.get('stars', 0)
            
            slack_summary += f"\n{i}. *{title}*"
            slack_summary += f"\n   Authors: {author_text} | Venue: {paper.get('venue', 'N/A')}"
            slack_summary += f"\n   *Repository*: {repo_url} ({stars} ⭐)"
        
        slack_summary += f"\n\nFull detailed report: output/report.md"
        
        payload = {
            "text": slack_summary,
            "username": "Research Agent",
            "icon_emoji": ":robot_face:"
        }
        
        resp = requests.post(SLACK_WEBHOOK, json=payload)
        if resp.status_code == 200:
            print("📱 Slack notification sent successfully")
        else:
            print(f"❌ Slack notification failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Slack notification error: {str(e)}")
else:
    print("⏭️  Slack webhook not configured, skipping notification")

print("🎉 Research Agent execution completed successfully!")
