// =============================================================================
// 9. 4K CANLI DUVAR KAĞITLARI & VİDEO HUB (DESKTOPHUT, MOTIONBGS, YOUTUBE)
// =============================================================================
let currentWallpaperSource = 'all';
let currentWallpaperResolution = 'all';
let wallpaperSearchResults = [];
let activePreviewWallpaper = null;
let wallpaperPollInterval = null;

function setWallpaperSource(src) {
  currentWallpaperSource = src;
  const btns = ['all', 'desktophut', 'motionbgs', 'youtube'];
  btns.forEach(b => {
    const el = document.getElementById(`wp-src-${b}`);
    if (el) {
      if (b === src) {
        el.className = 'px-2.5 py-1 rounded-lg bg-hextech-gold text-gray-950 font-extrabold text-[11px]';
      } else {
        el.className = 'px-2.5 py-1 rounded-lg text-gray-300 hover:text-white text-[11px]';
      }
    }
  });
  triggerWallpaperSearch();
}

function setWallpaperResolution(res) {
  currentWallpaperResolution = res;
  const btns = ['all', '4k', '1080p'];
  btns.forEach(b => {
    const el = document.getElementById(`wp-res-${b}`);
    if (el) {
      if (b === res) {
        el.className = 'px-2.5 py-1 rounded-lg bg-hextech-cyan text-gray-950 font-extrabold text-[11px]';
      } else {
        el.className = 'px-2.5 py-1 rounded-lg text-gray-300 hover:text-white text-[11px]';
      }
    }
  });
  triggerWallpaperSearch();
}

function quickSearchWallpaper(query) {
  const input = document.getElementById('wp-search-input');
  if (input) {
    input.value = query;
  }
  toggleWallpaperView('search');
  triggerWallpaperSearch();
}

async function triggerWallpaperSearch() {
  const input = document.getElementById('wp-search-input');
  const query = input ? input.value.trim() : '';

  const spinner = document.getElementById('wp-loading-spinner');
  const emptyState = document.getElementById('wp-empty-state');
  const grid = document.getElementById('wp-cards-grid');
  const btn = document.getElementById('btn-wp-search-action');

  if (spinner) spinner.classList.remove('hidden');
  if (emptyState) emptyState.classList.add('hidden');
  if (grid) grid.classList.add('hidden');
  if (btn) btn.disabled = true;

  try {
    const url = `/api/wallpapers/search?q=${encodeURIComponent(query)}&source=${encodeURIComponent(currentWallpaperSource)}&resolution=${encodeURIComponent(currentWallpaperResolution)}`;
    const res = await fetch(url);
    const json = await res.json();

    if (json.status === 'success') {
      wallpaperSearchResults = json.data || [];
      renderWallpaperCards(wallpaperSearchResults);
    } else {
      showToast("❌ Arama hatası: " + (json.message || "Bilinmeyen hata"));
    }
  } catch (err) {
    console.error("Wallpaper search error:", err);
    showToast("❌ Sunucu arama hatası: " + err.message);
  } finally {
    if (spinner) spinner.classList.add('hidden');
    if (btn) btn.disabled = false;
  }
}

function renderWallpaperCards(results) {
  const grid = document.getElementById('wp-cards-grid');
  const emptyState = document.getElementById('wp-empty-state');
  if (!grid) return;

  grid.innerHTML = '';

  if (!results || results.length === 0) {
    if (emptyState) {
      emptyState.classList.remove('hidden');
      emptyState.innerHTML = `
        <i data-lucide="search-x" class="w-12 h-12 text-gray-600 mb-2"></i>
        <h3 class="text-sm font-bold text-gray-300">Sonuç Bulunamadı</h3>
        <p class="text-xs text-gray-400">Aramanıza uygun canlı duvar kağıdı bulunamadı. Lütfen başka bir şampiyon veya kostüm adı deneyin.</p>
      `;
      if (window.lucide) lucide.createIcons();
    }
    grid.classList.add('hidden');
    return;
  }

  if (emptyState) emptyState.classList.add('hidden');
  grid.classList.remove('hidden');

  results.forEach((item, index) => {
    const is4K = (item.resolution || '').toLowerCase().includes('4k') || (item.title || '').toLowerCase().includes('4k');
    const badgeBg = is4K ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
    const badgeText = is4K ? '4K UHD' : '1080p FHD';
    const thumbUrl = item.thumbnail || '/images/default_thumb.jpg';

    const card = document.createElement('div');
    card.className = 'glass-card rounded-xl border border-hextech-borderSubtle hover:border-hextech-gold overflow-hidden flex flex-col group transition-all duration-300 shadow-lg hover:shadow-2xl hover:-translate-y-1 bg-[#020710]/80';
    
    card.innerHTML = `
      <!-- Thumbnail & Badges -->
      <div class="relative aspect-video bg-black/80 overflow-hidden cursor-pointer" onclick="openWallpaperPreviewModal(${index})">
        <img src="${thumbUrl}" alt="${item.title}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy" onerror="this.src='https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-splashes/uncentered/default.jpg'">
        <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/40 opacity-80 group-hover:opacity-60 transition-opacity"></div>
        
        <!-- Resolution Badge -->
        <div class="absolute top-2 left-2 px-2 py-0.5 rounded text-[10px] font-extrabold border uppercase tracking-wider backdrop-blur-md ${badgeBg}">
          ${badgeText}
        </div>

        <!-- Source Badge -->
        <div class="absolute top-2 right-2 px-2 py-0.5 rounded text-[10px] font-bold bg-black/70 text-gray-300 border border-white/10 backdrop-blur-md">
          ${item.source_badge || item.source}
        </div>

        <!-- Play Button Overlay -->
        <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <div class="w-10 h-10 rounded-full bg-hextech-gold/90 text-gray-950 flex items-center justify-center shadow-xl transform scale-75 group-hover:scale-100 transition-transform">
            <i data-lucide="play" class="w-5 h-5 fill-current ml-0.5"></i>
          </div>
        </div>

        <!-- FPS & Duration Pill -->
        <div class="absolute bottom-2 right-2 px-1.5 py-0.5 rounded text-[9px] font-mono bg-black/80 text-gray-300 border border-white/10">
          ${item.fps || '60 FPS'} • ${item.file_size || 'MP4'}
        </div>
      </div>

      <!-- Card Body -->
      <div class="p-3 flex-1 flex flex-col justify-between space-y-2.5">
        <div>
          <h4 class="text-xs font-extrabold text-gray-100 line-clamp-2 leading-tight group-hover:text-hextech-gold transition" title="${item.title}">
            ${item.title}
          </h4>
        </div>

        <!-- Action Buttons -->
        <div class="grid grid-cols-2 gap-2 pt-1">
          <button onclick="openWallpaperPreviewModal(${index})" class="px-2.5 py-1.5 rounded-lg bg-hextech-card hover:bg-hextech-cardHover border border-hextech-borderSubtle text-gray-200 hover:text-white text-[11px] font-bold flex items-center justify-center space-x-1 cursor-pointer transition">
            <i data-lucide="eye" class="w-3.5 h-3.5 text-hextech-cyan"></i>
            <span>Önizle</span>
          </button>
          <button id="btn-wp-dl-${item.id}" onclick="downloadWallpaperAction(${index})" class="lol-btn-gold px-2.5 py-1.5 rounded-lg text-gray-950 text-[11px] font-extrabold flex items-center justify-center space-x-1 cursor-pointer shadow-md transition">
            <i data-lucide="download" class="w-3.5 h-3.5"></i>
            <span>İndir</span>
          </button>
        </div>
      </div>
    `;

    grid.appendChild(card);
  });

  if (window.lucide) lucide.createIcons();
}

function openWallpaperPreviewModal(index) {
  const item = wallpaperSearchResults[index];
  if (!item) return;

  activePreviewWallpaper = item;
  const modal = document.getElementById('wallpaper-preview-modal');
  const titleEl = document.getElementById('wp-modal-title');
  const sourceEl = document.getElementById('wp-modal-source');
  const badgeEl = document.getElementById('wp-modal-badge');
  const videoPlayer = document.getElementById('wp-video-player');
  const ytPlayer = document.getElementById('wp-youtube-player');

  if (titleEl) titleEl.innerText = item.title;
  if (sourceEl) sourceEl.innerText = `Kaynak: ${item.source_badge || item.source} • ${item.fps || '60 FPS'}`;
  if (badgeEl) badgeEl.innerText = item.resolution || '4K UHD';

  if (item.source === 'YouTube' || (item.video_url && item.video_url.includes('youtube.com'))) {
    // YouTube embed
    let vidId = '';
    const m = item.video_url.match(/(?:v=|\/embed\/|\/watch\?v=|\.be\/)([^#\&\?]+)/);
    if (m) vidId = m[1];
    if (videoPlayer) {
      videoPlayer.pause();
      videoPlayer.classList.add('hidden');
    }
    if (ytPlayer) {
      ytPlayer.src = `https://www.youtube-nocookie.com/embed/${vidId}?autoplay=1&loop=1&playlist=${vidId}`;
      ytPlayer.classList.remove('hidden');
    }
  } else {
    // Direct MP4 / WebM
    if (ytPlayer) {
      ytPlayer.src = '';
      ytPlayer.classList.add('hidden');
    }
    if (videoPlayer) {
      videoPlayer.src = item.video_url || item.video_1080p_url || '';
      videoPlayer.classList.remove('hidden');
      videoPlayer.play().catch(e => console.log("Autoplay blocked:", e));
    }
  }

  if (modal) modal.classList.remove('hidden');
  if (window.lucide) lucide.createIcons();
}

function closeWallpaperPreviewModal() {
  const modal = document.getElementById('wallpaper-preview-modal');
  const videoPlayer = document.getElementById('wp-video-player');
  const ytPlayer = document.getElementById('wp-youtube-player');

  if (videoPlayer) {
    videoPlayer.pause();
    videoPlayer.src = '';
  }
  if (ytPlayer) {
    ytPlayer.src = '';
  }
  if (modal) modal.classList.add('hidden');
  activePreviewWallpaper = null;
}

let currentVideoFitMode = 'contain';

function setVideoFitMode(mode) {
  currentVideoFitMode = mode;
  const videoPlayer = document.getElementById('wp-video-player');
  const container = document.getElementById('wp-player-container');
  const hint = document.getElementById('wp-pos-hint');

  const modes = ['contain', 'cover', 'center', 'vertical'];
  modes.forEach(m => {
    const btn = document.getElementById(`wp-fit-${m}`);
    if (btn) {
      if (m === mode) {
        btn.className = 'px-2.5 py-1 rounded-lg bg-hextech-cyan text-gray-950 font-bold cursor-pointer';
      } else {
        btn.className = 'px-2.5 py-1 rounded-lg text-gray-300 hover:text-white cursor-pointer';
      }
    }
  });

  if (!videoPlayer || !container) return;

  if (mode === 'contain') {
    container.className = 'relative bg-black aspect-video flex items-center justify-center overflow-hidden transition-all duration-300';
    videoPlayer.className = 'w-full h-full object-contain transition-all duration-300';
    if (hint) hint.innerHTML = 'Konumlandırma: <b>Tam Sığdır (Orijinal 16:9 Oran)</b>';
  } else if (mode === 'cover') {
    container.className = 'relative bg-black aspect-video flex items-center justify-center overflow-hidden transition-all duration-300';
    videoPlayer.className = 'w-full h-full object-cover transition-all duration-300';
    if (hint) hint.innerHTML = 'Konumlandırma: <b>Tam Ekran Doldur (Cover / Kenarlıksız 16:9)</b>';
  } else if (mode === 'center') {
    container.className = 'relative bg-black aspect-video flex items-center justify-center overflow-hidden transition-all duration-300';
    videoPlayer.className = 'w-full h-full object-cover object-center scale-110 transition-all duration-300';
    if (hint) hint.innerHTML = 'Konumlandırma: <b>Karakter & Merkez Odaklı (4K Yakınlaştırma)</b>';
  } else if (mode === 'vertical') {
    container.className = 'relative bg-black aspect-[9/16] max-h-[65vh] mx-auto flex items-center justify-center overflow-hidden rounded-xl border border-hextech-borderMedium shadow-2xl transition-all duration-300';
    videoPlayer.className = 'w-full h-full object-cover object-center transition-all duration-300';
    if (hint) hint.innerHTML = 'Konumlandırma: <b>Mobil & Dikey Format (9:16 TikTok / Reels / Telefon)</b>';
  }
}

function applyDesktopWallpaperGuide() {
  if (!activePreviewWallpaper) {
    showToast("Önce bir video önizlemesi açın.");
    return;
  }
  
  const title = activePreviewWallpaper.title;
  alert(
    `🖥️ Windows Canlı Duvar Kağıdı Konumlandırma Rehberi:\n\n` +
    `1. Bu videoyu "4K İndir" butonuyla bilgisayarınıza kaydedin.\n` +
    `2. Ücretsiz ve Açık Kaynaklı "Lively Wallpaper" (Microsoft Store) veya "Wallpaper Engine" (Steam) uygulamasını açın.\n` +
    `3. İndirilenler klasörünüzdeki "${title}.mp4" dosyasını Lively/Wallpaper Engine penceresine sürükleyip bırakın.\n` +
    `4. Konumlandırma ayarını (Doldur / Fit / Cover) seçerek tek tıkla masaüstünüzü 4K canlı yapın!`
  );
  openWallpapersFolder();
}

let activeWallpaperDownloadsMap = {}; // dl_id -> { btnId, extraBtnId, title }

function downloadCurrentPreviewToChampFolder() {
  if (!activePreviewWallpaper) return;
  const champ = selectedChampion && selectedChampion !== 'ALL' ? selectedChampion : 'Genel';
  showToast(`📁 "${activePreviewWallpaper.title}" şampiyon klasörüne (${champ}) indiriliyor...`);
  downloadWallpaperItem(activePreviewWallpaper, activePreviewWallpaper.id, champ, 'wp-modal-btn-champ');
}

function downloadCurrentPreviewWallpaper() {
  if (activePreviewWallpaper) {
    downloadWallpaperItem(activePreviewWallpaper, activePreviewWallpaper.id, null, 'wp-modal-btn-download');
  }
}

function downloadWallpaperAction(index) {
  try {
    const item = wallpaperSearchResults[index];
    if (!item) return;

    const btn = document.getElementById(`btn-wp-dl-${item.id}`);
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>İndiriliyor...</span>`;
      if (window.lucide) lucide.createIcons();
    }
    downloadWallpaperItem(item, item.id);
  } catch (err) {
    console.error("downloadWallpaperAction error:", err);
    if (window.showToast) showToast("❌ İndirme başlatılamadı: " + err.message);
  }
}

async function downloadWallpaperItem(item, btnId, champName = null, extraBtnId = null) {
  if (window.showToast) {
    showToast(`📥 [${item.source || 'Canlı Duvar Kağıdı'}] "${item.title}" indirme başlatıldı...`);
  }
  
  if (extraBtnId) {
    const extraBtn = document.getElementById(extraBtnId);
    if (extraBtn) {
      extraBtn.disabled = true;
      extraBtn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>İndiriliyor...</span>`;
      if (window.lucide) lucide.createIcons();
    }
  }

  try {
    const res = await fetch('/api/wallpapers/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ item: item, champ_name: champName })
    });
    const json = await res.json();
    if (json.status === 'started' && json.download_id) {
      if (window.showToast) {
        showToast(`⚡ "${item.title}" arka planda indiriliyor...`);
      }
      activeWallpaperDownloadsMap[json.download_id] = { btnId, extraBtnId, title: item.title };
      ensureWallpaperPollingRunning();
    } else {
      if (window.showToast) {
        showToast(`❌ İndirme başlatılamadı: ${json.message || 'Bilinmeyen hata'}`);
      }
      resetDownloadBtn(btnId, extraBtnId);
    }
  } catch (err) {
    console.error("downloadWallpaperItem fetch error:", err);
    if (window.showToast) {
      showToast(`❌ Sunucu hatası: ${err.message}`);
    }
    resetDownloadBtn(btnId, extraBtnId);
  }
}

function resetDownloadBtn(btnId, extraBtnId = null) {
  if (btnId) {
    const btn = document.getElementById(`btn-wp-dl-${btnId}`);
    if (btn) {
      btn.disabled = false;
      btn.className = 'lol-btn-gold px-2.5 py-1.5 rounded-lg text-gray-950 text-[11px] font-extrabold flex items-center justify-center space-x-1 cursor-pointer shadow-md transition';
      btn.innerHTML = `<i data-lucide="download" class="w-3.5 h-3.5"></i><span>İndir</span>`;
      if (window.lucide) lucide.createIcons();
    }
  }
  if (extraBtnId) {
    const extraBtn = document.getElementById(extraBtnId);
    if (extraBtn) {
      extraBtn.disabled = false;
      if (extraBtnId === 'wp-modal-btn-download') {
        extraBtn.innerHTML = `<i data-lucide="download" class="w-3.5 h-3.5"></i><span>4K İndir</span>`;
      } else if (extraBtnId === 'wp-modal-btn-champ') {
        extraBtn.innerHTML = `<i data-lucide="folder-plus" class="w-3.5 h-3.5"></i><span>Şampiyon Klasörüne Aktar</span>`;
      }
      if (window.lucide) lucide.createIcons();
    }
  }
}

function ensureWallpaperPollingRunning() {
  if (wallpaperPollInterval) return;

  wallpaperPollInterval = setInterval(async () => {
    try {
      const res = await fetch('/api/wallpapers/status');
      const json = await res.json();
      if (json.status === 'success' && json.data) {
        renderActiveWallpaperDownloads(json.data);

        const dlIds = Object.keys(activeWallpaperDownloadsMap);
        if (dlIds.length === 0 && !Object.values(json.data).some(d => d.status === 'downloading')) {
          clearInterval(wallpaperPollInterval);
          wallpaperPollInterval = null;
          return;
        }

        dlIds.forEach(targetDlId => {
          const dlInfo = activeWallpaperDownloadsMap[targetDlId];
          const serverState = json.data[targetDlId];
          if (!serverState || !dlInfo) return;

          if (serverState.status === 'completed') {
            if (window.showToast) {
              showToast(`✨ "${serverState.title}" indirildi! Klasör: Downloads/LoL Canlı Duvar Kağıtları`);
            }
            loadDownloadedWallpapersCount();

            // Kart butonu güncelle
            if (dlInfo.btnId) {
              const btn = document.getElementById(`btn-wp-dl-${dlInfo.btnId}`);
              if (btn) {
                btn.disabled = false;
                btn.className = 'px-2.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] font-extrabold flex items-center justify-center space-x-1 shadow-md cursor-pointer transition';
                btn.innerHTML = `<i data-lucide="check-check" class="w-3.5 h-3.5"></i><span>İndi!</span>`;
                btn.onclick = () => openWallpapersFolder();
                if (window.lucide) lucide.createIcons();
              }
            }
            // Modal butonu güncelle
            if (dlInfo.extraBtnId) {
              const extraBtn = document.getElementById(dlInfo.extraBtnId);
              if (extraBtn) {
                extraBtn.disabled = false;
                extraBtn.className = 'px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center space-x-1.5 shadow-md cursor-pointer transition';
                extraBtn.innerHTML = `<i data-lucide="check-check" class="w-3.5 h-3.5"></i><span>İndi!</span>`;
                extraBtn.onclick = () => openWallpapersFolder();
                if (window.lucide) lucide.createIcons();
              }
            }

            delete activeWallpaperDownloadsMap[targetDlId];
          } else if (serverState.status === 'error') {
            if (window.showToast) {
              showToast(`❌ İndirme başarısız: ${serverState.error || 'Bilinmeyen hata'}`);
            }
            resetDownloadBtn(dlInfo.btnId, dlInfo.extraBtnId);
            delete activeWallpaperDownloadsMap[targetDlId];
          }
        });
      }
    } catch (e) {
      console.error("Poll error:", e);
    }
  }, 1000);
}

function renderActiveWallpaperDownloads(downloads) {
  const container = document.getElementById('wp-active-downloads-container');
  if (!container) return;

  const entries = Object.values(downloads);
  const activeEntries = entries.filter(d => d.status === 'downloading');

  if (activeEntries.length === 0) {
    container.classList.add('hidden');
    container.innerHTML = '';
    // If all completed, stop fast polling and refresh downloaded count
    if (entries.some(d => d.status === 'completed')) {
      loadDownloadedWallpapersCount();
    }
    return;
  }

  container.classList.remove('hidden');
  container.innerHTML = '';

  activeEntries.forEach(d => {
    const card = document.createElement('div');
    card.className = 'glass-card p-3 rounded-xl border border-hextech-cyan/50 bg-[#030d1e]/90 flex items-center justify-between shadow-lg space-x-3';
    
    card.innerHTML = `
      <div class="flex items-center space-x-2.5 truncate flex-1">
        <div class="w-7 h-7 rounded-lg bg-hextech-cyan/20 border border-hextech-cyan/40 flex items-center justify-center shrink-0 animate-pulse">
          <i data-lucide="download" class="w-4 h-4 text-hextech-cyan"></i>
        </div>
        <div class="truncate flex-1">
          <div class="text-xs font-bold text-gray-100 truncate">${d.title}</div>
          <div class="text-[10px] text-gray-400 font-mono">${d.speed} • %${d.progress} İndiriliyor</div>
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="w-36 h-2 rounded-full bg-gray-800 overflow-hidden border border-white/10 shrink-0">
        <div class="h-full bg-gradient-to-r from-hextech-cyan to-hextech-gold transition-all duration-300" style="width: ${d.progress}%"></div>
      </div>
    `;

    container.appendChild(card);
  });

  if (window.lucide) lucide.createIcons();
}

function toggleWallpaperView(view) {
  const searchToolbar = document.getElementById('wp-search-toolbar');
  const searchResults = document.getElementById('wp-search-results-wrapper');
  const downloadedWrapper = document.getElementById('wp-downloaded-wrapper');
  const btnSearch = document.getElementById('btn-wp-tab-search');
  const btnDownloaded = document.getElementById('btn-wp-tab-downloaded');

  if (view === 'search') {
    if (searchToolbar) searchToolbar.classList.remove('hidden');
    if (searchResults) searchResults.classList.remove('hidden');
    if (downloadedWrapper) downloadedWrapper.classList.add('hidden');
    
    if (btnSearch) btnSearch.className = 'px-3.5 py-1.5 rounded-lg bg-hextech-gold text-gray-950 font-extrabold text-xs shadow-md flex items-center space-x-1.5 cursor-pointer';
    if (btnDownloaded) btnDownloaded.className = 'px-3.5 py-1.5 rounded-lg bg-hextech-card hover:bg-hextech-cardHover border border-hextech-borderSubtle text-gray-300 font-bold text-xs flex items-center space-x-1.5 cursor-pointer';
  } else {
    if (searchToolbar) searchToolbar.classList.add('hidden');
    if (searchResults) searchResults.classList.add('hidden');
    if (downloadedWrapper) downloadedWrapper.classList.remove('hidden');

    if (btnSearch) btnSearch.className = 'px-3.5 py-1.5 rounded-lg bg-hextech-card hover:bg-hextech-cardHover border border-hextech-borderSubtle text-gray-300 font-bold text-xs flex items-center space-x-1.5 cursor-pointer';
    if (btnDownloaded) btnDownloaded.className = 'px-3.5 py-1.5 rounded-lg bg-hextech-gold text-gray-950 font-extrabold text-xs shadow-md flex items-center space-x-1.5 cursor-pointer';
    
    refreshDownloadedWallpapers();
  }
}

async function refreshDownloadedWallpapers() {
  const grid = document.getElementById('wp-downloaded-grid');
  const empty = document.getElementById('wp-downloaded-empty');
  
  try {
    const res = await fetch('/api/wallpapers/downloaded');
    const json = await res.json();
    if (json.status === 'success') {
      const files = json.data || [];
      renderDownloadedWallpapers(files);
      const countEl = document.getElementById('wp-downloaded-count');
      if (countEl) countEl.innerText = files.length;
    }
  } catch (err) {
    console.error("Load downloaded error:", err);
  }
}

async function loadDownloadedWallpapersCount() {
  try {
    const res = await fetch('/api/wallpapers/downloaded');
    const json = await res.json();
    if (json.status === 'success') {
      const files = json.data || [];
      const countEl = document.getElementById('wp-downloaded-count');
      if (countEl) countEl.innerText = files.length;
    }
  } catch (err) {}
}

function renderDownloadedWallpapers(files) {
  const grid = document.getElementById('wp-downloaded-grid');
  const empty = document.getElementById('wp-downloaded-empty');
  if (!grid) return;

  grid.innerHTML = '';
  if (!files || files.length === 0) {
    if (empty) empty.classList.remove('hidden');
    return;
  }
  if (empty) empty.classList.add('hidden');

  files.forEach(f => {
    const card = document.createElement('div');
    card.className = 'glass-card p-3 rounded-xl border border-hextech-borderSubtle hover:border-hextech-cyan flex flex-col justify-between space-y-3 bg-[#030914]/80 shadow-md group';
    
    card.innerHTML = `
      <div class="flex items-start space-x-3">
        <div class="w-10 h-10 rounded-lg bg-amber-500/20 border border-amber-500/30 flex items-center justify-center shrink-0">
          <i data-lucide="film" class="w-5 h-5 text-hextech-gold"></i>
        </div>
        <div class="truncate flex-1">
          <h4 class="text-xs font-bold text-gray-100 truncate group-hover:text-hextech-gold" title="${f.name}">
            ${f.title}
          </h4>
          <div class="text-[10px] text-gray-400 font-mono mt-0.5">
            ${f.size_mb} • ${f.date}
          </div>
          <span class="inline-block mt-1 px-1.5 py-0.2 rounded text-[9px] bg-cyan-950 text-cyan-300 border border-cyan-800/40">
            ${f.champion}
          </span>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-2 pt-1 border-t border-hextech-borderSubtle">
        <button onclick="openLocalVideo('${encodeURIComponent(f.path)}')" class="px-2 py-1 rounded bg-hextech-card hover:bg-hextech-cardHover border border-hextech-borderSubtle text-gray-200 text-[11px] font-bold flex items-center justify-center space-x-1 cursor-pointer">
          <i data-lucide="play" class="w-3 h-3 text-hextech-gold"></i>
          <span>Oynat</span>
        </button>
        <button onclick="openWallpapersFolder('${f.champion === 'Genel' ? '' : f.champion}')" class="px-2 py-1 rounded bg-hextech-card hover:bg-hextech-cardHover border border-hextech-borderSubtle text-gray-200 text-[11px] font-bold flex items-center justify-center space-x-1 cursor-pointer">
          <i data-lucide="folder" class="w-3 h-3 text-hextech-cyan"></i>
          <span>Klasör</span>
        </button>
      </div>
    `;

    grid.appendChild(card);
  });

  if (window.lucide) lucide.createIcons();
}

function openLocalVideo(encodedPath) {
  const path = decodeURIComponent(encodedPath);
  fetch('/api/open-file-location', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ file_path: path })
  });
}

async function openWallpapersFolder(champName) {
  try {
    await fetch('/api/wallpapers/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ champ_name: champName || null })
    });
  } catch (err) {
    console.error("Open folder error:", err);
  }
}

// Attach Search Enter Key listener
function initWallpapersModule() {
  const searchInput = document.getElementById('wp-search-input');
  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        triggerWallpaperSearch();
      }
    });
  }
  loadDownloadedWallpapersCount();
}

window.initWallpapersModule = initWallpapersModule;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initWallpapersModule);
} else {
  initWallpapersModule();
}



