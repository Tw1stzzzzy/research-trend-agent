import requests
import re
import time
from datetime import datetime

class GitHubFetcher:
    """
    利用 GitHub API 查询某个 Repo 的 stars 数量与开源时长（天）。
    """

    def __init__(self, github_token):
        self.headers = {"Authorization": f"token {github_token}"}

    def get_repo_stats(self, repo_url):
        """
        repo_url 形如 "https://github.com/owner/repo"
        返回字典：{'stars': int, 'forks': int, 'days_since_created': int}
        若无法获取则返回 None
        """
        if not repo_url or 'github.com' not in repo_url:
            return None

        owner_repo = repo_url.replace("https://github.com/", "").strip("/")
        api_url = f"https://api.github.com/repos/{owner_repo}"
        response = requests.get(api_url, headers=self.headers)
        if response.status_code != 200:
            return None

        data = response.json()
        created_at = data.get('created_at')
        stars = data.get('stargazers_count', 0)
        forks = data.get('forks_count', 0)

        created_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        days_since_created = (datetime.now() - created_date).days

        return {
            'stars': stars,
            'forks': forks,
            'days_since_created': days_since_created
        }
    
    def extract_keywords(self, title):
        """
        从论文标题中提取关键词，用于GitHub搜索
        """
        # 移除常见停用词
        stopwords = {'via', 'for', 'with', 'on', 'in', 'the', 'a', 'an', 'and', 'or', 'but', 'of', 'to', 'from', 'by', 'at'}
        
        # 提取可能的模型名称（大写字母开头的连续词）
        model_names = re.findall(r'[A-Z][a-zA-Z]*(?:-[A-Z][a-zA-Z]*)*', title)
        
        # 提取重要的技术词汇
        words = re.findall(r'\b[A-Za-z]+(?:-[A-Za-z]+)*\b', title)
        keywords = [word for word in words if word.lower() not in stopwords and len(word) > 2]
        
        # 优先返回模型名称和重要关键词
        all_keywords = model_names + keywords
        # 去重并保持顺序
        unique_keywords = []
        for kw in all_keywords:
            if kw not in unique_keywords:
                unique_keywords.append(kw)
        
        return unique_keywords[:5]  # 返回前5个最重要的关键词
    
    def search_paper_repository(self, paper_title):
        """
        基于论文标题搜索GitHub仓库
        返回最匹配的仓库URL和统计信息，如果没找到返回None
        """
        print(f"    🔍 Searching GitHub for: {paper_title[:50]}...")
        
        keywords = self.extract_keywords(paper_title)
        if not keywords:
            return None
        
        # 构造搜索查询：优先用前2个关键词
        primary_keywords = keywords[:2]
        query = f"{' '.join(primary_keywords)} language:python"
        
        # 如果第一个关键词看起来像模型名（包含大写和连字符），优先搜索
        if re.match(r'^[A-Z].*-.*[A-Z]', keywords[0]):
            query = f'"{keywords[0]}" language:python'
        
        return self._search_github_repos(query, paper_title, keywords)
    
    def _search_github_repos(self, query, paper_title, keywords):
        """
        执行GitHub搜索并返回最佳匹配
        """
        api_url = "https://api.github.com/search/repositories"
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': 10  # 只获取前10个结果
        }
        
        try:
            response = requests.get(api_url, headers=self.headers, params=params)
            
            if response.status_code == 403:  # Rate limit
                print(f"    ⚠️  GitHub API rate limit, waiting...")
                time.sleep(60)  # 等待1分钟
                response = requests.get(api_url, headers=self.headers, params=params)
            
            if response.status_code != 200:
                print(f"    ❌ GitHub search failed: {response.status_code}")
                return None
            
            data = response.json()
            if not data.get('items'):
                print(f"    ❌ No repositories found")
                return None
            
            # 对结果进行相关性排序
            best_repo = self._rank_repositories(data['items'], paper_title, keywords)
            
            if best_repo:
                repo_url = best_repo['html_url']
                stats = self.get_repo_stats(repo_url)
                if stats:
                    print(f"    ✅ Found: {best_repo['name']} ({stats['stars']} ⭐)")
                    return {
                        'repo_url': repo_url,
                        'stats': stats
                    }
        
        except Exception as e:
            print(f"    ❌ GitHub search error: {e}")
        
        return None
    
    def _rank_repositories(self, repos, paper_title, keywords):
        """
        对搜索结果按相关性排序，返回最佳匹配
        """
        scored_repos = []
        title_lower = paper_title.lower()
        keywords_lower = [kw.lower() for kw in keywords]
        
        for repo in repos:
            score = 0
            repo_name = repo.get('name', '').lower()
            repo_description = repo.get('description', '') or ''
            repo_description = repo_description.lower()
            
            # 1. 仓库名匹配 (权重最高)
            for kw in keywords_lower:
                if kw in repo_name:
                    score += 5
                    
            # 2. 描述匹配
            for kw in keywords_lower:
                if kw in repo_description:
                    score += 2
            
            # 3. 第一个关键词的精确匹配加分
            if keywords_lower and keywords_lower[0] in repo_name:
                score += 3
                
            # 4. Stars数量加分（归一化）
            stars = repo.get('stargazers_count', 0)
            if stars > 100:
                score += min(stars / 100, 5)  # 最多加5分
            elif stars > 10:
                score += 1
            
            # 5. 最近更新加分
            updated_at = repo.get('updated_at', '')
            if updated_at:
                try:
                    updated_date = datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%SZ")
                    days_since_update = (datetime.now() - updated_date).days
                    if days_since_update < 365:  # 一年内更新过
                        score += 1
                except:
                    pass
            
            scored_repos.append((score, repo))
        
        # 按分数排序，返回最高分的仓库
        if scored_repos:
            scored_repos.sort(key=lambda x: x[0], reverse=True)
            best_score, best_repo = scored_repos[0]
            
            # 如果最高分太低，说明匹配度不够
            if best_score < 3:
                return None
                
            return best_repo
        
        return None
