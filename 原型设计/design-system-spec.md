# 徽小助 Design System v3.0

> 设计系统规范文档 v3.0，基于 v2.1 改进：
> - 核心聚焦两大任务：**智能日程**（横向滑动卡片 + AI排程）+ **商机看板**（目标→缺口→挖掘→新客闭环）
> - 待办卡片支持横向滑动浏览，同类型可折叠
> - 商机挖掘与考核目标关联，含转化率计算和新客拓展路径
> 所有后续页面开发以此为唯一参考。
> 原型参考实现：`原型设计/workbench.html`

---

## 一、设计理念

```
关键词：任务驱动 · 智能排程 · 商机闭环 · 简洁明快

v3.0 核心改进：
- 工作台 = 智能日程 + 商机看板，不堆砌信息
- AI 主动排程，客户经理按时间线执行即可
- 商机挖掘与考核目标形成闭环：目标→缺口→挖掘→新客
- 横向滑动卡片，单屏可见更多任务，减少纵向滚动
```

---

## 二、配色规范

### 2.1 默认配色方案（v2.1）

#### 品牌色

| Token | 色值 | 用途 |
|------|------|------|
| `--color-primary` | `#3568F0` | 主按钮、链接、选中态 |
| `--color-primary-dark` | `#2554D6` | 按钮按下态 |
| `--color-primary-light` | `#EEF2FE` | 浅色背景、选中背景 |

#### AI 专属色

| Token | 色值 | 用途 |
|------|------|------|
| `--color-ai` | `#6366F1` | AI 元素主色（标签、图标、文字高亮） |
| `--color-ai-light` | `#EEF0FF` | AI 元素浅色背景 |
| `--color-ai-gradient` | `linear-gradient(135deg, #818CF8 → #6366F1 → #4F46E5)` | AI 洞察卡片背景 |
| `--color-ai-glow` | `0 4px 20px rgba(99, 102, 241, 0.25)` | AI 卡片/按钮发光投影 |

#### 功能色

| Token | 色值 | 用途 |
|------|------|------|
| `--color-success` | `#10B981` | 成功、完成、正向指标 |
| `--color-warning` | `#F59E0B` | 警告、待处理、中等优先级 |
| `--color-danger` | `#EF4444` | 错误、紧急、高优先级、红点角标 |
| `--color-highlight` | `#EF4444` | 关键数字强调（收益率、金额变动） |
| `--color-cta` | `#F59E0B` | CTA按钮 |

#### 中性色

| Token | 色值 | 用途 |
|------|------|------|
| `--color-bg` | `#EDEFF2` | 页面背景（加深增强对比度） |
| `--color-card` | `#FFFFFF` | 卡片背景 |
| `--color-divider` | `#E5E7EB` | 分割线 |
| `--color-border` | `#D1D5DB` | 描边按钮边框 |

#### 文字色

| Token | 色值 | 用途 |
|------|------|------|
| `--color-text-primary` | `#111827` | 标题、正文（更深，增强可读性） |
| `--color-text-secondary` | `#6B7280` | 副标题、辅助说明 |
| `--color-text-tertiary` | `#9CA3AF` | 占位文字、禁用态 |
| `--color-text-white` | `#FFFFFF` | 深色背景上的文字 |
| `--color-text-link` | `#3568F0` | 链接文字 |

---

### 2.2 备选配色方案

#### 方案B：经典商务（原v1.0配色）

适用于偏好稳重、专业感的场景。

```css
:root[data-theme="classic"] {
  --gradient-primary: linear-gradient(135deg, #1A6FF5 0%, #1A6FF5 100%);
  --color-primary: #1A6FF5;
  --color-primary-dark: #0D4FBF;
  --color-primary-light: #E8F1FE;
  --color-highlight: #FF3141;
  --color-cta: #FF8F1F;
}
```

#### 方案C：清新绿

适用于财富、理财主题页面，传递安全、稳健感。

```css
:root[data-theme="green"] {
  --gradient-primary: linear-gradient(135deg, #00B578 0%, #00C9A7 100%);
  --color-primary: #00B578;
  --color-primary-dark: #009966;
  --color-primary-light: #E6F9F1;
  --color-highlight: #FF3B30;
  --color-cta: #00B578;
}
```

#### 方案D：活力橙

适用于活动、促销页面，传递热情、活力感。

```css
:root[data-theme="orange"] {
  --gradient-primary: linear-gradient(135deg, #FF6B35 0%, #FF8C61 100%);
  --color-primary: #FF6B35;
  --color-primary-dark: #E55A2B;
  --color-primary-light: #FFF0E8;
  --color-highlight: #FF3B30;
  --color-cta: #FF6B35;
}
```

#### 方案E：科技深蓝

适用于数据看板、技术分析页面。

```css
:root[data-theme="dark-blue"] {
  --gradient-primary: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
  --color-primary: #3B82F6;
  --color-primary-dark: #2563EB;
  --color-primary-light: #EFF6FF;
  --color-highlight: #F59E0B;
  --color-cta: #3B82F6;
}
```

---

### 2.3 配色使用原则

```
1. Header
   → 干净白底 + 底部 1px 分割线
   → 绿色呼吸灯指示 AI 在线状态

2. AI 洞察卡片（color-ai-gradient）
   → 页面最顶部，紫色渐变背景，白色文字
   → 这是 AI 体验的核心入口，必须显眼

3. AI 快捷指令
   → 2×2 网格，与普通快捷入口分离
   → 使用"AI + 动词"命名（AI摘要、生成话术）

4. 关键数字（color-highlight）
   → 收益率、金额变动等关键数据使用红色

5. 功能色
   → 用于状态标签、提示、图标

6. 浮动 AI 按钮
   → 右下角悬浮，紫色渐变 + 发光投影
   → 轻微上下浮动动画，暗示"活的 AI"

7. AI 标注
   → 待办/商机上使用 AI 标签（"AI建议优先""AI推荐"）
   → 让用户感知 AI 在工作
```

---

## 三、Design Tokens（CSS 变量）

### 3.1 字体

| Token | 值 | 说明 |
|------|------|------|
| `--font-family` | `-apple-system, "PingFang SC", "Helvetica Neue", sans-serif` | 中西文混排最优 |
| `--font-number` | `"DIN Alternate", "SF Mono", monospace` | 数字专用（等宽、有辨识度） |

### 3.2 字号阶梯

| Token | 值 | 用途 |
|------|------|------|
| `--fs-page-title` | `24px / Bold` | 页面主标题 |
| `--fs-section-title` | `17px / Bold` | 区块标题 |
| `--fs-card-title` | `15px / Medium` | 卡片标题 |
| `--fs-body` | `14px / Regular` | 正文、列表项 |
| `--fs-caption` | `12px / Regular` | 辅助说明、标签文字 |
| `--fs-small` | `11px / Regular` | 极小标注 |
| `--fs-number-lg` | `32px / Bold` | 大数字（AUM、完成率） |
| `--fs-number-md` | `24px / Bold` | 中数字（收益率、金额） |
| `--fs-number-sm` | `18px / Bold` | 小数字（卡片内指标） |

### 3.3 间距（8px 基准）

| Token | 值 | 用途 |
|------|------|------|
| `--sp-xxs` | `4px` | 极小间距（图标与文字） |
| `--sp-xs` | `8px` | 紧凑间距（标签之间） |
| `--sp-sm` | `12px` | 小间距（卡片内部、按钮内边距） |
| `--sp-md` | `16px` | 标准间距（页面内边距、卡片内边距） |
| `--sp-lg` | `20px` | 大间距（区块之间） |
| `--sp-xl` | `24px` | 超大间距 |

### 3.4 圆角

| Token | 值 | 用途 |
|------|------|------|
| `--radius-sm` | `8px` | 小按钮、输入框、标签 |
| `--radius-md` | `12px` | 中型容器、CTA按钮 |
| `--radius-lg` | `16px` | **卡片（默认）** |
| `--radius-xl` | `24px` | 大容器、弹窗 |
| `--radius-full` | `999px` | 胶囊按钮、角标 |
| `--radius-circle` | `50%` | 头像、图标圆形容器 |

### 3.5 阴影

| Token | 值 | 用途 |
|------|------|------|
| `--shadow-card` | `0 4px 16px rgba(0, 0, 0, 0.06)` | 普通卡片投影 |
| `--shadow-elevated` | `0 8px 32px rgba(0, 0, 0, 0.12)` | 浮层/弹窗投影 |
| `--shadow-button` | `0 4px 12px rgba(74, 111, 253, 0.3)` | 主按钮投影 |

### 3.6 动效

| Token | 值 |
|------|------|
| `--ease-default` | `cubic-bezier(0.4, 0, 0.2, 1)` |
| `--duration-fast` | `150ms` |
| `--duration-normal` | `250ms` |
| `--duration-slow` | `350ms` |

---

## 四、组件规范

### 4.1 头部 Header

```css
.app-header {
  background: #FFFFFF;
  padding: 6px 16px 12px;
  box-shadow: 0 1px 0 #E5E7EB; /* 底部 1px 分割线 */
}
```

**规则：**
- 干净白底，不做渐变
- 底部仅用 1px 分割线做层次区分
- 问候语右侧放置绿色 AI 呼吸灯（`ai-dot`），表示 AI 在线状态
- 图标按钮背景色 `--color-bg`，按下变 `--color-divider`

### 4.2 AI 智能洞察卡片

```css
.ai-insight-card {
  background: linear-gradient(135deg, #818CF8 0%, #6366F1 50%, #4F46E5 100%);
  border-radius: 16px;
  padding: 16px;
  color: #fff;
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.25);
}
```

**规则：**
- 紫色渐变背景 + 发光投影，是页面的视觉焦点
- 置于滚动内容最顶部，比其他卡片更抢眼
- 包含 AI 徽章（半透明白底 + 毛玻璃）、洞察标题、洞察条目列表
- 洞察条目逐条渐显动画（各延迟 200ms）
- 整个卡片可点击，跳转 AI 洞察详情

### 4.3 AI 快捷指令

```css
.ai-quick-actions {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.ai-quick-btn {
  padding: 12px 16px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}
```

**规则：**
- 2×2 网格，位于 AI 洞察卡片下方
- 按钮突出 AI 能力："今日AI摘要""生成营销话术""客群智能分析""查看AI日报"
- 使用"AI + 动词"的命名模式
- 带小图标（紫色/蓝色/绿色/橙色四种背景）

### 4.4 浮动 AI 助手按钮

```css
.fab-ai {
  position: absolute; right: 16px; bottom: 80px;
  width: 52px; height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #818CF8, #4F46E5);
  box-shadow: 0 4px 20px rgba(99,102,241,0.25);
  animation: fabFloat 3s ease-in-out infinite;
}
@keyframes fabFloat {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-4px); }
}
```

**规则：**
- 始终悬浮在右下角，Tab Bar 上方
- 轻微上下浮动动画（3s周期），暗示 AI 是"活"的
- 点击弹出 AI 对话面板
- 旁边可显示文字标签（hover/active 时出现）

### 4.5 AI 标注标签

```css
.ai-label {
  font-size: 10px; font-weight: 600;
  color: #6366F1; background: #EEF0FF;
  padding: 2px 6px; border-radius: 4px;
}
```

**规则：**
- 用于待办项、商机项的 AI 标注
- 示例："AI建议优先""AI推荐"
- 紫色文字 + 浅紫色背景
- 小而精致，不喧宾夺主

### 4.6 卡片 Card

```css
.card {
  background: #FFFFFF;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}
```

**规则：**
- 圆角统一使用 `radius-lg`（16px）
- 投影明显但不厚重
- 可点击卡片：按下时 `scale(0.98)` + 投影减弱
- 卡片之间间距 `12px`

### 4.7 按钮 Button

| 类型 | Class | 场景 | 样式 |
|------|------|------|------|
| 主按钮 | `.btn--primary` | 主要操作 | 蓝色底 + 投影 |
| CTA按钮 | `.btn--cta` | 引导行动 | **橙色底 + 圆角** |
| 幽灵按钮 | `.btn--ghost` | 次要操作 | 透明底蓝字 |
| 描边按钮 | `.btn--outline` | 查看类操作 | 透明底灰字+边框 |

**尺寸：**

| Size | 高度 | 内边距 | 字号 | 圆角 |
|------|:---:|------|------|------|
| `sm` | 32px | 0 16px | 13px | 8px |
| `md` | 40px | 0 20px | 15px | 12px |
| `lg` | 48px | 0 24px | 16px | 16px |

**CTA按钮规范：**

```css
.btn--cta {
  background: var(--color-cta);
  color: #fff;
  border-radius: var(--radius-md);
  box-shadow: 0 4px 12px rgba(255, 149, 0, 0.3);
}
.btn--cta:active {
  background: var(--color-cta-dark);
  transform: scale(0.96);
}
```

**规则：**
- CTA按钮使用橙色，与主按钮蓝色形成对比
- 圆角较大（12px），现代感更强
- 按下时缩放 + 颜色加深
- 禁用态 `opacity: 0.4`

### 4.4 标签 Tag

| 颜色 | Class | 场景 |
|------|------|------|
| 红 | `.tag--red` | 高优先级、紧急、代销标签 |
| 橙 | `.tag--orange` | 中优先级、警告 |
| 绿 | `.tag--green` | 正常、已完成 |
| 蓝 | `.tag--blue` | 信息、推荐 |
| 灰 | `.tag--gray` | 中性标注 |

```css
.tag {
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.3px;
}
```

**规则：**
- 方形标签（`border-radius: 6px`），非胶囊形
- 字号 11px，字重 600（更醒目）
- 可放置在右上角（绝对定位）

### 4.5 状态圆点 Dot

| 颜色 | Class | 场景 |
|------|------|------|
| 红 | `.dot--danger` | 紧急待办（产品到期） |
| 橙 | `.dot--warning` | 需关注（大额异动、贷款逾期） |
| 绿 | `.dot--success` | 常规（生日提醒） |
| 灰 | `.dot--muted` | 信息类（联络超期） |

```css
.dot {
  width: 8px; height: 8px;
  border-radius: 50%;
}
```

### 4.6 数字展示 Number Display

**规则：**
- 所有数字使用 `font-family: --font-number`
- **关键数字（收益率、金额变动）使用红色（`color-highlight`）**
- 大数字（≥28px）必须加粗 `font-weight: 700`
- 金额单位（万/元）用小号文字跟随
- 百分比使用 `%` 符号，不加空格

**示例：**

```css
.number-highlight {
  font-family: var(--font-number);
  font-size: var(--fs-number-md);
  font-weight: 700;
  color: var(--color-highlight);
}
```

### 4.7 快捷入口图标 Grid Icons

```css
.shortcut-item .icon-circle {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.icon-bg-blue { background: linear-gradient(135deg, #E8EEFF 0%, #D6E4FF 100%); }
.icon-bg-green { background: linear-gradient(135deg, #E8F9ED 0%, #D4F4DD 100%); }
.icon-bg-orange { background: linear-gradient(135deg, #FFF5E6 0%, #FFE8CC 100%); }
.icon-bg-purple { background: linear-gradient(135deg, #F3E8FF 0%, #E9D5FF 100%); }
.icon-bg-red { background: linear-gradient(135deg, #FFE8E6 0%, #FFD6D1 100%); }
```

**规则：**
- 图标容器 48×48px（比 v1.0 的 44px 更大）
- 使用渐变色背景，增强层次感
- 图标字号 24px
- 支持 5 种背景色：蓝/绿/橙/紫/红

### 4.8 产品卡片 Product Card

参考UI中的理财产品卡片样式：

```css
.product-card {
  background: #fff;
  border-radius: 16px;
  padding: 16px;
  position: relative;
}

.product-card .yield {
  font-family: var(--font-number);
  font-size: 24px;
  font-weight: 700;
  color: var(--color-highlight);
}

.product-card .tag--agency {
  position: absolute;
  top: 12px;
  right: 12px;
}
```

**规则：**
- 收益率数字使用红色突出
- "代销"标签放在右上角
- 卡片底部展示起购金额和赎回方式

### 4.9 进度条 Progress Bar

```css
.progress-bar {
  height: 8px;
  background: #E8ECF0;
  border-radius: 4px;
}
.progress-bar .fill {
  background: linear-gradient(90deg, var(--color-primary), #6B8FFF);
  border-radius: 4px;
}
```

**规则：**
- 高度 8px（比 v1.0 的 6px 更明显）
- 圆角 4px（非全圆角）
- 填充色使用品牌色渐变

---

## 五、数据格式化规则

### 5.1 金额

| 场景 | 格式 | 示例 |
|------|------|------|
| ≥ 10,000 元 | `XX万`（保留整数） | `128万`、`85万` |
| < 10,000 元 | `X,XXX元`（千分位） | `5,200元` |
| 带目标值 | `{当前}万/{目标}万` | `85/120万` |
| 正增长 | 不加 `+`，用绿色 | `128万`（绿） |
| 负增长 | 加 `-`，用红色 | `-5万`（红） |

### 5.2 收益率

| 场景 | 格式 | 示例 |
|------|------|------|
| 年化收益率 | `X.XXXX%` | `1.9288%`（**红色**） |
| 7日年化 | `X.XX%` | `1.13%`（**红色**） |
| 日收益率 | `X.XXXX%` | `0.0695%`（**红色**） |

**规则：** 所有收益率数字使用 `color-highlight`（红色）突出显示。

### 5.3 百分比

| 场景 | 格式 | 示例 |
|------|------|------|
| 进度 | `XX%`（整数） | `64%`、`85%` |
| 变化率 | `+/−X%` + 箭头 | `+5% ↗`、`−3% ↘` |

### 5.4 人数/户数

| 场景 | 格式 | 示例 |
|------|------|------|
| 待办人数 | `X人` | `3人`、`1人` |
| 客户数 | `X位` | `2位客户`、`4位` |

### 5.5 日期/时间

| 场景 | 格式 | 示例 |
|------|------|------|
| 日期 | `MM月DD日` | `7月18日` |
| 倒计时 | `X天后` | `3天后` |
| 时间范围 | `未来X天` | `未来7天` |
| 收益率周期 | `YYYYMMDD–YYYYMMDD` | `20260415–20260714` |

---

## 六、图标系统

一期使用系统 Emoji 作为图标方案（零依赖、跨平台渲染一致）。后续可替换为自定义 SVG icon font。

### 6.1 场景图标

| 图标 | 用途 |
|:---:|------|
| 📊 | 业绩/数据看板 |
| 📋 | 待办/任务列表 |
| 💡 | 商机/推荐 |
| 📰 | 资讯/消息 |
| ⏰ | 回顾/历史 |
| 📅 | 日程/日历 |
| 👥 | 客户/联系人 |
| 📝 | 记录/笔记 |
| 💰 | 财富/理财 |
| 🏦 | 贷款/信贷 |

### 6.2 功能图标

| 图标 | 用途 |
|:---:|------|
| 🔍 | 搜索 |
| 🔔 | 通知 |
| 📥 | 收入/到账 |
| ⚠️ | 警告/风险 |
| 🏠 | 首页/工作台 |
| 💬 | 营销/话术 |
| 📦 | 产品 |
| 👤 | 我的/个人 |
| 📷 | 扫码/二维码 |
| ➕ | 新增/添加 |

---

## 七、交互一致性规范

### 7.1 点击反馈

| 元素 | 反馈方式 |
|------|---------|
| 卡片（可点击） | `scale(0.98)` + 投影减弱 + 150ms |
| 主按钮 | `scale(0.96)` + 颜色加深 + 150ms |
| CTA按钮 | `scale(0.96)` + 颜色加深 + 150ms |
| 列表行 | 背景变灰 + 150ms |
| 图标按钮 | 背景变灰 + 150ms |
| 快捷入口 | 背景变灰 + 150ms |
| Tab 切换 | 颜色切换 + 150ms（无缩放） |

**规则：** 所有可交互元素必须有视觉反馈，反馈时间 ≤ 150ms。

### 7.2 手势

| 手势 | 场景 |
|------|------|
| 点击 | 主要操作 |
| 长按 | 不推荐（移动端误触率高） |
| 左滑 | 列表项快捷操作（查看客户画像/生成作战包） |
| 右滑 | 关闭已展开的左滑操作 |
| 下拉 | 工作台首页刷新（scrollTop=0 时） |
| 上滑 | 页面内滚动（`scroll-content`） |

### 7.3 动效

| 类型 | 时长 | 缓动 |
|------|:---:|------|
| 点击反馈 | 150ms | `cubic-bezier(0.4, 0, 0.2, 1)` |
| 页面过渡 | 250ms | 同上 |
| 进度条动画 | 350ms | 同上 |
| Toast 显隐 | 250ms | 同上 |
| 按钮状态切换 | 300ms | 同上 |

**规则：**
- 所有动效使用相同的缓动函数（Material Design 标准缓动）
- 不做弹跳/回弹动效（金融产品需要稳重感）

### 7.4 Toast 提示

```css
.toast {
  position: fixed; bottom: 120px;
  background: rgba(29, 29, 31, 0.92);
  color: #fff; padding: 12px 24px;
  border-radius: 12px; font-size: 14px;
}
```

**规则：**
- 位置：底部 Tab Bar 上方（`bottom: 120px`）
- 显示时长：1.5 秒自动消失
- 圆角 12px（与按钮圆角一致）
- 内容：一句话，不超过 15 字

### 7.5 骨架屏加载

页面首次加载时展示骨架屏，替代传统的 loading spinner：

```css
.skeleton-line {
  background: linear-gradient(90deg, #E8ECF0 25%, #F2F4F7 50%, #E8ECF0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s ease-in-out infinite;
}
```

**规则：**
- 骨架屏结构与真实页面完全对应
- 加载时间 1.2s，之后淡出
- 大数字首次渲染时使用数字递增动画（easeOutCubic, 800ms）

### 7.6 左滑操作

待办列表项支持左滑露出操作按钮：

```
结构：[列表项内容] ← 左滑 → [画像(蓝) | 作战包(深蓝)]
                             70px      70px
```

**规则：**
- 滑动阈值：60px
- 展开后固定，点击其他区域或右滑关闭
- 同一时间只有一项展开
- 仅在待办项上启用

### 7.7 空状态

| 场景 | 处理方式 |
|------|---------|
| 待办为 0 条 | 不展示该类型（整行隐藏） |
| 列表为空 | 居中插图 + "暂无数据" + 操作引导 |
| 搜索无结果 | "未找到相关结果，试试其他关键词" |

---

## 八、页面布局规范

### 8.1 通用页面骨架

```
┌────────────────────────────── 375px ──────────────────────────────┐
│ Status Bar (24px)                                                 │
├───────────────────────────────────────────────────────────────────┤
│ Gradient Header (auto)                                            │
│  渐变背景 / 搜索栏 / 用户信息                                       │
│  底部圆角 24px                                                     │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Scroll Content (flex: 1, overflow-y: auto)                        │
│   padding: 12px 16px                                              │
│   gap: 12px                                                       │
│                                                                   │
│  Section                                                          │
│    Section Header (title + more link)                             │
│    Card                                                            │
│      ...                                                          │
│                                                                   │
├───────────────────────────────────────────────────────────────────┤
│ Tab Bar (56px + safe-area)                                        │
└───────────────────────────────────────────────────────────────────┘
```

### 8.2 安全区域

- 顶部 Status Bar 高度：24px
- 底部 Tab Bar 需适配 `safe-area-inset-bottom`
- 左右不留安全区（375px 全宽使用，内容 padding 16px）

### 8.3 触控最小区域

- 所有可点击元素的最小触控区域：**44×44px**
- 列表项高度 ≥ 44px
- 按钮最小高度 32px（sm）/ 40px（md）/ 48px（lg）

---

## 九、页面宽度与视口

| 设备 | 宽度 | 说明 |
|------|:---:|------|
| iPhone SE | 375px | 设计基准 |
| iPhone 12/13/14 | 390px | 等比缩放 |
| iPhone 12/13/14 Pro Max | 428px | 等比缩放 |
| Android 主流 | 360-412px | 弹性适配 |

**规则：**
- 设计稿以 **375px** 为基准
- 使用 `max-width: 375px` + 居中显示
- 内部使用弹性布局自适应

---

## 十、命名约定

| 类别 | 命名方式 | 示例 |
|------|------|------|
| CSS 变量 | `--{类别}-{属性}` | `--color-primary`, `--fs-body` |
| 组件 Class | BEM 风格 | `.card`, `.card--tappable`, `.btn--cta` |
| 页面文件 | 小写 + 连字符 | `workbench.html`, `customer-profile.html` |
| 配色主题 | `data-theme` 属性 | `data-theme="classic"` |
| 颜色语义 | danger/warning/success/primary | 不用 red/orange/green |

---

## 十一、工作台首页（W1）v3.0 结构

```
Status Bar (白色)
Header (白色, 底部分割线)
  下午好，李经理            [🔍] [🔔3]
────────────────────────────
🤖 AI 智能摘要 (浅紫背景，左侧紫色竖线)
  "今日8项待办，AI已根据紧急程度和预计耗时完成智能排程。
   上午优先处理高价值到期客户，下午集中联络超期客户。
   预计总耗时 3.5小时。"
────────────────────────────
📋 今日智能日程                    左右滑动查看

☀ 上午 · 4项待办 · 约2h
┌─ 横向滑动 ──────────────────────────┐
│ ┌──────────┐ ┌──────────┐           │
│ │#1 产品到期│ │#2 大额异动│  ← 滑动   │
│ │3位客户    │ │1位客户    │           │
│ │09:00-10:30│ │10:30-11:00│           │
│ │[开始处理] │ │[开始处理] │           │
│ └──────────┘ └──────────┘           │
└────────────────────────────────────┘

🌤 下午 · 4项待办 · 约1.5h
┌─ 横向滑动 ──────────────────────────┐
│ ┌──────────┐ ┌──────────┐ ┌───────┐ │
│ │#3 贷款逾期│ │#4 生日提醒│ │#5联络 │ │
│ │1位客户    │ │2位客户    │ │超期   │ │
│ │14:00-14:30│ │14:30-15:00│ │15-16h │ │
│ │[开始处理] │ │[开始处理] │ │[查看] │ │
│ └──────────┘ └──────────┘ └───────┘ │
└────────────────────────────────────┘
────────────────────────────
💡 商机看板                        详情 ›

┌ 目标进度 ──────────────────────────┐
│ +128万   本月AUM目标 200万          │
│ ████████████░░░░░░ 64%              │
│ 📐 转化率 15% → 需获取 12个商机     │
├────────────────────────────────────┤
│ 现有商机池              转化率 15%  │
│ ┌────────┬────────┬────────┐       │
│ │ 5个    │ 45万   │ 27万   │       │
│ │当前商机│预计贡献│金额缺口│       │
│ └────────┴────────┴────────┘       │
│ ⚠ 现有商机不足以完成目标            │
│ 📥 代发即将到账 → ≈8万    挖掘 ›   │
│ ⚠️ 流失预警挽回 → ≈30万   紧急 ›   │
├────────────────────────────────────┤
│ 🤖 AI 商机挖掘建议                  │
│ · 沉睡客户激活       预计 +5个      │
│ · 7月代发新名单      预计 +3个      │
│ · 贷款客户交叉销售   预计 +2个      │
│ ─────────────────────────           │
│ 合计 ≈10个 · 约50万 → 可覆盖缺口   │
│ [⚡ 一键AI挖掘]                     │
├────────────────────────────────────┤
│ 💡 客群基数预警                     │
│ 当前管户238人，可挖掘商机近上限。    │
│ 建议拓展新客源，AI推荐新增50户。    │
│ [📋 获取AI推荐新客名单]             │
└────────────────────────────────────┘
────────────────────────────
快捷行动
[📅日程] [💬话术] [🔍客户] [📊业绩]

Tab Bar: 🏠工作台 👥客户 💬AI营销 📦产品 👤我的
```

> **v3.0 关键变化**：
> - 从信息罗列转变为**任务驱动**：工作台只做两件事——告诉用户今天做什么（智能日程）、帮用户发现机会（商机看板）
> - 待办卡片改为**横向滑动布局**，按上午/下午分时段，每张卡片固定260px宽
> - AI摘要从卡片改为**横幅样式**，左侧紫色竖线+浅紫背景，突出排程理由
> - 商机看板形成**完整闭环**：目标进度 → 转化率计算 → 商机池 → 缺口预警 → AI挖掘建议 → 客群基数预警（新客拓展路径）
> - 新增**客群基数预警**卡片：当现有客户商机不足时，提示拓展新客
>