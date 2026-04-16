import { useState, useRef, useEffect } from 'react'

const PAGE_LABELS = { chapters: '章节页', outline: '大纲页', settings: '设定页' }

export default function AIAssistant({
  chatMessages,
  suggestedActions,
  currentTask,
  chatPending,
  onSendMessage,
  onRunAction,
  onRetryAction,
  onNavigateToPage,
  visible,
  onToggle,
}) {
  const [message, setMessage] = useState('')
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  function handleSubmit(event) {
    event.preventDefault()
    if (!message.trim()) return
    onSendMessage?.(message)
    setMessage('')
  }

  return (
    <>
      {/* Floating button */}
      <button
        type="button"
        className="ai-fab"
        onClick={() => onToggle?.()}
        aria-label="AI 助手"
      >
        💬
      </button>

      {/* Expanded dialog */}
      {visible && (
        <div className="ai-dialog">
          <div className="ai-dialog-header">
            <span>AI 助手</span>
            <button
              type="button"
              className="ai-dialog-close"
              onClick={() => onToggle?.()}
              aria-label="关闭"
            >
              ✕
            </button>
          </div>

          <div className="ai-dialog-messages">
            {chatMessages.length === 0 ? (
              <p className="empty-text">可以直接输入自然语言需求，例如"帮我规划第二卷"。</p>
            ) : (
              <ul className="workbench-message-list">
                {chatMessages.map((msg, index) => (
                  <li key={`${msg.role}-${index}`} className={`workbench-message-item ${msg.role}`}>
                    <span className="message-role">{msg.role === 'assistant' ? 'AI' : '你'}</span>
                    <span>{msg.content}</span>
                    {msg.reason ? (
                      <span className="message-reason">推荐原因：{msg.reason}</span>
                    ) : null}
                    {msg.navigateTo ? (
                      <button
                        type="button"
                        className="workbench-nav-button message-nav-button"
                        onClick={() => onNavigateToPage?.(msg.navigateTo)}
                      >
                        前往{PAGE_LABELS[msg.navigateTo] || '对应页面'}查看
                      </button>
                    ) : null}
                    {msg.scope?.page || msg.scope?.selectedPath ? (
                      <span className="message-scope">
                        作用范围：{msg.scope?.page || '未知页面'}
                        {msg.scope?.selectedPath ? ` / ${msg.scope.selectedPath}` : ''}
                      </span>
                    ) : null}
                  </li>
                ))}
                <div ref={messagesEndRef} />
              </ul>
            )}
          </div>

          {/* Action cards */}
          {suggestedActions && suggestedActions.length > 0 && (
            <div className="ai-dialog-actions">
              <ul className="workbench-action-list">
                {suggestedActions.map((action, index) => (
                  <li key={`${action.type}-${index}`} className="workbench-action-item">
                    <div>
                      <div className="action-title">{action.label}</div>
                      <div className="chapter-file-meta">{action.type}</div>
                    </div>
                    <button
                      type="button"
                      className="workbench-primary-button"
                      onClick={() => onRunAction?.(action)}
                    >
                      执行
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Task status */}
          {currentTask && currentTask.status !== 'idle' && (
            <div className="ai-dialog-task">
              <div className="ai-dialog-task-header">
                <strong>任务：{currentTask.task || '空闲'}</strong>
                <span className={`ai-task-status ai-task-status-${currentTask.status}`}>
                  {currentTask.status === 'pending' ? '等待中' :
                   currentTask.status === 'running' ? '执行中' :
                   currentTask.status === 'completed' ? '已完成' :
                   currentTask.status === 'failed' ? '失败' : currentTask.status}
                </span>
              </div>
              {currentTask.error ? <p className="error-text">错误：{currentTask.error}</p> : null}
              {currentTask.completionNotice ? (
                <div className={`workbench-notice ${currentTask.completionNotice.hint === 'navigate' ? 'notice-navigate' : 'notice-refresh'}`}>
                  <span>{currentTask.completionNotice.message}</span>
                  {currentTask.completionNotice.hint === 'navigate' && currentTask.completionNotice.targetPage ? (
                    <button
                      type="button"
                      className="workbench-nav-button notice-nav-button"
                      onClick={() => onNavigateToPage?.(currentTask.completionNotice.targetPage)}
                    >
                      前往{PAGE_LABELS[currentTask.completionNotice.targetPage] || '对应页面'}
                    </button>
                  ) : null}
                </div>
              ) : null}
              {currentTask.recoveryTips && currentTask.recoveryTips.length > 0 ? (
                <ul className="workbench-recovery-tips">
                  {currentTask.recoveryTips.map((tip, index) => (
                    <li key={`tip-${index}`} className="recovery-tip-item">{tip}</li>
                  ))}
                </ul>
              ) : null}
              {currentTask.status === 'failed' && onRetryAction ? (
                <button type="button" className="workbench-primary-button" onClick={onRetryAction}>
                  重试
                </button>
              ) : null}
              {currentTask.result?.summary && !currentTask.completionNotice ? (
                <p className="empty-text">结果：{currentTask.result.summary}</p>
              ) : null}
              {currentTask.logs && currentTask.logs.length > 0 ? (
                <ul className="workbench-task-log-list">
                  {currentTask.logs.slice(-5).map((entry, index) => (
                    <li key={`${entry.createdAt || 'log'}-${index}`} className="workbench-task-log-item">
                      <span className="chapter-file-meta">{entry.createdAt || 'now'}</span>
                      <span>{entry.message}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          )}

          {/* Input area */}
          <form className="ai-dialog-input" onSubmit={handleSubmit}>
            <textarea
              value={message}
              onChange={event => setMessage(event.target.value)}
              placeholder="输入你的创作需求…"
              rows={2}
            />
            <button type="submit" className="workbench-primary-button" disabled={chatPending}>
              {chatPending ? '发送中…' : '发送'}
            </button>
          </form>
        </div>
      )}
    </>
  )
}
