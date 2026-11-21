/**
 * ⚡ LoL Voice & Media Studio - Frontend Application Logic
 * Powered by Decoupled Native REST & SSE Engine
 */

// Global crash and error handler
window.onerror = function(message, source, lineno, colno, error) {
  console.error("Global JS Error:", message, source, lineno, error);
  const logElem = document.getElementById('console-logs');
  if (logElem) {
    const errDiv = document.createElement('div');
    errDiv.className = 'text-rose-400 font-mono text-[10px]';
    errDiv.innerText = `⚠️ JS Hatası (${lineno}:${colno}): ${message}`;
    logElem.appendChild(errDiv);
  }
  return false;
};

let allChampions = [];
let selectedChampion = null;
let selectedSkin = null;
let selectedRefChampion = null;

let audioPlayer;
let playBtn;
let playIcon;
let playText;
let audioSeek;
let playerTime;
let playerTitle;
let playerSubtitle;
let consoleLogs;
let progressBarContainer;

function initDomElements() {
  audioPlayer = document.getElementById('html5-audio');
  playBtn = document.getElementById('btn-play');
  playIcon = document.getElementById('play-icon');
  playText = document.getElementById('play-text');
  audioSeek = document.getElementById('audio-seek');
  playerTime = document.getElementById('player-time');
  playerTitle = document.getElementById('player-title');
  playerSubtitle = document.getElementById('player-subtitle');
  consoleLogs = document.getElementById('console-logs');
  progressBarContainer = document.getElementById('progress-bar-container');

  if (audioPlayer) {
    audioPlayer.ontimeupdate = () => {
      if (audioPlayer.duration) {
        const cur = formatTime(audioPlayer.currentTime);
        const dur = formatTime(audioPlayer.duration);
        if (playerTime) playerTime.innerText = `${cur} / ${dur}`;
        if (audioSeek) audioSeek.value = (audioPlayer.currentTime / audioPlayer.duration) * 100;
      }
    };
    audioPlayer.onended = () => {
      updatePlayButtonState(false);
      // Advance to next audio in queue if autoplay is enabled
      if (isAutoplayEnabled && activeAudioQueue.length > 0 && currentQueueIndex + 1 < activeAudioQueue.length) {
        playQueueItem(currentQueueIndex + 1);
      } else {
        isBatchPlaying = false;
        updateBatchPlayButtonState(false);
      }
    };
  }
}

// =========================================================================
// 1. INITIALIZATION & SSE REAL-TIME LOG STREAM
// =========================================================================
async function initAppCore() {
  initDomElements();
  setupSplitterResizer();
  restoreTheme();
  restoreLayoutSettings();
  restoreSplitterHeight();
  restoreGridDensity();
  restoreZoomLevel();
  setupZoomShortcuts();

  // Connect Server-Sent Events (SSE) for Real-Time Live Logs
  setupLiveLogStream();

  // Load champions list smoothly
  await loadChampions();

  // URL Hash support for direct tab opening (e.g. #references)
  const initialHash = window.location.hash.replace('#', '');
  if (initialHash && ['voices', 'skinhub', 'competitors', 'references', 'wallpapers', 'static-wallpapers'].includes(initialHash)) {
    switchTab(initialHash);
  }
}

window.initAppCore = initAppCore;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    if (typeof loadChampions === 'function') initAppCore();
  });
} else {
  if (typeof loadChampions === 'function') initAppCore();
}

// =========================================================================
// DYNAMIC UI ZOOM CONTROLLER (Ctrl + / - / 0 & Wheel)
// =========================================================================
let currentZoomLevel = 1.0;
let currentTab = 'voices';

function setZoomLevel(level, showToast = true) {
  level = Math.max(0.6, Math.min(2.0, Math.round(level * 100) / 100));
  currentZoomLevel = level;
  try {
    document.documentElement.style.zoom = currentZoomLevel;
    document.body.style.zoom = '';
    document.body.style.height = '';
    document.body.style.width = '';
    localStorage.setItem('app_zoom_level', String(currentZoomLevel));
    // Force instant DOM layout recalculation
    window.dispatchEvent(new Event('resize'));
  } catch (e) {
    console.warn("Zoom LocalStorage error:", e);
  }

  // Also persist to backend app_settings.json
  try {
    fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ zoom_level: currentZoomLevel })
    }).catch(() => {});
  } catch (e) {}

  const zoomDisplay = document.getElementById('zoom-percentage-badge');
  if (zoomDisplay) {
    zoomDisplay.innerText = `%${Math.round(currentZoomLevel * 100)}`;
  }

  if (showToast) {
    showZoomToast(`🔍 Görünüm Ölçeği: %${Math.round(currentZoomLevel * 100)}`);
  }
}

function zoomIn() {
  setZoomLevel(currentZoomLevel + 0.05);
}

function zoomOut() {
  setZoomLevel(currentZoomLevel - 0.05);
}

function resetZoom() {
  setZoomLevel(1.0);
}

async function restoreZoomLevel() {
  let restored = false;
  try {
    const saved = localStorage.getItem('app_zoom_level');
    if (saved) {
      const val = parseFloat(saved);
      if (!isNaN(val) && val >= 0.5 && val <= 2.5) {
        setZoomLevel(val, false);
        restored = true;
      }
    }
  } catch (e) {}

  // Double check with backend settings
  try {
    const res = await fetch('/api/settings');
    if (res.ok) {
      const json = await res.json();
      const sZoom = json?.data?.zoom_level;
      if (sZoom && typeof sZoom === 'number' && sZoom >= 0.5 && sZoom <= 2.5) {
        if (!restored || Math.abs(currentZoomLevel - sZoom) > 0.01) {
          setZoomLevel(sZoom, false);
        }
      }
    }
  } catch (e) {}
}


let zoomToastTimeout = null;
function showZoomToast(text) {
  let toast = document.getElementById('zoom-toast-indicator');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'zoom-toast-indicator';
    toast.className = 'fixed bottom-5 right-5 z-50 px-3.5 py-1.5 rounded-xl bg-hextech-card/95 border border-hextech-gold text-hextech-goldBright font-mono font-bold text-xs shadow-2xl backdrop-blur-md pointer-events-none transition-opacity duration-300';
    document.body.appendChild(toast);
  }
  toast.innerText = text;
  toast.style.opacity = '1';

  if (zoomToastTimeout) clearTimeout(zoomToastTimeout);
  zoomToastTimeout = setTimeout(() => {
    toast.style.opacity = '0';
  }, 1200);
}

let appToastTimeout = null;
function showToast(text, duration = 3500) {
  let toast = document.getElementById('app-global-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'app-global-toast';
    toast.className = 'fixed bottom-6 right-6 z-[9999] px-4 py-2.5 rounded-xl bg-[#030914]/95 border border-hextech-gold text-hextech-goldBright font-sans font-bold text-xs shadow-2xl backdrop-blur-md pointer-events-none transition-all duration-300 transform translate-y-0 opacity-0 flex items-center space-x-2';
    document.body.appendChild(toast);
  }
  toast.innerHTML = `<span>${text}</span>`;
  toast.style.opacity = '1';
  toast.style.transform = 'translateY(0)';

  if (appToastTimeout) clearTimeout(appToastTimeout);
  appToastTimeout = setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
  }, duration);
}
window.showToast = showToast;


function setupZoomShortcuts() {
  window.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey) {
      if (e.key === '=' || e.key === '+' || e.code === 'NumpadAdd') {
        e.preventDefault();
        zoomIn();
      } else if (e.key === '-' || e.key === '_' || e.code === 'NumpadSubtract') {
        e.preventDefault();
        zoomOut();
      } else if (e.key === '0' || e.code === 'Numpad0') {
        e.preventDefault();
        resetZoom();
      }
    }
  });

  window.addEventListener('wheel', (e) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      if (e.deltaY < 0) {
        zoomIn();
      } else {
        zoomOut();
      }
    }
  }, { passive: false });
}


function setupLiveLogStream() {
  try {
    const eventSource = new EventSource('/api/logs-stream');
    eventSource.onmessage = function(e) {
      if (e.data) {
        try {
          const msg = JSON.parse(e.data);
          onLogMessage(msg);
        } catch (err) {
          onLogMessage(e.data);
        }
      }
    };
    eventSource.onerror = function() {
      // Reconnects automatically
    };
  } catch (err) {
    console.warn("SSE connection error:", err);
  }
}

function onLogMessage(msg) {
  if (!consoleLogs) return;
  const div = document.createElement('div');
  div.className = 'font-mono leading-relaxed select-text cursor-text';
  if (msg.includes('✅') || msg.includes('✨')) div.className += ' text-emerald-400 font-bold';
  else if (msg.includes('❌') || msg.includes('Hata')) div.className += ' text-rose-400 font-bold';
  else if (msg.includes('🚀') || msg.includes('🎯')) div.className += ' text-hextech-cyanNeon';
  else if (msg.includes('📂') || msg.includes('Wwise')) div.className += ' text-hextech-gold';
  else div.className += ' text-gray-300';
  
  div.innerText = msg;
  consoleLogs.appendChild(div);
  consoleLogs.scrollTop = consoleLogs.scrollHeight;

  // Check extraction complete signals
  if (msg.includes('tamamlandı') || msg.includes('başarıyla çıkarıldı')) {
    const b1 = document.getElementById('btn-extract-selected');
    const b2 = document.getElementById('btn-extract-all');
    const b3 = document.getElementById('btn-scan-references');
    if (b1) b1.disabled = false;
    if (b2) b2.disabled = false;
    if (b3) b3.disabled = false;
    if (progressBarContainer) progressBarContainer.classList.add('hidden');
    refreshExtractedTree();
    refreshReferencesTree();
  }
}

// =========================================================================
// 2. THEME & LAYOUT CUSTOMIZER (100% PERSISTENT)
// =========================================================================
function applyTheme(themeClass) {
  const root = document.documentElement;
  root.classList.remove('theme-void', 'theme-noxus', 'theme-spirit', 'theme-shadow');
  
  if (themeClass && themeClass !== 'default') {
    root.classList.add(themeClass);
  }
  
  localStorage.setItem('app_theme', themeClass);
  closeThemeModal();
  onLogMessage(`🎨 Tema uygulandı: ${themeClass}`);
}

function restoreTheme() {
  const saved = localStorage.getItem('app_theme') || 'default';
  if (saved && saved !== 'default') {
    document.documentElement.classList.add(saved);
  }
}

function openThemeModal() {
  const modal = document.getElementById('theme-modal');
  if (modal) modal.classList.remove('hidden');
  lucide.createIcons();
}

function closeThemeModal() {
  const modal = document.getElementById('theme-modal');
  if (modal) modal.classList.add('hidden');
}

// Layout Configurator
function setLayoutPreset(preset) {
  const col1 = document.getElementById('panel-col-1');
  const col2 = document.getElementById('panel-col-2');
  const col3 = document.getElementById('panel-col-3');
  if (!col1 || !col2 || !col3) return;

  col1.className = col1.className.replace(/col-span-\d+/g, '').replace(/lg:col-span-\d+/g, '');
  col2.className = col2.className.replace(/col-span-\d+/g, '').replace(/lg:col-span-\d+/g, '');
  col3.className = col3.className.replace(/col-span-\d+/g, '').replace(/lg:col-span-\d+/g, '');

  if (preset === 'compact') {
    col1.classList.add('col-span-12', 'lg:col-span-2');
    col2.classList.add('col-span-12', 'lg:col-span-7');
    col3.classList.add('col-span-12', 'lg:col-span-3');
  } else if (preset === 'wide-explorer') {
    col1.classList.add('col-span-12', 'lg:col-span-2');
    col2.classList.add('col-span-12', 'lg:col-span-8');
    col3.classList.add('col-span-12', 'lg:col-span-2');
  } else {
    // Default 'balanced' -> Max Center Area
    col1.classList.add('col-span-12', 'lg:col-span-2');
    col2.classList.add('col-span-12', 'lg:col-span-8');
    col3.classList.add('col-span-12', 'lg:col-span-2');
  }

  ['balanced', 'wide-explorer', 'compact'].forEach(p => {
    const btn = document.getElementById(`layout-preset-${p}`);
    if (!btn) return;
    if (p === preset) {
      btn.className = 'p-2.5 rounded-lg border border-hextech-cyan bg-hextech-cardSelected text-hextech-cyanNeon font-bold text-center shadow';
    } else {
      btn.className = 'p-2.5 rounded-lg border border-hextech-borderSubtle hover:border-hextech-cyan bg-hextech-card text-gray-300 text-center';
    }
  });

  localStorage.setItem('app_layout_preset', preset);
}

function toggleConsoleVisibility(show) {
  const consolePanel = document.getElementById('panel-console');
  if (consolePanel) {
    if (show) consolePanel.classList.remove('hidden');
    else consolePanel.classList.add('hidden');
  }
  localStorage.setItem('app_show_console', show ? 'true' : 'false');
}

function restoreLayoutSettings() {
  const preset = localStorage.getItem('app_layout_preset') || 'balanced';
  setLayoutPreset(preset);

  const showConsole = localStorage.getItem('app_show_console');
  if (showConsole !== null) {
    const isShow = showConsole === 'true';
    const chk = document.getElementById('toggle-console');
    if (chk) chk.checked = isShow;
    toggleConsoleVisibility(isShow);
  }
}

function openLayoutModal() {
  const modal = document.getElementById('layout-modal');
  if (modal) modal.classList.remove('hidden');
  lucide.createIcons();
}

function closeLayoutModal() {
  const modal = document.getElementById('layout-modal');
  if (modal) modal.classList.add('hidden');
}

// =========================================================================
// 3. FLUID DRAGGABLE RESIZER SPLITTER (CHAMPIONS VS SKINS)
// =========================================================================
function setupSplitterResizer() {
  const resizer = document.getElementById('champ-skin-resizer');
  const skinWrapper = document.getElementById('skin-list-wrapper');
  if (!resizer || !skinWrapper) return;

  let isDragging = false;
  let startY = 0;
  let startHeight = 0;

  resizer.addEventListener('mousedown', (e) => {
    isDragging = true;
    startY = e.clientY;
    startHeight = skinWrapper.offsetHeight;
    resizer.classList.add('resizing');
    document.body.style.cursor = 'row-resize';
    e.preventDefault();
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    const dy = startY - e.clientY;
    const newHeight = Math.max(70, Math.min(360, startHeight + dy));
    skinWrapper.style.height = `${newHeight}px`;
  });

  window.addEventListener('mouseup', () => {
    if (isDragging) {
      isDragging = false;
      resizer.classList.remove('resizing');
      document.body.style.cursor = 'default';
      localStorage.setItem('champ_skin_split_height', skinWrapper.style.height);
    }
  });
}

function restoreSplitterHeight() {
  const saved = localStorage.getItem('champ_skin_split_height');
  const skinWrapper = document.getElementById('skin-list-wrapper');
  if (saved && skinWrapper) {
    skinWrapper.style.height = saved;
  }
}

// =========================================================================
// 4. TAB SWITCHING (LAZY LOADED ON DEMAND)
// =========================================================================
function switchTab(tabId) {
  currentTab = tabId;
  const tabs = ['voices', 'skinhub', 'competitors', 'references', 'wallpapers', 'static-wallpapers'];
  tabs.forEach(t => {
    const view = document.getElementById(`view-${t}`);
    const nav = document.getElementById(`nav-${t}`);
    if (!view || !nav) return;

    if (t === tabId) {
      view.classList.remove('hidden');
      nav.className = 'w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-heading font-bold text-hextech-goldBright bg-hextech-cardSelected border border-hextech-gold/70 shadow-md transition-all text-left cursor-pointer';
    } else {
      view.classList.add('hidden');
      nav.className = 'w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-heading font-semibold text-gray-400 hover:text-gray-200 hover:bg-hextech-cardHover border border-transparent transition-all text-left cursor-pointer';
    }
  });
  if (window.lucide) {
    lucide.createIcons();
  }

  if (tabId === 'skinhub' && typeof allSkinHubSkins !== 'undefined' && allSkinHubSkins.length === 0) {
    if (typeof initSkinHubData === 'function') initSkinHubData();
  } else if (tabId === 'competitors' && typeof competitorAnalysisData !== 'undefined' && !competitorAnalysisData) {
    if (typeof renderCompetitorWelcome === 'function') renderCompetitorWelcome();
  } else if (tabId === 'references') {
    if (typeof loadReferencesAnalytics === 'function') loadReferencesAnalytics();
    if (typeof loadRefChampions === 'function') loadRefChampions();
  } else if (tabId === 'wallpapers') {
    if (typeof loadDownloadedWallpapersCount === 'function') loadDownloadedWallpapersCount();
    if (typeof wallpaperSearchResults !== 'undefined' && wallpaperSearchResults.length === 0) {
      const searchInput = document.getElementById('wp-search-input');
      const initialQuery = (selectedChampion && selectedChampion !== 'ALL') ? selectedChampion : 'Yone';
      if (searchInput && !searchInput.value) {
        searchInput.value = initialQuery;
      }
      if (typeof triggerWallpaperSearch === 'function') triggerWallpaperSearch();
    }
  } else if (tabId === 'static-wallpapers') {
    if (typeof loadDownloadedStaticWallpapersCount === 'function') loadDownloadedStaticWallpapersCount();
    if (typeof currentStaticWpSkins !== 'undefined' && currentStaticWpSkins.length === 0) {
      const select = document.getElementById('static-wp-champ-select');
      const initialChamp = (selectedChampion && selectedChampion !== 'ALL') ? selectedChampion : 'Yone';
      if (select && !select.value) select.value = initialChamp;
      if (typeof loadStaticWpSkinsForChamp === 'function') loadStaticWpSkinsForChamp(initialChamp);
    }
  }
}

