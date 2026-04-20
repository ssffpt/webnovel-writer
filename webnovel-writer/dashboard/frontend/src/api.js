/**
 * API 请求工具函数
 */

const BASE = '';  // 开发时由 vite proxy 代理到 FastAPI

export async function fetchJSON(path, params = {}) {
    const url = new URL(path, window.location.origin);
    Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null) url.searchParams.set(k, v);
    });
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
}

export async function postJSON(path, body = {}) {
    const res = await fetch(`${BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    return res.json();
}

export function fetchFileTree() {
    return fetchJSON('/api/files/tree');
}

export function readFile(path) {
    return fetchJSON('/api/files/read', { path });
}

export function saveFile(path, content) {
    return postJSON('/api/files/save', { path, content });
}

export function sendChat(message, context = {}) {
    return postJSON('/api/chat', { message, context });
}

export function fetchCurrentTask() {
    return fetchJSON('/api/tasks/current');
}

export function createTask(action, context = {}) {
    return postJSON('/api/tasks', { action, context });
}

export function fetchTask(taskId) {
    return fetchJSON(`/api/tasks/${taskId}`);
}

/**
 * 订阅 SSE 实时事件流
 * @param {function} onMessage  收到 data 时回调
 * @param {{onOpen?: function, onError?: function}} handlers 连接状态回调
 * @returns {function} 取消订阅函数
 */
export function subscribeSSE(onMessage, handlers = {}) {
    const { onOpen, onError } = handlers
    const es = new EventSource(`${BASE}/api/events`);
    es.onopen = () => {
        if (onOpen) onOpen()
    };
    es.onmessage = (e) => {
        try {
            onMessage(JSON.parse(e.data));
        } catch { /* ignore parse errors */ }
    };
    es.onerror = (e) => {
        // EventSource 会自动重连，这里只更新连接状态
        if (onError) onError(e)
    };
    return () => es.close();
}

// --- 新增 API（创建向导 & 项目管理）---
export function fetchGenres() {
    return fetchJSON('/api/genres');
}
export function fetchGoldenFingerTypes() {
    return fetchJSON('/api/golden-finger-types');
}
export function createProject(data) {
    return postJSON('/api/project/create', data);
}
export function fetchProjects() {
    return fetchJSON('/api/projects');
}
export function switchProject(path) {
    return postJSON('/api/project/switch', { path });
}
export function fetchOutlineTree() {
    return fetchJSON('/api/outline/tree');
}
export function fetchRecentActivity() {
    return fetchJSON('/api/recent-activity');
}

// --- Skill API（Phase 0）---
export function startSkill(skillName, options = {}) {
    return postJSON(`/api/skill/${skillName}/start`, options);
}

export function getSkillStatus(skillId) {
    return fetchJSON(`/api/skill/${skillId}/status`);
}

export function submitSkillStep(skillId, stepId, data) {
    return postJSON(`/api/skill/${skillId}/step`, { step_id: stepId, data });
}

export function cancelSkill(skillId) {
    return postJSON(`/api/skill/${skillId}/cancel`);
}

// --- Query API（Phase 5）---
export function fetchForeshadowing() {
  return fetchJSON('/api/query/foreshadowing');
}

// --- RAG API（Phase 6）---
export function getRAGConfig() {
  return fetchJSON('/api/rag/config');
}

export function saveRAGConfig(config) {
  return postJSON('/api/rag/config', config);
}

export function testRAGConnection() {
  return postJSON('/api/rag/test', {});
}

export function startRAGBuild() {
  return postJSON('/api/rag/build', {});
}

export function getRAGBuildStatus(taskId) {
  const path = taskId
    ? `/api/rag/build/status?task_id=${encodeURIComponent(taskId)}`
    : '/api/rag/build/status';
  return fetchJSON(path);
}
