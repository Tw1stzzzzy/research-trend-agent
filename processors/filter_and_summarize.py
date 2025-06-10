import re
import yaml
from .llm_client import LLMClient

# 关键词列表，读取 configs/keywords.txt
with open("configs/keywords.txt", "r") as f:
    KEYWORDS = [line.strip().lower() for line in f if line.strip()]

# 初始化LLM客户端
llm_client = LLMClient()

def keyword_filter(title, abstract):
    """
    简单关键词过滤：title+abstract 中包含任意一个关键词即通过。
    """
    text = (title + " " + abstract).lower()
    for kw in KEYWORDS:
        if re.search(rf"\b{kw}\b", text):
            return True
    return False

def summarize_abstract(abstract):
    """
    调用LLM将长摘要精简成 2-3 句。
    """
    if not abstract:
        return ""

    messages = [
        {"role": "system", "content": "You are a research assistant. Summarize the paper abstract into 2-3 sentences, keeping only the task, method, and contributions."},
        {"role": "user", "content": abstract}
    ]
    try:
        return llm_client.generate_response(messages, temperature=0.3, max_tokens=200)
    except Exception as e:
        print(f"LLM summarization error: {e}")
        return abstract[:200] + "..."

def process_papers(papers):
    """
    对拉取回来的 papers 列表做筛选与摘要简化：
    输入 papers: 列表，每项为 {'title', 'authors', 'abstract', 'pdf_url', 'venue', 'decision'}
    返回 filtered: 列表，每项为 {'title', 'authors', 'summary', 'pdf_url', 'venue'}
    """
    results = []
    for paper in papers:
        title = paper.get('title', "")
        abstract = paper.get('abstract', "")
        if keyword_filter(title, abstract):
            summary = summarize_abstract(abstract)
            results.append({
                'title': title,
                'authors': paper.get('authors', []),
                'summary': summary,
                'pdf_url': paper.get('pdf_url', ""),
                'venue': paper.get('venue', ""),
                'decision': paper.get('decision', None)
            })
    return results
