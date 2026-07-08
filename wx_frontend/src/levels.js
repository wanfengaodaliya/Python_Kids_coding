export const LEVELS = [
  {
    id: 1,
    name: '初识 print',
    icon: '1',
    description: '用 print 让 Python 说出第一句话',
    theme: 'sky',
    left: 55,
    top: 40,
    title: '第一关：让 Python 开口说话',
    initialCode: "print('Hello, World!')",
    expectedOutput: 'Hello, World!',
    steps: [
      '小任务：让 Python 像第一次打招呼一样，说出 Hello, World!',
      '1. 使用 print() 函数输出一段文字。',
      '2. 文字要放在引号里，就像把句子装进一个小盒子。'
    ],
    hint: 'print() 是 Python 最常用的输出函数，它会把括号里的内容展示出来。',
    expectedText: '预期输出：Hello, World!'
  },
  {
    id: 2,
    name: 'for 循环',
    icon: '2',
    description: '让 for 循环帮你完成重复任务',
    theme: 'sun',
    left: 195,
    top: 130,
    title: '第二关：让循环帮你数数',
    initialCode: 'total = 0\nfor i in range(1, 101):\n    total = total + i\nprint(total)',
    expectedOutput: '5050',
    steps: [
      '小任务：计算 1 到 100 的总和。',
      '1. for 循环会按顺序经过 range() 里的每个数字。',
      '2. 每经过一个数字，就把它累加到 total 里。',
      '3. 最后用 print() 输出总和。'
    ],
    hint: 'for 这一行末尾需要冒号；total = total + i 才能不断累加。',
    expectedText: '预期输出：5050'
  },
  {
    id: 3,
    name: '变量背包',
    icon: '3',
    description: '把名字和数字装进变量背包',
    theme: 'leaf',
    left: 55,
    top: 220,
    title: '第三关：变量是会取名字的小背包',
    initialCode: "name = '小海獭'\nshells = 3\nshells = shells + 4\nprint(f'{name}收集了 {shells} 颗贝壳')",
    expectedOutput: '小海獭收集了 7 颗贝壳',
    steps: [
      '小任务：用变量记录名字和贝壳数量。',
      '1. 变量像贴了标签的小背包，name 里放名字，shells 里放数量。',
      '2. shells = shells + 4 表示再放进 4 颗贝壳。',
      '3. f-string 可以把变量自然地嵌进一句话里。'
    ],
    hint: '如果输出不对，先检查变量名，再看看 f-string 前面有没有小写字母 f。',
    expectedText: '预期输出：小海獭收集了 7 颗贝壳'
  },
  {
    id: 4,
    name: '列表小队',
    icon: '4',
    description: '用列表排好一队学习卡片',
    theme: 'rose',
    left: 195,
    top: 310,
    title: '第四关：列表把一队数据排整齐',
    initialCode: "topics = ['变量', '循环', '列表']\nscores = [20, 30, 40]\naverage = sum(scores) // len(scores)\nprint(f'一共学习了 {len(topics)} 个知识点')\nprint(f'平均得分是 {average}')",
    expectedOutput: '一共学习了 3 个知识点\n平均得分是 30',
    steps: [
      '小任务：用列表管理多个知识点和分数。',
      '1. 列表像一排排好的小卡片，可以一次装下很多数据。',
      '2. len(topics) 会数出列表里有几张卡片。',
      '3. sum(scores) 会把分数列表加起来，再除以数量得到平均分。'
    ],
    hint: '列表用方括号 [] 包起来；想知道列表长度，就把列表交给 len()。',
    expectedText: '预期输出：一共学习了 3 个知识点；平均得分是 30'
  }
]

export function getHighestCompleted() {
  const raw = JSON.parse(localStorage.getItem('level_progress') || '{"highestCompleted":0}')
  const value = Number(raw.highestCompleted || 0)
  return Math.max(0, Math.min(LEVELS.length, Number.isFinite(value) ? value : 0))
}

export function markLevelCompleted(id) {
  const highestCompleted = Math.max(getHighestCompleted(), Number(id) || 0)
  localStorage.setItem('level_progress', JSON.stringify({ highestCompleted }))
  return highestCompleted
}

export function getLevelById(id) {
  return LEVELS.find((level) => level.id === Number(id)) || LEVELS[0]
}

export function getLevelList(highestCompleted = 0) {
  return LEVELS.map((level) => {
    const status = level.id <= highestCompleted ? 'completed' : level.id === highestCompleted + 1 ? 'current' : 'locked'
    return {
      ...level,
      name: status === 'locked' ? '神秘关卡' : level.name,
      description: status === 'locked' ? '点亮上一关后出现新任务' : level.description,
      displayTheme: status === 'completed' ? 'completed' : level.theme,
      status,
      label: status === 'completed' ? '已通关' : status === 'current' ? '当前关卡' : '待点亮',
      badge: status === 'completed' ? '已点亮' : status === 'current' ? '挑战中' : '待点亮'
    }
  })
}

export function getPathLines(highestCompleted = 0) {
  return [1, 2, 3].map((id) => ({
    id,
    status: highestCompleted > id ? 'completed' : highestCompleted === id ? 'current' : 'locked'
  }))
}

export function getProgressSummary(highestCompleted = 0) {
  const completed = Math.max(0, Math.min(LEVELS.length, Number(highestCompleted) || 0))
  const total = LEVELS.length
  const percent = Math.round((completed / total) * 100)
  if (completed >= total) {
    return { completed, total, percent, goalText: '基础关卡全部点亮', helperText: '可以回到任意关卡复习啦' }
  }
  const next = LEVELS[completed]
  return {
    completed,
    total,
    percent,
    goalText: `下一站：第 ${next.id} 关 ${next.name}`,
    helperText: `继续前进，再点亮 ${total - completed} 个关卡`
  }
}
