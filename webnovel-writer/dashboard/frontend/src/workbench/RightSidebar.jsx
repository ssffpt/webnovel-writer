import { useState } from 'react'

export default function RightSidebar({ model, onSendMessage, onRunAction, onRetryAction, onNavigateToPage }) {
  const [message, setMessage] = useState('')

  function handleSubmit(event) {
    event.preventDefault()
    if (!message.trim()) return
    onSendMessage?.(message)
    setMessage('')
  }

  return (
    <aside className="workbench-right">
      <section className="workbench-panel">
        <h3>当前上下文</h3>
        {model.context ? (
          <ul className="workbench-meta-list">
            <li>页面：{model.context.page}</li>
            <li>对象：{model.context.selectedPath || '未选择'}</li>
            <li>未保存：{model.context.dirty ? '是' : '否'}</li>
          </ul>
        ) : (
          <p className="empty-text">暂无上下文。</p>
        )}
      </section>

      <section className="workbench-panel">
        <h3>聊天助手</h3>
        {model.chatMessages.length === 0 ? (
          <p className="empty-text">可以直接输入自然语言需求，例如“帮我规划第二卷”。</p>
        ) : (
          <ul className="workbench-message-list">
            {model.chatMessages.map((message, index) => (
              <li key={`${message.role}-${index}`} className={`workbench-message-item ${message.role}`}>
                <span className="message-role">{message.role === 'assistant' ? 'AI' : '你'}</span>
                <span>{message.content}</span>
                {message.reason ? (
                  <span className="message-reason">推荐原因：{message.reason}</span>
                ) : null}
                {message.navigateTo ? (
                  <button
                    type="button"
                    className="workbench-nav-button message-nav-button"
                    onClick={() => onNavigateToPage?.(message.navigateTo)}
                  >
                    前往${{ chapters: '章节页', outline: '大纲页', settings: '设定页' }[message.navigateTo] || '对应页面'}查看
                  </button>
                ) : null}
                {message.scope?.page || message.scope?.selectedPath ? (
                  <span className="message-scope">
                    作用范围：{message.scope?.page || '未知页面'}
                    {message.scope?.selectedPath ? ` / ${message.scope.selectedPath}` : ''}
                  </span>
                ) : null}
              </li>
            ))}
          </ul>
        )}
        <form className="workbench-chat-form" onSubmit={handleSubmit}>
          <textarea
            className="workbench-chat-input"
            value={message}
            onChange={event => setMessage(event.target.value)}
            placeholder="输入你的创作需求…"
            rows={4}
          />
          <button type="submit" className="workbench-primary-button" disabled={model.chatPending}>
            {model.chatPending ? '发送中…' : '发送'}
          </button>
        </form>
      </section>

      <section className="workbench-panel">
        <h3>动作卡</h3>
        {model.suggestedActions.length === 0 ? (
          <p className="empty-text">当前没有待执行动作。</p>
        ) : (
          <ul className="workbench-action-list">
            {model.suggestedActions.map((action, index) => (
              <li key={`${action.type}-${index}`} className="workbench-action-item">
                <div>
                  <div className="action-title">{action.label}</div>
                  <div className="chapter-file-meta">{action.type}</div>
                </div>
                <button type="button" className="workbench-primary-button" onClick={() => onRunAction?.(action)}>
                  执行
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="workbench-panel">
        <h3>当前任务</h3>
        <p>状态：{model.currentTask.status}</p>
        <p>任务：{model.currentTask.task || '空闲'}</p>
        <p>步骤：{model.currentTask.step || '暂无'}</p>
        <p>更新时间：{model.currentTask.updatedAt || '暂无'}</p>
        {model.currentTask.error ? <p className="error-text">错误：{model.currentTask.error}</p> : null}
        {model.currentTask.completionNotice ? (
          <div className={`workbench-notice ${model.currentTask.completionNotice.hint === 'navigate' ? 'notice-navigate' : 'notice-refresh'}`}>
            <span>{model.currentTask.completionNotice.message}</span>
            {model.currentTask.completionNotice.hint === 'navigate' && model.currentTask.completionNotice.targetPage ? (
              <button
                type="button"
                className="workbench-nav-button notice-nav-button"
                onClick={() => onNavigateToPage?.(model.currentTask.completionNotice.targetPage)}
              >
                前往${{ chapters: '章节页', outline: '大纲页', settings: '设定页' }[model.currentTask.completionNotice.targetPage] || '对应页面'}
              </button>
            ) : null}
          </div>
        ) : null}
        {model.currentTask.recoveryTips && model.currentTask.recoveryTips.length > 0 ? (
          <ul className="workbench-recovery-tips">
            {model.currentTask.recoveryTips.map((tip, index) => (
              <li key={`tip-${index}`} className="recovery-tip-item">{tip}</li>
            ))}
          </ul>
        ) : null}
        {model.currentTask.status === 'failed' && onRetryAction ? (
          <button type="button" className="workbench-primary-button" onClick={onRetryAction}>
            重试
          </button>
        ) : null}
        {model.currentTask.result?.summary && !model.currentTask.completionNotice ? (
          <p className="empty-text">结果：{model.currentTask.result.summary}</p>
        ) : null}
        {model.currentTask.logs.length > 0 ? (
          <ul className="workbench-task-log-list">
            {model.currentTask.logs.slice(-5).map((entry, index) => (
              <li key={`${entry.createdAt || 'log'}-${index}`} className="workbench-task-log-item">
                <span className="chapter-file-meta">{entry.createdAt || 'now'}</span>
                <span>{entry.message}</span>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    </aside>
  )
}
