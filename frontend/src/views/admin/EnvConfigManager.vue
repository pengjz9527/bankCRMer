<template>
  <div class="page">
    <h2 class="page-title">环境变量配置</h2>
    <p class="page-desc">管理平台运行时依赖的外部服务配置（Key、Token、端点等），修改后即时生效</p>

    <!-- 配置列表（按分类分组） -->
    <div class="panel" v-for="group in groupedConfigs" :key="group.category">
      <div class="panel-header">
        <h3 class="panel-title">{{ group.label }}</h3>
        <button class="btn btn-primary" @click="openAdd(group.category)">+ 新增</button>
      </div>
      <table class="data-table" v-if="group.items.length">
        <thead>
          <tr>
            <th style="width:200px">配置键</th>
            <th>配置值</th>
            <th style="width:100px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in group.items" :key="c.config_key">
            <td class="mono">
              {{ c.config_key }}
              <div class="config-desc" v-if="c.description">{{ c.description }}</div>
            </td>
            <td>
              <input
                v-if="editingKey === c.config_key"
                v-model="editValue"
                class="form-input form-input--inline"
                :type="isSecret(c.config_key) ? 'password' : 'text'"
              />
              <span v-else class="config-value" :class="{ 'value-masked': isSecret(c.config_key) }">
                {{ isSecret(c.config_key) ? maskValue(c.config_value) : (c.config_value || '(空)') }}
              </span>
            </td>
            <td>
              <template v-if="editingKey === c.config_key">
                <button class="btn btn-sm btn-primary" @click="saveEdit(c)">保存</button>
                <button class="btn btn-sm" @click="cancelEdit">取消</button>
              </template>
              <template v-else>
                <button class="btn btn-sm btn-link" @click="startEdit(c)">编辑</button>
                <button class="btn btn-sm btn-link btn-danger" @click="confirmDelete(c)">删除</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">暂无配置</div>
    </div>

    <!-- 新增弹窗 -->
    <div v-if="showAddForm" class="modal-overlay" @click.self="showAddForm = false">
      <div class="modal">
        <div class="modal-header">
          <h3>新增配置项</h3>
          <button class="btn btn-sm" @click="showAddForm = false">关闭</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>配置键 <span class="req">*</span></label>
            <input v-model="addForm.config_key" class="form-input" placeholder="如 MY_SERVICE_API_KEY" />
          </div>
          <div class="form-group">
            <label>配置值</label>
            <input v-model="addForm.config_value" class="form-input" placeholder="配置值" />
          </div>
          <div class="form-group">
            <label>分类</label>
            <select v-model="addForm.category" class="form-input">
              <option v-for="cat in categoryOptions" :key="cat.value" :value="cat.value">{{ cat.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>说明</label>
            <input v-model="addForm.description" class="form-input" placeholder="这项配置的用途说明" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="showAddForm = false">取消</button>
          <button class="btn btn-primary" @click="doAdd" :disabled="!addForm.config_key">创建</button>
        </div>
      </div>
    </div>

    <!-- 删除确认 -->
    <div v-if="deleteTarget" class="modal-overlay" @click.self="deleteTarget = null">
      <div class="modal modal-sm">
        <div class="modal-header"><h3>确认删除</h3></div>
        <div class="modal-body">
          <p>确定要删除配置项 <strong>{{ deleteTarget.config_key }}</strong> 吗？此操作不可恢复。</p>
        </div>
        <div class="modal-footer">
          <button class="btn" @click="deleteTarget = null">取消</button>
          <button class="btn btn-danger" @click="doDelete">确认删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface PlatformConfig {
  config_key: string
  config_value: string
  category: string
  description: string
  updated_at: string
}

const configs = ref<PlatformConfig[]>([])
const editingKey = ref('')
const editValue = ref('')
const showAddForm = ref(false)
const deleteTarget = ref<PlatformConfig | null>(null)
const addForm = ref({ config_key: '', config_value: '', category: 'general', description: '' })

const API_BASE = 'http://localhost:8008'

const categoryLabels: Record<string, string> = {
  '金融数据': '金融数据',
  '向量嵌入': '向量嵌入（RAG 知识库）',
  '向量存储': '向量存储',
  '语音识别': '语音识别（ASR）',
  'general': '其他',
}

const categoryOptions = [
  { value: '金融数据', label: '金融数据' },
  { value: '向量嵌入', label: '向量嵌入（RAG 知识库）' },
  { value: '向量存储', label: '向量存储' },
  { value: '语音识别', label: '语音识别（ASR）' },
  { value: 'general', label: '其他' },
]

const SECRET_KEYWORDS = ['KEY', 'SECRET', 'TOKEN', 'PASSWORD']

function isSecret(key: string): boolean {
  return SECRET_KEYWORDS.some(k => key.toUpperCase().includes(k))
}

function maskValue(val: string): string {
  if (!val) return '(空)'
  if (val.length <= 8) return '****'
  return val.substring(0, 4) + '****' + val.substring(val.length - 4)
}

const groupedConfigs = computed(() => {
  const groups: Record<string, { category: string; label: string; items: PlatformConfig[] }> = {}
  for (const c of configs.value) {
    if (!groups[c.category]) {
      groups[c.category] = { category: c.category, label: categoryLabels[c.category] || c.category, items: [] }
    }
    groups[c.category].items.push(c)
  }
  return Object.values(groups)
})

function formatTime(ts: string): string {
  if (!ts) return '-'
  return ts.replace('T', ' ').substring(0, 19)
}

async function loadConfigs() {
  try {
    const res = await fetch(`${API_BASE}/api/admin/platform-configs`)
    const d = await res.json()
    if (d.code === 0) configs.value = d.data.configs || []
  } catch (e) {
    console.error('加载配置失败', e)
  }
}

function openAdd(category: string) {
  addForm.value = { config_key: '', config_value: '', category, description: '' }
  showAddForm.value = true
}

async function doAdd() {
  try {
    const res = await fetch(`${API_BASE}/api/admin/platform-configs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(addForm.value),
    })
    const d = await res.json()
    if (d.code === 0) {
      showAddForm.value = false
      await loadConfigs()
      alert('配置已创建')
    } else {
      alert(d.message || '创建失败')
    }
  } catch (e) {
    alert('请求失败')
  }
}

function startEdit(c: PlatformConfig) {
  editingKey.value = c.config_key
  editValue.value = c.config_value
}

function cancelEdit() {
  editingKey.value = ''
  editValue.value = ''
}

async function saveEdit(c: PlatformConfig) {
  try {
    const res = await fetch(`${API_BASE}/api/admin/platform-configs/${encodeURIComponent(c.config_key)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ config_value: editValue.value }),
    })
    const d = await res.json()
    if (d.code === 0) {
      editingKey.value = ''
      await loadConfigs()
    } else {
      alert(d.message || '保存失败')
    }
  } catch (e) {
    alert('请求失败')
  }
}

function confirmDelete(c: PlatformConfig) {
  deleteTarget.value = c
}

async function doDelete() {
  if (!deleteTarget.value) return
  try {
    const res = await fetch(`${API_BASE}/api/admin/platform-configs/${encodeURIComponent(deleteTarget.value.config_key)}`, {
      method: 'DELETE',
    })
    const d = await res.json()
    deleteTarget.value = null
    if (d.code === 0) {
      await loadConfigs()
    } else {
      alert(d.message || '删除失败')
    }
  } catch (e) {
    deleteTarget.value = null
    alert('请求失败')
  }
}

onMounted(loadConfigs)
</script>

<style scoped>
.page { padding: 20px; }
.page-title { font-size: 20px; margin: 0 0 4px; }
.page-desc { color: #888; font-size: 13px; margin: 0 0 20px; }

.panel { background: #fff; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 16px; overflow: hidden; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 14px 20px; border-bottom: 1px solid #f0f0f0; }
.panel-title { font-size: 15px; margin: 0; }

.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 10px 20px; background: #fafafa; color: #888; font-weight: 600; border-bottom: 1px solid #f0f0f0; }
.data-table td { padding: 10px 20px; border-bottom: 1px solid #f5f5f5; vertical-align: middle; }
.mono { font-family: 'SF Mono', 'Consolas', monospace; font-size: 12px; }
.config-desc { font-size: 11px; color: #999; margin-top: 2px; font-family: inherit; }
.config-value { word-break: break-all; }
.value-masked { color: #aaa; }

.form-input--inline { width: 100%; max-width: 360px; padding: 4px 8px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 13px; }

.empty { padding: 30px; text-align: center; color: #aaa; font-size: 13px; }

/* Buttons */
.btn { padding: 6px 16px; border: 1px solid #d9d9d9; background: #fff; border-radius: 4px; cursor: pointer; font-size: 13px; color: #333; }
.btn:hover { border-color: #1890ff; color: #1890ff; }
.btn-primary { background: #1890ff; border-color: #1890ff; color: #fff; }
.btn-primary:hover { background: #40a9ff; color: #fff; }
.btn-danger { color: #ff4d4f; }
.btn-danger:hover { border-color: #ff4d4f; color: #ff4d4f; background: #fff1f0; }
.btn-sm { padding: 3px 10px; font-size: 12px; }
.btn-link { border: none; background: none; color: #1890ff; padding: 0 8px; }
.btn-link:hover { color: #40a9ff; border: none; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.req { color: #ff4d4f; }

/* Form */
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 13px; color: #555; margin-bottom: 4px; }
.form-input { width: 100%; padding: 6px 10px; border: 1px solid #d9d9d9; border-radius: 4px; font-size: 13px; box-sizing: border-box; }
.form-input:focus { outline: none; border-color: #1890ff; box-shadow: 0 0 0 2px rgba(24,144,255,.1); }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.35); display: flex; align-items: center; justify-content: center; z-index: 2000; }
.modal { background: #fff; border-radius: 8px; width: 480px; max-width: 90vw; box-shadow: 0 4px 24px rgba(0,0,0,.15); }
.modal-sm { width: 380px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #f0f0f0; }
.modal-header h3 { margin: 0; font-size: 16px; }
.modal-body { padding: 20px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 8px; padding: 12px 20px; border-top: 1px solid #f0f0f0; }
</style>
