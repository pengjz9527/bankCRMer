/**
 * 易会办 客户洞察 — 前端 API 适配层
 * 
 * 用法:
 *   <script src="api_adapter.js"></script>
 *   <script>
 *     // 设置 API 地址
 *     EYH.setBaseURL('http://localhost:8000');
 *     
 *     // 获取客户列表
 *     const result = await EYH.getCustomers({ keyword: '张', page: 1 });
 *     
 *     // 获取客户画像
 *     const profile = await EYH.getCustomerProfile(1);
 *     
 *     // 获取待办
 *     const tasks = await EYH.getTasks('2024-01-15');
 *   </script>
 */
(function (global) {
  'use strict';

  const EYH = {
    // ============================================================
    // 配置
    // ============================================================
    _baseURL: 'http://localhost:8000',
    _offline: false,
    _timeout: 5000,

    setBaseURL: function (url) {
      this._baseURL = url.replace(/\/$/, '');
    },

    setOffline: function (offline) {
      this._offline = offline;
    },

    // ============================================================
    // 内部 fetch 封装
    // ============================================================
    _fetch: async function (path) {
      if (this._offline) {
        console.warn('[EYH] Offline mode, skipping API call:', path);
        return { code: -1, data: null, message: 'offline' };
      }
      try {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), this._timeout);
        const resp = await fetch(this._baseURL + path, { signal: controller.signal });
        clearTimeout(timer);
        if (!resp.ok) {
          return { code: resp.status, data: null, message: 'HTTP ' + resp.status };
        }
        return await resp.json();
      } catch (e) {
        console.error('[EYH] API error:', e.message);
        return { code: -1, data: null, message: e.message };
      }
    },

    _post: async function (path, body) {
      if (this._offline) {
        return { code: -1, data: null, message: 'offline' };
      }
      try {
        const resp = await fetch(this._baseURL + path, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body || {}),
        });
        return await resp.json();
      } catch (e) {
        return { code: -1, data: null, message: e.message };
      }
    },

    // ============================================================
    // 5.2.1 客户搜索与摘要
    // ============================================================
    getCustomers: async function (params) {
      const q = new URLSearchParams();
      if (params) {
        Object.keys(params).forEach(k => {
          if (params[k] !== undefined && params[k] !== null && params[k] !== '') {
            q.append(k, params[k]);
          }
        });
      }
      return this._fetch('/api/customers?' + q.toString());
    },

    // ============================================================
    // 5.2.2 客户画像聚合入口
    // ============================================================
    getCustomerProfile: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/profile');
    },

    // ============================================================
    // 5.2.3 画像分段 — 基础/家庭/就业
    // ============================================================
    getCustomerBasic: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/basic');
    },

    getCustomerFamily: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/family');
    },

    getCustomerEmployment: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/employment');
    },

    // ============================================================
    // 5.2.4 画像分段 — 经营信息
    // ============================================================
    getCustomerBusiness: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/business');
    },

    // ============================================================
    // 5.2.5 财富解读(4个)
    // ============================================================
    getWealthSummary: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/wealth/summary');
    },

    getWealthHoldings: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/wealth/holdings');
    },

    getWealthFundFlow: async function (custId, months) {
      return this._fetch('/api/customers/' + custId + '/wealth/fund-flow?months=' + (months || 12));
    },

    getWealthSalary: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/wealth/salary');
    },

    // ============================================================
    // 5.2.6 信贷解读(3个)
    // ============================================================
    getCreditLoans: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/credit/loans');
    },

    getCreditRejections: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/credit/rejections');
    },

    getCreditSocialSecurity: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/credit/social-security');
    },

    // ============================================================
    // 5.2.7 行为洞察(2个)
    // ============================================================
    getBehaviorPreferences: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/behavior/preferences');
    },

    getBehaviorLogs: async function (custId, days, page, size) {
      const q = new URLSearchParams();
      if (days) q.append('days', days);
      if (page) q.append('page', page);
      if (size) q.append('size', size);
      return this._fetch('/api/customers/' + custId + '/behavior/logs?' + q.toString());
    },

    // ============================================================
    // 5.2.8 关系图谱
    // ============================================================
    getCustomerRelations: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/relations');
    },

    // ============================================================
    // 5.2.9 权益与活动(3个)
    // ============================================================
    getCustomerBenefits: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/benefits');
    },

    getCustomerActivities: async function (custId) {
      return this._fetch('/api/customers/' + custId + '/activities');
    },

    getGlobalActivities: async function (type, tier) {
      const q = new URLSearchParams();
      if (type) q.append('type', type);
      if (tier) q.append('tier', tier);
      return this._fetch('/api/activities?' + q.toString());
    },

    // ============================================================
    // 5.2.10 待办与商机(2个)
    // ============================================================
    getTasks: async function (dateStr) {
      const q = dateStr ? '?date=' + dateStr : '';
      return this._fetch('/api/tasks' + q);
    },

    getOpportunities: async function () {
      return this._fetch('/api/opportunities');
    },

    // ============================================================
    // 5.2.11 作战包(4个)
    // ============================================================
    getBattlePackages: async function (custId, status) {
      const q = new URLSearchParams();
      if (custId) q.append('cust_id', custId);
      if (status) q.append('status', status);
      return this._fetch('/api/battle-packages?' + q.toString());
    },

    getBattlePackageDetail: async function (bpId) {
      return this._fetch('/api/battle-packages/' + bpId);
    },

    getBattlePackageClues: async function (bpId) {
      return this._fetch('/api/battle-packages/' + bpId + '/clues');
    },

    useBattlePackage: async function (bpId) {
      return this._post('/api/battle-packages/' + bpId + '/use');
    },

    generateBattlePackage: async function (oppId) {
      return this._post('/api/battle-packages/generate', { opp_id: oppId });
    },
  };

  // 暴露到全局
  global.EYH = EYH;
})(window);
