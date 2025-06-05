import requests
from bs4 import BeautifulSoup

class ACLFetcher:
    """
    爬取 ACL 系列（如 ACL, NAACL, EMNLP 等）会议的论文列表。
    接口 URL 形如：https://aclanthology.org/events/acl/2024/
    """

    def __init__(self, year='2024', conference='ACL'):
        self.year = year
        self.conference = conference.lower()  # 小写形式

    def fetch_papers(self):
        url = f'https://aclanthology.org/events/{self.conference}/{self.year}/'
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        papers = []
        for item in soup.find_all('h5', class_='align-middle'):
            title = item.text.strip()
            papers.append({
                'title': title,
                'authors': [],     
                'abstract': '',    
                'pdf_url': '',     
                'venue': self.conference.upper(),
                'decision': None
            })
        return papers
