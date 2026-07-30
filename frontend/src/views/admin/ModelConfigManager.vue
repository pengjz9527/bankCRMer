<template>
  <div class="page">
    <h2 class="page-title">大模型配置管理</h2>

    <!-- 当前激活模型横幅 — 始终置顶 -->
    <div class="active-banner" v-if="activeModel">
      <div class="active-badge">当前使用</div>
      <div class="active-info">
        <span class="active-provider">{{ activeModel.provider }}</span>
        <span class="active-model">{{ activeModel.model_name }}</span>
        <span class="active-config-key">({{ activeModel.config_key }})</span>
      </div>
      <div class="active-time">激活于 {{ formatTime(activeModel.updated_at) }}</div>
    </div>
    <div class="active-banner inactive" v-else>
      <div class="active-badge" style="background:#faad14">未配置</div>
      <span style="color:#666">尚未激活任何模型，请先新增并激活一个模型配置</span>
    </div>

    <!-- 配置列表 -->
    <div class="panel">
      <div class="panel-header">
        <h3 class="panel-title">模型配置列表</h3>
        <button class="btn btn-primary" @click="openAdd">+ 新增配置</button>
      </div>
      <table class="data-table" v-if="models.length">
        <thead>
          <tr>
            <th>Config Key</th>
            <th>Provider</th>
            <th>模型名称</th>
            <th>API Base</th>
            <th>用途</th>
            <th>状态</th>
            <th>更新时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in models" :key="m.config_key">
            <td class="mono">{{ m.config_key }}</td>
            <td>{{ m.provider }}</td>
            <td class="mono">{{ m.model_name }}</td>
            <td class="mono" style="max-width:180px;overflow:hidden;text-overflow:ellipsis;">{{ m.api_base || '-' }}</td>
            <td>{{ m.purpose || '-' }}</td>
            <td>
              <span v-if="m.is_active" class="badge badge-active">激活</span>
              <span v-else class="badge badge-inactive">未激活</span>
            </td>
            <td class="time-cell">{{ formatTime(m.updated_at) }}</td>
            <td>
              <button v-if="!m.is_active" class="btn btn-sm btn-primary" @click="confirmActivate(m)">激活</button>
              <button class="btn btn-sm btn-link" @click="openEdit(m)">编辑</button>
              <button v-if="!m.is_active" class="btn btn-sm btn-link btn-danger" @click="confirmDelete(m)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">暂无模型配置，请新增</div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <div v-if="showForm" class="modal-overlay" @click.self="showForm = false">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ isEdit ? '编辑模型配置' : '新增模型配置' }}</h3>
          <button class="btn btn-sm" @click="showForm = false">关闭</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Config Key <span class="req">*</span></label>
            <input v-model="form.config_key" class="form-input" :disabled="isEdit" :placeholder="isEdit ? '' : '唯一标识，如 deepseek-v3'" />
          </div>
          <div class="form-group">
            <label>Provider <span class="req">*</span></label>
            <select v-model="form.provider" class="form-input">
              <option value="deepseek">DeepSeek</option>
              <option value="openai">OpenAI</option>
              <option value="qwen">千问 (Qwen)</option>
              <option value="zhipu">智谱 (GLM)</option>
              <option value="other">其他</option>
            </select>
          </div>
          <div class="form-group">
            <label>模型名称 <span class="req">*</span></label>
            <input v-model="form.model_name" class="form-input" placeholder="如 deepseek-chat" />
          </div>
          <div class="form-group">
            <label>API Base URL</label>
            <input v-model="form.api_base" class="form-input" placeholder="如 https://api.deepseek.com/v1" />
          </div>
          <div class="form-group">
            <label>API Key</label>
            <input v-model="form.api_key" class="form-input" type="password" placeholder="留空则使用环境变量" />
          </div>
          <div class="form-group">
            <label>用途</label>
            <input v-model="form.purpose" class="form-input" placeholder="如 general, coding, analysis" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="showForm = false">取消</button>
          <button class="btn btn-primary" @click="submitForm" :disabled="!form.config_key || !form.model_name">
            {{ isEdit ? '保存修改' : '创建配置' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 激活确认弹窗 -->
    <div v-if="activateTarget" class="modal-overlay" @click.self="activateTarget = null">
      <div class="modal modal-sm">
        <div class="modal-header">
          <h3>确认切换模型</h3>
        </div>
        <div class="modal-body">
          <p>确定要激活 <strong>{{ activateTarget.provider }}/{{ activateTarget.model_name }}</strong> 吗？</p>
          <p class="text-warn">切换后，所有后续的 Agent 调用将使用新模型。此操作会热切换全局 ModelAdapter 单例。</p>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="activateTarget = null">取消</button>
          <button class="btn btn-primary" @click="doActivate">确认激活</button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal modal-sm">
        <div class="modal-header"><h3>确认删除</h3></div>
        <div class="modal-body">
          <p>确定要删除模型配置 <strong>{{ deleteTarget.config_key }}</strong> 吗？此操作不可撤销。</p>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="deleteTarget = null">取消</button>
          <button class="btn" style="background:#ab2029;color:#fff;border-color:#ab2029" @click="doDelete">确认删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminApi } from '../../api'

interface ModelItem {
  config_key: string; provider: string; model_name: string; api_base: string;
  api_key: string; is_active: number; purpose: string; created_at: string; updated_at: string
}

const models = ref<ModelItem[]>([])
const activeModel = ref<ModelItem | null>(null)
const showForm = ref(false)
const isEdit = ref(false)
const form = ref({ config_key: '', provider: 'deepseek', model_name: '', api_base: '', api_key: '', purpose: 'general' })
const activateTarget = ref<ModelItem | null>(null)
const deleteTarget = ref<ModelItem | null>(null)

function formatTime(iso: string): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('zh-CN')
}

async function loadModels() {
  try {
    const res = await adminApi.getModels()
    models.value = res.data?.models || []
    activeModel.value = res.data?.active || null
  } catch (e) { console.error('load models error:', e) }
}

function openAdd() {
  isEdit.value = false
  form.value = { config_key: '', provider: 'deepseek', model_name: '', api_base: '', api_key: '', purpose: 'general' }
  showForm.value = true
}

function openEdit(m: ModelItem) {
  isEdit.value = true
  form.value = { config_key: m.config_key, provider: m.provider, model_name: m.model_name, api_base: m.api_base || '', api_key: '', purpose: m.purpose || 'general' }
  showForm.value = true
}

async function submitForm() {
  try {
    if (isEdit.value) {
      await adminApi.updateModel(form.value.config_key, form.value)
    } else {
      await adminApi.createModel(form.value)
    }
    showForm.value = false
    await loadModels()
  } catch (e: any) {
    alert('操作失败: ' + (e?.message || '未知错误'))
  }
}

function confirmActivate(m: ModelItem) { activateTarget.value = m }
async function doActivate() {
  if (!activateTarget.value) return
  try {
    await adminApi.activateModel(activateTarget.value.config_key)
    activateTarget.value = null
    await loadModels()
  } catch (e: any) { alert('激活失败: ' + (e?.message || '未知错误')) }
}

function confirmDelete(m: ModelItem) { deleteTarget.value = m }
async function doDelete() {
  if (!deleteTarget.value) return
  try {
    await adminApi.deleteModel(deleteTarget.value.config_key)
    deleteTarget.value = null
    await loadModels()
  } catch (e: any) { alert('删除失败: ' + (e?.message || '未知错误')) }
}

onMounted(() => { loadModels() })
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 20px; }
.page-title { font-size: 18px; font-weight: 700; color: #333; margin: 0; }

/* 激活横幅 — 始终置顶可见 */
.active-banner { display: flex; align-items: center; gap: 16px; background: linear-gradient(135deg, #e6f7ff, #f0faff); border: 1px solid #91d5ff; border-radius: 8px; padding: 16px 24px; position: sticky; top: 0; z-index: 10; }
.active-banner.inactive { background: #fff7e6; border-color: #ffd591; }
.active-badge { background: #1890ff; color: #fff; padding: 4px 14px; border-radius: 12px; font-size: 12px; font-weight: 600; white-space: nowrap; }
.active-info { display: flex; gap: 8px; align-items: baseline; flex: 1; }
.active-provider { font-size: 13px; color: #666; }
.active-model { font-size: 16px; font-weight: 700; color: #333; }
.active-config-key { font-size: 12px; color: #999; font-family: 'SF Mono', monospace; margin-left: 6px; }
.active-time { font-size: 12px; color: #999; white-space: nowrap; }

.panel { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.panel-title { font-size: 15px; font-weight: 600; margin: 0; color: #333; }

.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 8px 12px; background: #fafafa; color: #666; font-weight: 600; border-bottom: 2px solid #e8e8e8; white-space: nowrap; }
.data-table td { padding: 10px 12px; border-bottom: 1px solid #f0f0f0; color: #333; }
.mono { font-family: 'SF Mono', monospace; font-size: 12px; color: #666; }
.time-cell { white-space: nowrap; color: #888; font-size: 12px; }

.badge { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 500; }
.badge-active { background: #f6ffed; color: #52c41a; border: 1px solid #b7eb8f; }
.badge-inactive { background: #f5f5f5; color: #999; border: 1px solid #d9d9d9; }

.btn { display: inline-flex; align-items: center; padding: 4px 12px; border: 1px solid #d9d9d9; border-radius: 4px; background: #fff; color: #333; font-size: 12px; cursor: pointer; white-space: nowrap; gap: 4px; transition: all 0.2s; }
.btn:hover { border-color: #ab2029; color: #ab2029; }
.btn-sm { padding: 2px 8px; font-size: 12px; }
.btn-primary { background: #ab2029; color: #fff; border-color: #ab2029; }
.btn-primary:hover { background: #8b1a22; }
.btn-link { color: #1890ff; border: none; background: none; padding: 2px 4px; }
.btn-danger { color: #ab2029; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* 弹窗 */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.45); display: flex; align-items: flex-start; justify-content: center; z-index: 1000; padding-top: 80px; }
.modal { background: #fff; border-radius: 12px; width: 520px; display: flex; flex-direction: column; box-shadow: 0 8px 40px rgba(0,0,0,0.15); }
.modal-sm { width: 420px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; border-bottom: 1px solid #e8e8e8; }
.modal-header h3 { margin: 0; font-size: 16px; }
.modal-body { padding: 24px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 16px 24px; border-top: 1px solid #e8e8e8; }

.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 13px; font-weight: 600; color: #555; margin-bottom: 4px; }
.req { color: #ab2029; }
.form-input { width: 100%; padding: 8px 12px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 13px; box-sizing: border-box; background: #fff; }
.form-input:focus { border-color: #ab2029; outline: none; box-shadow: 0 0 0 2px rgba(171,32,41,0.1); }
.form-input:disabled { background: #f5f5f5; color: #999; }

.text-warn { font-size: 12px; color: #faad14; }

.empty { padding: 40px; text-align: center; color: #999; font-size: 14px; }
</style>
