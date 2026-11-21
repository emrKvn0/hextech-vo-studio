// =========================================================================
// 10. REVERSE REFERENCES DETECTOR (WITH DUAL FILTERING & SHIFT/CTRL SELECTION)
// =========================================================================
let selectedRefSkin = 'ALL';
let selectedRefSpeakerType = 'all'; // 'all', 'base_only', 'skins_only'
let refSkinsCache = [];
let refSelectedAudioPaths = new Set();
let refAudioFlatList = []; // Array of { index, path, name, isBase }
let lastSelectedRefIndex = -1;

async function loadRefChampions() {
  try {
    const res = await fetch('/api/champions');
    const champs = await res.json();
    allChampions = champs;
    const countEl = document.getElementById('ref-champ-count');
    if (countEl) countEl.innerText = champs.length;
    renderRefChampions(champs);
    if (champs.length > 0 && !selectedRefChampion) {
      selectRefChampion(champs[0]);
    }
  } catch (err) {
    console.error("Failed to load ref champs:", err);
  }
}

function renderRefChampions(champs) {
  const container = document.getElementById('ref-champions-list');
  if (!container) return;
  container.innerHTML = '';

  champs.forEach(ch => {
    const isSelected = ch === selectedRefChampion;
    const btn = document.createElement('button');
    btn.className = `w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs font-semibold cursor-pointer text-left transition-all ${
      isSelected 
        ? 'bg-hextech-cardSelected text-hextech-cyanNeon border border-hextech-cyanBorder shadow' 
        : 'text-gray-300 hover:bg-hextech-cardHover hover:text-white border border-transparent'
    }`;
    btn.innerHTML = `
      <div class="flex items-center space-x-2 truncate">
        <span class="text-sm">🎯</span>
        <span class="truncate">${ch}</span>
      </div>
      <i data-lucide="chevron-right" class="w-3.5 h-3.5 opacity-40"></i>
    `;
    btn.onclick = () => selectRefChampion(ch);
    container.appendChild(btn);
  });

  lucide.createIcons();
}

function filterRefChampions(query) {
  const q = query.toLowerCase().trim();
  const filtered = allChampions.filter(c => c.toLowerCase().includes(q));
  const countEl = document.getElementById('ref-champ-count');
  if (countEl) countEl.innerText = filtered.length;
  renderRefChampions(filtered);
}

async function selectRefChampion(ch) {
  selectedRefChampion = ch;
  selectedRefSkin = 'ALL';
  clearRefAudioSelection();

  const badgeEl = document.getElementById('ref-selected-champ-badge');
  if (badgeEl) badgeEl.innerText = ch;

  const activeTag = document.getElementById('ref-active-filter-tag');
  if (activeTag) activeTag.innerText = 'Tüm Kostümler';

  const btnScanLabel = document.getElementById('btn-scan-ref-label');
  if (btnScanLabel) btnScanLabel.innerText = 'Tüm Atıfları Tara & Çıkar';

  renderRefChampions(allChampions.filter(c => {
    const refSearchEl = document.getElementById('ref-search');
    const q = refSearchEl ? refSearchEl.value.toLowerCase().trim() : '';
    return c.toLowerCase().includes(q);
  }));

  await loadRefSkins(ch);
  await refreshReferencesTree();
}

async function loadRefSkins(championName) {
  const bar = document.getElementById('ref-skins-bar');
  if (!bar) return;
  bar.innerHTML = '<div class="text-xs text-gray-500 font-mono py-1 px-2 animate-pulse">Kostümler yükleniyor...</div>';

  try {
    const res = await fetch(`/api/skins?champion=${encodeURIComponent(championName)}`);
    const skins = await res.json();
    refSkinsCache = skins || [];
    renderRefSkins();
  } catch (err) {
    console.error("Failed to load ref skins:", err);
    refSkinsCache = [];
    bar.innerHTML = '<div class="text-xs text-gray-500 py-1">Kostümler yüklenemedi.</div>';
  }
}

function renderRefSkins() {
  const bar = document.getElementById('ref-skins-bar');
  if (!bar) return;
  bar.innerHTML = '';

  if (!refSkinsCache || refSkinsCache.length === 0) {
    const btnAll = document.createElement('button');
    btnAll.className = 'px-3 py-1.5 rounded-lg text-xs font-bold bg-hextech-cardSelected text-hextech-goldBright border border-hextech-gold/80 shrink-0';
    btnAll.innerHTML = '🌟 Tüm Kostümler (Full Paket)';
    bar.appendChild(btnAll);
    return;
  }

  refSkinsCache.forEach(sk => {
    const isSelected = sk.value === selectedRefSkin;
    const btn = document.createElement('button');
    const label = sk.display_name || sk.label || sk.value;
    
    btn.className = `px-3 py-1.5 rounded-lg text-xs font-bold shrink-0 transition-all cursor-pointer flex items-center space-x-1.5 ${
      isSelected
        ? 'bg-hextech-cardSelected text-hextech-cyanNeon border border-hextech-cyanNeon shadow-md ring-1 ring-hextech-cyan/40'
        : 'bg-hextech-card hover:bg-hextech-cardHover text-gray-300 hover:text-white border border-hextech-borderSubtle hover:border-hextech-gold/50'
    }`;
    
    let icon = '🎭';
    if (sk.value === 'ALL') icon = '🌟';
    else if (sk.num === 0 || (sk.value && sk.value.toLowerCase().includes('varsayilan'))) icon = '🛡️';

    btn.innerHTML = `<span>${icon}</span><span class="whitespace-nowrap">${label}</span>`;
    btn.onclick = () => selectRefSkin(sk.value, label);
    bar.appendChild(btn);
  });
}

async function selectRefSkin(skinVal, skinLabel) {
  selectedRefSkin = skinVal;

  const activeTag = document.getElementById('ref-active-filter-tag');
  if (activeTag) {
    activeTag.innerText = skinVal === 'ALL' ? 'Tüm Kostümler' : (skinLabel || skinVal);
  }

  const btnScanLabel = document.getElementById('btn-scan-ref-label');
  if (btnScanLabel) {
    btnScanLabel.innerText = skinVal === 'ALL' 
      ? 'Tüm Atıfları Tara & Çıkar' 
      : `${skinLabel || skinVal} Atıflarını Çıkar`;
  }

  renderRefSkins();
  await refreshReferencesTree();
}

function setRefSpeakerType(type) {
  selectedRefSpeakerType = type;
  
  const bAll = document.getElementById('ref-speaker-filter-all');
  const bBase = document.getElementById('ref-speaker-filter-base');
  const bSkins = document.getElementById('ref-speaker-filter-skins');

  const activeClass = 'px-2.5 py-1 text-[11px] font-bold rounded-md transition-all cursor-pointer bg-hextech-cardSelected text-hextech-goldBright border border-hextech-gold/60 shadow';
  const inactiveClass = 'px-2.5 py-1 text-[11px] font-bold rounded-md transition-all cursor-pointer text-gray-400 hover:text-white border border-transparent';

  if (bAll) bAll.className = type === 'all' ? activeClass : inactiveClass;
  if (bBase) bBase.className = type === 'base_only' ? activeClass : inactiveClass;
  if (bSkins) bSkins.className = type === 'skins_only' ? activeClass : inactiveClass;

  refreshReferencesTree();
}

async function refreshReferencesTree() {
  if (!selectedRefChampion) return;
  const container = document.getElementById('references-tree');
  if (!container) return;
  container.innerHTML = '<div class="text-center py-8 text-gray-500 text-xs font-mono animate-pulse">Atıf kütüphanesi taranıyor...</div>';

  try {
    const url = `/api/references-tree?target=${encodeURIComponent(selectedRefChampion)}&skin=${encodeURIComponent(selectedRefSkin)}&speaker_type=${encodeURIComponent(selectedRefSpeakerType)}`;
    const res = await fetch(url);
    const tree = await res.json();

    refAudioFlatList = [];

    if (!tree || tree.length === 0) {
      const skinDesc = selectedRefSkin === 'ALL' ? '' : ` (${selectedRefSkin.replace('_', ' ')})`;
      const spkDesc = selectedRefSpeakerType === 'base_only' ? ' [Yalnızca Varsayılan Şampiyonlar]' : (selectedRefSpeakerType === 'skins_only' ? ' [Yalnızca Kostümlü Şampiyonlar]' : '');
      container.innerHTML = `
        <div class="text-center py-12 text-gray-500 text-xs">
          <i data-lucide="target" class="w-10 h-10 mx-auto mb-2.5 opacity-30 text-hextech-gold"></i>
          <div class="font-bold text-gray-300 mb-1">${selectedRefChampion}${skinDesc}${spkDesc} için uygun atıf bulunamadı.</div>
          <div class="text-[11px] text-gray-500 mb-4">Yukarıdaki filtreleri değiştirebilir veya "Tara & Çıkar" butonuna basabilirsiniz.</div>
        </div>
      `;
      lucide.createIcons();
      updateRefSelectionUI();
      return;
    }

    container.innerHTML = '';
    
    let totalVoices = 0;
    tree.forEach(catObj => {
      catObj.speakers.forEach(spk => {
        spk.skins.forEach(sk => {
          totalVoices += sk.files.length;
        });
      });
    });

    const infoBanner = document.createElement('div');
    infoBanner.className = 'px-3 py-2 rounded-lg bg-[#01060D]/80 border border-hextech-gold/40 flex items-center justify-between text-xs text-hextech-goldBright mb-2 font-sans';
    infoBanner.innerHTML = `
      <div class="flex items-center space-x-2">
        <i data-lucide="sparkles" class="w-4 h-4 text-hextech-gold"></i>
        <span><strong>${selectedRefChampion}</strong> için <strong>${tree.length}</strong> kategoride toplam <strong>${totalVoices}</strong> atıf repliği filtrelendi!</span>
      </div>
      <button onclick="openOutputFolder('${selectedRefChampion}/${selectedRefChampion}e_Yapilan_Tum_Ozel_Atiflar')" class="px-2.5 py-1 rounded bg-hextech-card hover:bg-hextech-cardHover border border-hextech-gold/50 text-[11px] font-bold text-hextech-goldBright cursor-pointer flex items-center space-x-1">
        <i data-lucide="folder" class="w-3.5 h-3.5"></i>
        <span>Klasörü Aç</span>
      </button>
    `;
    container.appendChild(infoBanner);

    tree.forEach(catObj => {
      const catCard = document.createElement('div');
      catCard.className = 'glass-card rounded-xl border border-hextech-borderSubtle overflow-hidden shadow-md';

      let catCount = 0;
      catObj.speakers.forEach(spk => spk.skins.forEach(sk => catCount += sk.files.length));

      const cleanCatTitle = catObj.category.replace('_', ' ');

      const catHeader = document.createElement('div');
      catHeader.className = 'px-3.5 py-2.5 bg-hextech-cardHover/80 font-bold text-xs text-hextech-goldBright flex items-center justify-between border-b border-hextech-borderSubtle/60';
      catHeader.innerHTML = `
        <div class="flex items-center space-x-2">
          <span>🌟</span>
          <span class="font-heading uppercase tracking-wide">${cleanCatTitle}</span>
        </div>
        <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-hextech-base/80 text-hextech-cyan border border-hextech-cyanBorder">${catCount} ses</span>
      `;

      const spkContainer = document.createElement('div');
      spkContainer.className = 'p-2 space-y-1.5 bg-[#01060D]/40';

      catObj.speakers.forEach(spk => {
        const spkBox = document.createElement('details');
        spkBox.className = 'group rounded-lg border border-hextech-borderSubtle/50 overflow-hidden bg-hextech-base/50';
        spkBox.open = true;

        let spkTotal = 0;
        spk.skins.forEach(sk => spkTotal += sk.files.length);

        const spkSummary = document.createElement('summary');
        spkSummary.className = 'px-3 py-2 bg-hextech-input text-gray-200 font-bold text-xs flex items-center justify-between cursor-pointer list-none hover:bg-hextech-cardHover transition';
        spkSummary.innerHTML = `
          <div class="flex items-center space-x-2">
            <span class="text-sm">🗣️</span>
            <span class="text-gray-100 font-heading text-sm">${spk.speakerChampion}</span>
            <span class="text-[10px] text-gray-400 font-normal">(${spk.skins.length} kostüm)</span>
          </div>
          <span class="text-[11px] text-hextech-cyan font-mono font-bold">${spkTotal} replik</span>
        `;

        const skinsDiv = document.createElement('div');
        skinsDiv.className = 'p-2 space-y-2 bg-[#02050A]/70 border-t border-hextech-borderSubtle/40';

        spk.skins.forEach(sk => {
          const isBaseSkin = sk.isBase || sk.skinName.toLowerCase().includes('varsayilan');
          const badgeSkinType = isBaseSkin 
            ? '<span class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-700/50">🛡️ Varsayılan / Kanon</span>'
            : '<span class="text-[10px] px-1.5 py-0.5 rounded bg-amber-950/60 text-amber-300 border border-amber-700/50">🎭 Kostüm Evreni</span>';

          const skBox = document.createElement('div');
          skBox.className = 'p-2 rounded-lg bg-hextech-card/40 border border-hextech-gold/30 pl-2.5';
          skBox.innerHTML = `
            <div class="text-xs font-bold text-hextech-gold mb-1.5 flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <span>🎭 ${sk.skinName.replace('_', ' ')}</span>
                ${badgeSkinType}
              </div>
              <span class="text-[10px] text-gray-400 font-mono">${sk.files.length} ses</span>
            </div>
          `;

          const filesGrid = document.createElement('div');
          filesGrid.className = 'grid grid-cols-1 md:grid-cols-2 gap-1 mt-1';

          sk.files.forEach(f => {
            const flatIdx = refAudioFlatList.length;
            refAudioFlatList.push({
              index: flatIdx,
              path: f.path,
              name: f.name,
              isBase: isBaseSkin
            });

            const isSelected = refSelectedAudioPaths.has(f.path);

            const row = document.createElement('div');
            row.id = `ref-row-${flatIdx}`;
            row.dataset.index = flatIdx;
            row.dataset.path = f.path;
            row.className = `ref-audio-row px-2.5 py-1.5 rounded-lg text-[11px] cursor-pointer font-mono truncate flex items-center justify-between border transition group/item select-none ${
              isSelected 
                ? 'bg-hextech-cardSelected text-hextech-cyanNeon border-hextech-cyan ring-1 ring-hextech-cyan/40 shadow-sm' 
                : 'text-gray-300 hover:bg-hextech-cardHover hover:text-white border-transparent hover:border-hextech-cyan/40'
            }`;

            row.innerHTML = `
              <div class="flex items-center space-x-2 truncate pointer-events-none">
                <input type="checkbox" id="ref-check-${flatIdx}" ${isSelected ? 'checked' : ''} class="w-3.5 h-3.5 rounded accent-hextech-cyan pointer-events-auto cursor-pointer" onclick="event.stopPropagation()">
                <span class="truncate">${f.name}</span>
              </div>
              <button title="Dinle" class="btn-play-row p-1 rounded hover:bg-hextech-base text-hextech-cyan hover:text-hextech-cyanNeon shrink-0 ml-1">
                <i data-lucide="play" class="w-3.5 h-3.5"></i>
              </button>
            `;

            // Click handling with Shift, Ctrl and normal click
            row.onclick = (e) => handleRefAudioRowClick(e, flatIdx, f.path, f.name);

            // Checkbox direct change
            const chk = row.querySelector(`#ref-check-${flatIdx}`);
            if (chk) {
              chk.onchange = (e) => {
                e.stopPropagation();
                if (chk.checked) {
                  refSelectedAudioPaths.add(f.path);
                } else {
                  refSelectedAudioPaths.delete(f.path);
                }
                lastSelectedRefIndex = flatIdx;
                updateRefSelectionUI();
              };
            }

            // Play button
            const playBtn = row.querySelector('.btn-play-row');
            if (playBtn) {
              playBtn.onclick = (e) => {
                e.stopPropagation();
                playAudioFile(f.path, f.name);
              };
            }

            filesGrid.appendChild(row);
          });

          skBox.appendChild(filesGrid);
          skinsDiv.appendChild(skBox);
        });

        spkBox.appendChild(spkSummary);
        spkBox.appendChild(skinsDiv);
        spkContainer.appendChild(spkBox);
      });

      catCard.appendChild(catHeader);
      catCard.appendChild(spkContainer);
      container.appendChild(catCard);
    });

    lucide.createIcons();
    updateRefSelectionUI();
  } catch (err) {
    console.error("Refresh references tree error:", err);
  }
}

function handleRefAudioRowClick(e, index, filePath, fileName) {
  if (e.target.closest('.btn-play-row')) {
    playAudioFile(filePath, fileName);
    return;
  }

  if (e.shiftKey && lastSelectedRefIndex !== -1) {
    // Shift Range Select
    const start = Math.min(lastSelectedRefIndex, index);
    const end = Math.max(lastSelectedRefIndex, index);
    for (let i = start; i <= end; i++) {
      if (refAudioFlatList[i]) {
        refSelectedAudioPaths.add(refAudioFlatList[i].path);
      }
    }
  } else if (e.ctrlKey || e.metaKey) {
    // Ctrl Toggle
    if (refSelectedAudioPaths.has(filePath)) {
      refSelectedAudioPaths.delete(filePath);
    } else {
      refSelectedAudioPaths.add(filePath);
    }
    lastSelectedRefIndex = index;
  } else {
    // Single Toggle + Audio Preview
    if (refSelectedAudioPaths.has(filePath)) {
      refSelectedAudioPaths.delete(filePath);
    } else {
      refSelectedAudioPaths.add(filePath);
    }
    lastSelectedRefIndex = index;
    playAudioFile(filePath, fileName);
  }

  updateRefSelectionUI();
}

function updateRefSelectionUI() {
  const count = refSelectedAudioPaths.size;
  const total = refAudioFlatList.length;

  const countBadge = document.getElementById('ref-selected-count-badge');
  if (countBadge) {
    countBadge.innerText = `${count} ses seçildi`;
  }

  const btnExportFolder = document.getElementById('btn-ref-export-folder');
  if (btnExportFolder) {
    btnExportFolder.disabled = (count === 0);
  }

  const btnExportDavinci = document.getElementById('btn-ref-export-davinci');
  if (btnExportDavinci) {
    btnExportDavinci.disabled = (count === 0);
  }

  const btnPlaySeq = document.getElementById('btn-ref-play-selected');
  if (btnPlaySeq) {
    btnPlaySeq.disabled = (count === 0);
  }

  const selectAllChk = document.getElementById('ref-select-all-checkbox');
  if (selectAllChk) {
    if (count === 0) {
      selectAllChk.checked = false;
      selectAllChk.indeterminate = false;
    } else if (count === total && total > 0) {
      selectAllChk.checked = true;
      selectAllChk.indeterminate = false;
    } else {
      selectAllChk.checked = false;
      selectAllChk.indeterminate = true;
    }
  }

  // Update rows styling
  refAudioFlatList.forEach(item => {
    const row = document.getElementById(`ref-row-${item.index}`);
    const chk = document.getElementById(`ref-check-${item.index}`);
    const isSel = refSelectedAudioPaths.has(item.path);

    if (chk) chk.checked = isSel;
    if (row) {
      if (isSel) {
        row.className = 'ref-audio-row px-2.5 py-1.5 rounded-lg text-[11px] cursor-pointer font-mono truncate flex items-center justify-between border transition group/item select-none bg-hextech-cardSelected text-hextech-cyanNeon border-hextech-cyan ring-1 ring-hextech-cyan/40 shadow-sm';
      } else {
        row.className = 'ref-audio-row px-2.5 py-1.5 rounded-lg text-[11px] cursor-pointer font-mono truncate flex items-center justify-between border transition group/item select-none text-gray-300 hover:bg-hextech-cardHover hover:text-white border-transparent hover:border-hextech-cyan/40';
      }
    }
  });
}

function toggleSelectAllRefAudio(checked) {
  if (checked) {
    refAudioFlatList.forEach(item => refSelectedAudioPaths.add(item.path));
  } else {
    refSelectedAudioPaths.clear();
  }
  updateRefSelectionUI();
}

function clearRefAudioSelection() {
  refSelectedAudioPaths.clear();
  lastSelectedRefIndex = -1;
  updateRefSelectionUI();
}

async function exportRefSelectedToFolder() {
  if (refSelectedAudioPaths.size === 0) {
    alert("Lütfen klasöre aktarmak için en az bir ses seçin.");
    return;
  }

  const audioList = Array.from(refSelectedAudioPaths);
  const spkDesc = selectedRefSpeakerType === 'base_only' ? 'Kanon_Atiflar' : (selectedRefSpeakerType === 'skins_only' ? 'Kostumlu_Atiflar' : 'Secilen_Atiflar');
  const folderName = `${selectedRefChampion || 'Hedef'}_${spkDesc}`;

  onLogMessage(`📁 ${audioList.length} adet seçilen ses '${folderName}' klasörüne toplanıyor...`);

  try {
    const res = await fetch('/api/export-selected-to-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        champion: selectedRefChampion || 'Ozel_Atiflar',
        folder_name: folderName,
        audio_files: audioList
      })
    });
    const json = await res.json();
    if (json.status === 'success') {
      onLogMessage(`✨ Başarılı! ${json.total_files} adet ses '${json.folder_name}' klasörüne aktarıldı ve Windows Gezgini'nde açıldı.`);
      showToast(`📁 ${json.total_files} ses klasöre aktarıldı ve açıldı!`);
    } else {
      onLogMessage(`❌ Hata: ${json.message}`);
      alert(`Hata: ${json.message}`);
    }
  } catch (err) {
    onLogMessage(`❌ Bağlantı Hatası: ${err}`);
  }
}


function setRefGap(seconds) {
  const gapInput = document.getElementById('ref-davinci-gap');
  if (gapInput) {
    gapInput.value = seconds;
    showToast(`⏱️ DaVinci Boşluk Süresi: ${seconds} saniye olarak ayarlandı`);
  }
}

async function exportRefSelectedToDaVinci() {
  if (refSelectedAudioPaths.size === 0) {
    alert("Lütfen DaVinci Timeline'a aktarmak için en az bir atıf repliği seçin (Shift / Ctrl ile çoklu seçebilirsiniz).");
    return;
  }

  const gapInput = document.getElementById('ref-davinci-gap');
  const gapSeconds = gapInput ? parseFloat(gapInput.value) || 0.8 : 0.8;
  const audioList = Array.from(refSelectedAudioPaths);

  const fadeInInput = document.getElementById('davinci-fade-in-input');
  const fadeOutInput = document.getElementById('davinci-fade-out-input');
  const fadeInSec = fadeInInput ? parseFloat(fadeInInput.value) || 1.5 : 1.5;
  const fadeOutSec = fadeOutInput ? parseFloat(fadeOutInput.value) || 0.5 : 0.5;

  onLogMessage(`🎬 DaVinci Resolve Timeline hazırlanıyor (${audioList.length} seçili ses, ${gapSeconds}s aralık, Text+ In:${fadeInSec}s Out:${fadeOutSec}s)...`);
  if (progressBarContainer) progressBarContainer.classList.remove('hidden');

  try {
    const res = await fetch('/api/export-davinci', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        champion: selectedRefChampion || 'Hedef_Atiflar',
        skin: selectedRefSkin || 'Secilenler',
        gap_seconds: gapSeconds,
        fade_in_seconds: fadeInSec,
        fade_out_seconds: fadeOutSec,
        fps: 60,
        audio_files: audioList
      })
    });

    const data = await res.json();
    if (progressBarContainer) progressBarContainer.classList.add('hidden');

    if (data.status === 'success') {
      onLogMessage(`✨ DaVinci Timeline Hazır: ${data.filename || data.file_name} (${data.total_audio_count || data.clip_count} ses, ${data.total_duration_formatted || ''})`);
      openDaVinciModal({
        file_path: data.output_xml_path || data.file_path,
        file_name: data.filename || data.file_name,
        clips_count: data.clips_count || data.total_audio_count || data.clip_count,
        gap_seconds: gapSeconds,
        fade_in_seconds: fadeInSec,
        fade_out_seconds: fadeOutSec,
        total_duration_sec: data.total_duration_sec || data.total_duration_seconds || data.total_duration,
        clipboard_copied: data.clipboard_copied,
        setting_path: data.setting_path
      });
      showToast(`🎬 DaVinci Timeline Hazır: ${data.clips_count || data.total_audio_count || data.clip_count} ses (Panoya Kopyalandı)`);
    } else {
      onLogMessage(`❌ DaVinci Aktarım Hatası: ${data.message}`);
      alert(`Hata: ${data.message}`);
    }

  } catch (err) {
    if (progressBarContainer) progressBarContainer.classList.add('hidden');
    onLogMessage(`❌ DaVinci İletişim Hatası: ${err}`);
  }
}

let refPlaySequenceIndex = 0;
function playSelectedRefAudioSequence() {
  const audioList = Array.from(refSelectedAudioPaths);
  if (audioList.length === 0) return;

  refPlaySequenceIndex = 0;
  const playNext = () => {
    if (refPlaySequenceIndex >= audioList.length) {
      onLogMessage("🎵 Seçilen tüm repliklerin çalınması tamamlandı.");
      return;
    }
    const currentPath = audioList[refPlaySequenceIndex];
    const fileName = currentPath.split(/[\\/]/).pop();
    onLogMessage(`▶️ [${refPlaySequenceIndex + 1}/${audioList.length}] Çalınıyor: ${fileName}`);
    
    playAudioFile(currentPath, fileName);
    
    if (globalAudio) {
      globalAudio.onended = () => {
        refPlaySequenceIndex++;
        setTimeout(playNext, 300);
      };
    }
  };

  playNext();
}

async function scanTargetReferences() {
  if (!selectedRefChampion) return;
  const btn = document.getElementById('btn-scan-references');
  if (btn) btn.disabled = true;
  if (progressBarContainer) progressBarContainer.classList.remove('hidden');

  await fetch('/api/extract-references', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      target_champion: selectedRefChampion,
      target_skin: selectedRefSkin,
      speaker_base_only: (selectedRefSpeakerType === 'base_only')
    })
  });
}

// =========================================================================
// 11. REVERSE REFERENCES ANALYTICS & RELATIONSHIP MATRIX HUB (YENİ)
// =========================================================================
let refCurrentSubTab = 'analytics';
let analyticsAllChamps = [];
let selectedAnalyticsChamp = 'Yasuo';
let currentAnalyticsData = null;
let activeMatrixFilter = 'all';
let activeActionFilter = 'all';
let gridStatusFilter = 'all';
let analyticsAudioInstance = null;
let currentPlayingBtnId = null;

function switchRefSubTab(tab) {
  refCurrentSubTab = tab;
  const viewAnalytics = document.getElementById('ref-subview-analytics');
  const viewClassic = document.getElementById('ref-subview-classic');
  const btnAnalytics = document.getElementById('btn-subtab-analytics');
  const btnClassic = document.getElementById('btn-subtab-classic');

  if (tab === 'analytics') {
    if (viewAnalytics) viewAnalytics.classList.remove('hidden');
    if (viewClassic) viewClassic.classList.add('hidden');
    if (btnAnalytics) {
      btnAnalytics.className = 'px-3.5 py-1.5 text-xs font-extrabold rounded-md transition-all cursor-pointer bg-hextech-cardSelected text-hextech-cyanNeon border border-hextech-cyan/60 shadow flex items-center space-x-1.5';
    }
    if (btnClassic) {
      btnClassic.className = 'px-3.5 py-1.5 text-xs font-bold rounded-md transition-all cursor-pointer text-gray-400 hover:text-white border border-transparent flex items-center space-x-1.5';
    }
    if (analyticsAllChamps.length === 0) {
      loadReferencesAnalytics();
    }
  } else {
    if (viewAnalytics) viewAnalytics.classList.add('hidden');
    if (viewClassic) viewClassic.classList.remove('hidden');
    if (btnAnalytics) {
      btnAnalytics.className = 'px-3.5 py-1.5 text-xs font-bold rounded-md transition-all cursor-pointer text-gray-400 hover:text-white border border-transparent flex items-center space-x-1.5';
    }
    if (btnClassic) {
      btnClassic.className = 'px-3.5 py-1.5 text-xs font-extrabold rounded-md transition-all cursor-pointer bg-hextech-cardSelected text-hextech-goldBright border border-hextech-gold/60 shadow flex items-center space-x-1.5';
    }
    if (!allChampions || allChampions.length === 0) {
      loadRefChampions();
    }
  }
  if (window.lucide) lucide.createIcons();
}

async function loadReferencesAnalytics() {
  const gridContainer = document.getElementById('ref-champions-grid');
  if (gridContainer) {
    gridContainer.innerHTML = '<div class="col-span-full py-12 text-center text-xs text-gray-400 font-mono"><div class="animate-pulse">174 Şampiyon Analiz Verileri Yükleniyor...</div></div>';
  }

  try {
    const res = await fetch('/api/references-analytics');
    const data = await res.json();
    analyticsAllChamps = data || [];
    renderAnalyticsGrid();

    // Otomatik olarak taranmış olanlardan ilkini seç (örn: Yasuo)
    const defaultChamp = analyticsAllChamps.find(c => c.name.toLowerCase() === 'yasuo' && c.is_extracted) 
                      || analyticsAllChamps.find(c => c.is_extracted) 
                      || analyticsAllChamps[0];
    if (defaultChamp) {
      selectAnalyticsChampion(defaultChamp.name);
    }
  } catch (err) {
    console.error("Failed to load references analytics:", err);
    if (gridContainer) {
      gridContainer.innerHTML = '<div class="col-span-full py-12 text-center text-xs text-rose-400 font-mono">Analiz verileri alınamadı.</div>';
    }
  }
}

function renderAnalyticsGrid() {
  const container = document.getElementById('ref-champions-grid');
  if (!container) return;

  const searchInput = document.getElementById('ref-grid-search');
  const query = searchInput ? searchInput.value.toLowerCase().trim() : '';

  let filtered = analyticsAllChamps.filter(c => {
    const matchesQuery = c.name.toLowerCase().includes(query);
    if (!matchesQuery) return false;
    if (gridStatusFilter === 'extracted') return c.is_extracted;
    if (gridStatusFilter === 'unextracted') return !c.is_extracted;
    return true;
  });

  const countBadge = document.getElementById('grid-visible-count');
  if (countBadge) countBadge.innerText = `${filtered.length} / ${analyticsAllChamps.length} Şampiyon`;

  container.innerHTML = '';
  if (filtered.length === 0) {
    container.innerHTML = '<div class="col-span-full py-10 text-center text-xs text-gray-500 font-mono">Eşleşen şampiyon bulunamadı.</div>';
    return;
  }

  filtered.forEach(c => {
    const isSelected = (c.name.toLowerCase() === selectedAnalyticsChamp.toLowerCase());
    const card = document.createElement('div');
    card.className = `group flex flex-col items-center p-2 rounded-xl border transition-all cursor-pointer text-center relative select-none ${
      isSelected 
        ? 'bg-hextech-cardSelected/90 border-hextech-cyanNeon shadow-lg ring-1 ring-hextech-cyanNeon/50' 
        : 'bg-hextech-card/60 hover:bg-hextech-cardHover/90 border-hextech-borderSubtle hover:border-hextech-gold/50'
    }`;
    card.onclick = () => selectAnalyticsChampion(c.name);

    card.innerHTML = `
      <div class="relative w-12 h-12 rounded-lg overflow-hidden border ${isSelected ? 'border-hextech-cyanNeon' : 'border-hextech-borderMedium group-hover:border-hextech-gold'} mb-1.5 transition shrink-0 bg-[#06101D]">
        <img src="${c.icon_url}" alt="${c.name}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200" loading="lazy" onerror="this.src='https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/-1.png'">
        ${c.is_extracted ? '<div class="absolute top-0.5 right-0.5 w-2 h-2 rounded-full bg-emerald-400 ring-2 ring-emerald-950"></div>' : ''}
      </div>
      <div class="text-[11px] font-bold truncate w-full ${isSelected ? 'text-hextech-cyanNeon' : 'text-gray-200 group-hover:text-hextech-goldBright'}">${c.name}</div>
      ${c.is_extracted 
        ? `<div class="text-[9px] font-mono font-extrabold text-emerald-400 bg-emerald-950/70 border border-emerald-500/40 rounded px-1.5 py-0.2 mt-0.5">${c.total_quotes} Atıf</div>`
        : `<div class="text-[9px] font-mono text-gray-500 mt-0.5">Taranmadı</div>`
      }
    `;

    container.appendChild(card);
  });
}

function filterGridChampions(val) {
  renderAnalyticsGrid();
}

function setGridFilter(filterType) {
  gridStatusFilter = filterType;
  const btnAll = document.getElementById('grid-filter-all');
  const btnExt = document.getElementById('grid-filter-extracted');
  const btnUnext = document.getElementById('grid-filter-unextracted');

  [btnAll, btnExt, btnUnext].forEach(btn => {
    if (btn) btn.className = 'px-2 py-0.5 rounded text-[10px] font-bold text-gray-400 hover:text-white border border-transparent';
  });

  const activeBtn = filterType === 'all' ? btnAll : (filterType === 'extracted' ? btnExt : btnUnext);
  if (activeBtn) {
    activeBtn.className = 'px-2 py-0.5 rounded text-[10px] font-bold bg-hextech-cardSelected text-hextech-goldBright border border-hextech-gold/40';
  }

  renderAnalyticsGrid();
}

async function selectAnalyticsChampion(champName) {
  selectedAnalyticsChamp = champName;
  selectedRefChampion = champName;
  activeMatrixFilter = 'all';
  activeActionFilter = 'all';

  renderAnalyticsGrid();
  resetMatrixCardStyles();

  const nameEl = document.getElementById('analytics-target-name');
  if (nameEl) nameEl.innerText = champName;
  const subEl = document.getElementById('analytics-target-subtitle');
  if (subEl) subEl.innerText = `${champName} için derin analiz verileri hesaplanıyor...`;

  try {
    const res = await fetch(`/api/references-analytics?target=${encodeURIComponent(champName)}`);
    const data = await res.json();
    currentAnalyticsData = data;
    renderAnalyticsDashboard(data);
  } catch (err) {
    console.error("Failed to load champion analytics:", err);
  }
}

function renderAnalyticsDashboard(data) {
  if (!data) return;

  const iconImg = document.getElementById('analytics-target-icon');
  if (iconImg) iconImg.src = data.icon_url;

  const nameEl = document.getElementById('analytics-target-name');
  if (nameEl) nameEl.innerText = data.target;

  const totalBadge = document.getElementById('analytics-target-total-badge');
  if (totalBadge) totalBadge.innerText = `${data.total_quotes} Atıf`;

  const extBadge = document.getElementById('analytics-extracted-badge');
  if (extBadge) {
    if (data.is_extracted) {
      extBadge.className = 'absolute bottom-0 inset-x-0 bg-emerald-950/90 text-emerald-300 text-[8px] font-bold font-mono text-center py-0.5 border-t border-emerald-500/50';
      extBadge.innerText = 'TARANDI';
    } else {
      extBadge.className = 'absolute bottom-0 inset-x-0 bg-rose-950/90 text-rose-300 text-[8px] font-bold font-mono text-center py-0.5 border-t border-rose-500/50';
      extBadge.innerText = 'TARANMADI';
    }
  }

  const subEl = document.getElementById('analytics-target-subtitle');
  if (subEl) {
    subEl.innerText = data.is_extracted 
      ? `${data.target} için ${data.unique_speakers} farklı şampiyon tarafından söylenen ${data.total_quotes} özel replik bulundu.`
      : `Bu şampiyon için henüz diskte atıf çıkarılmadı. Üstteki 'Seçili Şampiyonu Tara' butonuna basarak anında çıkarabilirsiniz.`;
  }

  const statQuotes = document.getElementById('stat-total-quotes');
  if (statQuotes) statQuotes.innerText = data.total_quotes;
  const statSpeakers = document.getElementById('stat-unique-speakers');
  if (statSpeakers) statSpeakers.innerText = data.unique_speakers;
  const statSkins = document.getElementById('stat-target-skins');
  if (statSkins) statSkins.innerText = (data.target_skins || []).length;

  const m = data.matrix || {};
  const cBB = document.getElementById('count-base-base');
  if (cBB) cBB.innerText = m.base_to_base || 0;
  const cSB = document.getElementById('count-skin-base');
  if (cSB) cSB.innerText = m.skin_to_base || 0;
  const cBS = document.getElementById('count-base-skin');
  if (cBS) cBS.innerText = m.base_to_skin || 0;
  const cSS = document.getElementById('count-skin-skin');
  if (cSS) cSS.innerText = m.skin_to_skin || 0;

  const actionContainer = document.getElementById('analytics-action-badges');
  if (actionContainer) {
    actionContainer.innerHTML = '';
    const actions = data.action_types || {};
    const actionLabels = {
      'karsilasma': { label: '⚔️ Karşılaşma', color: 'bg-blue-950 text-blue-300 border-blue-500/40' },
      'katletme': { label: '💀 Katletme', color: 'bg-rose-950 text-rose-300 border-rose-500/40' },
      'dost_karsilasma': { label: '🤝 Dost Karşılaşma', color: 'bg-emerald-950 text-emerald-300 border-emerald-500/40' },
      'kiskirtma': { label: '🔥 Kışkırtma (Taunt)', color: 'bg-amber-950 text-amber-300 border-amber-500/40' },
      'saka': { label: '🃏 Şaka (Joke)', color: 'bg-yellow-950 text-yellow-300 border-yellow-500/40' },
      'yetenek_etkilesimi': { label: '⚡ Yetenek Etkileşimi', color: 'bg-purple-950 text-purple-300 border-purple-500/40' }
    };

    if (Object.keys(actions).length === 0) {
      actionContainer.innerHTML = '<span class="text-[10px] text-gray-500 font-mono">Veri yok</span>';
    } else {
      Object.entries(actions).forEach(([actKey, count]) => {
        const meta = actionLabels[actKey] || { label: actKey, color: 'bg-gray-800 text-gray-300 border-gray-600' };
        const btn = document.createElement('button');
        btn.className = `px-2 py-0.5 rounded-full text-[10px] font-bold border transition cursor-pointer flex items-center space-x-1 ${meta.color} hover:brightness-125`;
        btn.innerHTML = `<span>${meta.label}</span><span class="font-mono font-extrabold ml-1 bg-black/40 px-1 rounded-full">${count}</span>`;
        btn.onclick = () => filterByActionType(actKey);
        actionContainer.appendChild(btn);
      });
    }
  }

  const speakersContainer = document.getElementById('analytics-top-speakers');
  const speakersCountLabel = document.getElementById('analytics-speakers-count-label');
  if (speakersContainer) {
    speakersContainer.innerHTML = '';
    const spkList = data.speakers || [];
    if (speakersCountLabel) speakersCountLabel.innerText = `${spkList.length} Şampiyon`;

    if (spkList.length === 0) {
      speakersContainer.innerHTML = '<span class="text-[10px] text-gray-500 font-mono">Konuşan şampiyon bulunamadı.</span>';
    } else {
      spkList.forEach(spk => {
        const div = document.createElement('div');
        div.className = 'flex items-center space-x-2 px-2 py-1 rounded-lg bg-[#06101D] border border-hextech-borderSubtle shrink-0 hover:border-hextech-gold/50 transition cursor-pointer select-none';
        div.onclick = () => {
          const searchInput = document.getElementById('analytics-table-search');
          if (searchInput) {
            searchInput.value = spk.speaker;
            filterAnalyticsTable(spk.speaker);
          }
        };
        div.innerHTML = `
          <img src="${spk.icon_url}" alt="${spk.speaker}" class="w-6 h-6 rounded-md object-cover border border-hextech-borderMedium">
          <div class="leading-tight">
            <div class="text-[11px] font-bold text-gray-200 truncate">${spk.speaker}</div>
            <div class="text-[9px] font-mono text-hextech-cyan font-extrabold">${spk.count} replik</div>
          </div>
        `;
        speakersContainer.appendChild(div);
      });
    }
  }

  renderAnalyticsQuotesTable();
}

function resetMatrixCardStyles() {
  ['base-base', 'skin-base', 'base-skin', 'skin-skin'].forEach(k => {
    const el = document.getElementById(`card-matrix-${k}`);
    if (el) {
      el.classList.remove('ring-2', 'ring-hextech-cyanNeon', 'bg-hextech-cardSelected');
      el.classList.add('bg-hextech-surface/60');
    }
  });
}

function filterByMatrixType(matrixType) {
  if (activeMatrixFilter === matrixType) {
    activeMatrixFilter = 'all';
    resetMatrixCardStyles();
  } else {
    activeMatrixFilter = matrixType;
    resetMatrixCardStyles();
    const map = {
      'base_to_base': 'base-base',
      'skin_to_base': 'skin-base',
      'base_to_skin': 'base-skin',
      'skin_to_skin': 'skin-skin'
    };
    const targetCard = document.getElementById(`card-matrix-${map[matrixType]}`);
    if (targetCard) {
      targetCard.classList.remove('bg-hextech-surface/60');
      targetCard.classList.add('ring-2', 'ring-hextech-cyanNeon', 'bg-hextech-cardSelected');
    }
  }

  updateActiveMatrixTag();
  renderAnalyticsQuotesTable();
}

function filterByActionType(act) {
  activeActionFilter = (activeActionFilter === act) ? 'all' : act;
  updateActiveMatrixTag();
  renderAnalyticsQuotesTable();
}

function updateActiveMatrixTag() {
  const tag = document.getElementById('analytics-active-matrix-tag');
  if (!tag) return;
  const labels = [];
  if (activeMatrixFilter !== 'all') {
    const mNames = {
      'base_to_base': '🛡️ Kanon (Varsayılan ➔ Varsayılan)',
      'skin_to_base': '🎭 Kostümlü ➔ Varsayılan',
      'base_to_skin': '🎯 Varsayılan ➔ Kostümlü',
      'skin_to_skin': '🌌 Alternatif Evren (Kostümlü ➔ Kostümlü)'
    };
    labels.push(mNames[activeMatrixFilter]);
  }
  if (activeActionFilter !== 'all') {
    labels.push(`Eylem: ${activeActionFilter}`);
  }

  if (labels.length > 0) {
    tag.innerText = labels.join(' | ');
    tag.classList.remove('hidden');
  } else {
    tag.classList.add('hidden');
  }
}

function resetAnalyticsFilters() {
  activeMatrixFilter = 'all';
  activeActionFilter = 'all';
  resetMatrixCardStyles();
  updateActiveMatrixTag();
  const searchInput = document.getElementById('analytics-table-search');
  if (searchInput) searchInput.value = '';
  renderAnalyticsQuotesTable();
}

function filterAnalyticsTable(val) {
  renderAnalyticsQuotesTable();
}

function renderAnalyticsQuotesTable() {
  const tbody = document.getElementById('analytics-quotes-tbody');
  const emptyState = document.getElementById('analytics-empty-state');
  const countBadge = document.getElementById('analytics-table-count-badge');
  if (!tbody || !currentAnalyticsData) return;

  const searchInput = document.getElementById('analytics-table-search');
  const query = searchInput ? searchInput.value.toLowerCase().trim() : '';

  const allItems = currentAnalyticsData.items || [];
  const filtered = allItems.filter(item => {
    if (activeMatrixFilter !== 'all' && item.matrix_type !== activeMatrixFilter) return false;
    if (activeActionFilter !== 'all' && item.action_type !== activeActionFilter) return false;
    if (query) {
      const matchSpeaker = item.speaker_champion.toLowerCase().includes(query);
      const matchSkin = item.speaker_skin.toLowerCase().includes(query);
      const matchTargetSkin = item.target_skin.toLowerCase().includes(query);
      const matchText = (item.text || '').toLowerCase().includes(query);
      const matchFile = item.file_name.toLowerCase().includes(query);
      if (!matchSpeaker && !matchSkin && !matchTargetSkin && !matchText && !matchFile) return false;
    }
    return true;
  });

  if (countBadge) countBadge.innerText = `${filtered.length} / ${allItems.length} Ses`;
  tbody.innerHTML = '';

  if (filtered.length === 0) {
    if (emptyState) emptyState.classList.remove('hidden');
    return;
  }
  if (emptyState) emptyState.classList.add('hidden');

  const matrixBadges = {
    'base_to_base': '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-emerald-950/80 text-emerald-300 border border-emerald-500/40">Kanon</span>',
    'skin_to_base': '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-cyan-950/80 text-cyan-300 border border-cyan-500/40">Kostüm➔V</span>',
    'base_to_skin': '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-amber-950/80 text-amber-300 border border-amber-500/40">V➔Kostüm</span>',
    'skin_to_skin': '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold font-mono bg-purple-950/80 text-purple-300 border border-purple-500/40">Kostüm➔K</span>'
  };

  const actionBadges = {
    'karsilasma': '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-blue-950/80 text-blue-300 border border-blue-500/30">Karşılaşma</span>',
    'katletme': '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-rose-950/80 text-rose-300 border border-rose-500/30">Katletme</span>',
    'dost_karsilasma': '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-500/30">Dost</span>',
    'kiskirtma': '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-950/80 text-amber-300 border border-amber-500/30">Kışkırtma</span>',
    'saka': '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-yellow-950/80 text-yellow-300 border border-yellow-500/30">Şaka</span>',
    'yetenek_etkilesimi': '<span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-purple-950/80 text-purple-300 border border-purple-500/30">Yetenek</span>'
  };

  filtered.forEach((it, idx) => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-hextech-cardHover/70 transition-colors group';

    const btnId = `btn-play-row-${idx}`;
    const cleanPath = it.file_path.replace(/\\/g, '/');

    tr.innerHTML = `
      <td class="py-2 px-2.5 text-center">
        <button id="${btnId}" onclick="playAnalyticsAudio('${encodeURIComponent(cleanPath)}', '${btnId}')" class="w-7 h-7 rounded-lg bg-hextech-card hover:bg-hextech-cyan hover:text-gray-950 text-hextech-cyan border border-hextech-cyan/40 flex items-center justify-center transition cursor-pointer shadow">
          <i data-lucide="play" class="w-3.5 h-3.5 fill-current"></i>
        </button>
      </td>
      <td class="py-2 px-2.5 font-bold text-gray-200">
        <div class="flex items-center space-x-2">
          <span>${it.speaker_champion}</span>
        </div>
      </td>
      <td class="py-2 px-2.5 text-gray-300 text-[11px] truncate max-w-[130px]" title="${it.speaker_skin}">${it.speaker_skin}</td>
      <td class="py-2 px-2.5 text-amber-300 text-[11px] truncate max-w-[120px]" title="${it.target_skin}">${it.target_skin}</td>
      <td class="py-2 px-2.5">${matrixBadges[it.matrix_type] || it.matrix_type}</td>
      <td class="py-2 px-2.5">${actionBadges[it.action_type] || it.action_type}</td>
      <td class="py-2 px-2.5 min-w-[280px] max-w-[650px] whitespace-normal">
        ${it.text 
          ? `<div class="text-[11px] font-semibold text-gray-100 break-words whitespace-normal leading-relaxed italic" title="${it.text}">"${it.text}"</div>
             <div class="text-[9px] font-mono text-gray-400 break-all mt-0.5">${it.file_name}</div>`
          : `<div class="text-[11px] font-mono text-gray-400 break-all">${it.file_name}</div>`
        }
      </td>
    `;
    tbody.appendChild(tr);
  });

  if (window.lucide) lucide.createIcons();
}

function playAnalyticsAudio(encodedPath, btnId) {
  const filePath = decodeURIComponent(encodedPath);

  if (analyticsAudioInstance && currentPlayingBtnId === btnId && !analyticsAudioInstance.paused) {
    analyticsAudioInstance.pause();
    analyticsAudioInstance.currentTime = 0;
    resetPlayButton(btnId);
    analyticsAudioInstance = null;
    currentPlayingBtnId = null;
    return;
  }

  if (analyticsAudioInstance) {
    analyticsAudioInstance.pause();
    if (currentPlayingBtnId) resetPlayButton(currentPlayingBtnId);
  }

  const audioUrl = `/api/audio?path=${encodeURIComponent(filePath)}`;
  analyticsAudioInstance = new Audio(audioUrl);
  const volEl = document.getElementById('audio-volume');
  const currentVol = volEl ? parseFloat(volEl.value) / 100 : 0.85;
  analyticsAudioInstance.volume = Math.max(0, Math.min(1, currentVol));
  currentPlayingBtnId = btnId;

  const btn = document.getElementById(btnId);
  if (btn) {
    btn.innerHTML = '<i data-lucide="square" class="w-3.5 h-3.5 fill-current"></i>';
    btn.classList.add('bg-hextech-cyan', 'text-gray-950');
    btn.classList.remove('bg-hextech-card', 'text-hextech-cyan');
    if (window.lucide) lucide.createIcons();
  }

  analyticsAudioInstance.play().catch(e => {
    console.error("Audio playback error:", e);
    resetPlayButton(btnId);
  });

  analyticsAudioInstance.onended = () => {
    resetPlayButton(btnId);
    analyticsAudioInstance = null;
    currentPlayingBtnId = null;
  };
}

function resetPlayButton(btnId) {
  const btn = document.getElementById(btnId);
  if (btn) {
    btn.innerHTML = '<i data-lucide="play" class="w-3.5 h-3.5 fill-current"></i>';
    btn.classList.remove('bg-hextech-cyan', 'text-gray-950');
    btn.classList.add('bg-hextech-card', 'text-hextech-cyan');
    if (window.lucide) lucide.createIcons();
  }
}

// Auto init when tab switched or DOM loaded
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
    if (document.getElementById('view-references') && !document.getElementById('view-references').classList.contains('hidden')) {
      loadReferencesAnalytics();
    }
  }, 100);
});
