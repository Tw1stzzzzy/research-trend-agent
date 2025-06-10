from processors.llm_client import LLMClient

# 初始化LLM客户端
llm_client = LLMClient()

def generate_llm_summary(statistics: dict) -> str:
    """
    Input: statistics dictionary containing total_papers, open_source_count, avg_score, keyword_counts, etc.
    Output: LLM-generated 200-300 word research trend summary in English
    """
    # Build statistical summary text
    stat_lines = [
        f"- Total Papers: {statistics['total_papers']}",
        f"- Open Source Papers: {statistics['open_source_count']} ({statistics['open_source_count'] / statistics['total_papers']:.2%})",
        f"- Average Recognition Score: {statistics['avg_score']:.2f}"
    ]
    
    stat_lines.append("\n## Keyword Distribution:")
    # Sort keywords by count for better analysis
    sorted_keywords = sorted(statistics['keyword_counts'].items(), key=lambda x: x[1], reverse=True)
    for kw, cnt in sorted_keywords:
        if cnt > 0:  # Only include keywords with papers
            stat_lines.append(f"- {kw.title()}: {cnt} papers ({cnt / statistics['total_papers']:.1%})")

    stat_text = "\n".join(stat_lines)

    system_prompt = """
You are an AI research trend analyst. Based on the provided statistical data from top AI conferences (ICLR, NeurIPS, ICML, CVPR, ECCV, ACL), 
write a 200-300 word research trend summary covering:

- Current hottest research directions
- Most popular keywords and their significance
- Overall open source adoption rate and recognition patterns
- Notable emerging trends or breakthrough areas
- Recommendations for researchers and practitioners

Use clear, professional language suitable for academic reports and research lab meetings.
"""

    user_prompt = f"Here are the weekly statistics:\n\n{stat_text}\n\nPlease analyze these trends and provide insights."

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        summary = llm_client.generate_response(messages, temperature=0.3, max_tokens=400)
        return summary
        
    except Exception as e:
        # Fallback: provide basic statistical summary
        fallback_summary = f"""
**Research Activity Summary**

This report analyzed {statistics['total_papers']} papers from major AI conferences. 

**Open Source Landscape**: {statistics['open_source_count']} papers ({statistics['open_source_count'] / statistics['total_papers']:.1%}) have open source implementations, indicating {'strong' if statistics['open_source_count'] / statistics['total_papers'] > 0.5 else 'moderate' if statistics['open_source_count'] / statistics['total_papers'] > 0.3 else 'limited'} community engagement with reproducible research.

**Recognition Metrics**: The average recognition score is {statistics['avg_score']:.2f}, reflecting the overall impact and adoption of these research contributions.

**Research Focus**: The most active research areas based on keyword frequency are {', '.join([kw for kw, cnt in sorted_keywords[:3] if cnt > 0])}, suggesting these remain central themes in current AI research.

*Note: LLM analysis unavailable due to: {str(e)}*
"""
        return fallback_summary
