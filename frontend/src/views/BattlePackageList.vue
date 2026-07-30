<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '@/api'

const router = useRouter()
const loading = ref(false)

interface BattlePkg {
  id: string
  cust_name: string
  mode: string
  status: string
  generated_at: string
  expires_at: string
}

const packages = ref<BattlePkg[]>([])

const statusMap: Record<string, { label: string; color: string }> = {
  generated: { label: '已生成', color: '#2563EB' },
  used: { label: '已使用', color: '#059669' },
  expired: { label: '已过期', color: '#999' },
  generating: { label: '生成中', color: '#F59E0B' },
}

const modeMap: Record<string, string> = { full: '完整作战包', quick: '快速话术', product: '产品推荐', phone: '电话版', face: '面谈版', '标准版': '标准版' }

onMounted(async () => {
  loading.value = true
  try {
    const res = await api.getBattlePackages()
    const pkgs = res.data?.packages || []
    if (Array.isArray(pkgs)) {
      packages.value = pkgs.map((p: any) => ({
        id: p.bp_id || p.id || '',
        cust_name: p.cust_name || p.customer_name || '',
        mode: p.mode || 'full',
        status: p.status || 'generated',
        generated_at: p.generated_at || '',
        expires_at: p.expires_at || '',
      }))
    }
  } catch (e) {
    console.warn('加载作战包列表失败', e)
  } finally {
    loading.value = false
  }
})

function goDetail(pkg: BattlePkg) {
  router.push({ name: 'battle-package', query: { id: pkg.id } })
}

function goBack() { router.back() }
</script>

<template>
  <div class="bpl-page">
    <div class="bpl-header">
      <span class="bpl-back" @click="goBack">←</span>
      <span class="bpl-title">作战包</span>
      <span class="bpl-count">{{ packages.length }}个</span>
    </div>

    <div class="bpl-body">
      <div v-if="loading" class="bpl-loading">加载中...</div>
      <div v-else-if="packages.length === 0" class="bpl-empty">暂无作战包</div>

      <div v-for="pkg in packages" :key="pkg.id" class="bpl-card" @click="goDetail(pkg)">
        <div class="bpl-card-header">
          <span class="bpl-card-name">{{ pkg.cust_name }}</span>
          <span class="bpl-card-status" :style="{ color: (statusMap[pkg.status]?.color || '#999') }">
            {{ statusMap[pkg.status]?.label || pkg.status }}
          </span>
        </div>
        <div class="bpl-card-meta">
          <span class="bpl-card-mode">{{ modeMap[pkg.mode] || pkg.mode }}</span>
          <span v-if="pkg.generated_at" class="bpl-card-time">
            {{ pkg.generated_at.slice(0, 10) }}
          </span>
        </div>
        <div v-if="pkg.expires_at" class="bpl-card-expires">
          有效期至 {{ pkg.expires_at.slice(0, 10) }}
        </div>
        <div class="bpl-card-arrow">›</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.bpl-page { min-height: 100%; background: #f8f8f8; padding-bottom: 40px; }
.bpl-header { display: flex; align-items: center; padding: 12px 16px; background: #fff; position: sticky; top: 0; z-index: 5; border-bottom: 1px solid #eee; }
.bpl-back { font-size: 20px; cursor: pointer; margin-right: 12px; color: var(--color-primary); }
.bpl-title { flex: 1; font-size: 17px; font-weight: 600; }
.bpl-count { font-size: 12px; color: var(--color-text-secondary); background: #f0f0f0; padding: 2px 10px; border-radius: 999px; }

.bpl-body { padding: 12px 16px; }
.bpl-loading, .bpl-empty { text-align: center; padding: 60px 20px; color: #999; font-size: 14px; }

.bpl-card {
  background: #fff; border-radius: 10px; padding: 14px 16px; margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05); cursor: pointer; position: relative;
}
.bpl-card:active { background: #fafafa; }
.bpl-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.bpl-card-name { font-size: 15px; font-weight: 600; }
.bpl-card-status { font-size: 11px; font-weight: 500; }
.bpl-card-meta { display: flex; gap: 12px; font-size: 12px; color: var(--color-text-secondary); margin-bottom: 4px; }
.bpl-card-mode { background: #EDE9FE; color: #6C5CE7; padding: 1px 8px; border-radius: 4px; font-size: 11px; }
.bpl-card-time { color: #999; }
.bpl-card-expires { font-size: 11px; color: #bbb; }
.bpl-card-arrow { position: absolute; right: 14px; top: 50%; transform: translateY(-50%); font-size: 20px; color: #ccc; }
</style>
