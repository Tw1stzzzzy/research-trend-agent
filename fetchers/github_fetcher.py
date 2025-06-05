import requests
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
