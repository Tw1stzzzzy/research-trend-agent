import os
import yaml
import json
import time

from fetchers.openreview_fetcher import OpenReviewFetcher
from fetchers.acl_fetcher import ACLFetcher
from fetchers.cvf_fetcher import CVFFetcher
from fetchers.pwcode_fetcher import PWCodeFetcher
from fetchers.github_fetcher import GitHubFetcher

from processors.filter_and_summarize import process_papers
from processors.scoring import calculate_score
from processors.trend_analyzer import analyze_trends
from processors.report_generator import generate_report

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

# ── 4. 认可度打分 & GitHub筛选 ─────────────────────────────
scored_results = []
skipped_no_github = 0

print("🔍 Starting recognition scoring (GitHub repos required)...")
if PWC_API_KEY == "your-pwc-api-key-here" or not PWC_API_KEY:
    print("⚠️  PapersWithCode API not configured, trying direct GitHub search")

for i, paper in enumerate(filtered_papers, 1):
    title = paper['title']
    print(f"  📋 Processing {i}/{len(filtered_papers)}: {title[:50]}...")
    
    # 4.1 查询 PapersWithCode
    pwc_info = None
    if PWC_API_KEY and PWC_API_KEY != "your-pwc-api-key-here":
        pwc_info = pwcode_fetcher.search_paper(title)
    
    is_pwcode = True if pwc_info else False
    repo_url = pwc_info['repo_url'] if pwc_info else None

    # 4.2 如果没有从PWC找到，尝试直接搜索GitHub（基于论文标题）
    github_result = None
    if not repo_url:
        github_result = github_fetcher.search_paper_repository(title)
        if github_result:
            repo_url = github_result['repo_url']
            github_stats = github_result['stats']
        
    # 4.3 查询 GitHub Repo Stats（如果还没有统计信息）
    if repo_url and not github_result:
        github_stats = github_fetcher.get_repo_stats(repo_url)
    elif github_result:
        github_stats = github_result['stats']
    else:
        github_stats = None
        
    stars = github_stats['stars'] if github_stats else None
    days_open = github_stats['days_since_created'] if github_stats else None

    # 4.4 只保留有GitHub仓库的论文
    if not repo_url or not github_stats:
        print(f"    ❌ No GitHub repo found, skipping paper")
        skipped_no_github += 1
        continue
        
    # 4.5 计算分数（只有有GitHub的论文才会到这里）
    score = calculate_score(is_pwcode, stars, days_open)
    
    print(f"    ✅ Found repo with {stars} stars, score: {score:.1f}")
    
    scored_results.append({
        'title': title,
        'authors': paper.get('authors', []),
        'summary': paper.get('summary', ""),
        'pdf_url': paper.get('pdf_url', ""),
        'venue': paper.get('venue', ""),
        'repo': repo_url,
        'stars': stars,
        'days_since_created': days_open,
        'score': score
    })

# 保存评分结果
with open("output/scored_papers.json", "w", encoding="utf-8") as f:
    json.dump(scored_results, f, indent=2)

print(f"📊 Recognition scoring completed: {len(scored_results)} papers with GitHub repos found")
print(f"⚠️  Skipped {skipped_no_github} papers without GitHub repositories")

# ── 5. 趋势统计 & 报告生成 ─────────────────────────────────
stats = analyze_trends("output/scored_papers.json")
report_text = generate_report("output/scored_papers.json", "output")
print("📄 Trend report generated successfully → output/report.md")

# ── 6. Slack 推送（若配置了 webhook） ─────────────────────────
if SLACK_WEBHOOK:
    try:
        # 创建丰富但清晰的Slack消息
        date_str = datetime.now().strftime('%Y-%m-%d')
        slack_summary = f"""*AI Research Trend Report* ({date_str})

*Summary Statistics:*
• Total Papers: {stats.get('total_papers', 0)}
• Open Source: {stats.get('open_source_count', 0)} ({stats.get('open_source_count', 0)/max(stats.get('total_papers', 1), 1)*100:.1f}%)
• Average Score: {stats.get('avg_score', 0):.1f}/5.0

*Hot Research Topics:*"""
        
        # 添加关键词分布
        if stats.get('keyword_counts'):
            sorted_keywords = sorted(stats['keyword_counts'].items(), key=lambda x: x[1], reverse=True)
            for kw, cnt in sorted_keywords[:3]:
                if cnt > 0:
                    percentage = (cnt / stats.get('total_papers', 1)) * 100
                    slack_summary += f"\n• {kw.title()}: {cnt} papers ({percentage:.1f}%)"
        
        # 添加推荐论文（前3篇高分论文）
        with open("output/scored_papers.json", "r") as f:
            scored_papers = json.load(f)
        
        top_papers = sorted(scored_papers, key=lambda x: x['score'], reverse=True)[:3]
        
        slack_summary += "\n\n*Top Recommended Papers:*"
        for i, paper in enumerate(top_papers, 1):
            title = paper['title']
            # 智能截断：优先保留完整单词，最大100字符
            if len(title) > 100:
                # 在单词边界截断
                words = title.split()
                truncated = ""
                for word in words:
                    if len(truncated + word) > 95:  # 留5个字符给"..."
                        break
                    truncated += word + " "
                title = truncated.strip() + "..."
            
            authors = paper.get('authors', [])
            first_author = authors[0] if authors else "Unknown"
            author_text = f"{first_author} et al." if len(authors) > 1 else first_author
            
            slack_summary += f"\n{i}. *{title}*"
            slack_summary += f"\n   Authors: {author_text} | Venue: {paper.get('venue', 'N/A')} | ⭐ {paper.get('stars', 0)} stars"
        
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
