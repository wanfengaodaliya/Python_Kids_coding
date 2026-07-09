export function getStored(key, fallback = null) {
  try {
    const raw = localStorage.getItem(key)
    return raw === null ? fallback : JSON.parse(raw)
  } catch {
    return fallback
  }
}

export function setStored(key, value) {
  localStorage.setItem(key, JSON.stringify(value))
}

export function removeStored(key) {
  localStorage.removeItem(key)
}

export function formatDate(date) {
  const pad = (num) => String(num).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

export function buildMonthCalendar(year, monthIndex, records = {}) {
  const dayMs = 24 * 60 * 60 * 1000
  const firstDay = new Date(year, monthIndex, 1)
  const start = new Date(firstDay.getTime() - firstDay.getDay() * dayMs)

  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start.getTime() + index * dayMs)
    const dateText = formatDate(date)
    return {
      date: dateText,
      day: date.getDate(),
      isCurrentMonth: date.getMonth() === monthIndex,
      hasRecord: Boolean(records[dateText]),
      record: records[dateText] || null
    }
  })
}
