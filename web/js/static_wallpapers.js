// =============================================================================
// 10. 4K NORMAL STATİK DUVAR KAĞITLARI & KOSTÜM SPLASH STÜDYOSU
// =============================================================================

let staticWpChampions = [];
let currentStaticWpSkins = [];
let activeStaticModalSkin = null;
let currentStaticWpTab = 'search'; // 'search' or 'downloaded'

async function initStaticWallpapersModule() {
  await loadStaticWpChampions();
  await loadDownloadedStaticWallpapersCount();

  // Initial search if empty
  const initialChamp = (window.selectedChampion && window.selectedChampion !== 'ALL') ? window.selectedChampion : 'Yone';
  const select = document.getElementById('static-wp-champ-select');
  if (select) {
    select.value = initialChamp;
  }
  loadStaticWpSkinsForChamp(initialChamp);

  // Setup search input enter key
  const input = document.getElementById('static-wp-search-input');
  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        triggerStaticWpSearch();
      }
    });
  }
}
window.initStaticWallpapersModule = initStaticWallpapersModule;

function toggleStaticWallpaperView(tab) {
  currentStaticWpTab = tab;
  const searchToolbar = document.getElementById('static-wp-search-toolbar');
  const resultsWrapper = document.getElementById('static-wp-results-wrapper');
  const downloadedWrapper = document.getElementById('static-wp-downloaded-wrapper');
  const btnSearch = document.getElementById('btn-static-wp-tab-search');
  const btnDownloaded = document.getElementById('btn-static-wp-tab-downloaded');

  if (tab === 'search') {
    if (searchToolbar) searchToolbar.classList.remove('hidden');
    if (resultsWrapper) resultsWrapper.classList.remove('hidden');
    if (downloadedWrapper) downloadedWrapper.classList.add('hidden');
    if (btnSearch) btnSearch.className = 'px-3.5 py-1.5 rounded-lg bg-emerald-500 text-gray-950 font-extrabold text-xs shadow-md flex items-center space-x-1.5 cursor-pointer';
    if (btnDownloaded) btnDownloaded.className = 'px-3.5 py-1.5 rounded-lg bg-hextech-card hover:bg-hextech-cardHover border border-hextech-borderSubtle text-gray-300 font-bold text-xs flex items-center space-x-1.5 cursor-pointer';
  } else {
    if (searchToolbar) searchToolbar.classList.add('hidden');
    if (resultsWrapper) resultsWrapper.classList.add('hidden');
    if (downloadedWrapper) downloadedWrapper.classList.remove('hidden');
    if (btnSearch) btnSearch.className = 'px-3.5 py-1.5 rounded-lg bg-hextech-card hover:bg-hextech-cardHover border border-hextech-borderSubtle text-gray-300 font-bold text-xs flex items-center space-x-1.5 cursor-pointer';
    if (btnDownloaded) btnDownloaded.className = 'px-3.5 py-1.5 rounded-lg bg-emerald-500 text-gray-950 font-extrabold text-xs shadow-md flex items-center space-x-1.5 cursor-pointer';
    refreshDownloadedStaticWallpapers();
  }
}

async function loadStaticWpChampions() {
  try {
    const res = await fetch('/api/static-wallpapers/champions');
    const json = await res.json();
    if (json.status === 'success') {
      staticWpChampions = json.data || [];
      const select = document.getElementById('static-wp-champ-select');
      if (select) {
        select.innerHTML = '<option value="">🏆 Tüm Şampiyonlar (A-Z)</option>';
        staticWpChampions.forEach(c => {
          const opt = document.createElement('option');
          opt.value = c.alias || c.name;
          opt.innerText = `${c.name} (${c.skin_count} Kostüm)`;
          select.appendChild(opt);
        });
      }
    }
  } catch (err) {
    console.error("loadStaticWpChampions hatası:", err);
  }
}

function quickSelectStaticWpChamp(champName) {
  const select = document.getElementById('static-wp-champ-select');
  const input = document.getElementById('static-wp-search-input');
  if (select) select.value = champName;
  if (input) input.value = '';
  toggleStaticWallpaperView('search');
  loadStaticWpSkinsForChamp(champName);
}

function onStaticWpChampionSelect(val) {
  if (val) {
    const input = document.getElementById('static-wp-search-input');
    if (input) input.value = '';
    loadStaticWpSkinsForChamp(val);
  } else {
    triggerStaticWpSearch();
  }
}

async function loadStaticWpSkinsForChamp(champ) {
  const spinner = document.getElementById('static-wp-loading-spinner');
  const emptyState = document.getElementById('static-wp-empty-state');
  const grid = document.getElementById('static-wp-cards-grid');

  if (spinner) spinner.classList.remove('hidden');
  if (emptyState) emptyState.classList.add('hidden');
  if (grid) grid.classList.add('hidden');

  try {
    const res = await fetch(`/api/static-wallpapers/skins?champion=${encodeURIComponent(champ)}`);
    const json = await res.json();
    if (json.status === 'success') {
      currentStaticWpSkins = json.data || [];
      renderStaticWallpaperCards(currentStaticWpSkins);
    } else {
      if (window.showToast) showToast("❌ Kostümler yüklenemedi: " + (json.message || "Hata"));
    }
  } catch (err) {
    console.error("loadStaticWpSkinsForChamp hatası:", err);
    if (window.showToast) showToast("❌ Sunucu hatası: " + err.message);
  } finally {
    if (spinner) spinner.classList.add('hidden');
  }
}

async function triggerStaticWpSearch() {
  const input = document.getElementById('static-wp-search-input');
  const select = document.getElementById('static-wp-champ-select');
  const query = input ? input.value.trim() : '';

  if (!query && select && select.value) {
    loadStaticWpSkinsForChamp(select.value);
    return;
  }

  const spinner = document.getElementById('static-wp-loading-spinner');
  const emptyState = document.getElementById('static-wp-empty-state');
  const grid = document.getElementById('static-wp-cards-grid');
  const btn = document.getElementById('btn-static-wp-search-action');

  if (spinner) spinner.classList.remove('hidden');
  if (emptyState) emptyState.classList.add('hidden');
  if (grid) grid.classList.add('hidden');
  if (btn) btn.disabled = true;

  try {
    const res = await fetch(`/api/static-wallpapers/search?q=${encodeURIComponent(query)}`);
    const json = await res.json();
    if (json.status === 'success') {
      currentStaticWpSkins = json.data || [];
      renderStaticWallpaperCards(currentStaticWpSkins);
    } else {
      if (window.showToast) showToast("❌ Arama hatası: " + (json.message || "Hata"));
    }
  } catch (err) {
    console.error("triggerStaticWpSearch hatası:", err);
    if (window.showToast) showToast("❌ Arama sunucu hatası: " + err.message);
  } finally {
    if (spinner) spinner.classList.add('hidden');
    if (btn) btn.disabled = false;
  }
}

function renderStaticWallpaperCards(skins) {
  const grid = document.getElementById('static-wp-cards-grid');
  const emptyState = document.getElementById('static-wp-empty-state');
  if (!grid) return;

  grid.innerHTML = '';

  if (!skins || skins.length === 0) {
    if (emptyState) {
      emptyState.classList.remove('hidden');
      emptyState.innerHTML = `
        <i data-lucide="search-x" class="w-12 h-12 text-gray-600 mb-2"></i>
        <h3 class="text-sm font-bold text-gray-300">Kostüm Duvar Kağıdı Bulunamadı</h3>
        <p class="text-xs text-gray-400">Aramanıza uygun kostüm splash art'ı bulunamadı. Lütfen başka bir şampiyon veya anahtar kelime deneyin.</p>
      `;
      if (window.lucide) lucide.createIcons();
    }
    grid.classList.add('hidden');
    return;
  }

  if (emptyState) emptyState.classList.add('hidden');
  grid.classList.remove('hidden');

  skins.forEach((skin, index) => {
    const splashImg = skin.ddragon_splash_url || skin.splash_url;
    const skinNameTr = skin.name_tr || skin.name_en || 'Kostüm';
    const skinNameEn = skin.name_en || '';
    const champName = skin.champion_name || skin.champion_alias || '';
    const rarity = skin.rarity_tr || 'Standart';

    let rarityBadgeClass = 'bg-gray-800/80 text-gray-300 border-gray-700';
    if (rarity.includes('Prestij') || rarity.includes('İhtişamlı')) {
      rarityBadgeClass = 'bg-amber-500/20 text-amber-300 border-amber-500/40';
    } else if (rarity.includes('Efsanevi')) {
      rarityBadgeClass = 'bg-red-500/20 text-red-300 border-red-500/40';
    } else if (rarity.includes('Destansı')) {
      rarityBadgeClass = 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
    }

    const card = document.createElement('div');
    card.className = 'glass-card rounded-xl border border-hextech-borderSubtle hover:border-emerald-500 overflow-hidden flex flex-col group transition-all duration-300 shadow-lg hover:shadow-2xl hover:-translate-y-1 bg-[#020710]/85';

    const sourceName = skin.source || 'UHD Paper 4K';

    card.innerHTML = `
      <!-- Thumbnail & Overlay -->
      <div class="relative aspect-video bg-black/80 overflow-hidden cursor-pointer" onclick="openStaticWallpaperModal(${index})">
        <img src="${splashImg}" alt="${skinNameTr}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy" onerror="this.src='https://ddragon.leagueoflegends.com/cdn/img/champion/splash/Aatrox_0.jpg'">
        <div class="absolute inset-0 bg-gradient-to-t from-black/85 via-transparent to-black/30 opacity-80 group-hover:opacity-50 transition-opacity"></div>

        <!-- 4K UHD Master Badge -->
        <div class="absolute top-2 left-2 px-2 py-0.5 rounded text-[10px] font-extrabold border uppercase tracking-wider backdrop-blur-md bg-emerald-500/20 text-emerald-300 border-emerald-500/40">
          4K UHD
        </div>

        <!-- Rarity Badge -->
        <div class="absolute top-2 right-2 px-2 py-0.5 rounded text-[10px] font-bold border backdrop-blur-md ${rarityBadgeClass}">
          ${rarity}
        </div>

        <!-- Source Badge (Corner Badge requested by user) -->
        <div class="absolute bottom-2 left-2 px-2 py-0.5 rounded text-[10px] font-extrabold border backdrop-blur-md bg-black/85 text-emerald-300 border-emerald-500/50 flex items-center space-x-1 shadow-md">
          <i data-lucide="sparkles" class="w-2.5 h-2.5 text-emerald-400"></i>
          <span>${sourceName}</span>
        </div>

        <!-- Eye Preview Hover Overlay -->
        <div class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
          <div class="w-10 h-10 rounded-full bg-emerald-500/90 text-gray-950 flex items-center justify-center shadow-xl transform scale-75 group-hover:scale-100 transition-transform">
            <i data-lucide="maximize-2" class="w-5 h-5"></i>
          </div>
        </div>

        <!-- Release Date Pill -->
        ${skin.release_date ? `
        <div class="absolute bottom-2 right-2 px-1.5 py-0.5 rounded text-[9px] font-mono bg-black/80 text-gray-300 border border-white/10">
          ${skin.release_date}
        </div>` : ''}
      </div>

      <!-- Card Body -->
      <div class="p-3 flex-1 flex flex-col justify-between space-y-2.5">
        <div>
          <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">${champName}</div>
          <h4 class="text-xs font-extrabold text-gray-100 line-clamp-1 leading-tight group-hover:text-emerald-400 transition" title="${skinNameTr} (${skinNameEn})">
            ${skinNameTr}
          </h4>
        </div>

        <!-- Action Buttons -->
        <div class="grid grid-cols-2 gap-2 pt-1">
          <button id="btn-static-dl-${index}" onclick="downloadStaticWallpaperAction(${index}, false)" class="px-2.5 py-1.5 rounded-lg bg-hextech-card hover:bg-hextech-cardHover border border-emerald-500/40 text-emerald-300 hover:text-white text-[11px] font-bold flex items-center justify-center space-x-1 cursor-pointer transition shadow">
            <i data-lucide="download" class="w-3.5 h-3.5"></i>
            <span>4K İndir</span>
          </button>
          <button id="btn-static-desk-${index}" onclick="downloadStaticWallpaperAction(${index}, true)" class="px-2.5 py-1.5 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-gray-950 text-[11px] font-extrabold flex items-center justify-center space-x-1 cursor-pointer shadow-md transition">
            <i data-lucide="monitor" class="w-3.5 h-3.5"></i>
            <span>Masaüstü Yap</span>
          </button>
        </div>
      </div>
    `;

    grid.appendChild(card);
  });

  if (window.lucide) lucide.createIcons();
}

function openStaticWallpaperModal(index) {
  const skin = currentStaticWpSkins[index];
  if (!skin) return;

  activeStaticModalSkin = skin;
  const modal = document.getElementById('static-wallpaper-modal');
  const title = document.getElementById('static-modal-title');
  const subtitle = document.getElementById('static-modal-subtitle');
  const img = document.getElementById('static-modal-img');

  if (title) title.innerText = skin.name_tr || skin.name_en || 'Kostüm';
  if (subtitle) subtitle.innerText = `${skin.champion_name || skin.champion_alias} • ${skin.rarity_tr || 'Standart'} • Kaynak: ${skin.source || 'UHD Paper 4K'}`;
  
  const resBadge = document.getElementById('static-modal-res-badge');
  if (resBadge) resBadge.innerText = skin.source || 'UHD Paper 4K';

  if (img) {
    img.src = skin.ddragon_splash_url || skin.splash_url;
  }

  if (modal) modal.classList.remove('hidden');
  if (window.lucide) lucide.createIcons();
}

function closeStaticWallpaperModal() {
  const modal = document.getElementById('static-wallpaper-modal');
  if (modal) modal.classList.add('hidden');
  activeStaticModalSkin = null;
}

async function downloadModalStaticWallpaper(setDesktop = false) {
  if (!activeStaticModalSkin) return;

  const btnDl = document.getElementById('static-modal-btn-download');
  const btnDesk = document.getElementById('static-modal-btn-desktop');

  if (btnDl) btnDl.disabled = true;
  if (btnDesk) btnDesk.disabled = true;

  try {
    await executeDownloadStaticWallpaper(activeStaticModalSkin, setDesktop);
  } finally {
    if (btnDl) btnDl.disabled = false;
    if (btnDesk) btnDesk.disabled = false;
  }
}

async function downloadStaticWallpaperAction(index, setDesktop = false) {
  const skin = currentStaticWpSkins[index];
  if (!skin) return;

  const btn = document.getElementById(setDesktop ? `btn-static-desk-${index}` : `btn-static-dl-${index}`);
  const originalHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>İşleniyor...</span>`;
    if (window.lucide) lucide.createIcons();
  }

  try {
    await executeDownloadStaticWallpaper(skin, setDesktop);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
      if (window.lucide) lucide.createIcons();
    }
  }
}

async function executeDownloadStaticWallpaper(skin, setDesktop = false) {
  const force4k = document.getElementById('static-wp-force-4k')?.checked ?? true;
  const skinName = skin.name_tr || skin.name_en || 'Kostüm';
  const champName = skin.champion_name || skin.champion_alias || 'Şampiyon';

  if (window.showToast) {
    showToast(`⏳ [4K] "${champName} - ${skinName}" indiriliyor ve optimize ediliyor...`);
  }

  try {
    const res = await fetch('/api/static-wallpapers/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        skin: skin,
        force_4k: force4k,
        set_desktop: setDesktop
      })
    });

    const json = await res.json();
    if (json.status === 'success') {
      const srcText = json.source ? `[${json.source}] ` : '';
      const msg = setDesktop
        ? `🖥️ ${srcText}"${skinName}" 4K olarak indirildi ve Windows Masaüstü yapıldı! (${json.resolution})`
        : `✅ ${srcText}"${skinName}" başarıyla 4K indirildi! (${json.resolution}, ${json.file_size_mb} MB)`;
      
      if (window.showToast) showToast(msg, 5000);
      loadDownloadedStaticWallpapersCount();
    } else {
      if (window.showToast) showToast(`❌ İndirme hatası: ${json.message || 'Bilinmeyen hata'}`);
    }
  } catch (err) {
    console.error("executeDownloadStaticWallpaper hatası:", err);
    if (window.showToast) showToast(`❌ Sunucu hatası: ${err.message}`);
  }
}

async function loadDownloadedStaticWallpapersCount() {
  try {
    const res = await fetch('/api/static-wallpapers/downloaded');
    const json = await res.json();
    if (json.status === 'success') {
      const count = json.data ? json.data.length : 0;
      const countEl = document.getElementById('static-wp-downloaded-count');
      if (countEl) countEl.innerText = count;
    }
  } catch (err) {}
}

async function refreshDownloadedStaticWallpapers() {
  const grid = document.getElementById('static-wp-downloaded-grid');
  const empty = document.getElementById('static-wp-downloaded-empty');
  if (!grid) return;

  grid.innerHTML = '<div class="col-span-full text-center py-10 text-gray-400"><div class="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>Yükleniyor...</div>';

  try {
    const res = await fetch('/api/static-wallpapers/downloaded');
    const json = await res.json();
    if (json.status === 'success') {
      const files = json.data || [];
      loadDownloadedStaticWallpapersCount();

      if (files.length === 0) {
        grid.innerHTML = '';
        if (empty) empty.classList.remove('hidden');
        return;
      }

      if (empty) empty.classList.add('hidden');
      grid.innerHTML = '';

      files.forEach((f, idx) => {
        const previewUrl = `/api/static-wallpapers/preview?file=${encodeURIComponent(f.file_path)}`;
        const card = document.createElement('div');
        card.className = 'glass-card rounded-xl border border-hextech-borderSubtle overflow-hidden flex flex-col group bg-[#020710]/90 shadow-lg';

        card.innerHTML = `
          <div class="relative aspect-video bg-black/80 overflow-hidden cursor-pointer" onclick="viewDownloadedWallpaperFull('${previewUrl}', '${f.file_name}')">
            <img src="${previewUrl}" alt="${f.file_name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" loading="lazy">
            <div class="absolute top-2 left-2 px-2 py-0.5 rounded text-[10px] font-extrabold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 backdrop-blur-md">
              4K UHD
            </div>
            <div class="absolute bottom-2 right-2 px-1.5 py-0.5 rounded text-[9px] font-mono bg-black/80 text-gray-300 border border-white/10">
              ${f.size_mb} MB
            </div>
          </div>

          <div class="p-3 flex-1 flex flex-col justify-between space-y-2">
            <div>
              <div class="text-[10px] font-bold text-gray-400 uppercase">${f.champ_name}</div>
              <h4 class="text-xs font-bold text-gray-200 line-clamp-1" title="${f.file_name}">${f.file_name}</h4>
            </div>

            <div class="grid grid-cols-2 gap-2 pt-1">
              <button onclick="setDownloadedDesktopWallpaper('${encodeURIComponent(f.file_path)}')" class="px-2 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/50 text-emerald-300 text-[10px] font-bold flex items-center justify-center space-x-1 cursor-pointer transition">
                <i data-lucide="monitor" class="w-3 h-3"></i>
                <span>Masaüstü Yap</span>
              </button>
              <button onclick="deleteDownloadedWallpaper('${encodeURIComponent(f.file_path)}')" class="px-2 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 text-[10px] font-bold flex items-center justify-center space-x-1 cursor-pointer transition">
                <i data-lucide="trash-2" class="w-3 h-3"></i>
                <span>Sil</span>
              </button>
            </div>
          </div>
        `;
        grid.appendChild(card);
      });

      if (window.lucide) lucide.createIcons();
    }
  } catch (err) {
    console.error("refreshDownloadedStaticWallpapers hatası:", err);
  }
}

function viewDownloadedWallpaperFull(url, title) {
  const modal = document.getElementById('static-wallpaper-modal');
  const titleEl = document.getElementById('static-modal-title');
  const subtitleEl = document.getElementById('static-modal-subtitle');
  const img = document.getElementById('static-modal-img');

  if (titleEl) titleEl.innerText = title;
  if (subtitleEl) subtitleEl.innerText = 'İndirilen 4K Duvar Kağıdı';
  if (img) img.src = url;

  if (modal) modal.classList.remove('hidden');
  if (window.lucide) lucide.createIcons();
}

async function setDownloadedDesktopWallpaper(filePathEncoded) {
  const filePath = decodeURIComponent(filePathEncoded);
  try {
    const res = await fetch('/api/static-wallpapers/set-desktop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: filePath })
    });
    const json = await res.json();
    if (json.status === 'success') {
      if (window.showToast) showToast("🖥️ Windows Masaüstü Duvar Kağıdı Güncellendi!");
    } else {
      if (window.showToast) showToast("❌ Duvar kağıdı ayarlanamadı: " + json.message);
    }
  } catch (err) {
    if (window.showToast) showToast("❌ Sunucu hatası: " + err.message);
  }
}

async function deleteDownloadedWallpaper(filePathEncoded) {
  const filePath = decodeURIComponent(filePathEncoded);
  if (!confirm("Bu duvar kağıdını silmek istediğinize emin misiniz?")) return;

  try {
    const res = await fetch('/api/static-wallpapers/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: filePath })
    });
    const json = await res.json();
    if (json.status === 'success') {
      if (window.showToast) showToast("🗑️ Duvar kağıdı silindi.");
      refreshDownloadedStaticWallpapers();
    } else {
      if (window.showToast) showToast("❌ Silinemedi: " + json.message);
    }
  } catch (err) {
    if (window.showToast) showToast("❌ Sunucu hatası: " + err.message);
  }
}

async function openStaticWallpapersFolder() {
  try {
    const res = await fetch('/api/static-wallpapers/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    });
    const json = await res.json();
    if (json.status === 'success') {
      if (window.showToast) showToast("📂 4K Duvar Kağıtları klasörü açıldı.");
    }
  } catch (err) {
    if (window.showToast) showToast("❌ Klasör açılamadı: " + err.message);
  }
}
