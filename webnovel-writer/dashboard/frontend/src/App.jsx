import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { createTask, fetchCurrentTask, fetchJSON, sendChat, subscribeSSE } from './api.js'
import {
  buildChatReplyModel,
  buildRightSidebarModel,
  buildTopBarModel,
  createInitialWorkbenchState,
  normalizeWorkbenchPage,
} from './workbench/data.js'
import TopBar from './workbench/TopBar.jsx'
import RightSidebar from './workbench/RightSidebar.jsx'
import OverviewPage from './workbench/OverviewPage.jsx'
import ChapterPage from './workbench/ChapterPage.jsx'
import OutlinePage from './workbench/OutlinePage.jsx'
import SettingPage from './workbench/SettingPage.jsx'

export default function App() {
  const [workbenchState, setWorkbenchState] = useState(() => createInitialWorkbenchState())
  const [connected, setConnected] = useState(false)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [sidebarContext, setSidebarContext] = useState({
    page: 'overview',
    selectedPath: null,
    dirty: false,
  })
  const [chatPending, setChatPending] = useState(false)
  const [reloadKeys, setReloadKeys] = useState({
    chapters: 0,
    outline: 0,
    settings: 0,
  })
  const activeTaskIdRef = useRef(null)

  const loadSummary = useCallback(async () => {
    try {
      const summary = await fetchJSON('/api/workbench/summary')
      setWorkbenchState(prev => ({ ...prev, summary }))
      setLoadError('')
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : '加载工作台摘要失败')
    } finally {
      setLoading(false)
    }
  }, [])

  const loadCurrentTask = useCallback(async () => {
    try {
      const task = await fetchCurrentTask()
      setWorkbenchState(prev => ({ ...prev, currentTask: task }))
    } catch {
      // Phase 1 下任务接口失败时保持前端占位默认值
    }
  }, [])

  useEffect(() => {
    loadSummary()
    loadCurrentTask()
  }, [loadCurrentTask, loadSummary])

  useEffect(() => {
    const unsubscribe = subscribeSSE(
      (event) => {
        if (event?.type === 'file.changed') {
          loadSummary()
          return
        }
        if (event?.type === 'task.updated' && event.task) {
          const task = event.task
          activeTaskIdRef.current = task.id
          setWorkbenchState(prev => ({
            ...prev,
            currentTask: {
              status: task.status,
              task: task.action?.label || prev.currentTask.task,
              step:
                task.status === 'pending'
                  ? '等待执行'
                  : task.status === 'running'
                    ? '执行中'
                    : task.status === 'completed'
                      ? '执行完成'
                      : task.status === 'failed'
                        ? '执行失败'
                        : prev.currentTask.step,
              updatedAt: task.updatedAt,
              logs: task.logs || [],
              result: task.result ?? null,
              error: task.error ?? null,
            },
            chatMessages:
              prev.currentTask.updatedAt !== task.updatedAt &&
              (task.status === 'completed' || task.status === 'failed')
                ? [
                    ...prev.chatMessages,
                    {
                      role: 'assistant',
                      kind: task.status === 'completed' ? 'task-success' : 'task-error',
                      content:
                        task.status === 'completed'
                          ? `${task.action?.label || '任务'} 已完成。`
                          : `${task.action?.label || '任务'} 执行失败。`,
                      reason:
                        task.status === 'completed'
                          ? task.result?.summary || '任务已完成并刷新相关页面。'
                          : task.error || '任务执行失败，请查看任务日志。',
                      scope: {
                        page: sidebarContext?.page ?? null,
                        selectedPath: sidebarContext?.selectedPath ?? null,
                      },
                    },
                  ]
                : prev.chatMessages,
          }))
          if (task.status === 'completed') {
            loadSummary()
            triggerWorkspaceRefresh(task.action?.type)
          }
        }
      },
      {
        onOpen: () => setConnected(true),
        onError: () => setConnected(false),
      },
    )
    return () => {
      unsubscribe()
      setConnected(false)
    }
  }, [loadSummary, sidebarContext, triggerWorkspaceRefresh])

  useEffect(() => {
    return () => {
      activeTaskIdRef.current = null
    }
  }, [])

  const activePage = normalizeWorkbenchPage(workbenchState.page)
  useEffect(() => {
    setSidebarContext(prev => ({
      ...prev,
      page: activePage,
    }))
  }, [activePage])

  const topBarModel = useMemo(
    () => buildTopBarModel({
      page: activePage,
      summary: workbenchState.summary,
      currentTask: workbenchState.currentTask,
    }),
    [activePage, workbenchState.currentTask, workbenchState.summary],
  )

  const sidebarModel = useMemo(
    () => buildRightSidebarModel({
      context: sidebarContext,
      chatMessages: workbenchState.chatMessages,
      suggestedActions: workbenchState.suggestedActions,
      currentTask: workbenchState.currentTask,
      chatPending,
    }),
    [chatPending, sidebarContext, workbenchState.chatMessages, workbenchState.currentTask, workbenchState.suggestedActions],
  )

  const pageProps = {
    summary: workbenchState.summary,
    loading,
    loadError,
    onRetry: loadSummary,
    onContextChange: setSidebarContext,
  }

  const triggerWorkspaceRefresh = useCallback((actionType) => {
    const targetPage =
      actionType === 'write_chapter' || actionType === 'review_chapter'
        ? 'chapters'
        : actionType === 'plan_outline'
          ? 'outline'
          : actionType === 'inspect_setting'
            ? 'settings'
            : null

    if (!targetPage) return

    setReloadKeys(prev => ({
      ...prev,
      [targetPage]: prev[targetPage] + 1,
    }))
  }, [])

  const handleSendMessage = useCallback(async (message) => {
    const trimmed = message.trim()
    if (!trimmed) return

    const userMessage = { role: 'user', content: trimmed }
    setWorkbenchState(prev => ({
      ...prev,
      chatMessages: [...prev.chatMessages, userMessage],
    }))
    setChatPending(true)

    try {
      const response = await sendChat(trimmed, sidebarContext ?? {})
      const replyModel = buildChatReplyModel(response, sidebarContext)
      setWorkbenchState(prev => ({
        ...prev,
        chatMessages: [
          ...prev.chatMessages,
          {
            role: 'assistant',
            kind: 'reply',
            content: replyModel.reply,
            reason: replyModel.reason,
            scope: replyModel.scope,
          },
        ],
        suggestedActions: replyModel.suggestedActions,
      }))
    } catch (error) {
      setWorkbenchState(prev => ({
        ...prev,
        chatMessages: [
          ...prev.chatMessages,
          {
            role: 'assistant',
            kind: 'error',
            content: `发送失败：${error instanceof Error ? error.message : '未知错误'}`,
          },
        ],
      }))
    } finally {
      setChatPending(false)
    }
  }, [sidebarContext])

  const handleRunAction = useCallback((action) => {
    async function run() {
      if (!action) return
      const taskName = action.label || '执行动作'

      setWorkbenchState(prev => ({
        ...prev,
        currentTask: {
          status: 'pending',
          task: taskName,
          step: '任务创建中',
          updatedAt: new Date().toISOString(),
          logs: [],
          result: null,
          error: null,
        },
        suggestedActions: prev.suggestedActions.filter(item => item !== action),
      }))

      try {
        const createdTask = await createTask(action, sidebarContext ?? {})
        activeTaskIdRef.current = createdTask.id
        setWorkbenchState(prev => ({
          ...prev,
          currentTask: {
            status: createdTask.status,
            task: createdTask.action?.label || taskName,
            step: createdTask.status === 'pending' ? '等待执行' : '执行中',
            updatedAt: createdTask.updatedAt,
            logs: createdTask.logs || [],
            result: createdTask.result ?? null,
            error: createdTask.error ?? null,
          },
          chatMessages: [
            ...prev.chatMessages,
            {
              role: 'assistant',
              kind: 'task-update',
              content: `已创建任务：${createdTask.action?.label || taskName}`,
              reason: '动作卡已转为真实任务，后续状态会实时更新。',
              scope: {
                page: sidebarContext?.page ?? null,
                selectedPath: sidebarContext?.selectedPath ?? null,
              },
            },
          ],
        }))
      } catch (error) {
        setWorkbenchState(prev => ({
          ...prev,
          currentTask: {
            status: 'failed',
            task: taskName,
            step: '任务创建失败',
            updatedAt: new Date().toISOString(),
            logs: [],
            result: null,
            error: error instanceof Error ? error.message : '未知错误',
          },
        }))
      }
    }
    run()
  }, [sidebarContext])

  return (
    <div className="workbench-shell">
      <TopBar
        model={topBarModel}
        connected={connected}
        onSelectPage={page => setWorkbenchState(prev => ({ ...prev, page }))}
      />

      <div className="workbench-body">
        <div className="workbench-main">
          {activePage === 'overview' && <OverviewPage {...pageProps} />}
          {activePage === 'chapters' && <ChapterPage {...pageProps} reloadToken={reloadKeys.chapters} />}
          {activePage === 'outline' && <OutlinePage {...pageProps} reloadToken={reloadKeys.outline} />}
          {activePage === 'settings' && <SettingPage {...pageProps} reloadToken={reloadKeys.settings} />}
        </div>

        <RightSidebar
          model={sidebarModel}
          onSendMessage={handleSendMessage}
          onRunAction={handleRunAction}
        />
      </div>
    </div>
  )
}
