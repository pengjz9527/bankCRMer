// ========================================
//  Icon Set: Classic (经典)
//  Pure filled silhouettes — bold & recognizable
//  Reference: Alipay / ICBC / WeChat Pay tab bar
//  24×24 viewBox, predominantly filled shapes
//  Internal detail via opacity layers & white highlights
//  Visible at 14px (ico--sm), crisp at all sizes
// ========================================
window.ICON_SETS = window.ICON_SETS || {};
window.ICON_SETS['classic'] = {

// ── 导航 / Tab Bar ──
'ico-home':
  '<path d="M12 1.5a1 1 0 0 1 .7.3l9 7.5A1 1 0 0 1 22 10v11a2 2 0 0 1-2 2h-5v-7h-6v7H4a2 2 0 0 1-2-2V10a1 1 0 0 1 .3-.7l9-7.5a1 1 0 0 1 .7-.3z" fill="currentColor"/>',

'ico-people':
  '<circle cx="9" cy="6" r="4" fill="currentColor"/><path d="M1 20v-2a6 6 0 0 1 10.1-4.2A6 6 0 0 1 16 20v2H1zm12.5-13a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7zm1.2 4.5a5 5 0 0 0-2.7.9 5 5 0 0 1 5.5 4.6v2h4.5v-3a5 5 0 0 0-7.3-4.5z" fill="currentColor"/>',

'ico-package':
  '<path d="M12 2 2 7.5v9l10 5.5 10-5.5v-9zm0 3.2 6 3.3v6l-6 3.3-6-3.3v-6z" fill="currentColor"/><path d="M11 12v9" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/><path d="M5.5 9 11 12" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/>',

'ico-user':
  '<circle cx="12" cy="7" r="5" fill="currentColor"/><path d="M2 22c0-5.5 4.5-10 10-10s10 4.5 10 10z" fill="currentColor"/>',

// ── 搜索 / 通知 ──
'ico-search':
  '<circle cx="10" cy="10" r="8" fill="currentColor" opacity=".9"/><circle cx="10" cy="10" r="4" fill="#fff" opacity=".25"/><rect x="15" y="17" width="3" height="9" rx="1.5" fill="currentColor" transform="rotate(-45 16.5 21.5)"/>',

'ico-bell':
  '<path d="M5 9a7 7 0 0 1 14 0c0 8 3 10.5 3 10.5H2s3-2.5 3-10.5z" fill="currentColor"/><ellipse cx="12" cy="21.5" rx="2.5" ry="1.5" fill="currentColor"/>',

// ── AI / 智能 ──
'ico-ai':
  '<circle cx="12" cy="12" r="10" fill="currentColor"/><path d="M12 5v4m0 6v4M8 8l4-3 4 3M8 16l4 3 4-3" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>',

'ico-sparkles':
  '<path d="M12 2 14.3 8.5 21 11l-5.5 3.5L17 21l-5-3.5L7 21l1.5-6.5L3 11l6.7-2.5z" fill="currentColor"/>',

'ico-brain':
  '<path d="M12 2a5 5 0 0 0-5 5c0 2.5 1.5 4 2.5 5.5l-1 4.5 3.5-1V20h3v-4l3.5 1-1-4.5c1-1.5 2.5-3 2.5-5.5a5 5 0 0 0-5-5z" fill="currentColor"/><circle cx="9" cy="17" r="1.5" fill="#fff" opacity=".4"/><circle cx="15" cy="17" r="1.5" fill="#fff" opacity=".4"/>',

// ── 日程 ──
'ico-sun':
  '<circle cx="12" cy="12" r="5" fill="currentColor"/><g stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="1" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="23"/><line x1="1" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="23" y2="12"/><line x1="4.2" y1="4.2" x2="6.8" y2="6.8"/><line x1="17.2" y1="17.2" x2="19.8" y2="19.8"/><line x1="4.2" y1="19.8" x2="6.8" y2="17.2"/><line x1="17.2" y1="6.8" x2="19.8" y2="4.2"/></g>',

'ico-cloud-sun':
  '<path d="M6 17a5 5 0 0 1-2.5-9" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><path d="M3 22.5h14a5 5 0 0 0 .5-10" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><circle cx="18" cy="9" r="4" fill="currentColor"/><g stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="1" x2="18" y2="4.5"/><line x1="22" y1="9" x2="14" y2="9"/></g>',

'ico-clock':
  '<circle cx="12" cy="12" r="10" fill="currentColor"/><circle cx="12" cy="12" r="6.5" fill="#fff"/><polyline points="12 6 12 12 15.5 14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-calendar':
  '<rect x="2" y="4" width="20" height="19" rx="3" fill="currentColor"/><rect x="2" y="4" width="20" height="7" rx="3" fill="currentColor" opacity=".55"/><rect x="5" y="1" width="3" height="7" rx="1.5" fill="currentColor" opacity=".3"/><rect x="16" y="1" width="3" height="7" rx="1.5" fill="currentColor" opacity=".3"/><rect x="6" y="14.5" width="4" height="4" rx="1.5" fill="#fff" opacity=".85"/><rect x="14" y="14.5" width="4" height="4" rx="1.5" fill="#fff" opacity=".85"/>',

'ico-hourglass':
  '<path d="M5 2h14v5a7 7 0 0 1-3 5.8A7 7 0 0 1 19 17v5H5v-5a7 7 0 0 1 3-4.2A7 7 0 0 1 5 7z" fill="currentColor"/>',

'ico-alarm':
  '<circle cx="12" cy="13" r="9" fill="currentColor"/><circle cx="12" cy="13" r="6" fill="#fff"/><polyline points="12 7 12 13 15 16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="3.5" y1="3" x2="6" y2="5.5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="20.5" y1="3" x2="18" y2="5.5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>',

'ico-stopwatch':
  '<circle cx="12" cy="13" r="9" fill="currentColor"/><circle cx="12" cy="13" r="6" fill="#fff"/><polyline points="12 4 12 1.5 17 4.5" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="12 7 12 13 15.5 15" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>',

// ── 商机 / 作战包 ──
'ico-clipboard':
  '<rect x="6" y="1.5" width="12" height="4.5" rx="2.5" fill="currentColor" opacity=".3"/><rect x="4.5" y="6" width="15" height="17" rx="3.5" fill="currentColor"/><line x1="7.5" y1="13" x2="16.5" y2="13" stroke="#fff" stroke-width="2" stroke-linecap="round"/><line x1="7.5" y1="17" x2="14" y2="17" stroke="#fff" stroke-width="2" stroke-linecap="round"/>',

'ico-target':
  '<circle cx="12" cy="12" r="11" fill="currentColor" opacity=".1"/><circle cx="12" cy="12" r="7" fill="none" stroke="currentColor" stroke-width="2.5"/><circle cx="12" cy="12" r="3" fill="currentColor"/>',

'ico-lightbulb':
  '<path d="M12 2a7 7 0 0 0-4.5 12.7V18a1.5 1.5 0 0 0 1.5 1.5h6a1.5 1.5 0 0 0 1.5-1.5v-3.3A7 7 0 0 0 12 2z" fill="currentColor"/><line x1="10" y1="21.5" x2="14" y2="21.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',

'ico-lightning':
  '<path d="M13.5 1.5 3 14h9.5l-2 8.5L21 10h-9.5l2-8.5z" fill="currentColor"/>',

// ── 图表 / 数据 ──
'ico-chart':
  '<rect x="3" y="21" width="18" height="2" rx="1" fill="currentColor" opacity=".2"/><rect x="5" y="10" width="4" height="11" rx="2" fill="currentColor" opacity=".35"/><rect x="10" y="6" width="4" height="15" rx="2" fill="currentColor" opacity=".55"/><rect x="15" y="2" width="4" height="19" rx="2" fill="currentColor"/>',

'ico-money':
  '<ellipse cx="12" cy="4" rx="10" ry="4.5" fill="currentColor" opacity=".2"/><ellipse cx="12" cy="4" rx="10" ry="4.5" fill="none" stroke="currentColor" stroke-width="2"/><path d="M2 4v15c0 2.5 4.5 4.5 10 4.5s10-2 10-4.5V4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M2 11.5c0 2.5 4.5 4.5 10 4.5s10-2 10-4.5" fill="none" stroke="currentColor" stroke-width="2"/>',

'ico-ruler':
  '<rect x="2" y="2" width="20" height="20" rx="3" fill="currentColor" opacity=".12"/><rect x="2" y="2" width="20" height="20" rx="3" fill="none" stroke="currentColor" stroke-width="2.5"/><line x1="8" y1="2" x2="8" y2="12" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="15" y1="2" x2="15" y2="8" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>',

// ── 状态 / 操作 ──
'ico-warning':
  '<path d="M12 2.5 1 22h22z" fill="currentColor"/><line x1="12" y1="10" x2="12" y2="16" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/><circle cx="12" cy="19.5" r="1.5" fill="#fff"/>',

'ico-check-circle':
  '<circle cx="12" cy="12" r="11" fill="currentColor"/><polyline points="7 12 10.5 15.5 17 9" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-x-circle':
  '<circle cx="12" cy="12" r="11" fill="currentColor" opacity=".85"/><line x1="7.5" y1="7.5" x2="16.5" y2="16.5" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/><line x1="16.5" y1="7.5" x2="7.5" y2="16.5" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>',

'ico-check':
  '<polyline points="4 12 9.5 18 20 7" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-close':
  '<circle cx="12" cy="12" r="11" fill="currentColor" opacity=".12"/><line x1="7" y1="7" x2="17" y2="17" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><line x1="17" y1="7" x2="7" y2="17" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>',

'ico-x':
  '<line x1="5" y1="5" x2="19" y2="19" stroke="currentColor" stroke-width="3" stroke-linecap="round"/><line x1="19" y1="5" x2="5" y2="19" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>',

'ico-ban':
  '<circle cx="12" cy="12" r="11" fill="currentColor" opacity=".1"/><circle cx="12" cy="12" r="11" fill="none" stroke="currentColor" stroke-width="2.5"/><line x1="4.5" y1="4.5" x2="19.5" y2="19.5" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>',

// ── 通讯 ──
'ico-phone':
  '<path d="M21.5 16.5v3.2a2.2 2.2 0 0 1-2.4 2.2A20 20 0 0 1 1.7 3.2 2.2 2.2 0 0 1 3.9 1h3.3a2.2 2.2 0 0 1 2.2 1.9c.2 1 .5 2 .8 3a2.2 2.2 0 0 1-.6 2.2L8.2 9.6a16 16 0 0 0 6.2 6.2l1.5-1.4a2.2 2.2 0 0 1 2.2-.6 17 17 0 0 0 3 .8 2.2 2.2 0 0 1 .4 3.9z" fill="currentColor"/>',

'ico-mobile':
  '<rect x="5" y="0.5" width="14" height="23" rx="3.5" fill="currentColor"/><rect x="8" y="3" width="8" height="16.5" rx="1.5" fill="#fff" opacity=".88"/><circle cx="12" cy="21.5" r="1.5" fill="#fff" opacity=".55"/>',

'ico-message':
  '<path d="M21 11.5a9.5 9.5 0 0 1-12 9A9.5 9.5 0 0 1 3.2 16 9.5 9.5 0 0 1 11.5 2a9.5 9.5 0 0 1 9.5 9.5z" fill="currentColor"/><circle cx="7.5" cy="11.5" r="2" fill="#fff"/><circle cx="12" cy="11.5" r="2" fill="#fff"/><circle cx="16.5" cy="11.5" r="2" fill="#fff"/>',

'ico-email':
  '<rect x="1.5" y="4.5" width="21" height="16" rx="3.5" fill="currentColor"/><polyline points="1.5 4.5 12 14.5 22.5 4.5" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round"/>',

'ico-empty':
  '<rect x="1.5" y="4.5" width="21" height="16" rx="3.5" fill="currentColor" opacity=".1"/><rect x="1.5" y="4.5" width="21" height="16" rx="3.5" fill="none" stroke="currentColor" stroke-width="2"/><polyline points="1.5 8.5 12 15.5 22.5 8.5" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round"/>',

// ── 编辑 / 设置 ──
'ico-settings':
  '<path d="M13.5 3a2 2 0 0 1 1.2 3.2v.8h2v-1.2a2 2 0 0 1 3.6.7l-1.2 1.8 1.8 1.2 1.8-1.2a2 2 0 0 1 .7 3.6H22v2h1.2a2 2 0 0 1-.7 3.6l-1.8-1.2-1.8 1.2 1.2 1.8a2 2 0 0 1-3.6.7V19h-2v1.2a2 2 0 0 1-3.2-1.2l1.2-1.8-1.8-1.2-1.8 1.2a2 2 0 0 1-.7-3.6H5v-2H3.8a2 2 0 0 1 .7-3.6l1.8 1.2 1.8-1.2-1.2-1.8A2 2 0 0 1 10.3 5.3V4h.7A2 2 0 0 1 12 3c.5 0 1 0 1.5 0z" fill="currentColor"/><circle cx="12" cy="12.5" r="3.5" fill="#fff"/>',

'ico-pencil':
  '<path d="M15.5 2.5a2.8 2.8 0 0 1 5.5 5.5L7 22H1v-6z" fill="currentColor" opacity=".75"/>',

'ico-edit':
  '<path d="M12 21h9" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><path d="M16.5 3a2.8 2.8 0 1 1 4 4L8 19.5 3 21l1.5-5z" fill="currentColor" opacity=".9"/>',

'ico-tag':
  '<path d="M1.5 12V1.5h10.5L22.5 12 12 22.5z" fill="currentColor"/><circle cx="7" cy="7" r="2.5" fill="#fff"/>',

// ── 箭头 / 导航 ──
'ico-chevron-down':
  '<polyline points="4 8 12 17 20 8" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-chevron-right':
  '<polyline points="8 4 17 12 8 20" fill="none" stroke="currentColor" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-refresh':
  '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="2.5"/><path d="M12 20a8 8 0 0 1-7-4M12 4a8 8 0 0 1 7 4" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><polyline points="19 1.5 19 5.5 15 5.5" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="5 22.5 5 18.5 9 18.5" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>',

// ── 媒体 ──
'ico-play':
  '<polygon points="6 3.5 20 12 6 20.5" fill="currentColor"/>',

'ico-pause':
  '<rect x="5" y="3.5" width="5" height="17" rx="2" fill="currentColor"/><rect x="14" y="3.5" width="5" height="17" rx="2" fill="currentColor"/>',

'ico-skip-fwd':
  '<polygon points="5.5 4 18 12 5.5 20" fill="currentColor" opacity=".9"/><rect x="20" y="4" width="3" height="16" rx="1.5" fill="currentColor"/>',

// ── 庆祝 / 成就 ──
'ico-party':
  '<path d="M12 1 15.5 7.5 22 9l-5.5 4L18 21l-6-3.5L6 21l1.5-8L2 9l6.5-2z" fill="currentColor"/>',

'ico-star':
  '<polygon points="12 1 15.5 8.5 23 9 17.5 15 19 22 12 17.5 5 22 6.5 15 1 9 8.5 8.5" fill="currentColor"/>',

'ico-crown':
  '<path d="M1.5 4.5 7 15h10l5.5-10.5L17 8 12 1 7 8z" fill="currentColor"/><rect x="1.5" y="19" width="21" height="3" rx="1.5" fill="currentColor"/>',

'ico-trophy':
  '<path d="M6 2.5h12v6.5a6 6 0 0 1-12 0z" fill="currentColor" opacity=".85"/><rect x="4" y="17" width="16" height="5.5" rx="1.5" fill="currentColor" opacity=".35"/><rect x="8" y="4" width="8" height="2.5" rx="1.2" fill="#fff" opacity=".55"/>',

'ico-gift':
  '<rect x="1.5" y="8.5" width="21" height="6.5" rx="2.5" fill="currentColor"/><line x1="12" y1="8.5" x2="12" y2="22" stroke="currentColor" stroke-width="2"/><path d="M7.5 8.5a3.5 3.5 0 0 1 4.5-3 3.5 3.5 0 0 1 4.5 3" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><rect x="4.5" y="15" width="15" height="7" rx="2.5" fill="currentColor" opacity=".25"/>',

'ico-birthday':
  '<circle cx="12" cy="6.5" r="5.5" fill="currentColor" opacity=".45"/><rect x="3" y="12" width="18" height="11" rx="3.5" fill="currentColor"/><rect x="6" y="15.5" width="3.5" height="4.5" rx="1.5" fill="#fff" opacity=".8"/><rect x="14.5" y="15.5" width="3.5" height="4.5" rx="1.5" fill="#fff" opacity=".8"/>',

// ── 业务场景 ──
'ico-fire':
  '<path d="M12 1.5C7 7 4.5 12 4.5 16a7.5 7.5 0 0 0 15 0c0-4-2.5-9-7.5-14.5z" fill="currentColor"/><circle cx="12" cy="16" r="3" fill="#fff"/>',

'ico-diamond':
  '<polygon points="12 1 23 12 12 23 1 12" fill="currentColor"/><polygon points="12 5.5 17.5 12 12 18.5 6.5 12" fill="#fff" opacity=".4"/>',

'ico-pin':
  '<circle cx="12" cy="6" r="5.5" fill="currentColor"/><path d="M12 11.5v11" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><path d="M5.5 16.5h13" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>',

// ── 金融 ──
'ico-credit-card':
  '<rect x="1" y="3.5" width="22" height="17" rx="3.5" fill="currentColor"/><rect x="1" y="3.5" width="22" height="7.5" rx="3.5" fill="currentColor" opacity=".55"/><circle cx="6" cy="19" r="1.5" fill="#fff"/><line x1="10" y1="19" x2="17" y2="19" stroke="#fff" stroke-width="2.5" stroke-linecap="round"/>',

'ico-bank':
  '<rect x="1.5" y="21" width="21" height="2" rx="1" fill="currentColor"/><path d="M3 10v8h4v-8h3v8h4v-8h3v8h4V10" fill="currentColor" opacity=".85"/><path d="M2 10h20l-3.5-6.5h-13z" fill="currentColor" opacity=".25"/>',

'ico-handshake':
  '<path d="M1.5 12 6 7.5l3.5 3.5 2-2 3.5 3.5-3.5 3.5 3.5 3.5-3.5 3.5-8.5-9.5a2 2 0 0 1 0-2.8z" fill="currentColor"/><path d="M22.5 12 18 7.5l-3.5 3.5-2-2-3.5 3.5 3.5 3.5-3.5 3.5 3.5 3.5 8.5-9.5a2 2 0 0 0 0-2.8z" fill="currentColor"/>',

'ico-money-fly':
  '<path d="M12 2 2 12l10 10 10-10z" fill="currentColor" opacity=".15"/><path d="M12 2 2 12l10 10 10-10z" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round"/><circle cx="12" cy="12" r="4" fill="currentColor"/>',

'ico-balance':
  '<path d="M12 1.5 1.5 22h21z" fill="currentColor" opacity=".1"/><path d="M12 1.5 1.5 22h21z" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linejoin="round"/><line x1="12" y1="10.5" x2="12" y2="22" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><circle cx="12" cy="9" r="2.5" fill="currentColor"/>',

'ico-factory':
  '<path d="M1.5 20.5h21" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><path d="M5 8.5 10.5 4l4 4 4-5 4 5v12.5H5z" fill="currentColor"/><rect x="8" y="14" width="3" height="3" rx="1" fill="#fff" opacity=".7"/><rect x="15" y="14" width="3" height="3" rx="1" fill="#fff" opacity=".7"/>',

// ── 杂项 ──
'ico-inbox':
  '<path d="M21 6v14.5a2.5 2.5 0 0 1-2.5 2.5H5.5A2.5 2.5 0 0 1 3 20.5V6l9-5z" fill="currentColor"/><polyline points="3 6 12 12.5 21 6" fill="none" stroke="#fff" stroke-width="2" stroke-linejoin="round"/>',

// ── 补充：AI / 趋势 / 钱包 / 文档 / 公告 / 箭入 / 笔记本 / 建筑 / 家庭 / 上传 ──
'ico-robot':
  '<rect x="3" y="8" width="18" height="12" rx="3" fill="currentColor"/><rect x="7" y="8" width="2" height="7" rx="1" fill="#fff" opacity=".7"/><rect x="15" y="8" width="2" height="7" rx="1" fill="#fff" opacity=".7"/><line x1="12" y1="1.5" x2="12" y2="8" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><circle cx="12" cy="1.5" r="1.5" fill="currentColor"/>',

'ico-trend-up':
  '<polyline points="3 17 9 11 13 15 21 7" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="15 7 21 7 21 13" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="21" cy="7" r="2.5" fill="currentColor" opacity=".3"/>',

'ico-wallet':
  '<rect x="1.5" y="4" width="21" height="16" rx="3" fill="currentColor"/><rect x="6" y="7" width="13" height="10" rx="2" fill="#fff" opacity=".85"/><circle cx="17" cy="12" r="2" fill="currentColor"/>',

'ico-file-text':
  '<path d="M14 1.5H5.5a2 2 0 0 0-2 2v17a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-13z" fill="currentColor"/><polyline points="14 1.5 14 7.5 20.5 7.5" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><line x1="7.5" y1="12.5" x2="16.5" y2="12.5" stroke="#fff" stroke-width="2" stroke-linecap="round"/><line x1="7.5" y1="16.5" x2="14" y2="16.5" stroke="#fff" stroke-width="2" stroke-linecap="round"/>',

'ico-megaphone':
  '<path d="M21 3 11 9H4a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2h1l2 6h3l-2-6h6l10 6V3z" fill="currentColor"/><line x1="21" y1="3" x2="21" y2="21" stroke="#fff" stroke-width="2" stroke-linecap="round"/>',

'ico-inbox-arrow':
  '<path d="M21.5 16v5a2 2 0 0 1-2 2H4.5a2 2 0 0 1-2-2v-5" fill="none" stroke="currentColor" stroke-width="2.5"/><polyline points="7 10.5 12 15.5 17 10.5" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><line x1="12" y1="1.5" x2="12" y2="15.5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><circle cx="12" cy="15.5" r="2" fill="currentColor" opacity=".3"/>',

'ico-laptop':
  '<rect x="3" y="3" width="18" height="13" rx="2.5" fill="currentColor"/><rect x="7" y="5" width="10" height="8" rx="1" fill="#fff" opacity=".75"/><path d="M1 19h22" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><path d="M1 19 3 16M23 19l-2-3" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>',

'ico-building':
  '<rect x="3" y="3" width="18" height="19" rx="2" fill="currentColor" opacity=".9"/><rect x="7" y="7" width="3" height="3" rx=".5" fill="#fff" opacity=".8"/><rect x="14" y="7" width="3" height="3" rx=".5" fill="#fff" opacity=".8"/><rect x="7" y="13" width="3" height="3" rx=".5" fill="#fff" opacity=".8"/><rect x="14" y="13" width="3" height="3" rx=".5" fill="#fff" opacity=".8"/><path d="M10 22v-4h4v4" fill="none" stroke="#fff" stroke-width="2"/>',

'ico-family':
  '<circle cx="12" cy="5" r="3" fill="currentColor"/><circle cx="4.5" cy="8" r="2.5" fill="currentColor" opacity=".65"/><circle cx="19.5" cy="8" r="2.5" fill="currentColor" opacity=".65"/><path d="M1 21v-1.5a4 4 0 0 1 7 0V21" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><path d="M8 21v-2a5 5 0 0 1 8 0v2" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><path d="M16 21v-1.5a4 4 0 0 1 7 0V21" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>',

'ico-upload':
  '<path d="M21.5 15.5v5.5a2 2 0 0 1-2 2H4.5a2 2 0 0 1-2-2v-5.5" fill="none" stroke="currentColor" stroke-width="2.5"/><polyline points="17 8 12 3 7 8" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><line x1="12" y1="3" x2="12" y2="15.5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/><path d="M8 18h8" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>',

};
