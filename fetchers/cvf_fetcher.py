import requests
from bs4 import BeautifulSoup
import time

class CVFFetcher:
    """
    爬取 CVF 会议（CVPR, ICCV, ECCV）公开论文列表。
    以 CVPR2023 为例，URL: https://openaccess.thecvf.com/CVPR2023
    """

    def __init__(self, conference_url, venue_name):
        """
        conference_url: 例如 "https://openaccess.thecvf.com/CVPR2023"
        venue_name: 例如 "CVPR"
        """
        self.base_url = conference_url
        self.venue = venue_name

    def fetch_papers(self, max_papers=200):
        """
        获取CVF会议的已发表论文
        max_papers: 限制获取的论文数量，避免处理时间过长
        """
        print(f"🔍 Fetching papers from {self.venue} ({self.base_url})...")
        
        # 构建获取所有论文的URL
        all_papers_url = f"{self.base_url}?day=all"
        
        try:
            response = requests.get(all_papers_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 查找论文标题（在dt标签中）
            title_tags = soup.find_all('dt')
            print(f"📋 Found {len(title_tags)} papers, processing up to {max_papers}...")

            papers = []
            processed_count = 0
            
            for i, dt_tag in enumerate(title_tags):
                if processed_count >= max_papers:
                    print(f"⏹️  Reached limit of {max_papers} papers")
                    break
                
                title = dt_tag.text.strip()
                if not title:
                    continue
                
                # 查找对应的论文详情（通常在下一个dd标签中）
                dd_tag = dt_tag.find_next_sibling('dd')
                authors = []
                abstract = ""
                pdf_url = ""
                
                if dd_tag:
                    # 提取作者信息
                    author_links = dd_tag.find_all('a')
                    authors = [a.text.strip() for a in author_links if a.text.strip() and not a.text.strip().startswith('http')]
                    
                    # 查找PDF链接
                    pdf_link = dd_tag.find('a', href=True)
                    if pdf_link and pdf_link.get('href'):
                        pdf_url = pdf_link.get('href')
                        # 如果是相对路径，转换为绝对路径
                        if pdf_url.startswith('/'):
                            pdf_url = f"https://openaccess.thecvf.com{pdf_url}"

                paper_data = {
                    'title': title,
                    'authors': authors[:5],  # 限制作者数量
                    'abstract': abstract,  # CVF页面通常不包含摘要
                    'pdf_url': pdf_url,
                    'venue': self.venue,
                    'decision': 'Published (CVF Open Access)'
                }
                
                papers.append(paper_data)
                processed_count += 1
                
                # 进度提示
                if (processed_count) % 50 == 0:
                    print(f"  ⏳ Processed {processed_count} papers...")
                    time.sleep(0.1)  # 小延迟避免过快处理

            print(f"✅ Successfully fetched {len(papers)} papers from {self.venue}")
            return papers

        except requests.RequestException as e:
            print(f"❌ Error fetching from {all_papers_url}: {e}")
            return []
        except Exception as e:
            print(f"❌ Error parsing CVF papers: {e}")
            return []

    def get_paper_abstract(self, paper_url):
        """
        获取单篇论文的摘要（如果有详情页）
        """
        try:
            response = requests.get(paper_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找摘要
            abstract_tag = soup.find('div', {'id': 'abstract'}) or soup.find('div', class_='abstract')
            if abstract_tag:
                return abstract_tag.get_text().strip()
            
            return ""
        except Exception:
            return ""
