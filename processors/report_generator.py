from datetime import datetime
import os
from processors.trend_analyzer import analyze_trends
from processors.llm_summary import generate_llm_summary

def generate_report(scored_json_path, output_dir):
    """
    读取 scored_papers.json，生成完整 Markdown 报告并保存到 output_dir/report.md。
    报告内容包含：
      1. 统计数据表
      2. 关键词分布图（如 file 存在）
      3. LLM 简报
    返回 Markdown 文本内容。
    """
    stats = analyze_trends(scored_json_path)
    if not stats:
        return ""

    # 1. 生成统计文字部分
    report_lines = []
    report_lines.append(f"# 科研趋势周报 ({datetime.now().strftime('%Y-%m-%d')})\n")
    report_lines.append(f"- 总论文数: {stats['total_papers']}")
    report_lines.append(f"- 开源论文数: {stats['open_source_count']} ({stats['open_source_count']/stats['total_papers']:.2%})")
    report_lines.append(f"- 平均认可度分: {stats['avg_score']:.2f}\n")

    report_lines.append("## 关键词热度分布：")
    for kw, cnt in stats['keyword_counts'].items():
        report_lines.append(f"- {kw}: {cnt} ({cnt/stats['total_papers']:.2%})")
    report_lines.append("")

    # 2. 插入可视化图（如果存在 output/keyword_trend.png）
    fig_path = os.path.join(output_dir, "keyword_trend.png")
    if os.path.exists(fig_path):
        report_lines.append("![关键词热度分布](keyword_trend.png)\n")

    # 3. 调用 LLM 生成简报
    llm_text = generate_llm_summary(stats)
    report_lines.append("## LLM 智能简报：")
    report_lines.append(llm_text)

    report_text = "\n".join(report_lines)

    # 保存 Markdown 文件
    report_path = os.path.join(output_dir, "report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return report_text
