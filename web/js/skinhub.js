// =========================================================================
// 8. DYNAMIC SKIN & PBE CDN HUB WITH REAL CHRONOLOGICAL DATES
// =========================================================================
let allSkinHubSkins = [];
let filteredSkinHubSkins = [];
let displayedSkinCount = 48;
let currentSkinSource = 'all';
let currentSkinRarity = 'all';
let currentSkinSort = 'date-desc';
let currentYearFilter = 'all';
let currentGridDensity = 'normal';
let skinHubLoading = false;

let activeModalSkin = null;
let activeSplashMode = 'centered';
let modalAudio = new Audio();

const CD_PBE_BASE = 'https://raw.communitydragon.org/pbe/plugins/rcp-be-lol-game-data/global';
const CD_LIVE_BASE = 'https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global';

const RARITY_MAP = {
  'kExalted': { name: 'Haşmetli', label: 'Haşmetli (Exalted)', color: 'border-rose-400 text-rose-300 bg-rose-950/70', badge: 'bg-gradient-to-r from-rose-500 via-purple-600 to-amber-400 text-white font-extrabold shadow-md', score: 110 },
  'Exalted': { name: 'Haşmetli', label: 'Haşmetli (Exalted)', color: 'border-rose-400 text-rose-300 bg-rose-950/70', badge: 'bg-gradient-to-r from-rose-500 via-purple-600 to-amber-400 text-white font-extrabold shadow-md', score: 110 },
  'kSanctum': { name: 'Haşmetli', label: 'Haşmetli (Exalted)', color: 'border-rose-400 text-rose-300 bg-rose-950/70', badge: 'bg-gradient-to-r from-rose-500 via-purple-600 to-amber-400 text-white font-extrabold shadow-md', score: 110 },
  'Sanctum': { name: 'Haşmetli', label: 'Haşmetli (Exalted)', color: 'border-rose-400 text-rose-300 bg-rose-950/70', badge: 'bg-gradient-to-r from-rose-500 via-purple-600 to-amber-400 text-white font-extrabold shadow-md', score: 110 },
  'kTranscendent': { name: 'Ulu', label: 'Ulu (Transcendent)', color: 'border-amber-300 text-amber-200 bg-amber-950/80', badge: 'bg-gradient-to-r from-amber-400 via-yellow-200 to-amber-500 text-gray-950 font-black shadow-lg', score: 105 },
  'Transcendent': { name: 'Ulu', label: 'Ulu (Transcendent)', color: 'border-amber-300 text-amber-200 bg-amber-950/80', badge: 'bg-gradient-to-r from-amber-400 via-yellow-200 to-amber-500 text-gray-950 font-black shadow-lg', score: 105 },
  'kUltimate': { name: 'Ebedi', label: 'Ebedi (Ultimate)', color: 'border-amber-400 text-amber-300 bg-amber-950/70', badge: 'bg-gradient-to-r from-amber-500 to-yellow-300 text-gray-950 font-bold', score: 100 },
  'Ultimate': { name: 'Ebedi', label: 'Ebedi (Ultimate)', color: 'border-amber-400 text-amber-300 bg-amber-950/70', badge: 'bg-gradient-to-r from-amber-500 to-yellow-300 text-gray-950 font-bold', score: 100 },
  'kMythic': { name: 'İhtişamlı', label: 'İhtişamlı / Prestij', color: 'border-purple-400 text-purple-300 bg-purple-950/70', badge: 'bg-gradient-to-r from-purple-500 to-pink-400 text-white font-bold', score: 90 },
  'Mythic': { name: 'İhtişamlı', label: 'İhtişamlı / Prestij', color: 'border-purple-400 text-purple-300 bg-purple-950/70', badge: 'bg-gradient-to-r from-purple-500 to-pink-400 text-white font-bold', score: 90 },
  'kLegendary': { name: 'Efsanevi', label: 'Efsanevi (1820 RP)', color: 'border-red-500 text-red-300 bg-red-950/70', badge: 'bg-gradient-to-r from-red-600 to-rose-400 text-white font-bold', score: 80 },
  'Legendary': { name: 'Efsanevi', label: 'Efsanevi (1820 RP)', color: 'border-red-500 text-red-300 bg-red-950/70', badge: 'bg-gradient-to-r from-red-600 to-rose-400 text-white font-bold', score: 80 },
  'kEpic': { name: 'Epik', label: 'Epik (1350 RP)', color: 'border-hextech-cyan text-cyan-300 bg-cyan-950/70', badge: 'bg-gradient-to-r from-cyan-600 to-teal-400 text-gray-950 font-bold', score: 70 },
  'Epic': { name: 'Epik', label: 'Epik (1350 RP)', color: 'border-hextech-cyan text-cyan-300 bg-cyan-950/70', badge: 'bg-gradient-to-r from-cyan-600 to-teal-400 text-gray-950 font-bold', score: 70 },
  'kExclusive': { name: 'Özel / Sandık', label: 'Özel / Sandık', color: 'border-indigo-400 text-indigo-300 bg-indigo-950/70', badge: 'bg-indigo-600 text-white font-bold', score: 60 },
  'Exclusive': { name: 'Özel / Sandık', label: 'Özel / Sandık', color: 'border-indigo-400 text-indigo-300 bg-indigo-950/70', badge: 'bg-indigo-600 text-white font-bold', score: 60 },
  'kNoRarity': { name: 'Standart', label: 'Standart / Klasik', color: 'border-gray-700 text-gray-400 bg-gray-900/60', badge: 'bg-gray-700 text-gray-200', score: 20 },
  'NoRarity': { name: 'Standart', label: 'Standart / Klasik', color: 'border-gray-700 text-gray-400 bg-gray-900/60', badge: 'bg-gray-700 text-gray-200', score: 20 }
};

let globalSkinVoMap = {};

function resolveCDragonUrl(path, isPBE = false) {
  if (!path) return '';
  const base = isPBE ? CD_PBE_BASE : CD_LIVE_BASE;
  const clean = path.replace('/lol-game-data/assets/', '').toLowerCase();
  return `${base}/default/${clean}`;
}

function formatTurkishDate(isoDate) {
  if (!isoDate || isoDate === '9999-12-31' || isoDate === 'Bilinmiyor') return '🧪 PBE';
  if (isoDate === '0000-00-00') return 'Klasik';
  
  const parts = isoDate.split('-');
  if (parts.length === 3) {
    const months = ['Oca', 'Şub', 'Mar', 'Nis', 'May', 'Haz', 'Tem', 'Ağu', 'Eyl', 'Eki', 'Kas', 'Ara'];
    const mIdx = parseInt(parts[1], 10) - 1;
    const mName = months[mIdx] || parts[1];
    return `${parseInt(parts[2], 10)} ${mName} ${parts[0]}`;
  }
  return isoDate;
}

async function initSkinHubData() {
  if (skinHubLoading || allSkinHubSkins.length > 0) return;
  skinHubLoading = true;

  const countBadge = document.getElementById('skinhub-count-badge');
  const grid = document.getElementById('skinhub-grid');
  
  if (countBadge) countBadge.innerHTML = '<span class="animate-pulse">🔄 Canlı CDN, PBE ve Riot Wwise Dublaj Verileri Çekiliyor...</span>';
  if (grid) grid.innerHTML = `
    <div class="col-span-full py-20 text-center">
      <div class="inline-block w-8 h-8 border-4 border-hextech-gold border-t-transparent rounded-full animate-spin mb-3"></div>
      <div class="text-sm font-bold text-gray-200">CommunityDragon & Riot Wwise Ses Analiz Akışı Yükleniyor...</div>
      <div class="text-xs text-gray-500 mt-1 font-mono">1600+ Kostüm • Wwise VO Bankaları & Dublaj Durumları Otomatik İndeksleniyor</div>
    </div>
  `;

  try {
    const [pbeChampsRes, pbeSkinsRes, liveSkinsRes, voMapRes] = await Promise.allSettled([
      fetch(`${CD_PBE_BASE}/tr_tr/v1/champion-summary.json`).then(r => r.json()),
      fetch(`${CD_PBE_BASE}/tr_tr/v1/skins.json`).then(r => r.json()),
      fetch(`${CD_LIVE_BASE}/tr_tr/v1/skins.json`).then(r => r.json()),
      fetch(`/api/all-vo-map`).then(r => r.json())
    ]);

    if (voMapRes.status === 'fulfilled' && voMapRes.value) {
      globalSkinVoMap = voMapRes.value;
    }

    const pbeChamps = pbeChampsRes.status === 'fulfilled' ? pbeChampsRes.value : [];
    const pbeSkins = pbeSkinsRes.status === 'fulfilled' ? pbeSkinsRes.value : {};
    const liveSkins = liveSkinsRes.status === 'fulfilled' ? liveSkinsRes.value : {};

    const champMap = {};
    if (Array.isArray(pbeChamps)) {
      pbeChamps.forEach(c => {
        if (c && c.id) {
          champMap[c.id] = {
            id: c.id,
            name: c.name || c.alias,
            alias: c.alias || '',
            title: c.title || ''
          };
        }
      });
    }

    const parsedSkins = [];
    const entries = (pbeSkins && typeof pbeSkins === 'object') ? Object.entries(pbeSkins) : [];

    if (entries.length > 0) {
      for (const [skinIdStr, skin] of entries) {
        if (!skin) continue;
        const skinId = parseInt(skinIdStr, 10);
        if (isNaN(skinId)) continue;

        const champId = Math.floor(skinId / 1000);
        const skinNum = skinId % 1000;
        const champInfo = champMap[champId] || { name: 'Şampiyon', alias: '', title: '' };

        const isLivePresent = Boolean(liveSkins && (liveSkins[skinIdStr] || liveSkins[skinId]));
        const isPbeOnly = !isLivePresent;

        const rawRarity = skin.rarity || 'kNoRarity';
        const rarityMeta = RARITY_MAP[rawRarity] || RARITY_MAP['kNoRarity'];

        let skinName = skin.name || `${champInfo.name} Kostümü`;
        if (skin.isBase || skinNum === 0) {
          skinName = `Varsayılan ${champInfo.name}`;
        }

        // Exact Real Release Date Resolution from preloaded database
        let releaseDate = null;
        if (window.LOL_SKINS_DATES && window.LOL_SKINS_DATES[String(skinId)]) {
          releaseDate = window.LOL_SKINS_DATES[String(skinId)];
        } else if (window.LOL_SKINS_DATES && window.LOL_SKINS_DATES[skinId]) {
          releaseDate = window.LOL_SKINS_DATES[skinId];
        }

        if (isPbeOnly) {
          releaseDate = '9999-12-31';
        } else if (!releaseDate || releaseDate === '0000-00-00' || releaseDate === 'Bilinmiyor') {
          releaseDate = skinNum === 0 ? '2009-02-21' : '2024-01-01';
        }

        const year = releaseDate.startsWith('9999') ? 2026 : parseInt(releaseDate.split('-')[0], 10) || 2024;

        const splashCentered = resolveCDragonUrl(skin.splashPath, isPbeOnly);
        const splashUncentered = resolveCDragonUrl(skin.uncenteredSplashPath, isPbeOnly) || splashCentered;
        const loadScreen = resolveCDragonUrl(skin.loadScreenPath, isPbeOnly) || splashCentered;
        const tilePath = resolveCDragonUrl(skin.tilePath, isPbeOnly);

        const chooseVo = `${CD_PBE_BASE}/tr_tr/v1/champion-choose-vo/${champId}.ogg`;
        const banVo = `${CD_PBE_BASE}/tr_tr/v1/champion-ban-vo/${champId}.ogg`;

        // Precise Wwise VO Map matching for this skin
        const cClean = (champInfo.name || '').toLowerCase().replace(/['\s._-]/g, '');
        const cAliasClean = (champInfo.alias || '').toLowerCase().replace(/['\s._-]/g, '');
        const voLookupKeys = [
          `${cClean}_${skinNum}`,
          `${cAliasClean}_${skinNum}`,
          `${cClean}_skin${skinNum}`,
          `${cAliasClean}_skin${skinNum}`,
          `${cClean}_skin${String(skinNum).padStart(2, '0')}`,
          `${cAliasClean}_skin${String(skinNum).padStart(2, '0')}`
        ];
        
        let voData = null;
        for (const vk of voLookupKeys) {
          if (globalSkinVoMap[vk]) {
            voData = globalSkinVoMap[vk];
            break;
          }
        }

        let hasCustomVo = false;
        let voiceType = 'shared_base';
        let voCount = 0;
        let voStatusShort = 'Özel Dublaj: YOK';
        let voStatusText = 'Temel dublajı kullanır';
        let isRecommended = false;

        if (skin.isBase || skinNum === 0) {
          hasCustomVo = false;
          voiceType = 'base';
          voCount = voData ? voData.vo_count : 71;
          voStatusShort = 'Orijinal Dublaj';
          voStatusText = 'Ana şampiyon Türkçe seslendirmesi';
          isRecommended = false;
        } else if (voData) {
          hasCustomVo = voData.has_custom_vo;
          voiceType = voData.voice_type;
          voCount = voData.vo_count;
          voStatusShort = voData.vo_status_short || (voiceType === 'unique' ? 'Özel Dublaj: VAR' : voiceType === 'filtered' ? 'Özel Efekt: VAR' : 'Özel Dublaj: KISMİ');
          voStatusText = voData.vo_status_text || '';
          isRecommended = Boolean(voData.is_recommended || voiceType === 'unique');
        } else {
          hasCustomVo = false;
          voiceType = 'shared_base';
          voCount = 0;
          voStatusShort = 'Özel Dublaj: YOK';
          voStatusText = 'Standart şampiyon repliklerini kullanır';
          isRecommended = false;
        }

        parsedSkins.push({
          id: skinId,
          champId: champId,
          champName: champInfo.name,
          champAlias: champInfo.alias,
          champTitle: champInfo.title,
          name: skinName,
          skinNum: skinNum,
          isBase: Boolean(skin.isBase || skinNum === 0),
          isPBE: isPbeOnly,
          rarityKey: rawRarity.replace('k', ''),
          rarityMeta: rarityMeta,
          description: skin.description || '',
          splashCentered: splashCentered,
          splashUncentered: splashUncentered,
          loadScreen: loadScreen,
          tilePath: tilePath,
          chooseVo: chooseVo,
          banVo: banVo,
          releaseDate: releaseDate,
          year: year,
          hasCustomVo: hasCustomVo,
          voiceType: voiceType,
          voCount: voCount,
          voStatusShort: voStatusShort,
          voStatusText: voStatusText,
          isRecommended: isRecommended
        });
      }
    }

    allSkinHubSkins = parsedSkins;
    skinHubLoading = false;
    onSkinHubFilterChange();

  } catch (err) {
    console.error("Skin Hub CDN Yükleme Hatası:", err);
    skinHubLoading = false;
    if (grid) {
      grid.innerHTML = `
        <div class="col-span-full py-16 text-center text-rose-400">
          <i data-lucide="wifi-off" class="w-10 h-10 mx-auto mb-2 opacity-80"></i>
          <div class="font-bold text-sm">CDN verileri alınamadı. İnternet bağlantınızı kontrol edin.</div>
          <button onclick="reloadSkinHubData()" class="mt-3 px-4 py-1.5 rounded-lg bg-hextech-card text-xs text-gray-200 border border-hextech-borderMedium">Yeniden Dene</button>
        </div>
      `;
      lucide.createIcons();
    }
  }
}

async function reloadSkinHubData() {
  allSkinHubSkins = [];
  try {
    await fetch('/api/sync-skins', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
  } catch (e) {
    console.warn("Sync skins hatası:", e);
  }
  await initSkinHubData();
}

function onSkinHubFilterChange() {
  const searchInput = document.getElementById('skinhub-search');
  const voSelect = document.getElementById('skinhub-vo-filter');
  const raritySelect = document.getElementById('skinhub-rarity');
  const sortSelect = document.getElementById('skinhub-sort');

  const query = searchInput ? searchInput.value.toLowerCase().trim() : '';
  const voFilter = voSelect ? voSelect.value : 'all';
  const rarity = raritySelect ? raritySelect.value : 'all';
  const sort = sortSelect ? sortSelect.value : 'date-desc';

  currentSkinRarity = rarity;
  currentSkinSort = sort;

  let result = allSkinHubSkins.filter(skin => {
    if (currentSkinSource === 'pbe' && !skin.isPBE) return false;
    if (currentSkinSource === 'live' && skin.isPBE) return false;

    // VO / Dubbing Filter
    if (voFilter === 'unique_vo' && !(skin.voiceType === 'unique' || skin.isRecommended)) return false;
    if (voFilter === 'filtered_vo' && skin.voiceType !== 'filtered') return false;
    if (voFilter === 'partial_vo' && skin.voiceType !== 'partial') return false;
    if (voFilter === 'no_custom_vo' && (skin.hasCustomVo || skin.isBase)) return false;

    // Rarity Filter
    if (rarity !== 'all') {
      if (rarity === 'Exalted' && !skin.rarityKey.includes('Exalted') && !skin.rarityKey.includes('Sanctum')) return false;
      if (rarity === 'Transcendent' && !skin.rarityKey.includes('Transcendent')) return false;
      if (rarity === 'Ultimate' && !skin.rarityKey.includes('Ultimate')) return false;
      if (rarity === 'Mythic' && !skin.rarityKey.includes('Mythic')) return false;
      if (rarity === 'Legendary' && !skin.rarityKey.includes('Legendary')) return false;
      if (rarity === 'Epic' && !skin.rarityKey.includes('Epic')) return false;
      if (rarity === 'Exclusive' && !skin.rarityKey.includes('Exclusive')) return false;
      if (rarity === 'Standart' && (skin.rarityKey.includes('Epic') || skin.rarityKey.includes('Legendary') || skin.rarityKey.includes('Mythic') || skin.rarityKey.includes('Ultimate') || skin.rarityKey.includes('Transcendent') || skin.rarityKey.includes('Exalted') || skin.rarityKey.includes('Sanctum'))) return false;
    }

    if (currentYearFilter !== 'all') {
      if (currentYearFilter === 'older') {
        if (skin.year >= 2023) return false;
      } else {
        if (skin.year !== parseInt(currentYearFilter, 10)) return false;
      }
    }

    if (query) {
      const matchName = skin.name.toLowerCase().includes(query);
      const matchChamp = skin.champName.toLowerCase().includes(query) || skin.champAlias.toLowerCase().includes(query);
      const matchId = String(skin.id).includes(query);
      const matchVo = (skin.voStatusShort || '').toLowerCase().includes(query) || (skin.voStatusText || '').toLowerCase().includes(query);
      if (!matchName && !matchChamp && !matchId && !matchVo) return false;
    }

    return true;
  });

  result.sort((a, b) => {
    const isPbeA = Boolean(a.isPBE || a.releaseDate === '9999-12-31');
    const isPbeB = Boolean(b.isPBE || b.releaseDate === '9999-12-31');

    if (sort === 'recommended') {
      const recA = a.isRecommended ? 1 : 0;
      const recB = b.isRecommended ? 1 : 0;
      if (recA !== recB) return recB - recA;

      const custA = a.hasCustomVo ? 1 : 0;
      const custB = b.hasCustomVo ? 1 : 0;
      if (custA !== custB) return custB - custA;

      return (b.voCount || 0) - (a.voCount || 0);
    } else if (sort === 'vo-desc') {
      return (b.voCount || 0) - (a.voCount || 0);
    } else if (sort === 'date-desc') {
      // 1. PBE unreleased skins always at the top
      if (isPbeA !== isPbeB) return isPbeB ? 1 : -1;
      const dA = (a.releaseDate && a.releaseDate.length === 10 && a.releaseDate[0].match(/\d/)) ? a.releaseDate : '1970-01-01';
      const dB = (b.releaseDate && b.releaseDate.length === 10 && b.releaseDate[0].match(/\d/)) ? b.releaseDate : '1970-01-01';
      if (dA !== dB) {
        return dB.localeCompare(dA);
      }
      return b.id - a.id;
    } else if (sort === 'date-asc') {
      // 1. PBE unreleased skins at the bottom
      if (isPbeA !== isPbeB) return isPbeA ? 1 : -1;
      const dA = (a.releaseDate && a.releaseDate.length === 10 && a.releaseDate[0].match(/\d/)) ? a.releaseDate : '1970-01-01';
      const dB = (b.releaseDate && b.releaseDate.length === 10 && b.releaseDate[0].match(/\d/)) ? b.releaseDate : '1970-01-01';
      if (dA !== dB) {
        return dA.localeCompare(dB);
      }
      return a.id - b.id;
    } else if (sort === 'rarity-desc') {
      if (b.rarityMeta.score !== a.rarityMeta.score) {
        return b.rarityMeta.score - a.rarityMeta.score;
      }
      return (b.releaseDate || '').localeCompare(a.releaseDate || '');
    } else if (sort === 'name-asc') {
      return a.name.localeCompare(b.name, 'tr');
    } else if (sort === 'name-desc') {
      return b.name.localeCompare(a.name, 'tr');
    } else if (sort === 'champ-asc') {
      return a.champName.localeCompare(b.champName, 'tr');
    }
    return 0;
  });

  filteredSkinHubSkins = result;
  displayedSkinCount = 48;
  renderSkinHubGrid();
}

function setSkinSourceFilter(source) {
  currentSkinSource = source;
  const btns = {
    all: document.getElementById('src-all'),
    pbe: document.getElementById('src-pbe'),
    live: document.getElementById('src-live')
  };

  Object.keys(btns).forEach(k => {
    if (!btns[k]) return;
    if (k === source) {
      btns[k].className = 'px-3 py-1.5 rounded-md font-bold text-gray-200 bg-hextech-cardSelected shadow text-xs';
    } else {
      btns[k].className = 'px-3 py-1.5 rounded-md font-medium text-gray-400 hover:text-white text-xs';
    }
  });

  onSkinHubFilterChange();
}

function setYearFilter(year) {
  currentYearFilter = year;
  document.querySelectorAll('.year-filter-btn').forEach(btn => {
    const y = btn.getAttribute('data-year');
    if (y === year) {
      btn.className = 'year-filter-btn px-2 py-0.5 rounded text-[11px] font-semibold bg-hextech-cardSelected text-hextech-cyanNeon border border-hextech-cyanBorder';
    } else {
      btn.className = 'year-filter-btn px-2 py-0.5 rounded text-[11px] text-gray-400 hover:text-white';
    }
  });
  onSkinHubFilterChange();
}

function setGridDensity(mode) {
  currentGridDensity = mode;
  localStorage.setItem('skinhub_grid_density', mode);

  ['mini', 'normal', 'large', 'list'].forEach(m => {
    const btn = document.getElementById(`grid-mode-${m}`);
    if (!btn) return;
    if (m === mode) {
      btn.className = 'px-2 py-1 rounded text-[11px] font-bold text-gray-200 bg-hextech-cardSelected shadow';
    } else {
      btn.className = 'px-2 py-1 rounded text-[11px] text-gray-400 hover:text-white';
    }
  });

  const grid = document.getElementById('skinhub-grid');
  if (grid) {
    grid.className = 'pb-8';
    if (mode === 'mini') {
      grid.classList.add('grid', 'grid-cols-2', 'sm:grid-cols-4', 'md:grid-cols-6', 'lg:grid-cols-8', 'xl:grid-cols-10', 'gap-2.5');
    } else if (mode === 'large') {
      grid.classList.add('grid', 'grid-cols-1', 'sm:grid-cols-2', 'md:grid-cols-2', 'lg:grid-cols-3', 'xl:grid-cols-4', 'gap-5');
    } else if (mode === 'list') {
      grid.classList.add('grid', 'grid-cols-1', 'gap-2');
    } else {
      grid.classList.add('grid', 'grid-cols-1', 'sm:grid-cols-2', 'md:grid-cols-3', 'lg:grid-cols-4', 'xl:grid-cols-5', '2xl:grid-cols-6', 'gap-4');
    }
  }

  renderSkinHubGrid();
}

function restoreGridDensity() {
  const saved = localStorage.getItem('skinhub_grid_density') || 'normal';
  setGridDensity(saved);
}

function renderSkinHubGrid() {
  const grid = document.getElementById('skinhub-grid');
  const emptyState = document.getElementById('skinhub-empty');
  const countBadge = document.getElementById('skinhub-count-badge');

  if (!grid) return;

  const total = filteredSkinHubSkins.length;
  if (countBadge) {
    const pbeCount = filteredSkinHubSkins.filter(s => s.isPBE).length;
    const customVoCount = filteredSkinHubSkins.filter(s => s.voiceType === 'unique' || s.isRecommended).length;
    countBadge.innerHTML = `✨ <strong>${total.toLocaleString('tr-TR')}</strong> Kostüm (${pbeCount} PBE • <span class="text-emerald-400 font-bold">${customVoCount} Özel Dublaj</span>)`;
  }

  if (total === 0) {
    grid.innerHTML = '';
    if (emptyState) emptyState.classList.remove('hidden');
    return;
  }

  if (emptyState) emptyState.classList.add('hidden');

  const isListMode = currentGridDensity === 'list';
  const slice = filteredSkinHubSkins.slice(0, displayedSkinCount);
  const htmlChunks = slice.map(skin => {
    const rarity = skin.rarityMeta;
    const formattedDate = formatTurkishDate(skin.releaseDate);
    const pbeBadge = skin.isPBE 
      ? `<span class="px-2 py-0.5 rounded-md bg-purple-900/90 text-purple-200 border border-purple-400/50 text-[10px] font-extrabold flex items-center gap-1 shadow-lg backdrop-blur-sm animate-pulse">🧪 PBE</span>` 
      : '';

    // Voice Status Banner for Dynamic SkinHub Cards
    let voBadgeHtml = '';
    if (skin.voiceType === 'unique' || skin.isRecommended) {
      voBadgeHtml = `
        <div class="mt-1.5 px-2 py-0.8 rounded-md bg-emerald-950/80 border border-emerald-500/50 flex items-center justify-between text-[10px] shadow-sm">
          <span class="font-bold text-emerald-300 flex items-center gap-1 truncate">
            <i data-lucide="crown" class="w-3 h-3 text-emerald-400 shrink-0"></i>
            <span class="truncate">Özel Dublaj: VAR</span>
          </span>
          <span class="font-mono font-extrabold text-emerald-200 text-[9px] bg-emerald-900/90 px-1.5 py-0.2 rounded border border-emerald-500/40 shrink-0">${skin.voCount} Replik</span>
        </div>
      `;
    } else if (skin.voiceType === 'filtered') {
      voBadgeHtml = `
        <div class="mt-1.5 px-2 py-0.8 rounded-md bg-cyan-950/80 border border-cyan-500/50 flex items-center justify-between text-[10px] shadow-sm">
          <span class="font-bold text-cyan-300 flex items-center gap-1 truncate">
            <i data-lucide="sliders" class="w-3 h-3 text-cyan-400 shrink-0"></i>
            <span class="truncate">Özel Efekt: VAR</span>
          </span>
          <span class="font-mono font-extrabold text-cyan-200 text-[9px] bg-cyan-900/90 px-1.5 py-0.2 rounded border border-cyan-500/40 shrink-0">${skin.voCount} Replik</span>
        </div>
      `;
    } else if (skin.voiceType === 'partial') {
      voBadgeHtml = `
        <div class="mt-1.5 px-2 py-0.8 rounded-md bg-amber-950/60 border border-amber-500/40 flex items-center justify-between text-[10px] shadow-sm">
          <span class="font-bold text-amber-300 flex items-center gap-1 truncate">
            <i data-lucide="volume-2" class="w-3 h-3 text-amber-400 shrink-0"></i>
            <span class="truncate">Özel Dublaj: KISMİ</span>
          </span>
          <span class="font-mono font-extrabold text-amber-200 text-[9px] bg-amber-900/90 px-1.5 py-0.2 rounded border border-amber-500/40 shrink-0">${skin.voCount} Replik</span>
        </div>
      `;
    } else if (skin.isBase || skin.voiceType === 'base') {
      voBadgeHtml = `
        <div class="mt-1.5 px-2 py-0.8 rounded-md bg-amber-950/40 border border-amber-500/30 flex items-center justify-between text-[10px]">
          <span class="font-bold text-amber-300 flex items-center gap-1 truncate">
            <i data-lucide="mic" class="w-3 h-3 text-amber-400 shrink-0"></i>
            <span class="truncate">Orijinal Dublaj</span>
          </span>
          <span class="font-mono text-amber-200 text-[9px] bg-amber-950 px-1.5 py-0.2 rounded border border-amber-500/30 shrink-0">${skin.voCount || 71} Replik</span>
        </div>
      `;
    } else {
      voBadgeHtml = `
        <div class="mt-1.5 px-2 py-0.8 rounded-md bg-gray-900/80 border border-gray-700/60 flex items-center justify-between text-[10px]">
          <span class="font-medium text-rose-300/90 flex items-center gap-1 truncate">
            <i data-lucide="slash" class="w-3 h-3 text-rose-400/80 shrink-0"></i>
            <span class="truncate">Özel Dublaj: YOK</span>
          </span>
          <span class="font-mono text-gray-400 text-[9px] bg-gray-800 px-1.5 py-0.2 rounded border border-gray-700 shrink-0">Temel Ses</span>
        </div>
      `;
    }

    if (isListMode) {
      return `
        <div class="glass-card group relative rounded-xl border ${skin.isPBE ? 'border-purple-500/60' : skin.hasCustomVo ? 'border-emerald-500/50' : 'border-hextech-borderSubtle'} hover:border-hextech-gold p-2.5 flex items-center justify-between transition hover:-translate-y-0.5 cursor-pointer" onclick="openSkinModal(${skin.id})">
          <div class="flex items-center space-x-3 truncate">
            <img src="${skin.splashCentered}" alt="${skin.name}" loading="lazy" class="w-16 h-10 object-cover rounded-lg shrink-0">
            <div class="truncate">
              <div class="text-xs font-extrabold text-gray-100 group-hover:text-hextech-goldBright truncate">${skin.name}</div>
              <div class="text-[10px] text-gray-400 flex items-center space-x-2">
                <span>🛡️ ${skin.champName}</span>
                <span>•</span>
                <span class="text-hextech-gold">${formattedDate}</span>
                <span>•</span>
                <span class="${skin.hasCustomVo ? 'text-emerald-400 font-bold' : 'text-gray-500'}">${skin.voStatusShort}</span>
              </div>
            </div>
          </div>
          <div class="flex items-center space-x-3 shrink-0">
            <span class="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${rarity.badge}">${rarity.name}</span>
            <button onclick="event.stopPropagation(); playQuickAudio('${skin.chooseVo}', '${skin.champName}')" class="p-1.5 rounded-lg bg-hextech-cyan hover:bg-hextech-cyanNeon text-gray-950">
              <i data-lucide="volume-2" class="w-3.5 h-3.5"></i>
            </button>
          </div>
        </div>
      `;
    }

    return `
      <div class="glass-card group relative rounded-xl border ${skin.isPBE ? 'border-purple-500/60 shadow-purple-950/40' : skin.hasCustomVo ? 'border-emerald-500/50 shadow-emerald-950/20' : 'border-hextech-borderSubtle'} hover:border-hextech-gold overflow-hidden flex flex-col justify-between transition-all duration-200 hover:-translate-y-1 hover:shadow-2xl cursor-pointer" onclick="openSkinModal(${skin.id})">
        
        <div>
          <div class="relative w-full aspect-video bg-[#030712] overflow-hidden">
            <img 
              src="${skin.splashCentered}" 
              alt="${skin.name}" 
              loading="lazy" 
              onerror="this.onerror=null; this.src='https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-splashes/${skin.champId}/${skin.id}.jpg';" 
              class="w-full h-full object-cover object-center group-hover:scale-108 transition-transform duration-300"
            >

            <div class="absolute inset-x-0 top-0 p-2 flex items-center justify-between bg-gradient-to-b from-black/80 via-black/30 to-transparent">
              <span class="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${rarity.badge} shadow-md tracking-wider">
                ${rarity.name}
              </span>
              ${pbeBadge}
            </div>

            <div class="absolute inset-x-0 bottom-0 p-2 bg-gradient-to-t from-black/90 via-black/40 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-between">
              <span class="text-[10px] text-hextech-cyan font-mono">${skin.champName}</span>
              <div class="flex items-center space-x-1.5" onclick="event.stopPropagation()">
                <button onclick="playQuickAudio('${skin.chooseVo}', '${skin.champName}')" class="p-1.5 rounded-lg bg-hextech-cyan hover:bg-hextech-cyanNeon text-gray-950 shadow" title="Seçim Sesi Dinle">
                  <i data-lucide="volume-2" class="w-3.5 h-3.5"></i>
                </button>
              </div>
            </div>
          </div>

          <div class="p-2.5 bg-hextech-surface/80">
            <h3 class="text-xs font-extrabold text-gray-100 group-hover:text-hextech-goldBright line-clamp-1 transition-colors" title="${skin.name}">
              ${skin.name}
            </h3>
            <div class="text-[10px] text-gray-400 mt-1 flex items-center justify-between">
              <span>${skin.champName}</span>
              <span class="font-mono text-[10px] text-hextech-gold">${formattedDate}</span>
            </div>
            ${voBadgeHtml}
          </div>
        </div>

      </div>
    `;
  });

  grid.innerHTML = htmlChunks.join('');
  lucide.createIcons();
}

const skinGridContainer = document.getElementById('skinhub-grid-container');
if (skinGridContainer) {
  skinGridContainer.addEventListener('scroll', () => {
    if (skinGridContainer.scrollTop + skinGridContainer.clientHeight >= skinGridContainer.scrollHeight - 300) {
      if (displayedSkinCount < filteredSkinHubSkins.length) {
        displayedSkinCount += 36;
        renderSkinHubGrid();
      }
    }
  });
}

function playQuickAudio(url, champName) {
  modalAudio.pause();
  modalAudio.src = url;
  modalAudio.play().then(() => {
    onLogMessage(`🔊 [${champName}] Seçim sesi çalınıyor...`);
  }).catch(e => {
    console.warn("Audio play blocked/error:", e);
  });
}

// Skin Details Modal
function openSkinModal(skinId) {
  const skin = allSkinHubSkins.find(s => s.id === skinId);
  if (!skin) return;

  activeModalSkin = skin;
  activeSplashMode = 'centered';

  const modal = document.getElementById('skin-modal');
  const nameElem = document.getElementById('modal-skin-name');
  const champElem = document.getElementById('modal-champ-name');
  const rarityBadge = document.getElementById('modal-rarity-badge');
  const loreElem = document.getElementById('modal-lore');
  const idElem = document.getElementById('modal-meta-id');
  const dateElem = document.getElementById('modal-meta-date');
  const voElem = document.getElementById('modal-meta-vo');
  const statusElem = document.getElementById('modal-meta-status');

  if (nameElem) nameElem.innerText = skin.name;
  if (champElem) champElem.innerText = `${skin.champName} • ${skin.champTitle || "Runeterra Şampiyonu"}`;
  
  if (rarityBadge) {
    rarityBadge.className = `px-2.5 py-0.5 rounded text-[11px] font-extrabold uppercase ${skin.rarityMeta.badge}`;
    rarityBadge.innerText = skin.rarityMeta.name;
  }

  if (loreElem) loreElem.innerText = skin.description || `${skin.name} için resmi lore hikaye açıklaması henüz yayınlanmadı veya klasik model.`;
  if (idElem) idElem.innerText = skin.id;
  if (dateElem) dateElem.innerText = formatTurkishDate(skin.releaseDate);
  
  if (voElem) {
    if (skin.voiceType === 'unique' || skin.isRecommended) {
      voElem.className = 'text-emerald-300 font-extrabold';
      voElem.innerText = `👑 Özel Dublaj: VAR (${skin.voCount} Özgün Replik)`;
    } else if (skin.voiceType === 'filtered') {
      voElem.className = 'text-cyan-300 font-bold';
      voElem.innerText = `🎛️ Özel Efekt: VAR (${skin.voCount} Filtreli Replik)`;
    } else if (skin.voiceType === 'partial') {
      voElem.className = 'text-amber-300 font-bold';
      voElem.innerText = `⚡ Özel Dublaj: KISMİ (${skin.voCount} Ek Ses)`;
    } else if (skin.isBase || skin.voiceType === 'base') {
      voElem.className = 'text-amber-300/90 font-bold';
      voElem.innerText = `🎮 Orijinal Dublaj (${skin.voCount || 71} Replik)`;
    } else {
      voElem.className = 'text-gray-400 font-medium';
      voElem.innerText = '❌ Özel Dublaj: YOK (Temel Ses)';
    }
  }

  if (statusElem) {
    if (skin.isPBE) {
      statusElem.className = 'text-purple-400 font-bold';
      statusElem.innerText = '🧪 PBE Erken Erişim (Canlıya Çıkmadı)';
    } else {
      statusElem.className = 'text-emerald-400 font-bold';
      statusElem.innerText = '⚡ Canlı Sunucularda Mevcut';
    }
  }

  updateModalSplashView();

  if (modal) modal.classList.remove('hidden');
  lucide.createIcons();
}

function closeSkinModal() {
  const modal = document.getElementById('skin-modal');
  if (modal) modal.classList.add('hidden');
  modalAudio.pause();
}

function setModalSplashMode(mode) {
  activeSplashMode = mode;
  const modes = ['centered', 'uncentered', 'loadscreen'];
  modes.forEach(m => {
    const btn = document.getElementById(`splash-mode-${m}`);
    if (!btn) return;
    if (m === mode) {
      btn.className = 'px-2.5 py-1 rounded bg-hextech-cyan text-gray-950 font-bold';
    } else {
      btn.className = 'px-2.5 py-1 rounded text-gray-300 hover:text-white';
    }
  });
  updateModalSplashView();
}

function updateModalSplashView() {
  if (!activeModalSkin) return;
  const img = document.getElementById('modal-splash-img');
  if (!img) return;

  if (activeSplashMode === 'centered') {
    img.src = activeModalSkin.splashCentered;
    img.className = 'w-full h-full object-cover object-center transition-all duration-300';
  } else if (activeSplashMode === 'uncentered') {
    img.src = activeModalSkin.splashUncentered;
    img.className = 'w-full h-full object-cover object-center transition-all duration-300';
  } else if (activeSplashMode === 'loadscreen') {
    img.src = activeModalSkin.loadScreen;
    img.className = 'w-auto h-full mx-auto object-contain transition-all duration-300';
  }
}

function playModalAudio(type) {
  if (!activeModalSkin) return;
  const url = type === 'choose' ? activeModalSkin.chooseVo : activeModalSkin.banVo;
  const status = document.getElementById('modal-vo-status');

  modalAudio.pause();
  modalAudio.src = url;
  if (status) status.innerText = `Çalınıyor: ${type.toUpperCase()} VO...`;

  modalAudio.play().then(() => {
    if (status) status.innerText = `Oynatılıyor: ${activeModalSkin.champName} (${type})`;
  }).catch(err => {
    if (status) status.innerText = `Ses yüklenemedi: ${err}`;
  });
}

async function downloadCurrentModalSplash() {
  if (!activeModalSkin) return;
  const url = activeSplashMode === 'uncentered' ? activeModalSkin.splashUncentered : activeModalSkin.splashCentered;
  const filename = `${activeModalSkin.champName}_${activeModalSkin.name.replace(/ /g, '_')}_${activeSplashMode}.jpg`;

  try {
    const res = await fetch('/api/download-cdn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url, folder_name: 'Splashes', filename: filename })
    });
    const data = await res.json();
    if (data.status === 'success') {
      alert(`✅ 4K Splash Art başarıyla indirildi!\nKlasör: Champions/_CDN_Downloads/Splashes/\nDosya: ${filename}`);
    } else {
      alert(`❌ İndirme hatası: ${data.message}`);
    }
  } catch (err) {
    alert(`❌ İndirme hatası: ${err}`);
  }
}

async function downloadModalAudio(type) {
  if (!activeModalSkin) return;
  const url = type === 'choose' ? activeModalSkin.chooseVo : activeModalSkin.banVo;
  const filename = `${activeModalSkin.champName}_${type}_vo.ogg`;

  try {
    const res = await fetch('/api/download-cdn', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url, folder_name: 'Audio', filename: filename })
    });
    const data = await res.json();
    if (data.status === 'success') {
      alert(`✅ Ses dosyası indirildi!\nKlasör: Champions/_CDN_Downloads/Audio/\nDosya: ${filename}`);
    } else {
      alert(`❌ İndirme hatası: ${data.message}`);
    }
  } catch (err) {
    alert(`❌ İndirme hatası: ${err}`);
  }
}

