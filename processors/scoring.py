import math

def calculate_score(papers, github_fetcher, pwcode_fetcher):
    """
    批量为论文匹配GitHub仓库并计算分数
    """
    scored_results = []
    skipped_no_github = 0
    
    print("🔍 Starting recognition scoring (GitHub repos required)...")
    if pwcode_fetcher.api_key == "your-pwc-api-key-here" or not pwcode_fetcher.api_key:
        print("⚠️  PapersWithCode API not configured, trying direct GitHub search")
    
    for i, paper in enumerate(papers, 1):
        title = paper['title']
        print(f"  📋 Processing {i}/{len(papers)}: {title[:50]}...")
        
        # 1. 查询 PapersWithCode
        pwc_info = None
        if pwcode_fetcher.api_key and pwcode_fetcher.api_key != "your-pwc-api-key-here":
            pwc_info = pwcode_fetcher.search_paper(title)
        
        is_pwcode = True if pwc_info else False
        repo_url = pwc_info['repo_url'] if pwc_info else None
    
        # 2. 如果没有从PWC找到，尝试直接搜索GitHub（基于论文标题）
        github_result = None
        if not repo_url:
            github_result = github_fetcher.search_paper_repository(title)
            if github_result:
                repo_url = github_result['repo_url']
                github_stats = github_result['stats']
            
        # 3. 查询 GitHub Repo Stats（如果还没有统计信息）
        if repo_url and not github_result:
            github_stats = github_fetcher.get_repo_stats(repo_url)
        elif github_result:
            github_stats = github_result['stats']
        else:
            github_stats = None
            
        stars = github_stats['stars'] if github_stats else 0
        days_open = github_stats['days_since_created'] if github_stats else 0
    
        # 4. 计算论文分数（改为更宽容的处理方式，不跳过没有GitHub的论文）
        score = 0
        if repo_url and github_stats:
            # 使用原有的评分公式
            score = calculate_paper_score(is_pwcode, stars, days_open)
            print(f"    ✅ Found repo with {stars} stars, score: {score:.1f}")
        else:
            print(f"    ⚠️ No GitHub repo found for this paper")
            repo_url = None
            stars = 0
            skipped_no_github += 1
        
        scored_results.append({
            'title': title,
            'authors': paper.get('authors', []),
            'summary': paper.get('summary', ""),
            'pdf_url': paper.get('pdf_url', ""),
            'venue': paper.get('venue', ""),
            'repo': repo_url,
            'stars': stars,
            'days_since_created': days_open,
            'score': score
        })
    
    print(f"📊 Recognition scoring completed: {len(scored_results) - skipped_no_github} papers with GitHub repos found")
    print(f"⚠️  Skipped {skipped_no_github} papers without GitHub repositories")
    
    # 对结果按照分数和星星数降序排序
    scored_results.sort(key=lambda x: (x.get('score', 0), x.get('stars', 0)), reverse=True)
    
    return scored_results

def calculate_paper_score(is_pwcode, stars, days_since_created):
    """
    简单综合打分公式：
      score = 2*is_pwcode + log(stars+1) + 0.5*log(days_since_created+1)
    """
    score = 0.0
    score += 2 * (1 if is_pwcode else 0)
    if stars is not None:
        score += math.log(stars + 1)
    if days_since_created is not None:
        score += 0.5 * math.log(days_since_created + 1)
    return round(score, 2)
