import openreview
import datetime

class OpenReviewFetcher:
    """
    利用 OpenReview API 拉取 ICLR、NeurIPS、ICML 等会议的论文信息。
    """

    def __init__(self, conference_id):
        # conference_id 示例： "ICLR.cc/2024/Conference"
        self.client = openreview.Client(baseurl='https://api.openreview.net')
        self.conf_id = conference_id

    def fetch_papers(self, since_date):
        """
        拉取自 since_date（YYYY-MM-DD）之后的所有论文。
        返回列表，每篇论文包含：title, authors, abstract, pdf_url, tcdate(毫秒), decision_labels
        """
        # 把 since_date 转换为 Unix 毫秒
        since_ts = int(datetime.datetime.strptime(since_date, '%Y-%m-%d').timestamp() * 1000)

        submissions = self.client.get_notes(invitation=f'{self.conf_id}/-/Blind_Submission')
        papers = []
        for note in submissions:
            # tcdate 是提交时间的 Unix 毫秒时间戳
            if note.tcdate >= since_ts:
                papers.append({
                    'title': note.content.get('title', ''),
                    'authors': note.content.get('authors', []),
                    'abstract': note.content.get('abstract', ''),
                    'pdf_url': note.content.get('pdf', ''),
                    'created': note.tcdate,
                    'venue': self.conf_id.split('/')[0],  # 比如 "ICLR.cc"
                    'decision': None  # 后面可扩展：通过另一个 invitation 拉 Oral/Poster
                })
        return papers
