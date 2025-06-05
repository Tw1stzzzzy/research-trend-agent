import openai
import yaml

# 从配置文件中读取 OpenAI API Key
with open("configs/config.yaml", "r") as f:
    config = yaml.safe_load(f)
OPENAI_API_KEY = config['openai']['api_key']
openai.api_key = OPENAI_API_KEY

def generate_llm_summary(statistics: dict) -> str:
    """
    输入：statistics 字典，包含 total_papers, open_source_count, avg_score, keyword_counts 等
    输出：GPT-4o 生成的 200-300 字科研简报
    """
    # 构造统计文字
    stat_lines = [
        f"- 总论文数: {statistics['total_papers']}",
        f"- 开源论文数: {statistics['open_source_count']} ({statistics['open_source_count'] / statistics['total_papers']:.2%})",
        f"- 平均认可度分: {statistics['avg_score']:.2f}"
    ]
    stat_lines.append("## 关键词分布：")
    for kw, cnt in statistics['keyword_counts'].items():
        stat_lines.append(f"- {kw}: {cnt} ({cnt / statistics['total_papers']:.2%})")

    stat_text = "\n".join(stat_lines)

    system_prompt = """
你是一名科研趋势分析师。请根据我提供的本周机器学习六大顶会论文统计数据，
写一份200-300字的科研趋势简报，总结以下要点：
- 当前最热点的方向
- 热度占比最高的关键词
- 开源率与认可度总体情况
- 是否有值得重点关注的新模型或新论文
请用简明扼要的语言，适合给实验室组会报告使用。
"""
    user_prompt = f"本周统计数据如下：\n{stat_text}"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"LLM 生成失败，以下为原始统计算据：\n{stat_text}"
