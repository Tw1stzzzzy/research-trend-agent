import requests
from bs4 import BeautifulSoup

class CVFFetcher:
    """
    爬取 CVF 会议（CVPR, ICCV, ECCV）公开论文列表。
    以 CVPR2024 为例，URL: https://openaccess.thecvf.com/CVPR2024
    """

    def __init__(self, conference_url, venue_name):
        """
        conference_url: 例如 "https://openaccess.thecvf.com/CVPR2024"
        venue_name: 例如 "CVPR"
        """
        self.url = conference_url
        self.venue = venue_name

    def fetch_papers(self):
        response = requests.get(self.url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        papers = []
        for item in soup.find_all('dt', class_='ptitle'):
            title = item.text.strip()
            papers.append({
                'title': title,
                'authors': [],
                'abstract': '',
                'pdf_url': '',
                'venue': self.venue,
                'decision': None
            })
        return papers
