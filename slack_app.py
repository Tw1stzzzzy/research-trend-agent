# ── slack_app.py ──

import os
import logging
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

# --------------- 1. 读取 Slack App 配置 ---------------
# 从环境变量中获取 Bot Token 和 Signing Secret
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")

if not SLACK_BOT_TOKEN or not SLACK_SIGNING_SECRET:
    raise ValueError("请先在环境变量中设置 SLACK_BOT_TOKEN 和 SLACK_SIGNING_SECRET")

# --------------- 2. 初始化 Bolt 应用 ---------------
app = App(token=SLACK_BOT_TOKEN, signing_secret=SLACK_SIGNING_SECRET)
flask_app = Flask(__name__)
handler = SlackRequestHandler(app)

# --------------- 3. 日志设置（可选） ---------------
logging.basicConfig(level=logging.INFO)

# --------------- 4. 解析用户指令的小函数 ---------------
def parse_search_command(text: str):
    """
    解析 @Bot search <keyword> <year> 的格式
    例如："<@U12345> search autoregressive 2025"
    返回字典：{"action": "search", "keyword": "autoregressive", "year": "2025"}
    如格式不对，则返回 None。
    """
    tokens = text.split()
    if len(tokens) < 2:
        return None

    action = tokens[1].lower()
    if action != "search":
        return None

    if len(tokens) >= 4:
        keyword = tokens[2]
        year = tokens[3]
    elif len(tokens) == 3:
        keyword = tokens[2]
        year = ""
    else:
        return None

    return {"action": action, "keyword": keyword, "year": year}

# --------------- 5. 事件监听：当 Bot 被 @ 时触发 ---------------
@app.event("app_mention")
def handle_app_mention_events(body, say):
    """
    当有人在频道里 @Bot 时，会调用此函数处理事件。
    body: 包含 Slack 传来的事件原始 JSON。
    say: 用于在同一频道回复消息的函数。
    """
    event = body.get("event", {})
    user = event.get("user")        # 触发该事件的用户 ID
    text = event.get("text", "")    # 完整的消息文本
    channel = event.get("channel")  # 该消息所在的频道 ID

    # 解析指令
    cmd = parse_search_command(text)
    if not cmd:
        say(
            text="❗️ 格式不对，请使用 `@Bot search <关键词> <年份>`，"
                 "例如 `@Bot search autoregressive 2025`。",
            channel=channel
        )
        return

    keyword = cmd["keyword"]
    year = cmd["year"]

    # 先给用户一个“正在处理”的提示
    say(text=f":hourglass: 开始为你搜索 `{keyword}` 在 `{year}` 年份的论文…", channel=channel)

    try:
        # --------------- 6. 调用 Agent 核心逻辑进行检索 ---------------
        # 这里示例演示拉取 + 关键词筛选 + 简报的基本流程

        from fetchers.openreview_fetcher import OpenReviewFetcher
        from fetchers.acl_fetcher import ACLFetcher
        from fetchers.cvf_fetcher import CVFFetcher

        from processors.filter_and_summarize import process_papers
        from processors.trend_analyzer import analyze_trends
        from processors.llm_summary import generate_llm_summary

        # ① 拉取指定年份的 ICLR/NeurIPS/ICML 论文
        since_date = f"{year}-01-01"
        openreview_confs = [
            f"ICLR.cc/{year}/Conference",
            f"NeurIPS.cc/{year}/Conference",
            f"ICML.cc/{year}/Conference"
        ]
        all_papers = []
        for conf in openreview_confs:
            fetcher = OpenReviewFetcher(conf)
            papers = fetcher.fetch_papers(since_date)
            all_papers.extend(papers)

        # ② 拉取 CVF（CVPR 与 ECCV）论文
        cvf_confs = [
            (f"https://openaccess.thecvf.com/CVPR{year}", "CVPR"),
            (f"https://openaccess.thecvf.com/ECCV{year}", "ECCV")
        ]
        for url, venue in cvf_confs:
            fetcher = CVFFetcher(url, venue)
            papers = fetcher.fetch_papers()
            all_papers.extend(papers)

        # ③ 拉取 ACL 论文
        acl_fetcher = ACLFetcher(year=year, conference="ACL")
        acl_papers = acl_fetcher.fetch_papers()
        all_papers.extend(acl_papers)

        # ④ 关键词筛选 + 摘要简化
        filtered = process_papers(all_papers)

        # ⑤ 向用户展示前 5 篇论文的标题与摘要
        preview_lines = []
        preview_lines.append(
            f"*关键词*：{keyword}，*年份*：{year}，共计筛选到 {len(filtered)} 篇论文。以下是前 5 篇："
        )
        for i, paper in enumerate(filtered[:5]):
            title = paper["title"]
            summary = paper["summary"]
            preview_lines.append(f"{i+1}. *{title}*\n> {summary}")

        preview_text = "\n".join(preview_lines)
        say(text=preview_text, channel=channel)

        # ⑥ 将筛选结果保存到临时文件，再做趋势统计与 LLM 简报
        import json, os
        os.makedirs("output", exist_ok=True)
        with open("output/filter_temp.json", "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2)

        stats = analyze_trends("output/filter_temp.json")
        llm_text = generate_llm_summary(stats)

        # ⑦ 将 LLM 生成的趋势简报发送给用户
        say(text=f"*趋势简报：*\n{llm_text}", channel=channel)

    except Exception as e:
        logging.error(f"处理指令时报错：{e}", exc_info=True)
        say(text="❗️ 内部运行出错，请稍后再试或联系管理员。", channel=channel)

# --------------- 7. Flask 路由：Slack 事件打平到 Bolt ---------------
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

# --------------- 8. 启动服务 ---------------
if __name__ == "__main__":
    # 在服务器上运行时，监听 0.0.0.0:3000（或按需修改端口）
    flask_app.run(host="0.0.0.0", port=3000)
