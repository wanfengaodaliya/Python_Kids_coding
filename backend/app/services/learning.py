DEFAULT_LEVELS = [
    {
        "id": 1,
        "level_name": "初识 print",
        "title": "第一关：让 Python 开口说话",
        "description": "用 print 让 Python 说出第一句话",
        "initial_code": "print('Hello, World!')",
        "expected_output": "Hello, World!",
        "steps": "小任务：让 Python 像第一次打招呼一样，说出 Hello, World!\n1. 使用 print() 函数输出一段文字。\n2. 文字要放在引号里，就像把句子装进一个小盒子。",
        "hint": "print() 是 Python 最常用的输出函数，它会把括号里的内容展示出来。",
        "theme": "sky",
        "sort_order": 1,
    },
    {
        "id": 2,
        "level_name": "for 循环",
        "title": "第二关：让循环帮你数数",
        "description": "让 for 循环帮你完成重复任务",
        "initial_code": "total = 0\nfor i in range(1, 101)\n    total = i\nprint(total)",
        "expected_output": "5050",
        "steps": "小任务：计算 1 到 100 的总和。\n1. for 循环像一辆小车，会按顺序经过 range() 里的每个数字。\n2. 每经过一个数字，就把它累加到 total 里。\n3. 最后用 print() 输出总和。",
        "hint": "当前代码有两处小坑：for 这一行末尾需要冒号；total 要写成 total = total + i，才能不断累加。",
        "theme": "sun",
        "sort_order": 2,
    },
    {
        "id": 3,
        "level_name": "变量背包",
        "title": "第三关：变量是会取名字的小背包",
        "description": "把名字和数字装进变量背包",
        "initial_code": "name = '小海獭'\nshells = 3\nshells = shells + 4\nprint(f'{name}收集了 {shells} 颗贝壳')",
        "expected_output": "小海獭收集了 7 颗贝壳",
        "steps": "小任务：用变量记录名字和贝壳数量。\n1. 变量像一个贴了标签的小背包，name 里放名字，shells 里放数量。\n2. shells = shells + 4 表示往背包里再放 4 颗贝壳。\n3. f-string 可以把变量自然地嵌进一句话里。",
        "hint": "如果输出不对，先检查变量名有没有拼错，再看看 f-string 前面有没有小写字母 f。",
        "theme": "leaf",
        "sort_order": 3,
    },
    {
        "id": 4,
        "level_name": "列表小队",
        "title": "第四关：列表把一队数据排整齐",
        "description": "用列表排好一队学习卡片",
        "initial_code": "topics = ['变量', '循环', '列表']\nscores = [20, 30, 40]\naverage = sum(scores) // len(scores)\nprint(f'一共学习了 {len(topics)} 个知识点')\nprint(f'平均得分是 {average}')",
        "expected_output": "一共学习了 3 个知识点\n平均得分是 30",
        "steps": "小任务：用列表管理多个知识点和分数。\n1. 列表像一列排好队的小卡片，可以一次装下很多数据。\n2. len(topics) 会数出列表里有几张卡片。\n3. sum(scores) 会把分数列表加起来，再除以数量就能得到平均分。",
        "hint": "列表用方括号 [] 包起来；想知道列表长度，就把列表交给 len()。",
        "theme": "rose",
        "sort_order": 4,
    },
]


def seed_default_levels(db):
    """Insert the four built-in levels if they are missing."""
    from app.models.user import Level

    inserted = 0
    for level_data in DEFAULT_LEVELS:
        existing = db.query(Level).filter(Level.id == level_data["id"]).first()
        if existing:
            continue
        level = Level(**level_data)
        db.add(level)
        inserted += 1
    if inserted:
        db.commit()
    return inserted


def calculate_level_status(level_id: int, highest_completed: int) -> str:
    if level_id <= highest_completed:
        return "completed"
    if level_id == highest_completed + 1:
        return "current"
    return "locked"


def build_progress_summary(highest_completed: int, total_levels: int) -> dict:
    completed = max(0, min(highest_completed, total_levels))
    percent = round((completed / total_levels) * 100) if total_levels else 0

    if total_levels and completed >= total_levels:
        return {
            "completed": completed,
            "total": total_levels,
            "percent": percent,
            "goalText": "基础关卡全部点亮",
            "helperText": "可以回到任意关卡复习啦",
        }

    return {
        "completed": completed,
        "total": total_levels,
        "percent": percent,
        "goalText": f"下一站：第 {completed + 1} 关",
        "helperText": f"继续前进，再点亮 {total_levels - completed} 个关卡",
    }
