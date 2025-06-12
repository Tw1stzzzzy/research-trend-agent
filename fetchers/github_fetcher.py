import requests
import re
import time
import yaml
from datetime import datetime

class GitHubFetcher:
    """
    利用 GitHub API 查询某个 Repo 的 stars 数量与开源时长（天）。
    """

    def __init__(self, github_token):
        self.headers = {"Authorization": f"token {github_token}"}
        # 从配置文件加载黑名单
        self.repo_blacklist = {}
        try:
            with open("configs/config.yaml", "r") as f:
                config = yaml.safe_load(f)
                self.repo_blacklist = config.get('repo_blacklist', {})
                if self.repo_blacklist:
                    print(f"📋 Loaded repository blacklist with {len(self.repo_blacklist)} entries")
        except Exception as e:
            print(f"⚠️  Warning: Could not load blacklist from config: {e}")

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
        改进版：更精确地提取模型名称和技术词汇
        """
        # 移除常见停用词
        stopwords = {'via', 'for', 'with', 'on', 'in', 'the', 'a', 'an', 'and', 'or', 'but', 'of', 'to', 'from', 'by', 'at', 'using', 'towards', 'how', 'your'}
        
        # 预处理标题，处理特殊字符
        cleaned_title = re.sub(r'[^\w\s\-:]', ' ', title)
        
        # 1. 提取可能的模型/方法名称（通常是冒号前的部分）
        main_concept = cleaned_title.split(':')[0].strip() if ':' in cleaned_title else ''
        model_words = []
        if main_concept:
            # 提取模型名中的单词（通常是大写字母开头或全大写）
            model_words = re.findall(r'\b[A-Z][a-zA-Z0-9]*(?:-[A-Za-z0-9]+)*\b|\b[A-Z]{2,}\b', main_concept)
        
        # 2. 提取特殊格式的模型名（如ViT, GPT, BERT等全大写缩写）
        special_models = re.findall(r'\b[A-Z]{2,}(?:-[A-Z]+)*\b', title)
        
        # 3. 识别混合大小写的模型名（如BiGAN, DeepDream等）
        mixed_case = re.findall(r'\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b', title)
        
        # 4. 提取包含数字和连字符的技术词汇（如3D、X-Ray等）
        tech_terms = re.findall(r'\b\d+[A-Za-z]+\b|\b[A-Za-z]+\d+[A-Za-z]*\b|\b[A-Za-z]+[-][A-Za-z]+\b', title)
        
        # 5. 提取重要的领域词汇（通常是名词短语）
        words = re.findall(r'\b[A-Za-z]+(?:-[A-Za-z]+)*\b', title)
        keywords = [word for word in words if word.lower() not in stopwords and len(word) > 2]
        
        # 6. 提取完整的短语组合（通常更具代表性）
        if ':' in title:
            main_part = title.split(':')[0].strip()
            if 2 < len(main_part.split()) < 5:  # 合理长度的短语
                if all(w.lower() not in stopwords for w in main_part.split()):
                    model_words.append(main_part)
        
        # 合并所有关键词，优先级：模型名 > 特殊模型 > 混合大小写 > 技术词汇 > 领域词汇
        all_keywords = model_words + special_models + mixed_case + tech_terms + keywords
        
        # 去重并保持顺序
        unique_keywords = []
        seen = set()
        for kw in all_keywords:
            if kw.lower() not in seen:
                unique_keywords.append(kw)
                seen.add(kw.lower())
        
        # 对关键词进行额外过滤，排除常见的误导词
        filtered_keywords = [k for k in unique_keywords if k.lower() not in {
            'how', 'why', 'what', 'when', 'where', 'which', 'who', 'whose', 'whom', 
            'your', 'our', 'their', 'model', 'models', 'method', 'methods', 
            'approach', 'approaches', 'robust', 'novel', 'new', 'paper'
        }]
        
        # 如果过滤后没有关键词，返回原始关键词（避免过度过滤）
        if not filtered_keywords and unique_keywords:
            return unique_keywords[:6]
            
        return filtered_keywords[:6]  # 返回前6个最重要的关键词
    
    def search_paper_repository(self, paper_title):
        """
        基于论文标题搜索GitHub仓库
        返回最匹配的仓库URL和统计信息，如果没找到返回None
        改进版：使用多重搜索策略和严格验证
        """
        print(f"    🔍 Searching GitHub for: {paper_title[:50]}...")
        
        # 检查当前论文是否在黑名单中
        self._paper_specific_blacklist = []
        for blacklist_title, blacklist_repos in self.repo_blacklist.items():
            if blacklist_title in paper_title:
                print(f"    ⚠️  Special case: '{blacklist_title}' has known bad matches")
                # 在验证时会过滤这些仓库
                self._paper_specific_blacklist = blacklist_repos
                break
        
        # 提取关键词，去除常见问题词
        keywords = self.extract_keywords(paper_title)
        if not keywords:
            print(f"    ❌ No valid keywords extracted")
            return None
        
        # 过滤掉问题性关键词（too general or misleading）
        keywords = [k for k in keywords if k.lower() not in {'how', 'why', 'what', 'when', 'where', 'which', 'who', 'whose', 'whom', 'your', 'our', 'their', 'model', 'models', 'method', 'methods', 'approach', 'approaches'}]
        
        if not keywords:
            print(f"    ❌ No specific keywords available after filtering")
            return None
            
        print(f"    🔑 Keywords: {keywords[:3]}")
        
        # 策略1: 尝试精确的模型名搜索 (使用引号包围完整的模型名)
        if keywords and len(keywords[0]) > 2:
            if re.match(r'^[A-Z]', keywords[0]) or '-' in keywords[0]:  # 只有模型名才用精确匹配
                result = self._search_with_exact_match(keywords[0], paper_title, keywords)
                if result:
                    return result
        
        # 策略2: 组合前两个关键词搜索 + 具体化
        if len(keywords) >= 2:
            # 添加特定关键词，提高搜索精确度
            domain_keywords = ['paper', 'implementation', 'official']
            
            # 尝试包含特定关键词的搜索
            for domain_keyword in domain_keywords:
                if len(keywords) >= 2:
                    result = self._search_with_specific_context(keywords[:2], domain_keyword, paper_title, keywords)
                    if result:
                        return result
            
            # 常规多关键词搜索
            result = self._search_with_multiple_keywords(keywords[:2], paper_title, keywords)
            if result:
                return result
        
        # 策略3: 单个最重要关键词搜索 + 具体化
        domain_keywords = ['paper', 'implementation', 'official', 'code']
        for domain_keyword in domain_keywords:
            result = self._search_with_specific_context([keywords[0]], domain_keyword, paper_title, keywords)
            if result:
                return result
        
        # 策略4: 最后的单关键词搜索
        result = self._search_with_single_keyword(keywords[0], paper_title, keywords)
        if result:
            return result
        
        print(f"    ❌ No matching repository found with strict criteria")
        return None
    
    def _search_with_exact_match(self, keyword, paper_title, all_keywords):
        """使用精确匹配搜索策略"""
        query = f'"{keyword}" language:python'
        print(f"    🎯 Exact match search: {query}")
        return self._search_github_repos(query, paper_title, all_keywords, strategy="exact")
    
    def _search_with_multiple_keywords(self, keywords, paper_title, all_keywords):
        """使用多关键词搜索策略"""
        query = f"{' '.join(keywords)} language:python"
        print(f"    🔍 Multi-keyword search: {query}")
        return self._search_github_repos(query, paper_title, all_keywords, strategy="multi")
    
    def _search_with_single_keyword(self, keyword, paper_title, all_keywords):
        """使用单关键词搜索策略"""
        query = f"{keyword} language:python"
        print(f"    🔎 Single keyword search: {query}")
        return self._search_github_repos(query, paper_title, all_keywords, strategy="single")
    
    def _search_with_specific_context(self, keywords, context_keyword, paper_title, all_keywords):
        """使用特定上下文的搜索策略"""
        query = f"{' '.join(keywords)} {context_keyword} language:python"
        print(f"    🔬 Contextual search: {query}")
        return self._search_github_repos(query, paper_title, all_keywords, strategy="context")
    
    def _search_github_repos(self, query, paper_title, keywords, strategy="general"):
        """
        执行GitHub搜索并返回最佳匹配
        """
        api_url = "https://api.github.com/search/repositories"
        params = {
            'q': query,
            'sort': 'stars',
            'order': 'desc',
            'per_page': 15  # 增加搜索结果数量
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
            best_repo = self._rank_repositories(data['items'], paper_title, keywords, strategy)
            
            if best_repo:
                repo_url = best_repo['html_url']
                
                # 额外验证：检查仓库内容是否真的与论文相关
                if self._verify_repository_relevance(repo_url, paper_title, keywords):
                    stats = self.get_repo_stats(repo_url)
                    if stats:
                        print(f"    ✅ Found: {best_repo['name']} ({stats['stars']} ⭐)")
                        return {
                            'repo_url': repo_url,
                            'stats': stats
                        }
                else:
                    print(f"    ❌ Repository verification failed: not relevant to paper")
            
            return None
        
        except Exception as e:
            print(f"    ❌ GitHub search error: {e}")
        
        return None
    
    def _verify_repository_relevance(self, repo_url, paper_title, keywords):
        """
        验证仓库与论文的相关性
        检查README内容、仓库描述等
        """
        try:
            # 获取仓库信息
            owner_repo = repo_url.replace("https://github.com/", "").strip("/")
            api_url = f"https://api.github.com/repos/{owner_repo}"
            response = requests.get(api_url, headers=self.headers)
            
            if response.status_code != 200:
                return True  # 如果无法获取信息，不拒绝
            
            repo_data = response.json()
            repo_name = repo_data.get('name', '').lower()
            
            # 检查是否在当前论文的特定黑名单中
            if hasattr(self, '_paper_specific_blacklist') and self._paper_specific_blacklist:
                if repo_name in [r.lower() for r in self._paper_specific_blacklist]:
                    print(f"    ⚠️  Repository {repo_name} is blacklisted for this paper")
                    return False
            
            description = repo_data.get('description', '') or ''
            
            # 特别过滤掉一些明显不相关的通用工具库 (扩展列表)
            known_tools = ['howdoi', 'graphrag', 'xpra', 'wavelets', 'nboost', 'awesome-pytorch-papers', 
                          'awesome-deep-learning', 'awesome-machine-learning', 'pytorch-tutorial', 
                          'tensorflow-examples', 'robustmatting', 'robustvideo']
            if repo_name in known_tools or any(kt in repo_name for kt in known_tools):
                if not any(kw.lower() in repo_name.replace('-', ' ').replace('_', ' ') for kw in keywords[:2]):
                    print(f"    ⚠️  Filtering out known tool library: {repo_name}")
                    return False
                
            # 过滤一些明显不相关的工具类型
            tool_patterns = ['cli', 'tool', 'utility', 'framework', 'awesome', 'list', 'collection', 
                            'tutorial', 'example', 'template', 'boilerplate', 'starter', 'kit']
            if any(pattern in repo_name for pattern in tool_patterns) and not any(kw.lower() in repo_name for kw in keywords[:2]):
                # 有工具特征，但没有论文关键词特征
                stars = repo_data.get('stargazers_count', 0)
                if stars > 1000:  # 高星通用工具很可能不是论文实现
                    print(f"    ⚠️  Filtering out high-star general tool: {repo_name} ({stars} stars)")
                    return False
            
            # 严格检查仓库名与论文关键词的匹配度
            # 提取论文标题中的关键词特征（更细致地处理）
            paper_title_lower = paper_title.lower()
            
            # 1. 提取主要概念（冒号前的部分或第一个词组）
            primary_concept = ""
            if ':' in paper_title:
                primary_concept = paper_title.split(':')[0].strip().lower()
            else:
                # 取前3个词作为主要概念
                words = paper_title.split()
                primary_concept = ' '.join(words[:min(3, len(words))]).lower()
            
            # 2. 检查仓库名是否包含主要概念中的关键词
            primary_concept_words = re.findall(r'\b[a-z0-9]{3,}\b', primary_concept)
            repo_name_words = re.findall(r'[a-z0-9]+', repo_name)
            
            # 如果不包含任何主要概念词，可能不相关
            if primary_concept_words and not any(word in repo_name for word in primary_concept_words):
                # 但如果是低星仓库，我们更宽松一些
                stars = repo_data.get('stargazers_count', 0)
                if stars > 500:
                    # 如果是高星仓库，但名称与论文主要概念无关，可能不相关
                    # 需要通过其他方式进一步验证
                    strict_verification_needed = True
                else:
                    # 低星仓库更宽松一些
                    strict_verification_needed = False
            else:
                # 有主要概念词匹配，可能相关
                strict_verification_needed = False
            
            # 检查描述中是否包含关键词
            description_lower = description.lower()
            
            # 首先，检查描述中是否直接提到论文
            paper_indicators = ['paper', 'implementation', 'code', 'official', 'reproduction', 'pytorch']
            if any(indicator in description_lower for indicator in paper_indicators):
                # 描述中提到论文相关词汇，且包含关键词
                core_words = [kw.lower() for kw in keywords[:3]]
                if any(word in description_lower for word in core_words):
                    print(f"    ✅ Description mentions paper implementation")
                    return True
            
            # 如果描述中包含论文的核心词汇，认为相关
            core_words = [kw.lower() for kw in keywords[:3]]
            matches = sum(1 for word in core_words if word in description_lower)
            
            if matches >= 1:  # 至少匹配一个核心词
                # 但要排除过于通用的描述
                if len(description_lower) < 15 or description_lower in ['deep learning', 'machine learning', 'artificial intelligence']:
                    # 过于简短或通用的描述不足以判断相关性
                    pass
                else:
                    return True
            
            # 对于需要严格验证的仓库，检查README内容
            if strict_verification_needed:
                # 获取README内容
                readme_url = f"https://api.github.com/repos/{owner_repo}/readme"
                readme_response = requests.get(readme_url, headers=self.headers)
                
                if readme_response.status_code == 200:
                    readme_data = readme_response.json()
                    if 'content' in readme_data:
                        import base64
                        readme_content = base64.b64decode(readme_data['content']).decode('utf-8', errors='ignore').lower()
                        
                        # 1. 检查README中是否直接提到论文标题
                        paper_title_clean = re.sub(r'[^\w\s]', ' ', paper_title.lower())
                        title_words = set(paper_title_clean.split())
                        title_word_count = len(title_words)
                        
                        matches = sum(1 for word in title_words if word.lower() in readme_content)
                        match_ratio = matches / title_word_count if title_word_count > 0 else 0
                        
                        # README包含超过50%的标题词，可能相关
                        if match_ratio > 0.5:
                            print(f"    ✅ README contains many paper title words: {match_ratio:.1%}")
                            return True
                        
                        # 2. 检查README中是否有论文的关键词
                        important_words = [word for word in title_words if len(word) > 3 and word not in {'with', 'using', 'for', 'from', 'the', 'and'}]
                        
                        readme_matches = sum(1 for word in important_words if word in readme_content)
                        if readme_matches >= 2:  # README中至少出现2个重要词汇
                            print(f"    ✅ README contains multiple paper keywords")
                            return True
                        
                        # 3. 检查README中是否提到arXiv或论文引用
                        if 'arxiv' in readme_content or 'paper' in readme_content:
                            # 在arxiv或paper提及附近检查是否有论文关键词
                            arxiv_idx = readme_content.find('arxiv')
                            if arxiv_idx == -1:
                                arxiv_idx = readme_content.find('paper')
                            
                            if arxiv_idx != -1:
                                # 检查周围上下文
                                context_window = readme_content[max(0, arxiv_idx-200):min(len(readme_content), arxiv_idx+200)]
                                
                                # 计算上下文中有多少论文关键词
                                context_matches = sum(1 for word in important_words if word in context_window)
                                if context_matches >= 1:
                                    print(f"    ✅ README mentions arxiv/paper with relevant keywords")
                                    return True
                
                # 严格验证失败，仓库可能不相关
                print(f"    ❌ Repository fails strict verification: likely not related to paper")
                return False
            
            # 提取论文标题的特征部分（通常是冒号前的部分，如"BiFormer: Vision Transformer..."中的"BiFormer"）
            title_prefix = paper_title.split(':')[0].strip() if ':' in paper_title else paper_title.split()[0]
            
            # 获取README内容
            readme_url = f"https://api.github.com/repos/{owner_repo}/readme"
            readme_response = requests.get(readme_url, headers=self.headers)
            
            if readme_response.status_code == 200:
                readme_data = readme_response.json()
                if 'content' in readme_data:
                    import base64
                    readme_content = base64.b64decode(readme_data['content']).decode('utf-8', errors='ignore').lower()
                    
                    # 1. 检查README中是否直接提到论文标题
                    title_words = set(paper_title.lower().split())
                    
                    # 2. 检查README中是否有论文的关键词
                    important_words = [word for word in title_words if len(word) > 3 and word not in {'with', 'using', 'for', 'from', 'the', 'and'}]
                    
                    readme_matches = sum(1 for word in important_words if word in readme_content)
                    if readme_matches >= 2:  # README中至少出现2个重要词汇
                        print(f"    ✅ README contains multiple paper keywords")
                        return True
                        
                    # 3. 检查README中是否包含论文标题或特征部分
                    if title_prefix.lower() in readme_content:
                        # 检查上下文是否与论文相关
                        title_idx = readme_content.find(title_prefix.lower())
                        context_window = readme_content[max(0, title_idx-50):min(len(readme_content), title_idx+50)]
                        if any(kw in context_window for kw in ['paper', 'implementation', 'code', 'official', 'arxiv']):
                            print(f"    ✅ README mentions paper title in relevant context")
                            return True
                    
                    # 4. 检查是否有arXiv或DOI链接
                    if 'arxiv.org' in readme_content or 'doi.org' in readme_content:
                        # 有学术引用链接，且至少有一个关键词匹配
                        if any(word in readme_content for word in important_words):
                            print(f"    ✅ README contains academic references and paper keywords")
                            return True
            
            # 如果描述和README都没有足够的匹配，但仓库名直接包含关键词，也认为相关
            for keyword in core_words:
                if keyword.lower() in repo_name:
                    print(f"    ✅ Repository name contains key model term: {keyword}")
                    return True
            
            # 对于低星仓库更宽松一些
            stars = repo_data.get('stargazers_count', 0)
            if stars < 100:
                # 对于低星仓库，如果仓库名或描述中有任何一个关键词匹配，都接受
                for kw in keywords:
                    if kw.lower() in repo_name or kw.lower() in description_lower:
                        print(f"    ✅ Low-star repo with keyword match: {kw}")
                        return True
            
            return False  # 验证失败
            
        except Exception as e:
            print(f"    ⚠️  Verification error: {e}")
            return True  # 验证出错时不拒绝，避免过于严格
    
    def _rank_repositories(self, repos, paper_title, keywords, strategy="general"):
        """
        对搜索结果按相关性排序，返回最佳匹配
        改进版：更严格的评分标准，降低星星数的权重
        """
        scored_repos = []
        title_lower = paper_title.lower()
        keywords_lower = [kw.lower() for kw in keywords]
        
        # 特别关注的模式：
        # 1. 常见的论文实现命名模式（如"Paper-Pytorch", "Model-Implementation"等）
        implementation_patterns = ['implementation', 'official', 'pytorch', 'tensorflow', 'code', 'paper']
        
        # 2. 明显不相关的通用仓库
        generic_tools = ['howdoi', 'graphrag', 'xpra', 'wavelets', 'nboost', 'awesome-papers', 'robustvideo']
        
        # 3. 提取主要概念（冒号前的部分或第一个词组）
        primary_concept = ""
        if ':' in paper_title:
            primary_concept = paper_title.split(':')[0].strip().lower()
            primary_concept_words = primary_concept.split()
        else:
            # 取前3个词作为主要概念
            words = paper_title.split()
            primary_concept = ' '.join(words[:min(3, len(words))]).lower()
            primary_concept_words = words[:min(3, len(words))]
        
        for repo in repos:
            score = 0
            repo_name = repo.get('name', '').lower()
            repo_description = repo.get('description', '') or ''
            repo_description = repo_description.lower()
            
            # 0. 预先过滤明显不相关的工具库
            if repo_name in generic_tools or any(tool in repo_name for tool in generic_tools):
                # 除非名称中有明确的关键词匹配，否则跳过通用工具
                if not any(kw.lower() in repo_name for kw in keywords_lower[:2]):
                    score -= 100  # 严重惩罚，实际上排除这些仓库
                    scored_repos.append((score, repo))
                    continue
            
            # 1. 仓库名与主要概念词匹配 (权重最高)
            concept_matches = 0
            for concept_word in primary_concept_words:
                if len(concept_word) > 2 and concept_word.lower() in repo_name:
                    concept_matches += 1
                    if concept_word.lower() == repo_name or repo_name.startswith(concept_word.lower()):
                        score += 15  # 精确匹配给予更高分数
                    else:
                        score += 10
            
            # 2. 仓库名与关键词匹配
            exact_name_match = False
            for kw in keywords_lower:
                if kw in repo_name:
                    if kw == repo_name or repo_name.startswith(kw) or repo_name.endswith(kw):
                        score += 8  # 精确匹配更高分
                        exact_name_match = True
                    else:
                        score += 5
            
            # 3. 特别加分：实现模式 (implementation, official, pytorch等)
            impl_match = False
            for pattern in implementation_patterns:
                if pattern in repo_name:
                    score += 6
                    impl_match = True
                    break
                    
            # 4. 描述匹配
            desc_matches = 0
            for kw in keywords_lower:
                if kw in repo_description:
                    score += 3
                    desc_matches += 1
            
            # 检查描述中是否包含"implementation"或"official"等指示词
            paper_indicators = ['implementation', 'official', 'code for', 'paper', 'reproduction', 'pytorch implementation']
            if any(pattern in repo_description for pattern in paper_indicators):
                score += 5
                # 如果同时包含关键词，给额外加分
                if desc_matches > 0:
                    score += 3
            
            # 5. 第一个关键词的特殊加分（通常是模型名）
            if keywords_lower and keywords_lower[0] in repo_name:
                score += 7
                
            # 6. Stars数量加分（但权重降低，避免被高星仓库误导）
            stars = repo.get('stargazers_count', 0)
            if stars > 5000:
                # 高星项目有特殊处理：
                # 如果是通用工具但关键词匹配度低，减分而不是加分
                if repo_name in generic_tools or any(pattern in repo_name for pattern in ['tool', 'utility', 'framework']):
                    if not exact_name_match and not impl_match and concept_matches == 0:
                        score -= 15  # 严厉惩罚明显不相关的高星项目
                elif concept_matches >= 1 or exact_name_match:
                    # 如果高星项目有明确的概念匹配，适当加分
                    score += min(1.5, stars / 10000)  # 最多加1.5分，大幅降低权重
                else:
                    # 其他高星项目很小的加分
                    score += min(0.5, stars / 20000)  # 最多加0.5分
            elif stars > 1000:
                score += min(stars / 2000, 1)  # 最多加1分
            elif stars > 100:
                score += 0.5
            
            # 7. 最近更新加分
            updated_at = repo.get('updated_at', '')
            if updated_at:
                try:
                    updated_date = datetime.strptime(updated_at, "%Y-%m-%dT%H:%M:%SZ")
                    days_since_update = (datetime.now() - updated_date).days
                    if days_since_update < 180:  # 半年内更新过
                        score += 1
                except:
                    pass
            
            # 8. 根据搜索策略调整阈值
            min_score_threshold = {
                "exact": 18,    # 精确搜索要求更高分数
                "context": 15,  # 上下文搜索
                "multi": 12,    # 多关键词搜索
                "single": 10,   # 单关键词搜索
                "general": 8    # 一般搜索
            }.get(strategy, 8)
            
            # 9. 特殊惩罚：明显不相关的仓库
            irrelevant_patterns = ['awesome', 'list', 'collection', 'tutorial', 'course', 'book', 'survey', 'api', 'howto']
            for pattern in irrelevant_patterns:
                if pattern in repo_name and not exact_name_match and concept_matches == 0:
                    score -= 8  # 减分
            
            # 10. 额外的相关性检查
            # 计算仓库名和论文标题之间的单词重叠度
            repo_words = set(repo_name.split('-') + repo_name.split('_'))
            title_words = set(w.lower() for w in re.findall(r'\b[A-Za-z]+\b', paper_title) if len(w) > 2)
            overlap = len(repo_words.intersection(title_words))
            
            if overlap >= 2:
                score += 4  # 有多个词重叠
            elif overlap == 1:
                score += 2  # 有一个词重叠
            
            scored_repos.append((score, repo))
        
        # 按分数排序，返回最高分的仓库
        if scored_repos:
            scored_repos.sort(key=lambda x: x[0], reverse=True)
            best_score, best_repo = scored_repos[0]
            
            # 使用策略相关的阈值
            min_threshold = {
                "exact": 18,
                "context": 15,
                "multi": 12, 
                "single": 10,
                "general": 8
            }.get(strategy, 8)
            
            print(f"    📊 Best match score: {best_score:.1f} (threshold: {min_threshold})")
            
            if best_score < min_threshold:
                print(f"    ❌ Score too low, rejecting match")
                return None
                
            return best_repo
        
        return None
