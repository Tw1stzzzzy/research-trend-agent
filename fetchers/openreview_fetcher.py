import openreview
import datetime
import time

class OpenReviewFetcher:
    """
    利用 OpenReview API 拉取 ICLR、NeurIPS、ICML 等会议的已接收论文信息。
    """

    def __init__(self, conference_id):
        # conference_id 示例： "ICLR.cc/2024/Conference"
        self.client = openreview.Client(baseurl='https://api.openreview.net')
        self.conf_id = conference_id

    def fetch_papers(self, since_date, max_papers=100):
        """
        拉取自 since_date（YYYY-MM-DD）之后的已接收论文。
        max_papers: 限制处理的最大论文数量，避免API超限
        返回列表，每篇论文包含：title, authors, abstract, pdf_url, tcdate(毫秒), decision
        """
        print(f"🔍 Fetching papers from {self.conf_id}...")
        
        # 首先尝试获取Camera Ready论文（这些是已确认接收的）
        camera_ready_papers = self.fetch_camera_ready_papers(since_date)
        if camera_ready_papers:
            print(f"✅ Found {len(camera_ready_papers)} Camera Ready papers (confirmed accepted)")
            return camera_ready_papers
        
        # 如果没有Camera Ready，则查询决策信息
        print("📝 No Camera Ready papers found, checking submission decisions...")
        return self.fetch_papers_with_decisions(since_date, max_papers)

    def fetch_camera_ready_papers(self, since_date):
        """
        尝试直接获取Camera Ready论文（已接收）
        """
        since_ts = int(datetime.datetime.strptime(since_date, '%Y-%m-%d').timestamp() * 1000)
        
        try:
            camera_ready_invitation = f'{self.conf_id}/-/Camera_Ready_Submission'
            camera_ready_papers = self.client.get_notes(invitation=camera_ready_invitation)
            
            accepted_papers = []
            for note in camera_ready_papers:
                if note.tcdate >= since_ts:
                    accepted_papers.append({
                        'title': note.content.get('title', ''),
                        'authors': note.content.get('authors', []),
                        'abstract': note.content.get('abstract', ''),
                        'pdf_url': note.content.get('pdf', ''),
                        'created': note.tcdate,
                        'venue': self.conf_id.split('/')[0],
                        'decision': 'Camera Ready (Accepted)'
                    })
            
            return accepted_papers
                
        except Exception as e:
            print(f"⚠️  Unable to fetch Camera Ready papers: {e}")
            return []

    def fetch_papers_with_decisions(self, since_date, max_papers=100):
        """
        通过查询决策信息获取已接收论文（备选方案）
        """
        since_ts = int(datetime.datetime.strptime(since_date, '%Y-%m-%d').timestamp() * 1000)

        # 获取所有提交，但限制数量
        try:
            submissions = self.client.get_notes(
                invitation=f'{self.conf_id}/-/Blind_Submission',
                limit=max_papers
            )
        except Exception as e:
            print(f"❌ Error fetching submissions: {e}")
            return []
        
        print(f"📋 Processing {len(submissions)} submissions (limited to {max_papers})...")
        
        accepted_papers = []
        processed_count = 0
        
        for i, note in enumerate(submissions):
            # 只处理指定日期之后的论文
            if note.tcdate < since_ts:
                continue
                
            processed_count += 1
            
            # 获取该论文的决策信息（添加重试和延迟）
            decision_info = self._get_paper_decision_safe(note.id)
            
            # 只保留已接收的论文
            if decision_info and self._is_accepted(decision_info):
                accepted_papers.append({
                    'title': note.content.get('title', ''),
                    'authors': note.content.get('authors', []),
                    'abstract': note.content.get('abstract', ''),
                    'pdf_url': note.content.get('pdf', ''),
                    'created': note.tcdate,
                    'venue': self.conf_id.split('/')[0],
                    'decision': decision_info
                })
            
            # 进度提示和API限制保护
            if (i + 1) % 20 == 0:
                print(f"  ⏳ Processed {i + 1}/{len(submissions)}, found {len(accepted_papers)} accepted papers")
                time.sleep(2)  # 每20个请求后暂停2秒
        
        print(f"✅ Completed! Found {len(accepted_papers)} accepted papers from {processed_count} processed submissions")
        return accepted_papers

    def _get_paper_decision_safe(self, paper_id, max_retries=2):
        """
        安全获取单篇论文的决策信息，带重试和延迟
        """
        for attempt in range(max_retries):
            try:
                # 添加小延迟避免过于频繁的请求
                time.sleep(0.5)
                
                # 尝试多种可能的decision invitation格式
                decision_invitations = [
                    f'{self.conf_id}/-/Decision',
                    f'{self.conf_id}/-/Meta_Review'
                ]
                
                for invitation in decision_invitations:
                    try:
                        decisions = self.client.get_notes(
                            forum=paper_id, 
                            invitation=invitation,
                            limit=1
                        )
                        if decisions:
                            decision = decisions[0].content.get('decision', '').lower()
                            recommendation = decisions[0].content.get('recommendation', '').lower()
                            
                            # 返回找到的决策信息
                            result = decision or recommendation
                            if result:
                                return result
                                
                    except Exception as e:
                        if attempt == max_retries - 1:  # 最后一次尝试才打印错误
                            print(f"⚠️  Error checking {invitation}: {str(e)[:50]}...")
                        continue
                        
                return None
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️  Retry {attempt + 1}/{max_retries} for paper {paper_id}")
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    print(f"❌ Failed to get decision for paper {paper_id}: {e}")
                    return None

    def _is_accepted(self, decision):
        """
        判断论文是否被接收
        """
        if not decision:
            return False
            
        decision = decision.lower()
        
        # 接收的关键词
        accept_keywords = [
            'accept', 'accepted', 
            'oral', 'poster', 'spotlight',
            'workshop', 'short paper',
            'camera ready', 'camera-ready'
        ]
        
        # 拒绝的关键词
        reject_keywords = [
            'reject', 'rejected', 
            'decline', 'declined',
            'withdraw', 'withdrawn'
        ]
        
        # 先检查是否明确拒绝
        for keyword in reject_keywords:
            if keyword in decision:
                return False
        
        # 再检查是否接收
        for keyword in accept_keywords:
            if keyword in decision:
                return True
                
        return False
