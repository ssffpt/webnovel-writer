import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  createTask,
  fetchCurrentTask,
  fetchJSON,
  fetchProjects,
  fetchRecentActivity,
  sendChat,
  subscribeSSE,
  switchProject as switchProjectAPI,
} from './api.js'
import {
  buildChatReplyModel,
  buildCompletionNotice,
  buildTopBarModel,
  createInitialWorkbenchState,
  getProjectStatus,
  normalizeWorkbenchPage,
  resolveTargetPage,
  shouldConfirmAction,
} from './workbench/data.js'
import TopBar from './workbench/TopBar.jsx'
import AIAssistant from './workbench/AIAssistant.jsx'
import OverviewPage from './workbench/OverviewPage.jsx'
import ChapterPage from './workbench/ChapterPage.jsx'
import OutlinePage from './workbench/OutlinePage.jsx'
import SettingPage from './workbench/SettingPage.jsx'

// --- Dialogs ---

function ConflictDialog({ file, onReload, onKeep }) {
  return (
    <div className="conflict-dialog-overlay">
      <div className="conflict-dialog">
        <h3>文件已变更</h3>
        <p>{file} 已被外部修改，当前编辑区有未保存的内容。</p>
        <div className="conflict-dialog-actions">
          <button type="button" className="workbench-primary-button" onClick={onReload}>
            重新加载
          </button>
          <button type="button" className="workbench-nav-button" onClick={onKeep}>
            保留我的修改
          </button>
        </div>
      </div>
    </div>
  )
}

function UnsavedChangesDialog({ visible, message, onConfirm, onCancel }) {
  if (!visible) return null
  return (
    <div className="conflict-dialog-overlay">
      <div className="conflict-dialog">
        <h3>存在未保存内容</h3>
        <p>{message}</p>
        <div className="conflict-dialog-actions">
          <button type="button" className="workbench-primary-button" onClick={onConfirm}>
            继续
          </button>
          <button type="button" className="workbench-nav-button" onClick={onCancel}>
            取消
          </button>
        </div>
      </div>
    </div>
  )
}

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
  const [pageState, setPageState] = useState({
    chapters: { selectedPath: null, dirty: false },
    outline: { selectedPath: null, dirty: false },
    settings: { selectedPath: null, dirty: false },
  })
  const activeTaskIdRef = useRef(null)
  const lastActionRef = useRef(null)
  const topBarRef = useRef(null)
  const mainRef = useRef(null)

  // --- New project state ---
  const [projectStatus, setProjectStatus] = useState('loading') // 'loading'|'no-project'|'incomplete'|'ready'
  const [projectInfo, setProjectInfo] = useState(null)
  const [projects, setProjects] = useState([])
  const [showWizard, setShowWizard] = useState(false)
  const [aiOpen, setAiOpen] = useState(false)
  const [focusModeActive, setFocusModeActive] = useState(false)
  const [recentActivities, setRecentActivities] = useState([])
  const [conflictDialog, setConflictDialog] = useState({ visible: false, file: null })
  const [unsavedDialog, setUnsavedDialog] = useState({
    visible: false,
    message: '',
    onConfirm: null,
  })
  // --- Derived values (must be defined before useEffects that reference them) ---

  const activePage = normalizeWorkbenchPage(workbenchState.page)

  const triggerWorkspaceRefresh = useCallback((actionType) => {
    const targetPage = resolveTargetPage(actionType)
    if (!targetPage) return
    setReloadKeys(prev => ({
      ...prev,
      [targetPage]: prev[targetPage] + 1,
    }))
  }, [])

  // --- Data loading callbacks ---

  const loadSummary = useCallback(async () => {
    try {
      const summary = await fetchJSON('/api/workbench/summary')
      setWorkbenchState(prev => ({ ...prev, summary }))
      setProjectInfo(summary)
      setProjectStatus(getProjectStatus(summary))
      setLoadError('')
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : '加载工作台摘要失败')
      setProjectStatus('no-project')
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

  const reloadCurrentFile = useCallback(() => {
    setReloadKeys(prev => ({
      ...prev,
      [activePage]: prev[activePage] + 1,
    }))
  }, [activePage])

  // --- Action handlers (handleRunAction must be before handleRetryAction) ---

  const closeUnsavedDialog = useCallback(() => {
    setUnsavedDialog({ visible: false, message: '', onConfirm: null })
  }, [])

  const confirmUnsavedDialog = useCallback(() => {
    const callback = unsavedDialog.onConfirm
    closeUnsavedDialog()
    callback?.()
  }, [closeUnsavedDialog, unsavedDialog.onConfirm])

  const executeRunAction = useCallback((action) => {
    async function run() {
      if (!action) return
      const taskName = action.label || '执行动作'

      lastActionRef.current = action
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
          actionType: action.type ?? null,
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
            actionType: createdTask.action?.type ?? action.type ?? null,
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
            actionType: action.type ?? null,
          },
        }))
      }
    }
    run()
  }, [sidebarContext])

  const handleRunAction = useCallback((action) => {
    if (!action) return
    if (shouldConfirmAction(sidebarContext)) {
      setUnsavedDialog({
        visible: true,
        message: '当前页面有未保存的修改，执行动作可能覆盖内容。确定继续？',
        onConfirm: () => executeRunAction(action),
      })
      return
    }
    executeRunAction(action)
  }, [executeRunAction, sidebarContext])

  const handleRetryAction = useCallback(() => {
    if (lastActionRef.current) {
      handleRunAction(lastActionRef.current)
    }
  }, [handleRunAction])

  const handlePageStateChange = useCallback((page, state) => {
    setPageState(prev => ({ ...prev, [page]: { ...prev[page], ...state } }))
  }, [])

  const handleSelectPage = useCallback((page) => {
    if (sidebarContext.dirty) {
      setUnsavedDialog({
        visible: true,
        message: '当前页面有未保存的修改，切换页面可能丢失修改。确定继续？',
        onConfirm: () => setWorkbenchState(prev => ({ ...prev, page })),
      })
      return
    }
    setWorkbenchState(prev => ({ ...prev, page }))
  }, [sidebarContext.dirty])

  const handleNavigateToPage = useCallback((page) => {
    setWorkbenchState(prev => ({ ...prev, page }))
  }, [])

  const handleSwitchProject = useCallback(async (path) => {
    try {
      await switchProjectAPI(path)
      await loadSummary()
      const projectsData = await fetchProjects()
      setProjects(projectsData.projects || [])
    } catch {
      // switch failure - could show an error
    }
  }, [loadSummary])

  const handleCreateNew = useCallback(() => {
    setShowWizard(true)
  }, [])

  const handleWizardClosed = useCallback(() => {
    setShowWizard(false)
  }, [])

  const handleWizardCompleted = useCallback(() => {
    setShowWizard(false)
    loadSummary()
    fetchProjects().then(r => setProjects(r.projects || []))
  }, [loadSummary])

  // --- Effects ---

  useEffect(() => {
    loadSummary()
    loadCurrentTask()
    fetchProjects()
      .then(r => setProjects(r.projects || []))
      .catch(() => {})
    fetchRecentActivity()
      .then(r => setRecentActivities(r.activities || []))
      .catch(() => {})
  }, [loadCurrentTask, loadSummary])

  useEffect(() => {
    const unsubscribe = subscribeSSE(
      (event) => {
        if (event?.type === 'file.changed') {
          const changedFile = event.path || event.file
          if (changedFile && changedFile === pageState[activePage]?.selectedPath) {
            if (pageState[activePage]?.dirty) {
              setConflictDialog({ visible: true, file: changedFile })
            } else {
              reloadCurrentFile()
            }
          }
          loadSummary()
          return
        }
        // Dispatch skill events so SkillFlowPanel can listen
        if (
          event?.type === 'skill.step' ||
          event?.type === 'skill.log' ||
          event?.type === 'skill.completed' ||
          event?.type === 'skill.failed' ||
          event?.type === 'skill.cancelled'
        ) {
          window.dispatchEvent(new CustomEvent('skillEvent', { detail: event }))
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
              actionType: task.action?.type ?? prev.currentTask.actionType ?? null,
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
                          ? buildCompletionNotice({
                              activePage,
                              actionType: task.action?.type,
                              summary: task.result?.summary,
                            }).message
                          : task.error || '任务执行失败，请查看任务日志。',
                      scope: {
                        page: sidebarContext?.page ?? null,
                        selectedPath: sidebarContext?.selectedPath ?? null,
                      },
                      navigateTo:
                        task.status === 'completed' && activePage !== resolveTargetPage(task.action?.type)
                          ? resolveTargetPage(task.action?.type)
                          : null,
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
  }, [activePage, loadSummary, pageState, reloadCurrentFile, sidebarContext, triggerWorkspaceRefresh])

  useEffect(() => {
    const handler = (e) => {
      if (sidebarContext.dirty) {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [sidebarContext.dirty])

  useEffect(() => {
    setSidebarContext(prev => ({
      ...prev,
      page: activePage,
    }))
  }, [activePage])

  // --- Computed models ---

  const topBarModel = useMemo(
    () => buildTopBarModel({
      page: activePage,
      summary: workbenchState.summary,
      currentTask: workbenchState.currentTask,
    }),
    [activePage, workbenchState.currentTask, workbenchState.summary],
  )

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

  const handleFocusModeChange = useCallback((active) => {
    setFocusModeActive(active)
  }, [])

  const pageProps = {
    summary: workbenchState.summary,
    loading,
    loadError,
    onRetry: loadSummary,
    onContextChange: setSidebarContext,
    onPageStateChange: handlePageStateChange,
    cachedSelectedPath: pageState[activePage]?.selectedPath ?? null,
    projectStatus,
    projectInfo,
    recentActivities,
    onCreateNew: handleCreateNew,
    showWizard,
    onWizardClosed: handleWizardClosed,
    onWizardCompleted: handleWizardCompleted,
    onNavigateToPage: handleNavigateToPage,
    onRunAction: handleRunAction,
    onFocusModeChange: handleFocusModeChange,
  }

  // --- Render ---

  return (
    <div className="workbench-shell">
      <div ref={topBarRef}>
        <TopBar
          model={topBarModel}
          connected={connected}
          onSelectPage={handleSelectPage}
          projects={projects}
          currentProjectPath={workbenchState.summary?.project?.path || null}
          onSwitchProject={handleSwitchProject}
          onCreateNew={handleCreateNew}
        />
      </div>

      <div className="workbench-body">
        <div ref={mainRef} className="workbench-main">
          {activePage === 'overview' && <OverviewPage {...pageProps} />}
          {activePage === 'chapters' && <ChapterPage {...pageProps} reloadToken={reloadKeys.chapters} />}
          {activePage === 'outline' && <OutlinePage {...pageProps} reloadToken={reloadKeys.outline} />}
          {activePage === 'settings' && <SettingPage {...pageProps} reloadToken={reloadKeys.settings} />}
        </div>
      </div>

      {/* AIAssistant floating component — hidden in focus mode */}
      {!focusModeActive && (
        <AIAssistant
          chatMessages={workbenchState.chatMessages}
          suggestedActions={workbenchState.suggestedActions}
          currentTask={workbenchState.currentTask}
          chatPending={chatPending}
          onSendMessage={handleSendMessage}
          onRunAction={handleRunAction}
          onRetryAction={handleRetryAction}
          onNavigateToPage={handleNavigateToPage}
          visible={aiOpen}
          onToggle={() => setAiOpen(prev => !prev)}
        />
      )}

      {/* Conflict dialog */}
      {conflictDialog.visible && (
        <ConflictDialog
          file={conflictDialog.file}
          onReload={() => {
            reloadCurrentFile()
            setConflictDialog({ visible: false, file: null })
          }}
          onKeep={() => setConflictDialog({ visible: false, file: null })}
        />
      )}

      <UnsavedChangesDialog
        visible={unsavedDialog.visible}
        message={unsavedDialog.message}
        onConfirm={confirmUnsavedDialog}
        onCancel={closeUnsavedDialog}
      />
    </div>
  )
}
