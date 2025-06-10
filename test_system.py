#!/usr/bin/env python3
"""
完整系统测试脚本
测试研究代理系统的所有组件功能
"""

import os
import json
import requests
from datetime import datetime

def test_config():
    """测试配置文件"""
    print("🔧 Testing Configuration...")
    try:
        import yaml
        with open("configs/config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        print(f"  ✅ Config loaded successfully")
        print(f"  📊 LLM Provider: {config.get('llm_provider', 'NOT SET')}")
        print(f"  🔑 GitHub Token: {'✅ SET' if config.get('github', {}).get('token', '').startswith('ghp_') else '❌ NOT SET'}")
        print(f"  📡 Slack Webhook: {'✅ SET' if config.get('slack', {}).get('webhook_url', '').startswith('https://') else '❌ NOT SET'}")
        return True
    except Exception as e:
        print(f"  ❌ Config error: {e}")
        return False

def test_llm():
    """测试LLM连接"""
    print("\n🤖 Testing LLM Connection...")
    try:
        from processors.llm_client import LLMClient
        client = LLMClient()
        
        test_messages = [
            {"role": "user", "content": "Please respond with exactly: TEST_SUCCESS"}
        ]
        
        response = client.generate_response(test_messages, max_tokens=20)
        if "TEST_SUCCESS" in response:
            print(f"  ✅ LLM working correctly")
            return True
        else:
            print(f"  ⚠️ LLM response unexpected: {response}")
            return False
            
    except Exception as e:
        print(f"  ❌ LLM error: {e}")
        return False

def test_github():
    """测试GitHub API"""
    print("\n🐙 Testing GitHub API...")
    try:
        from fetchers.github_fetcher import GitHubFetcher
        import yaml
        
        with open("configs/config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        token = config.get('github', {}).get('token', '')
        if not token or token == "your-github-token-here":
            print("  ⚠️ GitHub token not configured")
            return False
            
        fetcher = GitHubFetcher(token)
        # 测试一个知名仓库
        stats = fetcher.get_repo_stats("https://github.com/pytorch/pytorch")
        
        if stats and stats.get('stars', 0) > 1000:
            print(f"  ✅ GitHub API working - PyTorch has {stats['stars']} stars")
            return True
        else:
            print(f"  ❌ GitHub API failed or unexpected response: {stats}")
            return False
            
    except Exception as e:
        print(f"  ❌ GitHub API error: {e}")
        return False

def test_slack():
    """测试Slack连接"""
    print("\n📱 Testing Slack Integration...")
    try:
        import yaml
        
        with open("configs/config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        webhook_url = config.get('slack', {}).get('webhook_url', '')
        if not webhook_url or not webhook_url.startswith('https://hooks.slack.com'):
            print("  ⚠️ Slack webhook not configured")
            return False
        
        test_payload = {
            "text": f"🧪 Test message from Research Agent - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "username": "Research Agent Test",
            "icon_emoji": ":test_tube:"
        }
        
        response = requests.post(webhook_url, json=test_payload, timeout=10)
        if response.status_code == 200:
            print("  ✅ Slack webhook working - test message sent")
            return True
        else:
            print(f"  ❌ Slack webhook failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Slack error: {e}")
        return False

def test_fetchers():
    """测试论文获取器"""
    print("\n📚 Testing Paper Fetchers...")
    try:
        from fetchers.cvf_fetcher import CVFFetcher
        
        # 测试CVF fetcher
        fetcher = CVFFetcher("https://openaccess.thecvf.com/CVPR2023", "CVPR")
        papers = fetcher.fetch_papers(max_papers=5)  # 只获取5篇测试
        
        if papers and len(papers) > 0:
            print(f"  ✅ CVF fetcher working - got {len(papers)} papers")
            print(f"    📄 Sample: {papers[0]['title'][:50]}...")
            return True
        else:
            print("  ❌ CVF fetcher failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Fetcher error: {e}")
        return False

def test_processing():
    """测试论文处理流程"""
    print("\n⚙️ Testing Paper Processing...")
    try:
        # 检查输出文件是否存在
        output_files = [
            "output/raw_papers.json",
            "output/filtered_papers.json", 
            "output/scored_papers.json",
            "output/report.md"
        ]
        
        missing_files = []
        for file_path in output_files:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            print(f"  ⚠️ Missing output files: {missing_files}")
            print("  🔄 Run 'python main.py' to generate outputs")
            return False
        
        # 检查文件内容
        with open("output/scored_papers.json", "r") as f:
            scored_papers = json.load(f)
        
        if len(scored_papers) > 0:
            avg_score = sum(p['score'] for p in scored_papers) / len(scored_papers)
            print(f"  ✅ Processing pipeline working")
            print(f"    📊 {len(scored_papers)} papers scored, avg: {avg_score:.2f}")
            return True
        else:
            print("  ❌ No scored papers found")
            return False
            
    except Exception as e:
        print(f"  ❌ Processing error: {e}")
        return False

def run_full_test():
    """运行完整系统测试"""
    print("🚀 Starting Full System Test")
    print("=" * 50)
    
    results = {
        "Config": test_config(),
        "LLM": test_llm(),
        "GitHub": test_github(),
        "Slack": test_slack(),
        "Fetchers": test_fetchers(),
        "Processing": test_processing()
    }
    
    print("\n📋 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:12} {status}")
        if result:
            passed += 1
    
    print("-" * 50)
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready to use.")
    else:
        print(f"\n⚠️ {total-passed} tests failed. Please check configuration.")
    
    return passed == total

if __name__ == "__main__":
    run_full_test() 