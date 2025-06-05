import re
import openai
import yaml

# 从配置文件中读取 OpenAI API Key
with open("configs/config.yaml", "r") as f:
    config = yaml.safe_load(f)
OPENAI_API_KEY = config['openai']['api_key']

# 关键词列表，读取 configs/keywords.txt
with open("configs/keywords.txt", "r") as f:
    KEYWORDS = [line.strip().lower() for line in f if line.strip()]

openai.api_key = OPENAI_API_KEY

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
    调用 GPT-4o 将长摘要精简成 2-3 句。
    """
    if not abstract:
        return ""

    prompt = [
        {"role": "system", "content": "你是科研助手，将论文摘要精炼成 2-3 句，只保留任务、方法和贡献。"},
        {"role": "user", "content": abstract}
    ]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=prompt,
            temperature=0.3
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
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
