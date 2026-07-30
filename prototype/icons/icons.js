// ========================================
//  Icon Theme Manager
//  Manage multiple icon sets with real-time switching
// ========================================
(function() {
  var THEME_KEY = 'yh_icon_theme';
  var current = localStorage.getItem(THEME_KEY) || 'modern';

  function inject(sprite, icons) {
    var defs = sprite.querySelector('defs');
    if (!defs) { defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs'); sprite.appendChild(defs); }
    defs.innerHTML = '';
    for (var id in icons) {
      var g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      g.setAttribute('id', id);
      g.innerHTML = icons[id];
      defs.appendChild(g);
    }
  }

  window.IconManager = {
    get: function() { return current; },
    set: function(name) {
      var sets = window.ICON_SETS || {};
      if (!sets[name]) return;
      current = name;
      localStorage.setItem(THEME_KEY, name);
      var sprite = document.getElementById('iconSprite');
      if (sprite) inject(sprite, sets[name]);
      // fire event for UI updates
      document.dispatchEvent(new CustomEvent('icon-theme-changed', { detail: name }));
    },
    init: function() {
      var sprite = document.getElementById('iconSprite');
      if (!sprite) return;
      var icons = (window.ICON_SETS || {})[current];
      if (icons) inject(sprite, icons);
    },
    themes: function() { return Object.keys(window.ICON_SETS || {}); },
    displayName: function(name) {
      return ({ classic: '经典(实心)', modern: '简约(描边)' })[name] || name;
    }
  };

  // auto-init on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() { IconManager.init(); });
  } else {
    IconManager.init();
  }
})();
