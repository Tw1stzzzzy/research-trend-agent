import json
import pandas as pd

def analyze_trends(scored_json_path):
    """
    输入：scored_papers.json 路径
    输出：统计结果字典，包括总论文数、开源数、平均分、关键词分布等
    """
    with open(scored_json_path, "r") as f:
        papers = json.load(f)

    if not papers:
        return {}

    df = pd.DataFrame(papers)

    # 总论文数
    total_papers = len(df)
    # 开源论文数（repo 不为 None）
    open_source_count = df['repo'].notnull().sum()
    # 平均认可度分
    avg_score = df['score'].mean() if 'score' in df.columns else 0

    # 从 configs/keywords.txt 读取关键词
    with open("configs/keywords.txt", "r") as f:
        keywords = [line.strip().lower() for line in f if line.strip()]

    keyword_counts = {}
    for kw in keywords:
        count = df['title'].str.contains(kw, case=False).sum()
        keyword_counts[kw] = int(count)

    return {
        'total_papers': total_papers,
        'open_source_count': int(open_source_count),
        'avg_score': round(float(avg_score), 2),
        'keyword_counts': keyword_counts
    }
