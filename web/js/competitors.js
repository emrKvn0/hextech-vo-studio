// =========================================================================
// 9. YOUTUBE COMPETITOR & OPPORTUNITY ANALYSIS ENGINE
// =========================================================================
let competitorAnalysisData = null;
let competitorSubTab = 'opps';
let competitorSearchQuery = '';
let selectedCompetitorChannelFilter = 'ALL';

function getSelectedCompetitorChannels() {
  const checkboxes = document.querySelectorAll('#channel-selection-chips input[type="checkbox"]:checked');
  const selected = Array.from(checkboxes).map(cb => cb.value);
  return selected.length > 0 ? selected : ['leaguevoices', 'quaxanos', 'pbetr', 'leagueofvoice', 'turkish_videogamevoice', 'lolnewstr'];
}

function toggleAllCompetitorChannels(selectState) {
  const checkboxes = document.querySelectorAll('#channel-selection-chips input[type="checkbox"]');
  checkboxes.forEach(cb => cb.checked = !!selectState);
  updateSelectedChannelsUI();
}

function updateSelectedChannelsUI() {
  const selected = getSelectedCompetitorChannels();
  const label = document.getElementById('active-channels-label');
  if (label) {
    label.innerText = `${selected.length} Kanal Seçili`;
  }
}

function filterCompetitorByChannel(val) {
  selectedCompetitorChannelFilter = val || 'ALL';
  renderCompetitorView();
}

function renderCompetitorWelcome() {
  const container = document.getElementById('competitors-content-container');
  if (!container) return;
  
  container.innerHTML = `
    <div class="flex flex-col items-center justify-center py-16 px-4 text-center max-w-2xl mx-auto">
      <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-red-600/30 to-rose-900/30 border border-red-500/40 flex items-center justify-center text-3xl shadow-xl mb-4">
        🎯
      </div>
      <h2 class="text-xl font-extrabold text-gray-100 mb-2">Hedef Odaklı YouTube Fırsat & Rakip Dedektörü</h2>
      <p class="text-xs text-gray-400 mb-6 leading-relaxed">
        Yukarıdaki kanal çubuğundan taramak istediğin YouTube kanallarını seçebilir (<strong class="text-red-300">@LeagueVoices</strong>, <strong class="text-amber-300">@Quaxanos</strong>, <strong class="text-purple-300">@pbetr</strong>, <strong class="text-cyan-300">@LeagueOfVoice</strong>, <strong class="text-rose-300">@turkish.videogamevoice</strong>, <strong class="text-emerald-300">@LoLNewsTr</strong>), ardından <strong>"Seçili Kanalları Canlı Tara"</strong> butonuna tıklayarak doğrudan içerik fırsatlarını analiz edebilirsin.
      </p>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full mb-8 text-left text-xs">
        <div class="bg-hextech-surface/80 p-3.5 rounded-xl border border-hextech-borderSubtle">
          <div class="font-bold text-red-300 flex items-center gap-1.5 mb-1">
            <span>⚡ Hızlı & Canlı Tarama</span>
          </div>
          <p class="text-[11px] text-gray-400">Rakiplerin son yüklediği videoları doğrudan YouTube üzerinden canlı çeker.</p>
        </div>
        <div class="bg-hextech-surface/80 p-3.5 rounded-xl border border-hextech-borderSubtle">
          <div class="font-bold text-amber-300 flex items-center gap-1.5 mb-1">
            <span>🔥 Efsanevi & PBE Fırsatları</span>
          </div>
          <p class="text-[11px] text-gray-400">Rakiplerin henüz çekmediği tüm özel dublajlı kostümleri anında listeler.</p>
        </div>
        <div class="bg-hextech-surface/80 p-3.5 rounded-xl border border-hextech-borderSubtle">
          <div class="font-bold text-cyan-300 flex items-center gap-1.5 mb-1">
            <span>🎬 Tek Tıkla Ses Çıkarma</span>
          </div>
          <p class="text-[11px] text-gray-400">Fırsat kartından tek tıkla ses çıkarma başlatıp DaVinci Timeline üretebilirsin.</p>
        </div>
      </div>

      <button onclick="runCompetitorScan(true)" class="flex items-center space-x-2 px-6 py-3 rounded-xl bg-gradient-to-r from-red-600 via-rose-600 to-red-700 hover:from-red-500 hover:to-rose-500 text-white font-extrabold text-sm shadow-2xl cursor-pointer transition-all hover:scale-105 active:scale-95">
        <i data-lucide="play" class="w-4 h-4 fill-white"></i>
        <span>Seçili Kanalları Şimdi Tara ve Fırsatları Keşfet</span>
      </button>
    </div>
  `;
  if (window.lucide) lucide.createIcons();
}

async function runCompetitorScan(forceRefresh = false) {
  const container = document.getElementById('competitors-content-container');
  const btn = document.getElementById('btn-scan-competitors');
  const selectedChannels = getSelectedCompetitorChannels();
  
  if (btn) btn.disabled = true;
  if (container) {
    container.innerHTML = `
      <div class="col-span-full py-24 text-center">
        <div class="inline-block w-8 h-8 border-4 border-red-500 border-t-transparent rounded-full animate-spin mb-3"></div>
        <div class="text-sm font-bold text-gray-200">${selectedChannels.length} Seçili YouTube Kanalı Canlı Taranıyor...</div>
        <div class="text-xs text-gray-500 mt-1 font-mono">Videolar analiz ediliyor • Çekilmeyen şampiyon ve kostüm fırsatları hesaplanıyor...</div>
      </div>
    `;
  }

  try {
    const chanParam = encodeURIComponent(selectedChannels.join(','));
    const url = `/api/competitor-analysis?channels=${chanParam}${forceRefresh ? '&refresh=1' : ''}`;
    const res = await fetch(url);
    const result = await res.json();
    if (result && result.status === 'success') {
      competitorAnalysisData = result.data;
      
      const badgeUncovered = document.getElementById('badge-uncovered-count');
      const badgeCovered = document.getElementById('badge-covered-count');
      if (badgeUncovered) badgeUncovered.innerText = (competitorAnalysisData.uncovered_champions || []).length;
      if (badgeCovered) badgeCovered.innerText = competitorAnalysisData.total_videos || 0;

      renderCompetitorView();
    } else {
      if (container) {
        container.innerHTML = `<div class="text-center py-16 text-rose-400 font-bold">❌ Analiz hatası: ${result.message || 'Bilinmeyen hata'}</div>`;
      }
    }
  } catch (err) {
    console.error("Competitor analysis error:", err);
    if (container) {
      container.innerHTML = `<div class="text-center py-16 text-rose-400 font-bold">❌ Bağlantı hatası: ${err}</div>`;
    }
  } finally {
    if (btn) btn.disabled = false;
  }
}

function setCompetitorSubTab(subTab) {
  competitorSubTab = subTab;
  ['opps', 'uncovered', 'covered'].forEach(t => {
    const btn = document.getElementById(`comp-tab-${t}`);
    if (!btn) return;
    if (t === subTab) {
      btn.className = 'px-3.5 py-1.5 rounded-md font-bold text-gray-200 bg-hextech-cardSelected shadow text-xs flex items-center space-x-1.5';
    } else {
      btn.className = 'px-3.5 py-1.5 rounded-md font-medium text-gray-400 hover:text-white text-xs flex items-center space-x-1.5';
    }
  });
  renderCompetitorView();
}

function filterCompetitorView(query) {
  competitorSearchQuery = query.toLowerCase().trim();
  renderCompetitorView();
}

function renderCompetitorView() {
  const container = document.getElementById('competitors-content-container');
  if (!container) return;
  if (!competitorAnalysisData) {
    renderCompetitorWelcome();
    return;
  }

  const q = competitorSearchQuery;
  const chanFilter = selectedCompetitorChannelFilter;

  if (competitorSubTab === 'opps') {
    let opps = competitorAnalysisData.legendary_opportunities || [];
    if (q) {
      opps = opps.filter(o => o.champion_name.toLowerCase().includes(q) || o.skin_name.toLowerCase().includes(q));
    }

    if (opps.length === 0) {
      container.innerHTML = '<div class="text-center py-16 text-gray-400 text-xs">Aramanıza uygun fırsat bulunamadı.</div>';
      return;
    }

    const cardsHtml = opps.map(item => {
      const relDate = item.release_date || 'Yeni';
      const safeChamp = item.champion_name.replace(/'/g, "\\'");
      const safeSkin = item.skin_name.replace(/'/g, "\\'");
      
      let splashUrl = item.splash_url || '';
      if (!splashUrl && typeof allSkinHubSkins !== 'undefined' && allSkinHubSkins.length > 0) {
        const found = allSkinHubSkins.find(s => s.name.toLowerCase() === item.skin_name.toLowerCase() || (s.champName === item.champion_name && s.id === item.skin_id));
        if (found) splashUrl = found.splashCentered || found.splashUncentered;
      }
      if (!splashUrl && item.skin_id) {
        const cKey = item.champ_key || item.champion_name.replace(/[^a-zA-Z0-9]/g, '');
        const sNum = item.skin_num || (item.skin_id % 1000);
        splashUrl = `https://ddragon.leagueoflegends.com/cdn/img/champion/splash/${cKey}_${sNum}.jpg`;
      }

      const cKey = item.champ_key || item.champion_name.replace(/[^a-zA-Z0-9]/g, '');
      const sNum = item.skin_num || (item.skin_id ? item.skin_id % 1000 : 0);
      const fallbackUrl = `https://ddragon.leagueoflegends.com/cdn/img/champion/splash/${cKey}_${sNum}.jpg`;

      return `
        <div class="glass-card rounded-2xl border border-hextech-borderSubtle hover:border-hextech-gold flex flex-col justify-between transition-all duration-300 hover:-translate-y-1.5 shadow-2xl overflow-hidden group">
          
          <!-- Top Splash Art Banner -->
          <div class="relative w-full aspect-video bg-[#050B14] overflow-hidden border-b border-hextech-borderSubtle/60">
            ${splashUrl ? `
              <img src="${splashUrl}" alt="${item.skin_name}" loading="lazy" class="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500" onerror="if(this.src!=='${fallbackUrl}'){this.src='${fallbackUrl}';}">
            ` : `
              <div class="w-full h-full flex items-center justify-center text-3xl">🎨</div>
            `}
            <div class="absolute inset-0 bg-gradient-to-t from-hextech-surface via-transparent to-black/30"></div>
            
            <div class="absolute top-2.5 left-2.5 flex items-center space-x-1.5">
              <span class="px-2 py-0.5 rounded-md text-[10px] font-black bg-gradient-to-r from-red-600 to-rose-600 text-white shadow-lg border border-red-400/30">
                🔥 ÇEKİLMEMİŞ FIRSAT
              </span>
            </div>

            <div class="absolute top-2.5 right-2.5">
              <span class="px-2 py-0.5 rounded-md text-[10px] font-extrabold bg-black/80 backdrop-blur-md text-amber-300 border border-amber-500/40">
                ${item.rarity}
              </span>
            </div>

            <div class="absolute bottom-2.5 left-3 right-3 flex items-center justify-between">
              <span class="text-xs font-black text-white drop-shadow-md truncate">
                ${item.champion_name}
              </span>
              <span class="text-[10px] text-gray-300 font-mono bg-black/60 px-1.5 py-0.5 rounded">
                📅 ${relDate}
              </span>
            </div>
          </div>

          <!-- Body Info -->
          <div class="p-4 space-y-3 flex-1 flex flex-col justify-between">
            <div>
              <h3 class="font-extrabold text-sm text-gray-100 group-hover:text-hextech-goldBright transition-colors line-clamp-1">
                ${item.skin_name}
              </h3>
              
              <div class="mt-2.5 flex flex-wrap gap-1.5">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 flex items-center gap-1">
                  <span>👑</span>
                  <span>Özel Yeni Dublaj</span>
                </span>
                <span class="px-2 py-0.5 rounded text-[10px] font-medium bg-hextech-surface text-gray-300 border border-hextech-borderSubtle font-mono">
                  ID: ${item.skin_id || 'Base'}
                </span>
              </div>
            </div>

            <!-- Action Button -->
            <button onclick="requestVoiceExtractionConfirm('${safeChamp}', '${safeSkin}')" class="w-full mt-3 py-2 px-3 rounded-xl bg-gradient-to-r from-hextech-gold to-amber-600 hover:from-amber-400 hover:to-amber-500 text-black font-extrabold text-xs flex items-center justify-center space-x-2 shadow-lg transition-transform hover:scale-[1.02] active:scale-95 cursor-pointer">
              <i data-lucide="download" class="w-3.5 h-3.5"></i>
              <span>Bu Fırsatın Seslerini Çıkar</span>
            </button>
          </div>
        </div>
      `;
    }).join('');

    container.innerHTML = `
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 pb-8">
        ${cardsHtml}
      </div>
    `;

  } else if (competitorSubTab === 'uncovered') {
    let list = competitorAnalysisData.uncovered_champions || [];
    if (q) {
      list = list.filter(c => c.champion_name.toLowerCase().includes(q) || c.skins.some(s => s.toLowerCase().includes(q)));
    }

    if (list.length === 0) {
      container.innerHTML = '<div class="text-center py-16 text-gray-400 text-xs">Eşleşen şampiyon bulunamadı.</div>';
      return;
    }

    const rowsHtml = list.map(c => {
      const safeChamp = c.champion_name.replace(/'/g, "\\'");
      return `
        <div class="glass-card rounded-xl p-4 border border-hextech-borderSubtle hover:border-amber-500/50 flex flex-col justify-between space-y-3">
          <div class="flex items-center justify-between pb-2 border-b border-hextech-borderSubtle/60">
            <div class="flex items-center space-x-2">
              <span class="text-lg">🛡️</span>
              <div>
                <h4 class="font-extrabold text-sm text-gray-100">${c.champion_name}</h4>
                <span class="text-[10px] text-gray-400 font-mono">${c.total_skins} Kostüm</span>
              </div>
            </div>
            ${c.has_legendary_vo ? `
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-300 border border-amber-800">
                ⭐ Efsanevi VO Var (${c.legendary_skins_count})
              </span>
            ` : `
              <span class="px-2 py-0.5 rounded text-[10px] font-medium bg-hextech-surface text-gray-400 border border-hextech-borderSubtle">
                Standart Dublaj
              </span>
            `}
          </div>

          <!-- Highlight skins -->
          <div class="space-y-1">
            <div class="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Kostümler:</div>
            <div class="flex flex-wrap gap-1">
              ${(c.highlight_skins || []).slice(0, 3).map(sk => `
                <span class="text-[10px] px-1.5 py-0.5 rounded bg-hextech-surface text-gray-300 border border-hextech-borderSubtle truncate max-w-[140px]" title="${sk.name}">
                  ${sk.name}
                </span>
              `).join('')}
              ${c.total_skins > 3 ? `<span class="text-[10px] px-1 py-0.5 rounded text-gray-500 font-mono">+${c.total_skins - 3}</span>` : ''}
            </div>
          </div>

          <button onclick="requestVoiceExtractionConfirm('${safeChamp}', null)" class="w-full py-1.5 rounded-lg bg-hextech-surface hover:bg-hextech-cardHover border border-hextech-borderSubtle text-hextech-goldBright hover:text-white font-bold text-xs flex items-center justify-center space-x-1.5 cursor-pointer">
            <span>Tüm Seslerini Çıkar →</span>
          </button>
        </div>
      `;
    }).join('');

    container.innerHTML = `
      <div class="pb-3 text-xs text-gray-400 flex items-center justify-between">
        <span>Rakipler tarafından YouTube'da hiç ses videosu yüklenmemiş <strong class="text-amber-300">${list.length}</strong> şampiyon listeleniyor:</span>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 pb-8">
        ${rowsHtml}
      </div>
    `;

  } else if (competitorSubTab === 'covered') {
    let coveredChamps = competitorAnalysisData.covered_champions || [];
    
    if (chanFilter && chanFilter !== 'ALL') {
      coveredChamps = coveredChamps.map(c => {
        const filteredVids = c.videos.filter(v => (v.channel || '').toLowerCase().includes(chanFilter.toLowerCase()));
        return {
          ...c,
          videos: filteredVids,
          video_count: filteredVids.length
        };
      }).filter(c => c.video_count > 0);
    }

    if (q) {
      coveredChamps = coveredChamps.filter(c => c.champion_name.toLowerCase().includes(q) || c.videos.some(v => v.title.toLowerCase().includes(q)));
    }

    if (coveredChamps.length === 0) {
      container.innerHTML = '<div class="text-center py-16 text-gray-400 text-xs">Eşleşen video bulunamadı.</div>';
      return;
    }

    const chunks = coveredChamps.map(c => {
      const safeChamp = c.champion_name.replace(/'/g, "\\'");
      const vidsHtml = c.videos.map(v => {
        const chName = v.channel || 'Kanal';
        return `
          <div class="bg-hextech-surface/80 rounded-lg p-2 border border-hextech-borderSubtle/50 flex items-center justify-between text-xs space-x-3">
            <div class="truncate">
              <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-950 text-red-300 border border-red-800 mr-2">
                ${chName}
              </span>
              <span class="text-gray-200 font-medium">${v.title}</span>
            </div>
            <a href="${v.url}" target="_blank" class="px-2.5 py-1 rounded bg-red-600 hover:bg-red-500 text-white font-bold text-[11px] shrink-0 flex items-center space-x-1">
              <i data-lucide="external-link" class="w-3 h-3"></i>
              <span>İzle</span>
            </a>
          </div>
        `;
      }).join('');

      return `
        <div class="glass-card rounded-xl p-4 border border-hextech-borderSubtle space-y-2">
          <div class="flex items-center justify-between pb-2 border-b border-hextech-borderSubtle/60">
            <div class="flex items-center space-x-2">
              <span class="text-sm font-extrabold text-hextech-goldBright">${c.champion_name}</span>
              <span class="text-xs text-gray-400 font-mono">(${c.video_count} video)</span>
            </div>
            <button onclick="requestVoiceExtractionConfirm('${safeChamp}', null)" class="text-xs text-hextech-cyan hover:underline font-semibold cursor-pointer">
              Kalan Kostümlerin Sesini Çıkar →
            </button>
          </div>
          <div class="space-y-1.5 pt-1">
            ${vidsHtml}
          </div>
        </div>
      `;
    }).join('');

    container.innerHTML = `
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pb-8">
        ${chunks}
      </div>
    `;
  }

  lucide.createIcons();
}

