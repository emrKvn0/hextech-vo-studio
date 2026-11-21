// =========================================================================
// 5. CHAMPIONS & LOCAL SKINS LOGIC (VOICE EXTRACTOR TAB)
// =========================================================================
async function loadChampions() {
  try {
    const res = await fetch('/api/champions');
    allChampions = await res.json();
    const countEl = document.getElementById('champ-count');
    if (countEl) countEl.innerText = allChampions.length;
    renderChampions(allChampions);

    if (allChampions.length > 0 && !selectedChampion) {
      selectChampion(allChampions[0]);
    }
  } catch (err) {
    console.error("Failed to load champions:", err);
  }
}

function renderChampions(champs) {
  const container = document.getElementById('champions-list');
  if (!container) return;
  container.innerHTML = '';

  champs.forEach(ch => {
    const isSelected = ch === selectedChampion;
    const btn = document.createElement('button');
    btn.className = `w-full flex items-center justify-between px-2 py-1.5 rounded-lg text-xs font-medium cursor-pointer text-left transition-all ${
      isSelected 
        ? 'bg-hextech-cardSelected text-hextech-goldBright border border-hextech-gold shadow-md font-bold' 
        : 'text-gray-300 hover:bg-hextech-cardHover hover:text-white border border-transparent'
    }`;
    btn.innerHTML = `
      <div class="flex items-center space-x-1.5 truncate">
        <span class="text-xs opacity-90">🛡️</span>
        <span class="truncate font-sans">${ch}</span>
      </div>
      <i data-lucide="chevron-right" class="w-3 h-3 ${isSelected ? 'text-hextech-gold opacity-100' : 'opacity-25'}"></i>
    `;
    btn.onclick = () => selectChampion(ch);
    container.appendChild(btn);
  });

  if (window.lucide) lucide.createIcons();
}

function filterChampions(query) {
  const q = query.toLowerCase().trim();
  const filtered = allChampions.filter(c => c.toLowerCase().includes(q));
  renderChampions(filtered);
}

async function selectChampion(championName) {
  selectedChampion = championName;
  renderChampions(allChampions.filter(c => {
    const searchEl = document.getElementById('champ-search');
    const q = searchEl ? searchEl.value.toLowerCase().trim() : '';
    return c.toLowerCase().includes(q);
  }));

  const champTitle = document.getElementById('skin-selected-champ-title');
  if (champTitle) champTitle.innerText = `🎭 ${championName} Kostümleri`;

  selectedSkin = null;
  await loadSkinsForChampion(championName);
  refreshExtractedTree();
}

let rawChampionSkins = [];
let voiceSkinSelectorFilter = 'all';
let voiceSkinSearchQuery = '';
let voiceSkinSelectorSort = 'recommended';

async function loadSkinsForChampion(championName) {
  try {
    const res = await fetch(`/api/skins?champion=${encodeURIComponent(championName)}`);
    rawChampionSkins = await res.json();
    
    // Reset search
    voiceSkinSearchQuery = '';
    const searchInput = document.getElementById('skin-search-input');
    if (searchInput) searchInput.value = '';

    // Auto-select first skin if nothing is selected or previous selection does not match
    if (!selectedSkin || !rawChampionSkins.some(s => s.value === selectedSkin.value)) {
      selectedSkin = rawChampionSkins.find(s => s.num === 0) || rawChampionSkins[0];
    }

    renderSkinsList();
  } catch (err) {
    console.error("Skins load error:", err);
  }
}

function setSkinRarityFilter(filterType) {
  voiceSkinSelectorFilter = filterType;
  
  // Update UI pills
  document.querySelectorAll('.skin-filter-pill').forEach(pill => {
    pill.classList.remove('bg-hextech-gold', 'text-gray-950', 'font-bold', 'border-hextech-gold');
  });

  const activePill = document.getElementById(`skin-filter-${filterType}`);
  if (activePill) {
    activePill.classList.add('bg-hextech-gold', 'text-gray-950', 'font-bold', 'border-hextech-gold');
  }

  renderSkinsList();
}

function clearSkinFilters() {
  voiceSkinSelectorFilter = 'all';
  voiceSkinSearchQuery = '';
  voiceSkinSelectorSort = 'recommended';

  const searchInput = document.getElementById('skin-search-input');
  const sortSelect = document.getElementById('skin-sort-select');
  if (searchInput) searchInput.value = '';
  if (sortSelect) sortSelect.value = 'recommended';

  document.querySelectorAll('.skin-filter-pill').forEach(pill => {
    pill.classList.remove('bg-hextech-gold', 'text-gray-950', 'font-bold', 'border-hextech-gold');
  });
  document.getElementById('skin-filter-all')?.classList.add('bg-hextech-gold', 'text-gray-950', 'font-bold', 'border-hextech-gold');
  renderSkinsList();
}

function onSkinSearchInput(val) {
  voiceSkinSearchQuery = (val || '').trim().toLowerCase();
  renderSkinsList();
}

function onSkinSortChange(sortType) {
  voiceSkinSelectorSort = sortType;
  renderSkinsList();
}

function renderSkinsList() {
  const container = document.getElementById('skins-list');
  if (!container) return;

  const countEl = document.getElementById('skin-count');
  const summaryEl = document.getElementById('skin-selection-summary');
  if (!rawChampionSkins || rawChampionSkins.length === 0) {
    container.innerHTML = '<div class="text-center py-8 text-xs text-gray-500 w-full">Kostüm bulunamadı.</div>';
    if (countEl) countEl.innerText = '(0)';
    if (summaryEl) summaryEl.innerText = 'Bu şampiyon için kostüm verisi bulunamadı.';
    return;
  }

  // 1. Filter skins
  let filtered = rawChampionSkins.filter(s => {
    // Keep 'ALL' option only in 'all' filter and empty search
    if (s.num === -1) {
      return voiceSkinSelectorFilter === 'all' && !voiceSkinSearchQuery;
    }

    // Filter by Rarity / Voice Type
    if (voiceSkinSelectorFilter === 'unique_vo' && !(s.voice_type === 'unique' || s.is_recommended)) return false;
    if (voiceSkinSelectorFilter === 'filtered_vo' && s.voice_type !== 'filtered') return false;
    if (voiceSkinSelectorFilter === 'no_custom_vo' && !(s.voice_type === 'shared_base' || (!s.has_custom_vo && s.num > 0))) return false;
    if (voiceSkinSelectorFilter === 'legendary' && s.rarity_tier !== 'legendary') return false;
    if (voiceSkinSelectorFilter === 'mythic' && !(s.rarity_tier === 'mythic' || s.rarity_tier === 'ultimate')) return false;
    if (voiceSkinSelectorFilter === 'epic' && s.rarity_tier !== 'epic') return false;
    if (voiceSkinSelectorFilter === 'standard' && !(s.rarity_tier === 'standard' || s.rarity_tier === 'base' || s.rarity_tier === 'rare')) return false;

    // Filter by search query
    if (voiceSkinSearchQuery) {
      const q = voiceSkinSearchQuery;
      const matchName = (s.display_name || '').toLowerCase().includes(q);
      const matchRarity = (s.rarity_tr || '').toLowerCase().includes(q);
      const matchDesc = (s.voice_desc || '').toLowerCase().includes(q);
      const matchStatus = (s.vo_status_short || '').toLowerCase().includes(q);
      const matchStatusText = (s.vo_status_text || '').toLowerCase().includes(q);
      const matchBadge = (s.voice_badge || '').toLowerCase().includes(q);
      const matchNum = String(s.num).includes(q);
      if (!matchName && !matchRarity && !matchDesc && !matchStatus && !matchStatusText && !matchBadge && !matchNum) return false;
    }

    return true;
  });

  if (countEl) {
    const realCount = filtered.filter(s => s.num !== -1).length;
    const totalCount = rawChampionSkins.filter(s => s.num !== -1).length;
    countEl.innerText = `(${realCount}/${totalCount})`;
  }

  if (summaryEl) {
    if (selectedSkin) {
      const selectionLabel = selectedSkin.num === -1 ? 'Tüm kostümler' : selectedSkin.display_name;
      summaryEl.innerText = `Seçili: ${selectionLabel} • Kartlara tıklayarak değiştirin`;
    } else {
      summaryEl.innerText = 'Kartlara tıklayarak bir kostüm seçin.';
    }
  }

  // 2. Sort skins
  filtered.sort((a, b) => {
    if (a.num === -1) return -1;
    if (b.num === -1) return 1;

    if (voiceSkinSelectorSort === 'recommended') {
      const recA = a.is_recommended ? 1 : 0;
      const recB = b.is_recommended ? 1 : 0;
      if (recA !== recB) return recB - recA;

      const custA = a.has_custom_vo ? 1 : 0;
      const custB = b.has_custom_vo ? 1 : 0;
      if (custA !== custB) return custB - custA;

      const voA = a.has_vo ? 1 : 0;
      const voB = b.has_vo ? 1 : 0;
      if (voA !== voB) return voB - voA;

      if (a.vo_count !== b.vo_count) return (b.vo_count || 0) - (a.vo_count || 0);
      return (a.num || 0) - (b.num || 0);
    }

    if (voiceSkinSelectorSort === 'vo_count') {
      return (b.vo_count || 0) - (a.vo_count || 0);
    }

    if (voiceSkinSelectorSort === 'rarity') {
      const tierRank = { 'ultimate': 6, 'mythic': 5, 'legendary': 4, 'epic': 3, 'rare': 2, 'standard': 1, 'base': 0 };
      const rankA = tierRank[a.rarity_tier] || 0;
      const rankB = tierRank[b.rarity_tier] || 0;
      if (rankA !== rankB) return rankB - rankA;
      return (b.vo_count || 0) - (a.vo_count || 0);
    }

    if (voiceSkinSelectorSort === 'date_desc') {
      return (b.release_date || '').localeCompare(a.release_date || '');
    }

    if (voiceSkinSelectorSort === 'name_asc') {
      return (a.display_name || '').localeCompare(b.display_name || '', 'tr');
    }

    return (a.num || 0) - (b.num || 0);
  });

// Helper: Normalize champion names for Riot Data Dragon CDN
function normalizeDDragonChampName(name) {
  if (!name) return '';
  const clean = name.replace(/['\s._-]/g, '');
  const map = {
    'wukong': 'MonkeyKing',
    'renataglasc': 'Renata',
    'nunuwillump': 'Nunu',
    'nunu': 'Nunu',
    'drmundo': 'DrMundo',
    'aurelionsol': 'AurelionSol',
    'chogath': 'Chogath',
    'kaisa': 'Kaisa',
    'khazix': 'Khazix',
    'kogmaw': 'KogMaw',
    'leblanc': 'Leblanc',
    'masteryi': 'MasterYi',
    'missfortune': 'MissFortune',
    'reksai': 'RekSai',
    'tahmkench': 'TahmKench',
    'twistedfate': 'TwistedFate',
    'velkoz': 'Velkoz',
    'xinzhao': 'XinZhao',
    'ksante': 'KSante',
    'belveth': 'Belveth',
    'jarvaniv': 'JarvanIV'
  };
  return map[clean.toLowerCase()] || (clean.charAt(0).toUpperCase() + clean.slice(1));
}

function getSkinThumbUrls(champName, skinNum, backendSplashUrl) {
  const ddragonChamp = normalizeDDragonChampName(champName);
  const ddragonSplash = `https://ddragon.leagueoflegends.com/cdn/img/champion/splash/${ddragonChamp}_${skinNum}.jpg`;
  const ddragonLoading = `https://ddragon.leagueoflegends.com/cdn/img/champion/loading/${ddragonChamp}_${skinNum}.jpg`;
  const ddragonCentered = `https://ddragon.leagueoflegends.com/cdn/img/champion/centered/${ddragonChamp}_${skinNum}.jpg`;
  const ddragonTile = `https://ddragon.leagueoflegends.com/cdn/img/champion/tiles/${ddragonChamp}_${skinNum}.jpg`;

  const primary = backendSplashUrl || ddragonSplash;
  const fallback = ddragonSplash !== primary ? ddragonSplash : ddragonLoading;
  const finalFallback = `https://ddragon.leagueoflegends.com/cdn/img/champion/splash/${ddragonChamp}_0.jpg`;

  return { primary, fallback, finalFallback, ddragonCentered };
}

  // 3. Render Horizontal Cards
  container.innerHTML = '';
  if (filtered.length === 0) {
    container.innerHTML = '<div class="text-center py-6 text-xs text-gray-400 w-full">Bu filtreye uygun kostüm bulunamadı.</div>';
    return;
  }

  filtered.forEach(s => {
    const isSelected = selectedSkin && selectedSkin.value === s.value;
    const isAll = s.num === -1;

    const card = document.createElement('button');
    card.type = 'button';
    card.setAttribute('aria-pressed', String(Boolean(isSelected)));
    card.setAttribute('aria-label', `${s.display_name} kostümünü seç`);
    card.className = `skin-selection-card min-w-0 min-h-[142px] rounded-xl p-2 cursor-pointer text-left transition-all duration-200 border relative flex flex-col justify-between overflow-hidden group select-none ${
      isSelected
        ? 'bg-gradient-to-b from-hextech-surface via-hextech-card to-amber-950/40 border-hextech-gold shadow-[0_0_15px_rgba(200,155,60,0.35)] ring-2 ring-hextech-gold'
        : s.is_recommended
          ? 'bg-hextech-card/95 hover:bg-hextech-cardHover border-emerald-500/50 hover:border-hextech-gold shadow-md'
          : s.voice_type === 'filtered'
            ? 'bg-hextech-card/90 hover:bg-hextech-cardHover border-cyan-500/40 hover:border-cyan-400'
            : s.voice_type === 'base'
              ? 'bg-hextech-card/80 hover:bg-hextech-cardHover border-amber-500/40 hover:border-amber-400'
              : 'bg-hextech-card/50 hover:bg-hextech-card/90 border-hextech-borderSubtle hover:border-gray-500 text-gray-300'
    }`;

    // Rarity badge styling
    let rarityBadgeClass = 'bg-gray-800 text-gray-300 border-gray-700';
    if (s.rarity_tier === 'legendary') rarityBadgeClass = 'bg-amber-950/90 text-amber-300 border-amber-500/60 font-bold';
    else if (s.rarity_tier === 'mythic' || s.rarity_tier === 'ultimate') rarityBadgeClass = 'bg-purple-950/90 text-purple-300 border-purple-500/60 font-bold';
    else if (s.rarity_tier === 'epic') rarityBadgeClass = 'bg-blue-950/90 text-blue-300 border-blue-500/50 font-bold';
    else if (s.rarity_tier === 'base') rarityBadgeClass = 'bg-slate-900 text-gray-400 border-slate-700';

    // Voice badge styling (Bottom Pill)
    let voiceBadgeClass = 'bg-gray-900/80 text-gray-400 border-gray-700';
    if (s.voice_type === 'unique' || s.is_recommended) voiceBadgeClass = 'bg-emerald-950 text-emerald-300 border-emerald-500/60 font-extrabold shadow-sm';
    else if (s.voice_type === 'filtered') voiceBadgeClass = 'bg-cyan-950 text-cyan-300 border-cyan-500/50 font-bold';
    else if (s.voice_type === 'partial') voiceBadgeClass = 'bg-amber-950/80 text-amber-300 border-amber-500/50 font-bold';
    else if (s.voice_type === 'base') voiceBadgeClass = 'bg-amber-950/60 text-amber-300/90 border-amber-500/30';
    else if (isAll) voiceBadgeClass = 'bg-cyan-950 text-cyan-300 border-cyan-500/60 font-extrabold';

    // Multi-tier Splash thumbnail URLs
    const urls = getSkinThumbUrls(selectedChampion, s.num >= 0 ? s.num : 0, s.splash_url);

    let bannerHtml = '';
    if (!isAll) {
      bannerHtml = `
        <div class="h-12 w-full rounded-lg overflow-hidden relative border border-hextech-borderSubtle/60 bg-[#040812] mb-1.5 shrink-0">
          <img src="${urls.primary}" 
               loading="lazy"
               class="w-full h-full object-cover object-top transition-transform duration-300 group-hover:scale-105" 
               onerror="if (!this.dataset.retry) { this.dataset.retry='1'; this.src='${urls.fallback}'; } else if (this.dataset.retry==='1') { this.dataset.retry='2'; this.src='${urls.finalFallback}'; } else { this.onerror=null; this.style.opacity='0.4'; }">
          <div class="absolute inset-0 bg-gradient-to-t from-[#020712] via-transparent to-black/40 pointer-events-none"></div>
          <span class="absolute top-1 left-1 px-1.5 py-0.2 rounded text-[8px] border font-bold ${rarityBadgeClass}">
            ${s.rarity_tr}
          </span>
          <span class="absolute top-1 right-1 px-1 rounded text-[8px] font-mono bg-black/80 text-gray-300 border border-gray-700">
            #${s.num}
          </span>
          ${s.cost_rp ? `<span class="absolute bottom-1 right-1 px-1 rounded text-[8px] font-mono bg-black/70 text-hextech-gold">${s.cost_rp} RP</span>` : ''}
        </div>
      `;
    } else {
      bannerHtml = `
        <div class="h-12 w-full rounded-lg overflow-hidden relative border border-cyan-500/40 bg-gradient-to-r from-cyan-950 to-blue-950 flex items-center justify-center text-cyan-300 mb-1.5 shrink-0">
          <div class="flex items-center gap-1.5 font-heading font-extrabold text-xs">
            <i data-lucide="sparkles" class="w-4 h-4 text-cyan-300"></i>
            <span>TÜM KOSTÜMLER</span>
          </div>
        </div>
      `;
    }

    // Explicit Custom VO / Voice Status Indicator Box
    let voStatusCardHtml = '';
    if (isAll) {
      voStatusCardHtml = `
        <div class="rounded-lg bg-gradient-to-r from-cyan-950/80 to-blue-950/80 border border-cyan-500/40 p-1.5 flex flex-col gap-0.5 shadow-sm">
          <div class="flex items-center justify-between gap-1">
            <span class="text-[10px] font-heading font-extrabold text-cyan-300 flex items-center gap-1 truncate">
              <i data-lucide="sparkles" class="w-3 h-3 text-cyan-400 shrink-0"></i>
              <span>TÜM SES BANKALARI</span>
            </span>
            <span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-cyan-900 text-cyan-200 border border-cyan-500/40 shrink-0">Full Paket</span>
          </div>
          <div class="text-[9px] text-cyan-400/80 font-sans truncate">🌟 Tüm kostümleri tek seferde çıkarır</div>
        </div>
      `;
    } else if (s.voice_type === 'unique' || s.is_recommended) {
      voStatusCardHtml = `
        <div class="rounded-lg bg-emerald-950/75 border border-emerald-500/50 p-1.5 flex flex-col gap-0.5 shadow-sm">
          <div class="flex items-center justify-between gap-1">
            <span class="text-[10px] font-heading font-extrabold text-emerald-300 flex items-center gap-1 truncate">
              <i data-lucide="crown" class="w-3.5 h-3.5 text-emerald-400 shrink-0"></i>
              <span>Özel Dublaj: VAR</span>
            </span>
            <span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-emerald-900/90 text-emerald-200 border border-emerald-500/50 shrink-0">${s.vo_count} Replik</span>
          </div>
          <div class="text-[9px] text-emerald-300/90 font-sans truncate">👑 Özgün yeni replikler & özel atıflar</div>
        </div>
      `;
    } else if (s.voice_type === 'filtered') {
      voStatusCardHtml = `
        <div class="rounded-lg bg-cyan-950/75 border border-cyan-500/50 p-1.5 flex flex-col gap-0.5 shadow-sm">
          <div class="flex items-center justify-between gap-1">
            <span class="text-[10px] font-heading font-extrabold text-cyan-300 flex items-center gap-1 truncate">
              <i data-lucide="sliders" class="w-3.5 h-3.5 text-cyan-400 shrink-0"></i>
              <span>Özel Efekt: VAR</span>
            </span>
            <span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-cyan-900/90 text-cyan-200 border border-cyan-500/50 shrink-0">${s.vo_count} Replik</span>
          </div>
          <div class="text-[9px] text-cyan-300/90 font-sans truncate">🔊 Kostüme özel vokal filtreli sesler</div>
        </div>
      `;
    } else if (s.voice_type === 'partial') {
      voStatusCardHtml = `
        <div class="rounded-lg bg-amber-950/60 border border-amber-500/40 p-1.5 flex flex-col gap-0.5 shadow-sm">
          <div class="flex items-center justify-between gap-1">
            <span class="text-[10px] font-heading font-extrabold text-amber-300 flex items-center gap-1 truncate">
              <i data-lucide="volume-2" class="w-3.5 h-3.5 text-amber-400 shrink-0"></i>
              <span>Özel Dublaj: KISMİ</span>
            </span>
            <span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-amber-900/90 text-amber-200 border border-amber-500/40 shrink-0">${s.vo_count} Replik</span>
          </div>
          <div class="text-[9px] text-amber-300/80 font-sans truncate">⚡ Kostüme özel ek replik/efekt</div>
        </div>
      `;
    } else if (s.voice_type === 'base' || s.num === 0) {
      voStatusCardHtml = `
        <div class="rounded-lg bg-amber-950/40 border border-amber-500/30 p-1.5 flex flex-col gap-0.5">
          <div class="flex items-center justify-between gap-1">
            <span class="text-[10px] font-heading font-bold text-amber-300 flex items-center gap-1 truncate">
              <i data-lucide="mic" class="w-3.5 h-3.5 text-amber-400 shrink-0"></i>
              <span>Orijinal Dublaj</span>
            </span>
            <span class="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-amber-950 text-amber-200 border border-amber-500/30 shrink-0">${s.vo_count || 71} Replik</span>
          </div>
          <div class="text-[9px] text-amber-300/70 font-sans truncate">🛡️ Şampiyonun varsayılan ana sesi</div>
        </div>
      `;
    } else {
      voStatusCardHtml = `
        <div class="rounded-lg bg-gray-900/80 border border-gray-700/60 p-1.5 flex flex-col gap-0.5">
          <div class="flex items-center justify-between gap-1">
            <span class="text-[10px] font-heading font-semibold text-rose-300/90 flex items-center gap-1 truncate">
              <i data-lucide="slash" class="w-3 h-3 text-rose-400/80 shrink-0"></i>
              <span>Özel Dublaj: YOK</span>
            </span>
            <span class="px-1.5 py-0.2 rounded text-[9px] font-mono bg-gray-800 text-gray-400 border border-gray-700 shrink-0">Temel Ses</span>
          </div>
          <div class="text-[9px] text-gray-500 font-sans truncate">Standart şampiyon repliklerini kullanır</div>
        </div>
      `;
    }

    card.innerHTML = `
      ${bannerHtml}
      
      <div class="flex-1 flex flex-col justify-between min-w-0">
        <div class="font-heading font-bold text-xs truncate mb-1.5 ${isSelected ? 'text-hextech-goldBright' : 'text-gray-100 group-hover:text-hextech-gold'}">
          ${s.display_name}
        </div>

        <div class="mb-1.5">
          ${voStatusCardHtml}
        </div>

        <div class="flex items-center justify-between pt-1 border-t border-hextech-borderSubtle/50 text-[9px]">
          <span class="px-1.5 py-0.2 rounded border ${voiceBadgeClass} truncate max-w-[135px]">
            ${s.voice_badge}
          </span>
          ${isSelected ? `
            <span class="text-hextech-gold flex items-center gap-0.5 font-bold shrink-0">
              <i data-lucide="check-circle-2" class="w-3 h-3 text-hextech-gold"></i>
              <span>Seçili</span>
            </span>
          ` : `
            <span class="text-gray-500 group-hover:text-gray-300 font-medium shrink-0">Seç</span>
          `}
        </div>
      </div>
    `;

    card.onclick = () => {
      selectedSkin = s;
      renderSkinsList();
    };

    container.appendChild(card);
  });

  if (window.lucide) lucide.createIcons();
}

async function checkSelectedChampionVO() {
  if (!selectedChampion) {
    showVoCheckModal(`
      <div class="text-center py-4">
        <div class="text-amber-400 font-bold text-sm">⚠️ Lütfen önce sol menüden bir şampiyon seçin!</div>
      </div>
    `);
    return;
  }
  
  const btn = document.getElementById('btn-check-skin-vo');
  if (btn) btn.innerHTML = '<div class="w-3 h-3 border-2 border-hextech-cyanNeon border-t-transparent rounded-full animate-spin"></div><span>Sorgulanıyor...</span>';

  try {
    const res = await fetch(`/api/check-skin-vo?champion=${encodeURIComponent(selectedChampion)}`);
    const data = await res.json();
    
    if (data && data.status === 'success') {
      const customSkins = data.skins || [];
      let msgHtml = `
        <div class="space-y-3">
          <div class="flex items-center justify-between border-b border-hextech-borderSubtle pb-2">
            <div>
              <h3 class="text-base font-extrabold text-hextech-goldBright flex items-center gap-2">
                <span>🎙️ ${selectedChampion} - Riot Wwise Ses Bankası Analizi</span>
              </h3>
              <p class="text-xs text-gray-400 mt-0.5">Riot WAD dosyası doğrudan Wwise HIRC Event grafiğiyle sorgulandı.</p>
            </div>
            <span class="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-950 text-amber-300 border border-amber-500/40">
              ${data.total_custom_vo_skins} Bağımsız Ses Bankası
            </span>
          </div>

          <div class="space-y-2 max-h-72 overflow-y-auto pr-1">
      `;
      
      if (customSkins.length === 0) {
        msgHtml += `<div class="text-center py-6 text-gray-400 text-xs">Bu şampiyon yalnızca standart repliklere sahiptir.</div>`;
      } else {
        customSkins.forEach(s => {
          const isBase = s.is_base ? ' (Varsayılan)' : '';
          let badgeStyle = 'from-gray-900 to-slate-900 text-gray-300 border-gray-600';
          let badgeText = `🎙️ ${s.vo_count} Replik`;
          let noteText = 'Standart ses bankası.';

          if (s.voice_type === 'unique' || s.is_recommended) {
            badgeStyle = 'from-emerald-950 to-teal-950 text-emerald-300 border-emerald-500/60 font-extrabold shadow-sm';
            badgeText = `👑 ÖZGÜN YENİ DUBLAJ (${s.vo_count} Replik)`;
            noteText = '🔥 Tamamen sıfırdan kaydedilmiş bağımsız yeni replikler ve özel atıflar barındırır.';
          } else if (s.voice_type === 'filtered') {
            badgeStyle = 'from-cyan-950 to-blue-950 text-cyan-300 border-cyan-500/50 font-bold';
            badgeText = `🎛️ VOKAL EFEKTLİ (${s.vo_count} Replik)`;
            noteText = 'ℹ️ Temel dublaj üzerine kostüme özel ses efekti/filtresi uygulanmıştır.';
          } else if (s.voice_type === 'base') {
            badgeStyle = 'from-amber-950 to-yellow-950 text-amber-300 border-amber-500/50';
            badgeText = `🎮 STANDART DUBLAJ (${s.vo_count} Replik)`;
            noteText = 'Şampiyonun orijinal varsayılan Türkçe dublajı.';
          }

          msgHtml += `
            <div class="p-3 rounded-lg bg-hextech-surface/80 border border-hextech-borderSubtle hover:border-hextech-gold flex flex-col gap-1.5 transition-all">
              <div class="flex items-center justify-between gap-2 flex-wrap">
                <div class="font-bold text-sm text-gray-100 flex items-center gap-1.5">
                  <span>🎭 ${s.skin_name.replace(/_/g, ' ')}${isBase}</span>
                </div>
                <span class="px-2.5 py-1 rounded-md bg-gradient-to-r ${badgeStyle} text-xs border shadow">
                  ${badgeText}
                </span>
              </div>
              <div class="text-[11px] text-gray-300">
                ${noteText}
              </div>
              <div class="text-[10px] text-gray-500 font-mono">
                Wwise Bankası: <span class="text-hextech-cyan font-semibold">${s.skin_id}</span> • Boyut: ${(s.bank_size/1024).toFixed(1)} KB
              </div>
            </div>
          `;
        });
      }
      
      msgHtml += `
          </div>
          <div class="text-[11px] text-gray-300 bg-hextech-base/80 p-3 rounded-lg border border-hextech-borderSubtle space-y-1">
            <div class="font-bold text-hextech-gold flex items-center gap-1.5">
              <i data-lucide="info" class="w-3.5 h-3.5"></i>
              <span>Ses Türleri Rehberi:</span>
            </div>
            <div>• <strong class="text-emerald-300">👑 Özgün Yeni Dublaj:</strong> Efsanevi kostümler gibi sıfırdan kaydedilen zengin replikler ve özel şampiyon atıfları.</div>
            <div>• <strong class="text-cyan-300">🎛️ Vokal Efektli:</strong> Epik kostümler gibi temel dublaja özel ses filtresi uygulanmış haller (yeni metin içermez).</div>
            <div>• <strong class="text-gray-400">🛡️ Temel Ses:</strong> Şampiyonun standart seslendirmesi.</div>
          </div>
        </div>
      `;
      
      showVoCheckModal(msgHtml);
    } else {
      showVoCheckModal(`<div class="text-rose-400 font-bold text-xs py-4">❌ Ses bankası sorgulama hatası: ${data.message || 'Bilinmeyen hata'}</div>`);
    }
  } catch (err) {
    console.error("VO check error:", err);
    showVoCheckModal(`<div class="text-rose-400 font-bold text-xs py-4">❌ Bağlantı hatası: ${err}</div>`);
  } finally {
    if (btn) btn.innerHTML = '<i data-lucide="scan-line" class="w-3 h-3 text-hextech-gold"></i><span>Wwise Ses Analizi</span>';
    if (window.lucide) lucide.createIcons();
  }
}

function showVoCheckModal(contentHtml) {
  let modal = document.getElementById('vo-check-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'vo-check-modal';
    modal.className = 'fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-fade-in';
    modal.innerHTML = `
      <div class="glass-card max-w-xl w-full rounded-2xl border border-hextech-goldDim p-5 shadow-2xl relative flex flex-col max-h-[85vh]">
        <button onclick="closeVoCheckModal()" class="absolute top-4 right-4 text-gray-400 hover:text-white p-1 rounded-lg hover:bg-hextech-surface cursor-pointer">
          <i data-lucide="x" class="w-5 h-5"></i>
        </button>
        <div id="vo-check-modal-body" class="overflow-y-auto pr-1"></div>
        <div class="mt-4 pt-3 border-t border-hextech-borderSubtle flex justify-end">
          <button onclick="closeVoCheckModal()" class="px-4 py-2 rounded-lg bg-hextech-cardSelected hover:bg-hextech-surface border border-hextech-borderSubtle text-gray-200 text-xs font-bold cursor-pointer">
            Kapat
          </button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
  }
  
  const body = document.getElementById('vo-check-modal-body');
  if (body) body.innerHTML = contentHtml;
  modal.classList.remove('hidden');
  if (window.lucide) lucide.createIcons();
}

function closeVoCheckModal() {
  const modal = document.getElementById('vo-check-modal');
  if (modal) modal.classList.add('hidden');
}

// =========================================================================
// =========================================================================
// 6. EXTRACTED VOICE EXPLORER TREE & BATCH SELECTION
// =========================================================================
let currentExtractedTree = [];
let selectedAudioPaths = new Set();
let currentTreeSearchQuery = '';

// Active Playback Queue
let activeAudioQueue = []; // array of { path, name, skinName, catName }
let currentQueueIndex = -1;
let isAutoplayEnabled = true;
let isBatchPlaying = false;

async function refreshExtractedTree() {
  if (!selectedChampion) return;
  const container = document.getElementById('extracted-tree');
  if (!container) return;
  container.innerHTML = '<div class="text-center py-6 text-gray-500 text-xs font-mono animate-pulse">Ses kütüphanesi taranıyor...</div>';

  try {
    const res = await fetch(`/api/extracted-tree?champion=${encodeURIComponent(selectedChampion)}`);
    currentExtractedTree = await res.json();
    renderExtractedTree();
  } catch (err) {
    console.error("Refresh extracted tree error:", err);
  }
}

function onTreeSearchInput(query) {
  currentTreeSearchQuery = (query || '').toLowerCase().trim();
  renderExtractedTree();
}

function renderExtractedTree() {
  const container = document.getElementById('extracted-tree');
  if (!container) return;

  if (!currentExtractedTree || currentExtractedTree.length === 0) {
    container.innerHTML = `
      <div class="text-center py-10 text-gray-500 text-xs">
        <i data-lucide="folder-x" class="w-8 h-8 mx-auto mb-2 opacity-30"></i>
        <span>${selectedChampion} için henüz çıkarılmış ses bulunamadı.</span>
      </div>
    `;
    if (window.lucide) lucide.createIcons();
    updateSelectedAudioBadge();
    return;
  }

  container.innerHTML = '';
  let visibleAudioCount = 0;

  currentExtractedTree.forEach(skinObj => {
    // Filter categories and files
    const matchedCategories = [];

    skinObj.categories.forEach(cat => {
      const filteredFiles = cat.files.filter(f => {
        if (!currentTreeSearchQuery) return true;
        const q = currentTreeSearchQuery;
        return (f.name || '').toLowerCase().includes(q) || (cat.name || '').toLowerCase().includes(q) || (skinObj.skinName || '').toLowerCase().includes(q);
      });

      if (filteredFiles.length > 0) {
        matchedCategories.push({
          name: cat.name,
          files: filteredFiles,
          fileCount: filteredFiles.length
        });
        visibleAudioCount += filteredFiles.length;
      }
    });

    if (matchedCategories.length === 0) return;

    const skinCard = document.createElement('div');
    skinCard.className = 'glass-card rounded-xl border border-hextech-borderSubtle overflow-hidden shadow-lg';

    const header = document.createElement('div');
    header.className = 'px-3.5 py-2 bg-gradient-to-r from-hextech-cardHover to-hextech-surface font-heading font-bold text-xs text-hextech-goldBright flex items-center justify-between border-b border-hextech-borderSubtle';
    header.innerHTML = `
      <div class="flex items-center space-x-2 truncate">
        <span class="text-sm">🎭</span>
        <span class="truncate font-sans font-bold tracking-wide text-gray-100">${skinObj.skinName.replace(/_/g, ' ')}</span>
      </div>
      <span class="text-[10px] px-2 py-0.5 rounded bg-hextech-base text-hextech-gold font-mono font-bold border border-hextech-borderSubtle">${matchedCategories.length} Kategori</span>
    `;

    const catContainer = document.createElement('div');
    catContainer.className = 'p-2 space-y-1.5';

    matchedCategories.forEach(cat => {
      const details = document.createElement('details');
      details.className = 'group rounded-lg bg-hextech-surface/80 border border-hextech-borderSubtle/60 overflow-hidden';
      if (currentTreeSearchQuery) details.open = true;

      const summary = document.createElement('summary');
      summary.className = 'px-3 py-1.5 text-xs font-heading font-bold text-gray-200 hover:text-hextech-goldBright cursor-pointer flex items-center justify-between list-none transition-colors select-none';
      
      const allCatSelected = cat.files.length > 0 && cat.files.every(f => selectedAudioPaths.has(f.path));

      summary.innerHTML = `
        <span class="truncate flex items-center gap-2">
          <span class="text-hextech-gold">📁</span>
          <span>${cat.name.replace(/_/g, ' ')}</span>
        </span>
        <div class="flex items-center gap-1.5" onclick="event.stopPropagation();">
          <button onclick="playCategoryDirect('${skinObj.skinName}', '${cat.name}', ${JSON.stringify(cat.files).replace(/"/g, '&quot;')})" class="px-2 py-0.5 rounded bg-hextech-card hover:bg-hextech-gold hover:text-gray-950 text-hextech-cyan text-[10px] font-bold border border-hextech-borderSubtle flex items-center gap-1 transition-all cursor-pointer" title="Bu Kategoriyi Sıralı Çal">
            <i data-lucide="play" class="w-2.5 h-2.5"></i>
            <span>Çal</span>
          </button>
          <span class="text-[10px] px-1.5 py-0.5 rounded bg-hextech-card text-hextech-cyan font-mono font-bold">${cat.fileCount} ses</span>
        </div>
      `;

      const fileList = document.createElement('div');
      fileList.className = 'p-1 space-y-0.5 bg-[#01060D] border-t border-hextech-borderSubtle/40';

      cat.files.forEach(f => {
        const isChecked = selectedAudioPaths.has(f.path);
        const isPlayingThis = activeAudioQueue[currentQueueIndex] && activeAudioQueue[currentQueueIndex].path === f.path;

        const row = document.createElement('div');
        row.className = `px-2.5 py-1.5 rounded-md text-[11px] font-mono truncate flex items-center justify-between group/row transition-all ${
          isPlayingThis
            ? 'bg-emerald-950/70 border border-emerald-500/60 text-emerald-300 shadow-[0_0_10px_rgba(16,185,129,0.2)]'
            : isChecked
              ? 'bg-hextech-goldBorder/20 border border-hextech-gold/40 text-hextech-goldBright'
              : 'text-gray-300 hover:bg-hextech-cardHover hover:text-hextech-gold border border-transparent'
        }`;

        row.innerHTML = `
          <div class="flex items-center space-x-2 truncate flex-1 min-w-0">
            <input type="checkbox" ${isChecked ? 'checked' : ''} onclick="event.stopPropagation(); toggleAudioSelection('${f.path.replace(/\\/g, '\\\\')}', this.checked)" class="rounded bg-gray-900 border-gray-700 text-hextech-gold focus:ring-0 cursor-pointer">
            ${isPlayingThis ? `<i data-lucide="activity" class="w-3.5 h-3.5 text-emerald-400 animate-pulse shrink-0"></i>` : `<i data-lucide="volume-2" class="w-3.5 h-3.5 text-hextech-cyan group-hover/row:text-hextech-gold shrink-0"></i>`}
            <span class="truncate">${f.name}</span>
          </div>
          <div class="flex items-center gap-1.5 shrink-0 opacity-0 group-hover/row:opacity-100 transition-opacity">
            <button onclick="event.stopPropagation(); playSingleAudioDirect('${f.path.replace(/\\/g, '\\\\')}', '${f.name}', '${skinObj.skinName}', '${cat.name}')" class="p-1 hover:bg-hextech-card rounded text-hextech-gold" title="Hemen Dinle">
              <i data-lucide="play" class="w-3 h-3"></i>
            </button>
          </div>
        `;

        row.onclick = () => playSingleAudioDirect(f.path, f.name, skinObj.skinName, cat.name);
        fileList.appendChild(row);
      });

      details.appendChild(summary);
      details.appendChild(fileList);
      catContainer.appendChild(details);
    });

    skinCard.appendChild(header);
    skinCard.appendChild(catContainer);
    container.appendChild(skinCard);
  });

  if (window.lucide) lucide.createIcons();
  updateSelectedAudioBadge();
}

function toggleAudioSelection(path, isChecked) {
  if (isChecked) selectedAudioPaths.add(path);
  else selectedAudioPaths.delete(path);
  updateSelectedAudioBadge();
}

function toggleSelectAllAudio(isChecked) {
  if (!currentExtractedTree) return;
  currentExtractedTree.forEach(skinObj => {
    skinObj.categories.forEach(cat => {
      cat.files.forEach(f => {
        if (isChecked) selectedAudioPaths.add(f.path);
        else selectedAudioPaths.delete(f.path);
      });
    });
  });
  renderExtractedTree();
  updateSelectedAudioBadge();
}

function clearAudioSelection() {
  selectedAudioPaths.clear();
  const cb = document.getElementById('cb-select-all-audio');
  if (cb) cb.checked = false;
  renderExtractedTree();
  updateSelectedAudioBadge();
}

function updateSelectedAudioBadge() {
  const badge = document.getElementById('selected-audio-badge');
  if (badge) badge.innerText = `${selectedAudioPaths.size} ses seçili`;
  const cb = document.getElementById('cb-select-all-audio');
  if (cb) cb.checked = selectedAudioPaths.size > 0;
}

async function openExtractedFolder() {
  try {
    const res = await fetch('/api/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder: selectedChampion || 'latest' })
    });
    const data = await res.json();
    if (data && data.target_rel) {
      onLogMessage(`📂 Windows Gezgini'nde açıldı: ${data.target_rel}`);
    }
  } catch (err) {
    console.error("Open folder error:", err);
  }
}



// =========================================================================
// VOICE EXTRACTION CONFIRMATION & TRIGGER SYSTEM
// =========================================================================
let pendingExtractTarget = null; // { champ: string, skin: string|null, skinLabel: string }

function requestVoiceExtractionConfirm(champName, skinName) {
  if (!champName) return;

  const skinLabel = skinName || 'Tüm Kostümler';
  pendingExtractTarget = {
    champ: champName,
    skin: skinName,
    skinLabel: skinLabel
  };

  const modal = document.getElementById('extract-confirm-modal');
  const titleEl = document.getElementById('confirm-modal-target-title');
  const descEl = document.getElementById('confirm-modal-target-desc');

  if (titleEl) {
    titleEl.innerText = skinName ? `${skinName} (${champName})` : `${champName} - Tüm Kostümler`;
  }
  if (descEl) {
    descEl.innerText = skinName 
      ? `"${skinName}" kostümüne ait tüm Türkçe replikler ve ses efektleri Wwise motoruyla doğrudan çıkarılacaktır. İşlemi başlatmak istediğinize emin misiniz?`
      : `"${champName}" şampiyonunun tüm kostüm sesleri ve replikleri Wwise motoruyla doğrudan çıkarılacaktır. İşlemi başlatmak istediğinize emin misiniz?`;
  }

  if (modal) {
    modal.classList.remove('hidden');
    lucide.createIcons();
  }
}

function closeExtractConfirmModal() {
  const modal = document.getElementById('extract-confirm-modal');
  if (modal) modal.classList.add('hidden');
  pendingExtractTarget = null;
}

async function executeConfirmedVoiceExtraction() {
  if (!pendingExtractTarget) return;
  const target = pendingExtractTarget;
  closeExtractConfirmModal();

  onLogMessage(`🚀 [${target.champ}] - ${target.skinLabel} için ses çıkarma başlatılıyor...`);
  if (progressBarContainer) progressBarContainer.classList.remove('hidden');

  try {
    const res = await fetch('/api/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ champion: target.champ, skin: target.skin })
    });
    const data = await res.json();
    if (data && data.status === 'busy') {
      onLogMessage(`⚠️ ${data.message}`);
      if (progressBarContainer) progressBarContainer.classList.add('hidden');
    }
  } catch (err) {
    onLogMessage(`❌ Sunucu bağlantı hatası: ${err}`);
    if (progressBarContainer) progressBarContainer.classList.add('hidden');
  }
}

function jumpToVoiceExtractorFromModal() {
  if (!activeModalSkin) return;
  const champ = activeModalSkin.champName;
  const skin = activeModalSkin.name;
  closeSkinModal();
  requestVoiceExtractionConfirm(champ, skin);
}

function jumpToWallpaperSearchFromModal() {
  if (!activeModalSkin) return;
  const skin = activeModalSkin.name || activeModalSkin.champName;
  closeSkinModal();
  switchTab('wallpapers');
  const searchInput = document.getElementById('wp-search-input');
  if (searchInput) {
    searchInput.value = skin;
  }
  toggleWallpaperView('search');
  triggerWallpaperSearch();
}

function jumpToVoiceExtractorForChamp(champName) {
  switchTab('voices');
  const search = document.getElementById('champ-search');
  if (search) {
    search.value = champName;
    filterChampions(champName);
  }
  selectChampion(champName);
}

function openDownloadsDir() {
  fetch('/api/open-folder', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ folder: '_CDN_Downloads' })
  });
}



// =========================================================================
// SECTION 13: A'DAN Z'YE TÜM VARSAYILAN ŞAMPİYONLAR HUB'I & DAVINCI RESOLVE
// =========================================================================
async function openBaseHubModal() {
  const modal = document.getElementById('base-hub-modal');
  if (modal) modal.classList.remove('hidden');
  if (window.lucide) lucide.createIcons();
  await loadBaseHubStatus();
}

function closeBaseHubModal() {
  const modal = document.getElementById('base-hub-modal');
  if (modal) modal.classList.add('hidden');
}

async function loadBaseHubStatus() {
  try {
    const res = await fetch('/api/base-hub-status');
    const json = await res.json();
    if (json.status === 'success') {
      const d = json.data;
      const chEl = document.getElementById('hub-synced-champs');
      const vEl = document.getElementById('hub-synced-voices');
      if (chEl) chEl.innerText = d.synced_champions_count || 0;
      if (vEl) vEl.innerText = (d.total_synced_voices || 0).toLocaleString();
    }
  } catch (err) {
    console.error("Base hub status error:", err);
  }
}

async function openBaseHubFolder() {
  try {
    await fetch('/api/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder: '_Tum_Varsayilan_Sampiyonlar_A_dan_Z_ye' })
    });
  } catch (err) {
    console.error("Open hub folder error:", err);
  }
}

async function syncBaseHubAction() {
  try {
    showToast("🔄 A-Z Hub senkronizasyonu başlatıldı...");
    const res = await fetch('/api/sync-base-hub', { method: 'POST' });
    const json = await res.json();
    if (json.status === 'success') {
      showToast(`✨ ${json.data.synced_champions} şampiyon (${json.data.total_files} replik) A-Z Hub'ına senkronize edildi!`);
      await loadBaseHubStatus();
    } else {
      showToast("❌ Senkronizasyon hatası: " + json.message);
    }
  } catch (err) {
    showToast("❌ Bağlantı hatası: " + err.message);
  }
}

async function exportBaseHubMasterDaVinci() {
  const btn = document.getElementById('btn-export-hub-davinci');
  const gapInput = document.getElementById('hub-davinci-gap');
  const gap = gapInput ? parseFloat(gapInput.value) || 0.2 : 0.2;

  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>XML Üretiliyor...</span>`;
    if (window.lucide) lucide.createIcons();
  }

  try {
    const res = await fetch('/api/export-base-hub-davinci', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gap_seconds: gap, fps: 60 })
    });
    const json = await res.json();

    if (json.status === 'success') {
      closeBaseHubModal();
      openDaVinciModal({
        file_path: json.output_xml_path,
        file_name: json.filename,
        clip_count: json.total_audio_count,
        gap_seconds: gap,
        total_duration: json.total_duration_seconds
      });
      showToast(`🎬 Master DaVinci Timeline hazır: ${json.total_audio_count} ses (${json.total_duration_formatted})`);
    } else {
      showToast("❌ DaVinci Hatası: " + (json.message || "Bilinmeyen hata"));
    }
  } catch (err) {
    showToast("❌ İstek Hatası: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="film" class="w-3.5 h-3.5"></i><span>Master DaVinci XML Üret</span>`;
      if (window.lucide) lucide.createIcons();
    }
  }
}

async function extractAllBaseChampionsAction() {
  if (!confirm("Tüm 170+ şampiyonun varsayılan sesleri sırayla çıkarılıp A-Z Hub'ına kaydedilecek. Bu işlem birkaç dakika sürebilir. Başlatılsın mı?")) {
    return;
  }
  try {
    showToast("🚀 Tüm varsayılan şampiyon sesleri çıkarma işlemi başlatıldı!");
    await fetch('/api/extract-all-base', { method: 'POST' });
    closeBaseHubModal();
  } catch (err) {
    showToast("❌ Hata: " + err.message);
  }
}

