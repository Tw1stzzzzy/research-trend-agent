import openreview

# 测试OpenReview API结构
client = openreview.Client(baseurl='https://api.openreview.net')

# 以ICLR 2023为例
conf_id = "ICLR.cc/2023/Conference"

print("=== 探索OpenReview API结构 ===")
print(f"会议ID: {conf_id}")

# 1. 查看所有可用的invitations
try:
    invitations = client.get_invitations(regex=f'{conf_id}/.*')
    print(f"\n找到 {len(invitations)} 个invitations:")
    for inv in invitations[:10]:  # 只显示前10个
        print(f"  - {inv.id}")
        if 'Decision' in inv.id or 'Camera_Ready' in inv.id or 'Accept' in inv.id:
            print(f"    ★ 可能相关: {inv.id}")
except Exception as e:
    print(f"获取invitations失败: {e}")

# 2. 尝试获取决策信息
print(f"\n=== 尝试获取决策信息 ===")
decision_invitations = [
    f'{conf_id}/-/Decision',
    f'{conf_id}/-/Meta_Review',
    f'{conf_id}/-/Official_Review',
    f'{conf_id}/-/Camera_Ready_Submission'
]

for inv in decision_invitations:
    try:
        notes = client.get_notes(invitation=inv, limit=5)
        print(f"✓ {inv}: 找到 {len(notes)} 条记录")
        if notes:
            sample = notes[0]
            print(f"  示例内容字段: {list(sample.content.keys())}")
    except Exception as e:
        print(f"✗ {inv}: {e}")

# 3. 获取一些Blind_Submission样本，看看它们的结构
print(f"\n=== Blind_Submission 样本分析 ===")
try:
    submissions = client.get_notes(invitation=f'{conf_id}/-/Blind_Submission', limit=3)
    print(f"获取到 {len(submissions)} 个提交")
    
    for i, note in enumerate(submissions):
        print(f"\n样本 {i+1}:")
        print(f"  ID: {note.id}")
        print(f"  标题: {note.content.get('title', 'N/A')}")
        print(f"  内容字段: {list(note.content.keys())}")
        
        # 查看是否有关联的决策
        try:
            decisions = client.get_notes(forum=note.id, invitation=f'{conf_id}/-/Decision')
            if decisions:
                decision_content = decisions[0].content
                print(f"  决策: {decision_content.get('decision', 'N/A')}")
                print(f"  决策字段: {list(decision_content.keys())}")
            else:
                print(f"  决策: 未找到")
        except Exception as e:
            print(f"  决策查询失败: {e}")
            
except Exception as e:
    print(f"获取Blind_Submission失败: {e}")

print("\n=== 测试完成 ===") 