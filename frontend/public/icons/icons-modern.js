// ========================================
//  Icon Set: Modern (现代简约 · 细线条)
//  Reference: 图标示例.png thin-line style
//  24×24 viewBox · stroke-width 1.8
//  Pure outline — no background fills
//  Every element has explicit fill/stroke
// ========================================
window.ICON_SETS = window.ICON_SETS || {};
window.ICON_SETS['modern'] = {

// ── 导航 / Tab Bar ──
'ico-home':
  '<path d="M3 9.5 12 2l9 7.5V21a1.5 1.5 0 0 1-1.5 1.5h-5v-7.5h-5v7.5H4.5A1.5 1.5 0 0 1 3 21z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-people':
  '<circle cx="9" cy="6" r="4" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M1 20v-2a6 6 0 0 1 16 0v2" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="19" cy="6.5" r="3.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M13 20v-2a5 5 0 0 1 10 0v2" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-package':
  '<path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" fill="none" stroke="currentColor" stroke-width="1.8"/><polyline points="3.5 7 12 12 20.5 7" fill="none" stroke="currentColor" stroke-width="1.8"/><line x1="12" y1="12" x2="12" y2="22" stroke="currentColor" stroke-width="1.8"/><line x1="7.5" y1="4.5" x2="16.5" y2="9.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-user':
  '<circle cx="12" cy="7" r="4.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M2 22c0-5.5 4.5-10 10-10s10 4.5 10 10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

// ── 搜索 / 通知 ──
'ico-search':
  '<circle cx="10.5" cy="10.5" r="7.5" fill="none" stroke="currentColor" stroke-width="1.8"/><line x1="16.5" y1="16.5" x2="22" y2="22" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',

'ico-bell':
  '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M13.7 21a2 2 0 0 1-3.4 0" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

// ── AI / 智能 ──
'ico-ai':
  '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 5.5v4M12 14.5v4M8 9.5l4-4 4 4M8 14.5l4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-sparkles':
  '<path d="M12 2.5 14.5 9l6.5 2-5 3.5L17.5 22 12 18l-5.5 4L8 14.5 3 11l6.5-2z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',

'ico-brain':
  '<path d="M12 3a5 5 0 0 0-5 5c0 2.5 1.5 3.5 2.5 5.5l-1 4.5 3.5-1V21h3v-4l3.5 1-1-4.5c1-2 2.5-3 2.5-5.5a5 5 0 0 0-5-5z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><circle cx="9" cy="17" r="1.5" fill="currentColor"/><circle cx="15" cy="17" r="1.5" fill="currentColor"/>',

// ── 日程 ──
'ico-sun':
  '<circle cx="12" cy="12" r="5" fill="none" stroke="currentColor" stroke-width="1.8"/><g fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><line x1="12" y1="1" x2="12" y2="3.5"/><line x1="12" y1="20.5" x2="12" y2="23"/><line x1="1" y1="12" x2="3.5" y2="12"/><line x1="20.5" y1="12" x2="23" y2="12"/><line x1="4.2" y1="4.2" x2="6" y2="6"/><line x1="18" y1="18" x2="19.8" y2="19.8"/><line x1="4.2" y1="19.8" x2="6" y2="18"/><line x1="18" y1="6" x2="19.8" y2="4.2"/></g>',

'ico-cloud-sun':
  '<path d="M5 17a5 5 0 0 1-2.5-9" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M3 23h14a5 5 0 0 0 .5-10" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="19" cy="9" r="3" fill="none" stroke="currentColor" stroke-width="1.8"/><g fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><line x1="19" y1="2" x2="19" y2="5"/><line x1="23" y1="9" x2="15" y2="9"/></g>',

'ico-clock':
  '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.8"/><polyline points="12 6 12 12 16 14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-calendar':
  '<rect x="2.5" y="4" width="19" height="18" rx="3" fill="none" stroke="currentColor" stroke-width="1.8"/><line x1="2.5" y1="10.5" x2="21.5" y2="10.5" stroke="currentColor" stroke-width="1.8"/><line x1="8" y1="1.5" x2="8" y2="6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="16" y1="1.5" x2="16" y2="6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><rect x="7" y="14" width="3" height="3" rx="1" fill="currentColor"/><rect x="14" y="14" width="3" height="3" rx="1" fill="currentColor"/>',

'ico-hourglass':
  '<path d="M5 22h14M5 2h14M17 2v5a5 5 0 0 1-2.5 4.3A5 5 0 0 0 17 17v5M7 2v5a5 5 0 0 0 2.5 4.3A5 5 0 0 1 7 17v5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-alarm':
  '<circle cx="12" cy="13" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/><polyline points="12 7 12 13 15.5 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="3.5" y1="3" x2="6" y2="5.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="20.5" y1="3" x2="18" y2="5.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-stopwatch':
  '<circle cx="12" cy="13" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/><polyline points="12 4 12 1.5 17 4.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><polyline points="12 7 12 13 16 15" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

// ── 商机 / 作战包 ──
'ico-clipboard':
  '<rect x="7" y="2" width="10" height="4" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M16 4.5h2.5a2 2 0 0 1 2 2V21a2 2 0 0 1-2 2H5.5a2 2 0 0 1-2-2V6.5a2 2 0 0 1 2-2H8" fill="none" stroke="currentColor" stroke-width="1.8"/><line x1="9" y1="13" x2="15" y2="13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="9" y1="17" x2="13" y2="17" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-target':
  '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="12" r="5.5" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="12" r="2" fill="currentColor"/>',

'ico-lightbulb':
  '<path d="M12 2a7 7 0 0 0-4.5 12.7V18a1.5 1.5 0 0 0 1.5 1.5h6a1.5 1.5 0 0 0 1.5-1.5v-3.3A7 7 0 0 0 12 2z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><line x1="10" y1="22" x2="14" y2="22" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-lightning':
  '<path d="M13.5 1.5 3 14h9.5l-2 8.5L21 10h-9.5l2-8.5z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',

// ── 图表 / 数据 ──
'ico-chart':
  '<rect x="3" y="21" width="18" height="2" rx="1" fill="none" stroke="currentColor" stroke-width="1.8"/><rect x="5" y="11" width="3.5" height="10" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8"/><rect x="10" y="7" width="3.5" height="14" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8"/><rect x="15" y="2" width="3.5" height="19" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8"/>',

'ico-money':
  '<ellipse cx="12" cy="4" rx="10" ry="4.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M2 4v15c0 2.5 4.5 4.5 10 4.5s10-2 10-4.5V4" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M2 11.5c0 2.5 4.5 4.5 10 4.5s10-2 10-4.5" fill="none" stroke="currentColor" stroke-width="1.8"/>',

'ico-ruler':
  '<rect x="2.5" y="2.5" width="19" height="19" rx="3" fill="none" stroke="currentColor" stroke-width="1.8"/><line x1="8" y1="2.5" x2="8" y2="12.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="14.5" y1="2.5" x2="14.5" y2="8.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

// ── 状态 / 操作 ──
'ico-warning':
  '<path d="M12 2.5 1 22h22z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><line x1="12" y1="10" x2="12" y2="15.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="12" cy="19" r="1.5" fill="currentColor"/>',

'ico-check-circle':
  '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.8"/><polyline points="7.5 12 10.5 15.5 16.5 9.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-x-circle':
  '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.8"/><line x1="7.5" y1="7.5" x2="16.5" y2="16.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="16.5" y1="7.5" x2="7.5" y2="16.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-check':
  '<polyline points="4 13 9.5 18.5 20 7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-close':
  '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.8"/><line x1="7" y1="7" x2="17" y2="17" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="17" y1="7" x2="7" y2="17" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-x':
  '<line x1="5" y1="5" x2="19" y2="19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><line x1="19" y1="5" x2="5" y2="19" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',

'ico-ban':
  '<circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.8"/><line x1="5" y1="5" x2="19" y2="19" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

// ── 通讯 ──
'ico-phone':
  '<path d="M22 16.5v3.2a2.2 2.2 0 0 1-2.4 2.2C15 21 10 19 7.2 16.5A21 21 0 0 1 1.7 3.2 2.2 2.2 0 0 1 3.9 1h3.3a2.2 2.2 0 0 1 2.2 1.9c.2 1 .5 2 .8 3a2.2 2.2 0 0 1-.6 2.2L8.2 9.6a16 16 0 0 0 6.2 6.2l1.5-1.4a2.2 2.2 0 0 1 2.2-.6 17 17 0 0 0 3 .8 2.2 2.2 0 0 1 .7 3.9z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-mobile':
  '<rect x="5.5" y="1" width="13" height="22" rx="3.5" fill="none" stroke="currentColor" stroke-width="1.8"/><line x1="8" y1="18.5" x2="16" y2="18.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-message':
  '<path d="M21 11.5a9.5 9.5 0 0 1-5 8.3 9.5 9.5 0 0 1-9.3-4.3A9.5 9.5 0 0 1 10.3 1.7 9.5 9.5 0 0 1 21 11.5z" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M8 11.5h.01M12 11.5h.01M16 11.5h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',

'ico-email':
  '<rect x="2" y="4.5" width="20" height="16" rx="3" fill="none" stroke="currentColor" stroke-width="1.8"/><polyline points="2 6.5 12 13.5 22 6.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',

'ico-empty':
  '<rect x="2" y="4.5" width="20" height="16" rx="3" fill="none" stroke="currentColor" stroke-width="1.8"/><polyline points="2 9 12 16 22 9" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',

// ── 编辑 / 设置 ──
'ico-settings':
  '<path d="M14.3 2.8a1 1 0 0 1 1 1l.4 2.5a7 7 0 0 1 1.5.8l2.3-1.4a1 1 0 0 1 1.3.4l1.4 2.4a1 1 0 0 1-.2 1.3l-1.9 1.7a7 7 0 0 1 0 1.6l1.9 1.7a1 1 0 0 1 .2 1.3l-1.4 2.4a1 1 0 0 1-1.3.4l-2.3-1.4a7 7 0 0 1-1.5.8l-.4 2.5a1 1 0 0 1-1 1h-2.8a1 1 0 0 1-1-1l-.4-2.5a7 7 0 0 1-1.5-.8l-2.3 1.4a1 1 0 0 1-1.3-.4l-1.4-2.4a1 1 0 0 1 .2-1.3l1.9-1.7a7 7 0 0 1 0-1.6l-1.9-1.7a1 1 0 0 1-.2-1.3l1.4-2.4a1 1 0 0 1 1.3-.4l2.3 1.4a7 7 0 0 1 1.5-.8l.4-2.5a1 1 0 0 1 1-1z" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.8"/>',

'ico-pencil':
  '<path d="M16.5 2.5a2.8 2.8 0 1 1 5.5 5.5L7.5 22H1.5v-6z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-edit':
  '<path d="M12 20.5h9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M16.5 3a2.5 2.5 0 1 1 3.5 3.5L8 18.5 3 20l1.5-5z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-tag':
  '<path d="M12 1.5H1.5V12L12 22.5 22.5 12z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><circle cx="7" cy="7" r="2" fill="currentColor"/>',

// ── 箭头 / 导航 ──
'ico-chevron-down':
  '<polyline points="4.5 8.5 12 17 19.5 8.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-chevron-right':
  '<polyline points="8.5 4.5 17 12 8.5 19.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-refresh':
  '<path d="M21 2v6h-6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 22v-6h6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M3.5 15.5a9 9 0 0 1 14.8-6.1L21 12M20.5 8.5a9 9 0 0 1-14.8 6.1L3 12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

// ── 媒体 ──
'ico-play':
  '<polygon points="6 4 19 12 6 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',

'ico-pause':
  '<rect x="6" y="4.5" width="4" height="15" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8"/><rect x="14" y="4.5" width="4" height="15" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8"/>',

'ico-skip-fwd':
  '<polygon points="5 4 17.5 12 5 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><line x1="20" y1="4" x2="20" y2="20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

// ── 庆祝 / 成就 ──
'ico-party':
  '<path d="M12 2 15.5 8 22 9.5l-5.5 4L18 21.5 12 18l-6 3.5L7.5 13.5 2 9.5l6.5-2z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',

'ico-star':
  '<polygon points="12 1.5 15.5 9 23 9.5 17.5 15.5 19 22.5 12 18 5 22.5 6.5 15.5 1 9.5 8.5 9" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',

'ico-crown':
  '<path d="M2 5 7.5 15h9L22 5l-5 3.5L12 1 7 8.5z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><line x1="2" y1="20" x2="22" y2="20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-trophy':
  '<path d="M6 9H5a1.5 1.5 0 0 1-1.5-1.5V5.5A1.5 1.5 0 0 1 5 4h1" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M18 9h1a1.5 1.5 0 0 0 1.5-1.5V5.5A1.5 1.5 0 0 0 19 4h-1" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="4" y1="21.5" x2="20" y2="21.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><rect x="8" y="3" width="8" height="6" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8"/><line x1="12" y1="9" x2="12" y2="21.5" stroke="currentColor" stroke-width="1.8"/>',

'ico-gift':
  '<rect x="2" y="8.5" width="20" height="6" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/><line x1="12" y1="8.5" x2="12" y2="22" stroke="currentColor" stroke-width="1.8"/><path d="M8 8.5a3 3 0 0 1 4-2.5 3 3 0 0 1 4 2.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><rect x="5" y="14.5" width="14" height="7.5" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8"/>',

'ico-birthday':
  '<circle cx="12" cy="7" r="4" fill="none" stroke="currentColor" stroke-width="1.8"/><line x1="12" y1="11" x2="12" y2="12" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><rect x="3.5" y="12" width="17" height="11" rx="3" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="8" cy="19.5" r="1.5" fill="currentColor"/><circle cx="16" cy="19.5" r="1.5" fill="currentColor"/>',

// ── 业务场景 ──
'ico-fire':
  '<path d="M15 14.5a3 3 0 1 1-6 0c0-2 3-7 3-7s3 5 3 7z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><path d="M12 5C6 9 4.5 14 4.5 17a7.5 7.5 0 0 0 15 0c0-3-1.5-8-7.5-12z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',

'ico-diamond':
  '<polygon points="12 1.5 22.5 12 12 22.5 1.5 12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',

'ico-pin':
  '<path d="M12 2.5v8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="12" cy="6.5" r="4" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 22.5v-8M8 14.5h8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

// ── 金融 ──
'ico-credit-card':
  '<rect x="1.5" y="4" width="21" height="16" rx="3.5" fill="none" stroke="currentColor" stroke-width="1.8"/><line x1="1.5" y1="10.5" x2="22.5" y2="10.5" stroke="currentColor" stroke-width="1.8"/><line x1="4" y1="15.5" x2="9" y2="15.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="4" y1="18.5" x2="7" y2="18.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-bank':
  '<line x1="3" y1="21" x2="21" y2="21" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M4 18V9.5h3V18M10 18V9.5h3V18M16 18V9.5h3V18" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M2 9.5h20l-3-5.5H5z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>',

'ico-handshake':
  '<path d="M20.5 14 16 9.5l-3.5 3.5-2-2L7 14.5l-4.5-4.3a1.5 1.5 0 0 1 2-2.1L7 10.5l3.5-3.5 2 2 3.5-3.5 4.5 4a1.5 1.5 0 0 1-2 2.1z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-money-fly':
  '<path d="M12 2 2 12l10 10 10-10z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><circle cx="12" cy="12" r="3.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-balance':
  '<line x1="1.5" y1="1.5" x2="22.5" y2="1.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M12 1.5v9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M7.5 10.5 4 22.5h16L15.5 10.5z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><line x1="12" y1="17.5" x2="12" y2="22.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-factory':
  '<line x1="1.5" y1="20.5" x2="22.5" y2="20.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M5 10.5v10h3.5v-6h3.5v6H15.5V7.5l3-4 4 6v11H5z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><rect x="8.5" y="16" width="2" height="2" rx=".5" fill="none" stroke="currentColor" stroke-width="1.8"/><rect x="14.5" y="16" width="2" height="2" rx=".5" fill="none" stroke="currentColor" stroke-width="1.8"/>',

// ── 杂项 ──
'ico-inbox':
  '<path d="M21.5 12.5v8.5a2 2 0 0 1-2 2H4.5a2 2 0 0 1-2-2v-8.5" fill="none" stroke="currentColor" stroke-width="1.8"/><polyline points="16 6 12 10.5 8 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><line x1="12" y1="10.5" x2="12" y2="1.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

// ── 补充：AI / 文档 / 公告 ──
'ico-robot':
  '<rect x="3" y="8" width="18" height="12" rx="3" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="9" cy="14" r="1.5" fill="currentColor"/><circle cx="15" cy="14" r="1.5" fill="currentColor"/><line x1="12" y1="1.5" x2="12" y2="8" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="12" cy="1.5" r="1.5" fill="currentColor"/>',

'ico-trend-up':
  '<polyline points="3 17 9 11 13 15 21 7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><polyline points="15 7 21 7 21 13" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>',

'ico-wallet':
  '<rect x="1.5" y="4" width="21" height="16" rx="3" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M16 12h5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><circle cx="18.5" cy="12" r="1" fill="currentColor"/><path d="M1.5 8h21" stroke="currentColor" stroke-width="1.8"/>',

'ico-file-text':
  '<path d="M14 1.5H5.5a2 2 0 0 0-2 2v17a2 2 0 0 0 2 2h13a2 2 0 0 0 2-2v-13z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><polyline points="14 1.5 14 7.5 20.5 7.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><line x1="7.5" y1="12.5" x2="16.5" y2="12.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><line x1="7.5" y1="16.5" x2="14" y2="16.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-megaphone':
  '<path d="M21 3 11 9H4a2 2 0 0 0-2 2v2a2 2 0 0 0 2 2h1l2 6h3l-2-6h6l10 6V3z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/><line x1="21" y1="3" x2="21" y2="21" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-inbox-arrow':
  '<path d="M21.5 15.5v5.5a2 2 0 0 1-2 2H4.5a2 2 0 0 1-2-2v-5.5" fill="none" stroke="currentColor" stroke-width="1.8"/><polyline points="7 10.5 12 15.5 17 10.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><line x1="12" y1="15.5" x2="12" y2="1.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-laptop':
  '<rect x="3" y="3" width="18" height="13" rx="2.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M1 19h22" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M1 19 3 16M23 19l-2-3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

// ── 补充：建筑 / 家庭 / 导出 ──
'ico-building':
  '<rect x="3" y="3" width="18" height="19" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/><rect x="7" y="7" width="3" height="3" rx=".5" fill="currentColor"/><rect x="14" y="7" width="3" height="3" rx=".5" fill="currentColor"/><rect x="7" y="13" width="3" height="3" rx=".5" fill="currentColor"/><rect x="14" y="13" width="3" height="3" rx=".5" fill="currentColor"/><path d="M10 22v-4h4v4" fill="none" stroke="currentColor" stroke-width="1.8"/>',

'ico-family':
  '<circle cx="12" cy="5" r="3" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="4.5" cy="8" r="2.5" fill="none" stroke="currentColor" stroke-width="1.8"/><circle cx="19.5" cy="8" r="2.5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M1 21v-1.5a4 4 0 0 1 7 0V21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M8 21v-2a5 5 0 0 1 8 0v2" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/><path d="M16 21v-1.5a4 4 0 0 1 7 0V21" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>',

'ico-upload':
  '<path d="M21.5 15.5v5.5a2 2 0 0 1-2 2H4.5a2 2 0 0 1-2-2v-5.5" fill="none" stroke="currentColor" stroke-width="1.8"/><polyline points="17 8 12 3 7 8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><line x1="12" y1="3" x2="12" y2="15.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>'
};
