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

# 2.1 OpenReview 部分
for conf in openreview_confs:
    fetcher = OpenReviewFetcher(conf)
    papers = fetcher.fetch_papers(since_date)
    all_papers.extend(papers)

# 2.2 CVF 部分
for url, venue in cvf_confs:
    fetcher = CVFFetcher(url, venue)
    papers = fetcher.fetch_papers()
    all_papers.extend(papers)

# 2.3 ACL 部分 (暂时注释，URL可能有问题)
# acl_fetcher = ACLFetcher(year=acl_year, conference=acl_conf)
# acl_papers = acl_fetcher.fetch_papers()
# all_papers.extend(acl_papers)
print("ACL部分暂时跳过，URL需要修复")

# 2.4 保存原始拉取数据（可选）
os.makedirs("output", exist_ok=True)
with open("output/raw_papers.json", "w", encoding="utf-8") as f:
    json.dump(all_papers, f, indent=2)

print(f"拉取完毕，共计 {len(all_papers)} 篇论文。")

# ── 3. 关键词筛选 & 摘要精简 ────────────────────────────────
filtered_papers = process_papers(all_papers)
with open("output/filtered_papers.json", "w", encoding="utf-8") as f:
    json.dump(filtered_papers, f, indent=2)

print(f"关键词筛选完毕，剩余 {len(filtered_papers)} 篇论文。")

# ── 4. 认可度打分 ─────────────────────────────────────────
scored_results = []
for paper in filtered_papers:
    title = paper['title']
    # 4.1 查询 PapersWithCode
    pwc_info = pwcode_fetcher.search_paper(title)
    is_pwcode = True if pwc_info else False
    repo_url = pwc_info['repo_url'] if pwc_info else None

    # 4.2 查询 GitHub Repo Stats
    github_stats = github_fetcher.get_repo_stats(repo_url) if repo_url else None
    stars = github_stats['stars'] if github_stats else None
    days_open = github_stats['days_since_created'] if github_stats else None

    score = calculate_score(is_pwcode, stars, days_open)
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

print(f"认可度打分完毕，{len(scored_results)} 篇论文生成评分。")

# ── 5. 趋势统计 & 报告生成 ─────────────────────────────────
report_text = generate_report("output/scored_papers.json", "output")
print("趋势报告生成完成，保存在 output/report.md")

# ── 6. Slack 推送（若配置了 webhook） ─────────────────────────
if SLACK_WEBHOOK:
    try:
        payload = {"text": report_text}
        resp = requests.post(SLACK_WEBHOOK, json=payload)
        if resp.status_code == 200:
            print("Slack 推送成功")
        else:
            print("Slack 推送失败，状态码：", resp.status_code, resp.text)
    except Exception as e:
        print("Slack 推送异常：", str(e))
else:
    print("未配置 Slack Webhook，跳过推送。")

print("===== 本次 Agent 运行结束 =====")
