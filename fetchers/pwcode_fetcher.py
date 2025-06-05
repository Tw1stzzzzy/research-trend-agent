import requests

class PWCodeFetcher:
    """
    利用 PapersWithCode API 查询论文是否被收录，及其对应的 GitHub Repo 链接。
    """

    def __init__(self, pwc_api_key):
        self.api_key = pwc_api_key
        self.headers = {"Authorization": f"Token {self.api_key}"}

    def search_paper(self, title):
        """
        在 PapersWithCode 上按 title 搜索，取第一个最匹配结果。
        返回字典：{'repo_url': ..., 'sota': bool}
        若未找到则返回 None
        """
        url = f"https://paperswithcode.com/api/v1/papers/search/?q={title}"
        response = requests.get(url, headers=self.headers)
        if response.status_code != 200:
            return None

        results = response.json().get('results', [])
        if not results:
            return None

        paper = results[0]
        repo_url = paper['repository']['url'] if paper.get('repository') else None
        return {
            'repo_url': repo_url,
            'sota': paper.get('is_code_open', False)
        }
