import { useEffect, useMemo, useRef, useState } from 'react'
import { api, getBaseUrl } from './api.js'
import { assets } from './assets.js'
import {
  getHighestCompleted,
  getLevelById,
  getLevelList,
  getPathLines,
  getProgressSummary,
  markLevelCompleted
} from './levels.js'
import { buildMonthCalendar, formatDate, getStored, removeStored, setStored } from './storage.js'

const DEFAULT_SETTINGS = {
  nickname: '小海獭',
  codeSize: 'medium',
  hintLevel: 'normal',
  autoSaveCodeEnabled: true,
  restReminderEnabled: true,
  soundEnabled: true,
  encourageAnimationEnabled: true,
  eyeProtectionEnabled: false,
  aiReplyStyle: 'simple',
  aiHintFirst: true
}

const CHAT_WELCOME = '你好呀，我是小海獭，请问有什么可以帮助你的呢？'
const toast = (message) => window.alert(message)

function loadSettings() {
  return Object.keys(DEFAULT_SETTINGS).reduce((settings, key) => {
    settings[key] = getStored(key, DEFAULT_SETTINGS[key])
    return settings
  }, {})
}

function App() {
  const [page, setPage] = useState(getStored('access_token') ? 'levels' : 'auth')
  const [levelId, setLevelId] = useState(1)
  const [chatState, setChatState] = useState({
    currentSessionId: '',
    messages: [{ content: CHAT_WELCOME, isUser: false }],
    question: '',
    sessions: []
  })

  const navigate = (nextPage, nextLevelId) => {
    if (nextLevelId) setLevelId(nextLevelId)
    setPage(nextPage)
  }

  return (
    <div className="app-shell">
      {page === 'auth' && <AuthPage navigate={navigate} />}
      {page === 'levels' && <LevelsPage navigate={navigate} />}
      {page === 'level' && <LevelPage id={levelId} navigate={navigate} />}
      {page === 'chat' && <ChatPage chatState={chatState} setChatState={setChatState} />}
      {page === 'records' && <RecordsPage />}
      {page === 'settings' && <SettingsPage navigate={navigate} />}
      {page !== 'auth' && page !== 'level' && <TabBar page={page} navigate={navigate} />}
    </div>
  )
}

function TabBar({ page, navigate }) {
  const tabs = [
    ['levels', '关卡', assets.tabLevels, assets.tabLevelsActive],
    ['chat', 'AI 对话', assets.tabChat, assets.tabChatActive],
    ['records', '记录', assets.tabRecords, assets.tabRecordsActive],
    ['settings', '设置', assets.tabSettings, assets.tabSettingsActive]
  ]
  return (
    <nav className="tabbar">
      {tabs.map(([key, label, icon, activeIcon]) => (
        <button key={key} className={page === key ? 'tabbar-item active' : 'tabbar-item'} onClick={() => navigate(key)}>
          <img src={page === key ? activeIcon : icon} alt="" />
          <span>{label}</span>
        </button>
      ))}
    </nav>
  )
}

function AuthPage({ navigate }) {
  const [activeTab, setActiveTab] = useState('login')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [messageType, setMessageType] = useState('info')
  const [form, setForm] = useState({ username: '', password: '', phone: '', new_password: '' })

  const showMessage = (text, type = 'info') => {
    setMessage(text)
    setMessageType(type)
    window.clearTimeout(showMessage.timer)
    showMessage.timer = window.setTimeout(() => setMessage(''), 3000)
  }
  const update = (key, value) => setForm((current) => ({ ...current, [key]: value }))
  const validate = (keys) => {
    const labels = { username: '用户名', password: '密码', phone: '手机号', new_password: '新密码' }
    for (const key of keys) {
      const value = String(form[key] || '').trim()
      if (!value) return showMessage(`请输入${labels[key]}`, 'error'), false
      if ((key === 'password' || key === 'new_password') && value.length < 6) return showMessage('密码至少 6 位', 'error'), false
      if (key === 'username' && activeTab === 'register' && value.length < 3) return showMessage('用户名至少 3 个字符', 'error'), false
      if (key === 'phone' && (value.length < 10 || value.length > 20)) return showMessage('请输入有效手机号', 'error'), false
    }
    return true
  }

  const submit = async () => {
    const config = {
      login: { keys: ['username', 'password'], url: '/auth/login', body: { username: form.username.trim(), password: form.password } },
      register: { keys: ['username', 'password', 'phone'], url: '/auth/register', body: { username: form.username.trim(), password: form.password, phone: form.phone.trim() } },
      reset: { keys: ['phone', 'new_password'], url: '/auth/reset-password', body: { phone: form.phone.trim(), new_password: form.new_password } }
    }[activeTab]
    if (!validate(config.keys)) return
    setLoading(true)
    try {
      const result = await api.post(config.url, config.body)
      if (result.code && result.code !== 200 && result.code !== 201) return showMessage(result.msg || '操作失败', 'error')
      if (activeTab === 'login') {
        setStored('access_token', result.data?.access_token || '')
        setStored('refresh_token', result.data?.refresh_token || '')
        showMessage('登录成功', 'success')
        window.setTimeout(() => navigate('levels'), 500)
      } else {
        showMessage(activeTab === 'register' ? '注册成功，请登录' : '密码重置成功，请登录', 'success')
        setActiveTab('login')
      }
    } catch (error) {
      showMessage(error.message || '网络错误，请稍后重试', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page auth-page">
      <img className="decor star" src={assets.star} alt="" />
      <img className="decor cloud" src={assets.cloud} alt="" />
      <div className="wave" />
      <img className="otter" src={assets.loginOtter} alt="" />
      <section className="auth-card card">
        <h1 className="title">用户认证系统</h1>
        <div className="tabs auth-tabs">
          {[
            ['login', '登录'],
            ['register', '注册'],
            ['reset', '重置密码']
          ].map(([key, label]) => (
            <button key={key} className={activeTab === key ? 'tab active' : 'tab'} onClick={() => setActiveTab(key)}>
              {label}
            </button>
          ))}
        </div>
        {message && <div className={`message ${messageType}`}>{message}</div>}
        <div className="form">
          {activeTab !== 'reset' && (
            <>
              <label className="label">用户名</label>
              <input className="input" value={form.username} onChange={(e) => update('username', e.target.value)} placeholder={activeTab === 'login' ? '请输入用户名' : '3-50 个字符'} />
            </>
          )}
          {activeTab !== 'login' && (
            <>
              <label className="label">手机号</label>
              <input className="input" value={form.phone} onChange={(e) => update('phone', e.target.value)} placeholder="请输入手机号" />
            </>
          )}
          <label className="label">{activeTab === 'reset' ? '新密码' : '密码'}</label>
          <input className="input" type="password" value={activeTab === 'reset' ? form.new_password : form.password} onChange={(e) => update(activeTab === 'reset' ? 'new_password' : 'password', e.target.value)} placeholder={activeTab === 'reset' ? '至少 6 位' : '请输入密码'} />
          <button className="primary-button submit" disabled={loading} onClick={submit}>{loading ? '处理中...' : activeTab === 'login' ? '登录' : activeTab === 'register' ? '注册' : '重置密码'}</button>
        </div>
      </section>
    </main>
  )
}

function LevelsPage({ navigate }) {
  const [summary, setSummary] = useState(getProgressSummary(getHighestCompleted()))
  const levels = useMemo(() => getLevelList(summary.completed), [summary.completed])
  const pathLines = useMemo(() => getPathLines(summary.completed), [summary.completed])

  useEffect(() => {
    api.get('/levels')
      .then((result) => {
        const completed = Number(result.data?.summary?.completed || getHighestCompleted())
        setSummary(result.data?.summary || getProgressSummary(completed))
      })
      .catch(() => setSummary(getProgressSummary(getHighestCompleted())))
  }, [])

  const openLevel = (level) => {
    if (level.status === 'locked') return toast('先完成前一关，这一关才会亮起来哦')
    navigate('level', level.id)
  }

  return (
    <main className="page levels-page">
      <img className="decoration star" src={assets.star} alt="" />
      <img className="decoration cloud cloud-one" src={assets.cloud} alt="" />
      <img className="decoration cloud cloud-two" src={assets.cloud} alt="" />
      <section className="hero-panel">
        <div className="hero-copy">
          <span className="eyebrow">Python Adventure</span>
          <h1 className="hero-title">Python 闯关地图</h1>
          <span className="hero-goal">{summary.goalText}</span>
          <div className="hero-progress">
            <div className="progress-meta"><span>已点亮 {summary.completed} / {summary.total} 关</span><span>{summary.percent}%</span></div>
            <div className="progress-track"><div className="progress-fill" style={{ width: `${summary.percent}%` }} /></div>
          </div>
        </div>
        <div className="hero-badge"><span className="badge-number">{summary.completed}</span><span className="badge-label">关</span></div>
      </section>
      <section className="map-panel">
        <div className="map-header">
          <div><h2 className="map-title">星光路线</h2><span className="map-helper">{summary.helperText}</span></div>
          <div className="status-legend">
            <span className="legend-item"><i className="legend-dot completed-dot" />已完成</span>
            <span className="legend-item"><i className="legend-dot current-dot" />当前</span>
          </div>
        </div>
        <div className="path">
          {pathLines.map((line) => <div key={line.id} className={`path-line line-${line.id} ${line.status}`} />)}
          {levels.map((level) => (
            <button key={level.id} className={`level-node ${level.status} theme-${level.displayTheme}`} style={{ left: `${(level.left / 320) * 100}%`, top: `${(level.top / 520) * 100}%` }} onClick={() => openLevel(level)}>
              {level.status === 'current' && <span className="current-marker">继续挑战</span>}
              <span className="node-orb">{level.status === 'completed' && <span className="check-mark">✓</span>}<span className="level-icon">{level.icon}</span></span>
              <span className="node-card"><span className="level-name">{level.name}</span><span className="level-desc">{level.description}</span><span className="level-badge">{level.badge}</span></span>
            </button>
          ))}
        </div>
      </section>
      <section className="tip-panel"><span className="tip-icon">?</span><span className="tip-text">点亮当前关卡后，下一站会自动出现。</span></section>
      <div className="wave" />
    </main>
  )
}

function LevelPage({ id, navigate }) {
  const level = getLevelById(id)
  const [code, setCode] = useState(level.initialCode)
  const [output, setOutput] = useState('运行结果将显示在这里')
  const [outputType, setOutputType] = useState('hidden')
  const [running, setRunning] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [lastRunResult, setLastRunResult] = useState(null)
  const [modal, setModal] = useState(null)
  const lineNumbers = String(code || '').split('\n').map((_, index) => index + 1)

  const formatResult = (data) => {
    let display = ''
    if (data.output) display += `程序输出:\n${data.output}\n`
    if (data.errors?.length) data.errors.forEach((err) => { display += `------------------------------\n${err.type || 'Error'}\n${err.line ? `第 ${err.line} 行\n` : ''}${err.message || ''}\n${err.suggestion ? `提示：${err.suggestion}\n` : ''}` })
    if (data.execution_time !== undefined) display += `执行时间: ${data.execution_time} 秒\n`
    return display.trim() || '代码已执行，但没有输出。'
  }

  const runCode = async () => {
    if (!code.trim()) return setOutput('请输入代码'), setOutputType('error')
    setRunning(true)
    setOutput('代码正在执行，请稍等...')
    setOutputType('info')
    try {
      const result = await api.post('/code/run', { code, timeout: 10, level_id: id, is_submission: false })
      const data = result.data || {}
      setLastRunResult(data)
      setOutput(formatResult(data))
      setOutputType(data.success ? 'success' : 'error')
    } catch (error) {
      setOutput(error.message || '无法连接到服务器，请确认后端服务已启动')
      setOutputType('error')
    } finally {
      setRunning(false)
    }
  }

  const submitCode = async () => {
    if (!lastRunResult?.success) return setOutput('请先点击“运行”验证代码'), setOutputType('info')
    setSubmitting(true)
    try {
      const result = await api.post('/code/run', { code, timeout: 10, level_id: id, is_submission: true })
      const data = result.data || {}
      if (data.passed || String(data.output || '').trim() === level.expectedOutput.trim()) {
        markLevelCompleted(id)
        setModal({ type: 'success', title: '通过', message: id >= 4 ? '漂亮！四个基础关卡都完成啦。' : '漂亮！这一关通关了，下一关已经点亮。' })
      } else {
        setModal({ type: 'error', title: '未通过', message: `预期输出: "${level.expectedOutput}"\n实际输出: "${String(data.output || '').trim()}"` })
      }
    } catch (error) {
      setModal({ type: 'error', title: '错误', message: error.message || '网络错误，请稍后重试' })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="page level-page">
      <button className="ghost-button back" onClick={() => navigate('levels')}>← 返回关卡选择</button>
      <section className="level-card card">
        <div className="problem">
          <h1 className="problem-title">{level.title}</h1>
          <div className="steps">{level.steps.map((step) => <span key={step} className="step">{step}</span>)}<div className="hint">{level.hint}</div><div className="expected">{level.expectedText}</div></div>
        </div>
        <div className="code-section">
          <div className="code-header"><i className="dot red" /><i className="dot yellow" /><i className="dot green" /></div>
          <div className="editor"><div className="line-numbers">{lineNumbers.map((line) => <span key={line} className="line-number">{line}</span>)}</div><textarea className="code-textarea mono" value={code} onChange={(e) => setCode(e.target.value)} spellCheck="false" /></div>
          {outputType !== 'hidden' && <pre className={`output ${outputType} mono`}>{output}</pre>}
          <div className="actions"><button className="run-button" disabled={running} onClick={runCode}>{running ? '运行中...' : '运行'}</button><button className="submit-button" disabled={submitting} onClick={submitCode}>{submitting ? '提交中...' : '提交'}</button></div>
        </div>
      </section>
      {modal && <div className="modal-mask" onClick={() => setModal(null)}><div className="modal card" onClick={(e) => e.stopPropagation()}><div className={`modal-icon ${modal.type}`}>{modal.type === 'success' ? '✓' : '!'}</div><h2 className="modal-title">{modal.title}</h2><p className="modal-message">{modal.message}</p><button className="primary-button modal-button" onClick={() => { setModal(null); if (modal.type === 'success') navigate('levels') }}>关闭</button></div></div>}
    </main>
  )
}

function ChatPage({ chatState, setChatState }) {
  const [activeTab, setActiveTab] = useState('chat')
  const [typing, setTyping] = useState(false)
  const { currentSessionId, messages, question, sessions } = chatState
  const bottomRef = useRef(null)
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, typing])

  const patchChatState = (patch) => setChatState((current) => ({ ...current, ...patch }))
  const updateMessages = (updater) => {
    setChatState((current) => ({
      ...current,
      messages: typeof updater === 'function' ? updater(current.messages) : updater
    }))
  }

  const loadSessions = async () => {
    try {
      const result = await api.get('/ai/sessions')
      patchChatState({
        sessions: (result.data?.sessions || []).map((item) => ({
          ...item,
          preview: item.first_question || item.preview || `会话 ${String(item.session_id || '').slice(0, 8)}...`
        }))
      })
    } catch {
      patchChatState({ sessions: [] })
    }
  }

  const loadSessionHistory = async (sessionId) => {
    try {
      const result = await api.get('/ai/history', { session_id: sessionId })
      const historyMessages = (result.data || []).flatMap((record) => [
        { content: record.question, isUser: true },
        { content: record.answer, isUser: false }
      ]).filter((message) => message.content)
      patchChatState({
        currentSessionId: sessionId,
        messages: historyMessages.length ? historyMessages : [{ content: CHAT_WELCOME, isUser: false }]
      })
      setActiveTab('chat')
    } catch (error) {
      toast(error.message || '历史对话加载失败')
    }
  }

  const sendMessage = async () => {
    const text = question.trim()
    if (!text || typing) return
    updateMessages((current) => [...current, { content: text, isUser: true }, { content: '', isUser: false }])
    patchChatState({ question: '' })
    setTyping(true)
    try {
      await api.streamPost('/ai/chat', { question: text, stream: true, session_id: currentSessionId || null }, (event) => {
        if (event.session_id) patchChatState({ currentSessionId: event.session_id })
        if (!event.content || event.content === '[END]') return
        updateMessages((current) => current.map((item, index) => index === current.length - 1 ? { ...item, content: `${item.content}${event.content}` } : item))
      })
      loadSessions()
    } catch (error) {
      updateMessages((current) => current.map((item, index) => index === current.length - 1 ? { ...item, content: item.content || error.message || '抱歉，AI 服务暂时不可用，请稍后再试。' } : item))
    } finally {
      setTyping(false)
    }
  }

  const startNewSession = () => {
    patchChatState({ currentSessionId: '', messages: [{ content: CHAT_WELCOME, isUser: false }], question: '' })
    setActiveTab('chat')
  }

  return (
    <main className="page chat-page">
      <div className="tabs">
        <button className={activeTab === 'chat' ? 'tab active' : 'tab'} onClick={() => setActiveTab('chat')}>对话</button>
        <button className={activeTab === 'history' ? 'tab active' : 'tab'} onClick={() => { setActiveTab('history'); loadSessions() }}>历史记录</button>
      </div>
      {activeTab === 'chat' ? (
        <section className="chat-panel">
          <div className="chat-body">
            {messages.map((message, index) => (
              <div key={index} className={`message-row ${message.isUser ? 'user-row' : 'ai-row'}`}>
                {!message.isUser && <img className="avatar" src={assets.chatOtter} alt="" />}
                <div className={`bubble ${message.isUser ? 'user' : 'ai'}`}>{message.content}</div>
                {message.isUser && <img className="avatar" src={assets.user} alt="" />}
              </div>
            ))}
            {typing && <div className="message-row ai-row"><img className="avatar" src={assets.chatOtter} alt="" /><div className="typing"><i className="typing-dot" /><i className="typing-dot delay-1" /><i className="typing-dot delay-2" /></div></div>}
            <div ref={bottomRef} />
          </div>
          <div className="input-bar">
            <input className="question-input" value={question} onChange={(e) => patchChatState({ question: e.target.value })} onKeyDown={(e) => e.key === 'Enter' && sendMessage()} placeholder="请输入消息..." />
            <button className={`send-btn ${typing || !question.trim() ? 'disabled' : ''}`} onClick={sendMessage}>发送</button>
          </div>
        </section>
      ) : (
        <section className="history-panel">
          <div className="history-toolbar"><h2 className="history-title">历史对话</h2><button className="new-session-btn" onClick={startNewSession}>＋新会话</button></div>
          <div className="history-list">
            {sessions.length ? sessions.map((session) => (
              <button key={session.session_id} className="session-card" onClick={() => loadSessionHistory(session.session_id)}>
                <span className="session-label">{session.preview}</span><span className="session-meta">{session.message_count || 0} 条消息</span>
                <span className="session-arrow">›</span>
              </button>
            )) : <div className="empty">暂无历史对话</div>}
          </div>
        </section>
      )}
    </main>
  )
}

function RecordsPage() {
  const today = new Date()
  const [year, setYear] = useState(today.getFullYear())
  const [monthIndex, setMonthIndex] = useState(today.getMonth())
  const [selectedDate, setSelectedDate] = useState(formatDate(today))
  const [records, setRecords] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const selectedRecord = records[selectedDate] || null
  const [form, setForm] = useState({ content: '', duration: '', mood: '一般' })
  const monthKey = `${year}-${String(monthIndex + 1).padStart(2, '0')}`
  const monthRecords = Object.fromEntries(Object.entries(records).filter(([date]) => date.startsWith(monthKey)))
  const cells = buildMonthCalendar(year, monthIndex, monthRecords)

  useEffect(() => {
    let active = true
    setLoading(true)
    api.get('/study-records', { month: monthKey })
      .then((result) => {
        if (!active) return
        const nextRecords = (result.data?.records || []).reduce((resultMap, record) => {
          resultMap[record.date] = record
          return resultMap
        }, {})
        setRecords(nextRecords)
      })
      .catch((error) => {
        if (active) toast(error.message || '学习记录加载失败')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [monthKey])

  useEffect(() => setForm({ content: selectedRecord?.content || '', duration: selectedRecord?.duration ? String(selectedRecord.duration) : '', mood: selectedRecord?.mood || '一般' }), [selectedDate, selectedRecord])
  const moveMonth = (offset) => { const date = new Date(year, monthIndex + offset, 1); setYear(date.getFullYear()); setMonthIndex(date.getMonth()); setSelectedDate(formatDate(date)) }
  const saveRecord = async () => {
    if (!form.content.trim()) return toast('请先写下学习内容')
    const record = { date: selectedDate, content: form.content.trim(), duration: Math.max(0, Number(form.duration || 0)), mood: form.mood, updatedAt: new Date().toISOString() }
    setSaving(true)
    try {
      await api.post('/study-records', { study_date: selectedDate, content: record.content, duration: record.duration, mood: record.mood })
      setRecords((current) => ({ ...current, [selectedDate]: record }))
      toast('已保存打卡')
    } catch (error) {
      toast(error.message || '学习记录保存失败')
    } finally {
      setSaving(false)
    }
  }
  const deleteRecord = async () => {
    if (!selectedRecord || !window.confirm('确定删除这一天的学习记录吗？')) return
    setDeleting(true)
    try {
      await api.del(`/study-records/${selectedDate}`)
      setRecords((current) => {
        const next = { ...current }
        delete next[selectedDate]
        return next
      })
      toast('已删除打卡')
    } catch (error) {
      toast(error.message || '学习记录删除失败')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <main className="page records-page">
      <header className="calendar-header"><div className="month-block"><h1 className="month-title">{year}年{monthIndex + 1}月</h1><span className="month-meta">{loading ? '记录加载中...' : `本月已打卡 ${Object.keys(monthRecords).length} 天`}</span><div className="month-controls"><button className="icon-button" disabled={loading} onClick={() => moveMonth(-1)}>‹</button><button className="icon-button" disabled={loading} onClick={() => moveMonth(1)}>›</button></div></div></header>
      <div className="toolbar"><button className="today-button" disabled={loading} onClick={() => { const now = new Date(); setYear(now.getFullYear()); setMonthIndex(now.getMonth()); setSelectedDate(formatDate(now)) }}>今天</button></div>
      <section className="calendar card"><div className="weekday-row">{['日', '一', '二', '三', '四', '五', '六'].map((day) => <span key={day} className="weekday">{day}</span>)}</div><div className="calendar-grid">{cells.map((cell) => <button key={cell.date} className={`day-cell ${cell.isCurrentMonth ? '' : 'muted'} ${cell.date === selectedDate ? 'selected' : ''} ${cell.date === formatDate(today) ? 'today' : ''}`} onClick={() => setSelectedDate(cell.date)}><span className="day-number">{cell.day}</span>{cell.hasRecord && <span className="record-dot" />}</button>)}</div></section>
      <section className="record-editor card"><div className="editor-header"><div><h2 className="editor-title">{selectedRecord ? '编辑打卡' : '今日打卡'}</h2><span className="editor-date">{selectedDate}</span></div>{selectedRecord && <button className="delete-button" disabled={loading || saving || deleting} onClick={deleteRecord}>{deleting ? '删除中...' : '删除'}</button>}</div><textarea className="content-input" disabled={loading || saving || deleting} value={form.content} onChange={(e) => setForm({ ...form, content: e.target.value })} placeholder="记录今天学了什么，例如：完成 for 循环练习，理解了 range 的用法。" /><div className="form-row"><span className="form-label">学习时长</span><div className="duration-control"><input className="duration-input" disabled={loading || saving || deleting} value={form.duration} onChange={(e) => setForm({ ...form, duration: e.target.value })} placeholder="0" /><span className="duration-unit">分钟</span></div></div><div className="form-row mood-row"><span className="form-label">状态</span><div className="mood-list">{['轻松', '一般', '有点难'].map((mood) => <button key={mood} disabled={loading || saving || deleting} className={form.mood === mood ? 'mood-chip active' : 'mood-chip'} onClick={() => setForm({ ...form, mood })}>{mood}</button>)}</div></div><button className="primary-button save-button-wide" disabled={loading || saving || deleting} onClick={saveRecord}>{saving ? '保存中...' : selectedRecord ? '保存修改' : '完成打卡'}</button></section>
    </main>
  )
}

function SettingsPage({ navigate }) {
  const [settings, setSettings] = useState(loadSettings())
  const [nicknameInput, setNicknameInput] = useState(settings.nickname)
  const [baseUrlInput, setBaseUrlInput] = useState(getBaseUrl())
  const [developerTapCount, setDeveloperTapCount] = useState(0)
  const [showDeveloperSettings, setShowDeveloperSettings] = useState(false)
  const [progress, setProgress] = useState(getProgressSummary(getHighestCompleted()))
  const saveSetting = (key, value) => { setStored(key, value); setSettings(loadSettings()) }

  useEffect(() => {
    api.get('/levels')
      .then((result) => {
        const completed = Number(result.data?.summary?.completed || 0)
        setProgress(result.data?.summary || getProgressSummary(completed))
      })
      .catch(() => setProgress(getProgressSummary(getHighestCompleted())))
  }, [])

  return (
    <main className={`page settings-page ${settings.eyeProtectionEnabled ? 'eye' : ''}`}>
      <img className="decoration star" src={assets.star} alt="" /><img className="decoration cloud" src={assets.cloud} alt="" />
      <section className="profile-panel"><img className="avatar" src={assets.user} alt="" /><div className="profile-copy"><span className="hello">我的设置</span><h1 className="nickname">{settings.nickname}</h1><span className="progress-text">已点亮 {progress.completed} / {progress.total} 关 · {progress.goalText}</span><div className="progress-track"><div className="progress-fill" style={{ width: `${progress.percent}%` }} /></div></div></section>
      <SettingsSection title="我的资料"><div className="setting-row edit-row last"><SettingCopy label="昵称" help="2-12 个字，展示在学习页里" /><div className="edit-control"><input className="nickname-input" value={nicknameInput} onChange={(e) => setNicknameInput(e.target.value)} maxLength={12} /><button className="save-button" onClick={() => { const value = nicknameInput.trim(); if (value.length < 2) return toast('昵称需要 2-12 个字'); setStored('nickname', value); setSettings(loadSettings()) }}>保存</button></div></div></SettingsSection>
      <SettingsSection title="学习体验"><OptionRow label="代码字号" help="写代码时看得更舒服" options={[['small', '小'], ['medium', '中'], ['large', '大']]} value={settings.codeSize} onChange={(v) => saveSetting('codeSize', v)} /><OptionRow label="提示方式" help="遇到难题时给多少提醒" wide options={[['low', '少提示'], ['normal', '普通'], ['high', '多一点']]} value={settings.hintLevel} onChange={(v) => saveSetting('hintLevel', v)} /><SwitchRow label="自动保存代码" help="离开页面也不怕丢失练习" checked={settings.autoSaveCodeEnabled} onChange={(v) => saveSetting('autoSaveCodeEnabled', v)} /><SwitchRow label="鼓励动画" help="通关后给一点小奖励反馈" checked={settings.encourageAnimationEnabled} onChange={(v) => saveSetting('encourageAnimationEnabled', v)} /><SwitchRow label="提示音效" help="按钮和通关声音开关" checked={settings.soundEnabled} onChange={(v) => saveSetting('soundEnabled', v)} last /></SettingsSection>
      <SettingsSection title="护眼与专注"><SwitchRow label="护眼模式" help="把背景换成更柔和的颜色" checked={settings.eyeProtectionEnabled} onChange={(v) => saveSetting('eyeProtectionEnabled', v)} /><SwitchRow label="休息提醒" help="学习一会儿，记得放松眼睛" checked={settings.restReminderEnabled} onChange={(v) => saveSetting('restReminderEnabled', v)} last /></SettingsSection>
      <SettingsSection title="AI 小助手"><OptionRow label="回答风格" help="选择小助手解释得多还是少" wide options={[['simple', '简单点'], ['detailed', '详细点']]} value={settings.aiReplyStyle} onChange={(v) => saveSetting('aiReplyStyle', v)} /><SwitchRow label="先给提示" help="尽量不直接说答案" checked={settings.aiHintFirst} onChange={(v) => saveSetting('aiHintFirst', v)} /><ActionRow label="清空临时对话" help="不影响账号里的历史记录" onClick={() => { ['chat_cache', 'chat_draft', 'current_session_id'].forEach(removeStored); toast('已清空') }} last /></SettingsSection>
      <SettingsSection title="账号与数据"><ActionRow danger label="重置本机关卡缓存" help="不会删除账号中的打卡记录" onClick={() => { if (window.confirm('只会清空本机关卡进度缓存，不会删除账号中的打卡记录。')) { removeStored('level_progress'); setProgress(getProgressSummary(0)); toast('本机关卡缓存已重置') } }} /><div className="setting-row last"><SettingCopy label="退出登录" help="离开当前账号" /><button className="logout-button" onClick={() => { removeStored('access_token'); removeStored('refresh_token'); navigate('auth') }}>退出</button></div></SettingsSection>
      {showDeveloperSettings && <SettingsSection title="开发者设置"><div className="setting-row edit-row last"><SettingCopy label="后端接口" help="调试服务地址，平时不用改" /><div className="url-control"><input className="url-input" value={baseUrlInput} onChange={(e) => setBaseUrlInput(e.target.value)} placeholder="http://localhost:8000/api/v1" /><button className="save-button" onClick={() => { if (!/^https?:\/\/.+/.test(baseUrlInput)) return toast('请输入 http 或 https 地址'); setStored('baseUrl', baseUrlInput.replace(/\/$/, '')); toast('接口地址已保存') }}>保存</button></div></div></SettingsSection>}
      <button className="version" onClick={() => { const count = developerTapCount + 1; setDeveloperTapCount(count); if (count >= 5) setShowDeveloperSettings(true) }}>Python 学习小程序 v1.0</button>
    </main>
  )
}

function SettingsSection({ title, children }) {
  return <section className="section"><h2 className="section-title">{title}</h2><div className="setting-group">{children}</div></section>
}

function SettingCopy({ label, help, danger }) {
  return <div className="setting-copy"><span className={`setting-label ${danger ? 'danger-text' : ''}`}>{label}</span><span className="setting-help">{help}</span></div>
}

function OptionRow({ label, help, options, value, onChange, wide }) {
  return <div className="setting-row"><SettingCopy label={label} help={help} /><div className={`segmented ${wide ? 'wide' : ''}`}>{options.map(([key, text]) => <button key={key} className={value === key ? 'segment active' : 'segment'} onClick={() => onChange(key)}>{text}</button>)}</div></div>
}

function SwitchRow({ label, help, checked, onChange, last }) {
  return <div className={`setting-row ${last ? 'last' : ''}`}><SettingCopy label={label} help={help} /><label className="switch"><input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} /><span /></label></div>
}

function ActionRow({ label, help, onClick, danger, last }) {
  return <button className={`setting-row action-row ${last ? 'last' : ''}`} onClick={onClick}><SettingCopy label={label} help={help} danger={danger} /><span className={`row-arrow ${danger ? 'danger-text' : ''}`}>›</span></button>
}

export default App
