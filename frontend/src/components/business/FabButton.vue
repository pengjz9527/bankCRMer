<template>
  <div class="fab-ai" @click="$router.push('/ai/chat')">
    <span class="fab-ai-icon">
      <svg viewBox="0 0 24 24" class="ico ico--md"><use href="#ico-sparkles" /></svg>
    </span>
  </div>
</template>

<style scoped>
.fab-ai {
  position: absolute; bottom: 12px; right: 16px; z-index: 150;
  width: 48px; height: 48px; border-radius: 50%;
  background: linear-gradient(135deg, var(--color-ai), #7C6FF0);
  box-shadow: 0 4px 16px rgba(108, 92, 231, 0.45), 0 0 0 3px var(--color-card);
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  transition: transform var(--duration-fast), box-shadow var(--duration-fast);
  animation: fab-pulse 2.5s ease-in-out infinite;
  -webkit-tap-highlight-color: transparent;
}
.fab-ai:active { transform: scale(0.92); }
.fab-ai-icon { font-size: 20px; line-height: 1; pointer-events: none; }

@keyframes fab-pulse {
  0%, 100% { box-shadow: 0 4px 16px rgba(108, 92, 231, 0.45), 0 0 0 3px var(--color-card); }
  50% { box-shadow: 0 4px 24px rgba(108, 92, 231, 0.65), 0 0 0 5px rgba(108, 92, 231, 0.12); }
}
</style>
