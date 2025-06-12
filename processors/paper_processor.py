import re
import json
from difflib import SequenceMatcher

def validate_and_clean_matches(scored_papers):
    """
    对匹配结果进行验证和清理，确保高质量的匹配
    输入: scored_papers列表
    输出: 清理后的scored_papers列表
    """
    print("🧹 Validating and cleaning repository matches...")
    
    # 0. 检查特定的错误匹配
    known_bad_matches = {
        "Frame Interpolation": ["google-research/frame-interpolation", "frame-interpolation"],
        "Robust 3D Shape": ["RobustVideoMatting", "robustmatting"],
        "Paint by Example": ["stable-diffusion", "controlnet"]
    }
    
    for paper in scored_papers:
        for keyword, bad_repos in known_bad_matches.items():
            if keyword in paper['title'] and paper.get('repo'):
                repo_name = paper['repo'].split('/')[-1].lower()
                full_repo_path = paper['repo'].replace("https://github.com/", "").lower()
                
                if repo_name in bad_repos or full_repo_path in bad_repos:
                    print(f"⚠️ Removing known bad match: {paper['title']} -> {paper['repo']}")
                    paper['repo'] = None
                    paper['stars'] = 0
    
    # 1. 识别误匹配的模式
    # 例如论文A -> 仓库A，论文B -> 仓库A (同一个仓库匹配到多个论文)
    repo_to_papers = {}
    for paper in scored_papers:
        repo_url = paper.get('repo')
        if repo_url:
            if repo_url not in repo_to_papers:
                repo_to_papers[repo_url] = []
            repo_to_papers[repo_url].append(paper['title'])
    
    # 检查重复匹配的仓库
    duplicate_repos = {repo: papers for repo, papers in repo_to_papers.items() if len(papers) > 1}
    
    # 2. 对于每个重复匹配的仓库，保留最可能正确的匹配
    for repo_url, paper_titles in duplicate_repos.items():
        print(f"⚠️ Repository {repo_url} matched to multiple papers:")
        for title in paper_titles:
            print(f"  - {title}")
        
        # 提取仓库名
        repo_name = repo_url.split('/')[-1].lower() if repo_url else ""
        
        # 计算每个论文标题与仓库名的相似度
        best_match = None
        best_score = 0
        
        for title in paper_titles:
            # 提取标题中的模型名（通常是冒号前的部分）
            model_name = title.split(':')[0].strip().lower() if ':' in title else title.split()[0].lower()
            
            # 计算相似度 (使用最长公共子序列)
            similarity = SequenceMatcher(None, model_name, repo_name).ratio()
            
            # 检查是否有精确的关键词匹配
            title_words = re.findall(r'\b[a-z0-9]{3,}\b', title.lower())
            word_match = any(word in repo_name for word in title_words)
            
            # 词匹配比一般相似度更重要
            if word_match:
                similarity += 0.3
                
            if similarity > best_score:
                best_score = similarity
                best_match = title
        
        print(f"  ✅ Best match: {best_match} (score: {best_score:.2f})")
        
        # 清除其他论文的该仓库匹配
        for paper in scored_papers:
            if paper['title'] in paper_titles and paper['title'] != best_match:
                print(f"  ❌ Removing match from: {paper['title']}")
                paper['repo'] = None
                paper['stars'] = 0
    
    # 3. 检查可疑的匹配 (如基于单一通用词汇的匹配)
    suspicious_keywords = ['tool', 'utility', 'framework', 'awesome', 'list', 'collection', 'tutorial']
    for paper in scored_papers:
        repo_url = paper.get('repo')
        if repo_url:
            repo_name = repo_url.split('/')[-1].lower()
            title_words = re.findall(r'\b[a-z0-9]{3,}\b', paper['title'].lower())
            
            # 检查仓库名是否只匹配了标题中的通用词
            matches = [word for word in title_words if word in repo_name]
            
            # 1. 如果仓库名包含可疑关键词但不包含论文特定词汇
            if any(keyword in repo_name for keyword in suspicious_keywords):
                specific_match = False
                for word in title_words:
                    # 跳过常见通用词
                    if word in ['model', 'deep', 'learning', 'neural', 'network', 'using', 'with', 'based']:
                        continue
                    if word in repo_name:
                        specific_match = True
                        break
                        
                if not specific_match and paper.get('stars', 0) > 1000:
                    print(f"⚠️ Suspicious match - generic high-star repo: {paper['title']} -> {repo_url}")
                    paper['repo'] = None
                    paper['stars'] = 0
            
            # 2. 如果仓库名称很长，但与论文标题没有显著重叠
            elif len(repo_name) > 15:
                overlap_ratio = len(matches) / len(title_words) if title_words else 0
                if overlap_ratio < 0.2 and paper.get('stars', 0) > 2000:
                    print(f"⚠️ Suspicious match - low overlap ratio: {paper['title']} -> {repo_url}")
                    paper['repo'] = None
                    paper['stars'] = 0
    
    # 4. 检查模型名称与仓库名称的匹配
    for paper in scored_papers:
        if not paper.get('repo'):
            continue
            
        title = paper['title']
        repo_url = paper['repo']
        repo_name = repo_url.split('/')[-1].lower() if repo_url else ""
        
        # 提取模型名称 (通常是冒号前的部分或标题的第一个词)
        model_name = ""
        if ':' in title:
            model_name = title.split(':')[0].strip()
        else:
            # 假设第一个词可能是模型名
            model_name = title.split()[0]
        
        # 检查模型名是否在仓库名中
        model_in_repo = False
        model_words = model_name.lower().split()
        
        for word in model_words:
            if len(word) > 2 and word.lower() in repo_name:
                model_in_repo = True
                break
        
        # 如果模型名不在仓库名中，但这是一个高星仓库，则可疑
        if not model_in_repo and paper.get('stars', 0) > 3000:
            # 再次验证是否有其他强匹配特征
            title_words = set(re.findall(r'\b[a-z0-9]{3,}\b', title.lower()))
            repo_words = set(re.findall(r'\b[a-z0-9]{3,}\b', repo_name))
            
            # 计算两者的词汇重叠
            overlap = title_words.intersection(repo_words)
            
            # 如果重叠词汇少于2个，且都是常见词，则可疑
            common_words = {'deep', 'learning', 'neural', 'network', 'model', 'gan', 'net', 'transformer'}
            meaningful_overlap = [word for word in overlap if word not in common_words]
            
            if len(meaningful_overlap) < 1:
                print(f"⚠️ Suspicious match - model name not in repo: {title} -> {repo_url}")
                paper['repo'] = None
                paper['stars'] = 0
    
    print(f"✅ Validation complete. {sum(1 for p in scored_papers if p.get('repo'))} valid matches remain.")
    return scored_papers 