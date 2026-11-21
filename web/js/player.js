// =========================================================================
// 7. HEXTECH AUDIO PLAYER & SEQUENTIAL BATCH QUEUE
// =========================================================================
function playSingleAudioDirect(filePath, fileName, skinName, catName) {
  // Set as a 1-item queue or play directly
  activeAudioQueue = [{
    path: filePath,
    name: fileName,
    skinName: skinName || selectedChampion,
    catName: catName || 'Replik'
  }];
  currentQueueIndex = 0;
  isBatchPlaying = false;
  playQueueItem(0);
}

function playCategoryDirect(skinName, catName, files) {
  if (!files || files.length === 0) return;
  activeAudioQueue = files.map(f => ({
    path: f.path,
    name: f.name,
    skinName: skinName,
    catName: catName
  }));
  currentQueueIndex = 0;
  isBatchPlaying = true;
  onLogMessage(`🎵 [${skinName}] ${catName} kategorisindeki ${files.length} ses sırayla çalınıyor...`);
  playQueueItem(0);
}

function toggleBatchPlayQueue() {
  if (isBatchPlaying && audioPlayer && !audioPlayer.paused) {
    audioPlayer.pause();
    updatePlayButtonState(false);
    updateBatchPlayButtonState(false);
    return;
  }

  if (isBatchPlaying && audioPlayer && audioPlayer.paused && activeAudioQueue.length > 0) {
    audioPlayer.play();
    updatePlayButtonState(true);
    updateBatchPlayButtonState(true);
    return;
  }

  // Gather selected files or all files in tree
  const queue = [];
  if (selectedAudioPaths.size > 0) {
    currentExtractedTree.forEach(skinObj => {
      skinObj.categories.forEach(cat => {
        cat.files.forEach(f => {
          if (selectedAudioPaths.has(f.path)) {
            queue.push({ path: f.path, name: f.name, skinName: skinObj.skinName, catName: cat.name });
          }
        });
      });
    });
  } else {
    // If none selected, play all visible files
    currentExtractedTree.forEach(skinObj => {
      skinObj.categories.forEach(cat => {
        cat.files.forEach(f => {
          queue.push({ path: f.path, name: f.name, skinName: skinObj.skinName, catName: cat.name });
        });
      });
    });
  }

  if (queue.length === 0) {
    onLogMessage("⚠️ Oynatılacak çıkarılmış ses bulunamadı. Lütfen önce ses çıkarın!");
    return;
  }

  activeAudioQueue = queue;
  currentQueueIndex = 0;
  isBatchPlaying = true;
  onLogMessage(`🚀 Sıralı Oynatma Başlatıldı: Toplam ${queue.length} ses art arda çalınacak.`);
  playQueueItem(0);
}

function playQueueItem(index) {
  if (index < 0 || index >= activeAudioQueue.length) {
    isBatchPlaying = false;
    updatePlayButtonState(false);
    updateBatchPlayButtonState(false);
    const statusText = document.getElementById('player-status-text');
    if (statusText) statusText.innerText = 'OYNA' + 'TMA TAMAMLANDI';
    onLogMessage("✅ Sıralı oynatma listesi tamamlandı.");
    return;
  }

  currentQueueIndex = index;
  const item = activeAudioQueue[index];
  
  if (playerTitle) playerTitle.innerText = item.name;
  if (playerSubtitle) playerSubtitle.innerText = `${item.skinName.replace(/_/g, ' ')} • ${item.catName.replace(/_/g, ' ')} (${index + 1}/${activeAudioQueue.length})`;
  
  const statusText = document.getElementById('player-status-text');
  if (statusText) statusText.innerText = `🎵 SIRALI OYNATILIYOR (${index + 1}/${activeAudioQueue.length})`;

  audioPlayer.src = `/api/audio?path=${encodeURIComponent(item.path)}`;
  audioPlayer.play().catch(err => console.error("Play error:", err));

  updatePlayButtonState(true);
  updateBatchPlayButtonState(true);
  renderAudioQueue();
  renderExtractedTree(); // updates highlight
}

function playNextQueueAudio() {
  if (activeAudioQueue.length > 0 && currentQueueIndex + 1 < activeAudioQueue.length) {
    playQueueItem(currentQueueIndex + 1);
  }
}

function playPrevQueueAudio() {
  if (activeAudioQueue.length > 0 && currentQueueIndex > 0) {
    playQueueItem(currentQueueIndex - 1);
  }
}

function toggleAutoplayMode() {
  isAutoplayEnabled = !isAutoplayEnabled;
  const autoText = document.getElementById('autoplay-text');
  const btn = document.getElementById('btn-toggle-autoplay');
  if (autoText) autoText.innerText = isAutoplayEnabled ? 'Sıralı: AÇIK' : 'Sıralı: KAPALI';
  if (btn) {
    if (isAutoplayEnabled) {
      btn.className = 'px-2 py-1 rounded text-[10px] font-sans font-bold bg-hextech-surface hover:bg-hextech-cardHover text-hextech-cyan border border-hextech-cyan/40 cursor-pointer flex items-center gap-1';
    } else {
      btn.className = 'px-2 py-1 rounded text-[10px] font-sans font-bold bg-hextech-surface hover:bg-hextech-cardHover text-gray-500 border border-gray-700 cursor-pointer flex items-center gap-1';
    }
  }
}

function clearAudioQueue() {
  activeAudioQueue = [];
  currentQueueIndex = -1;
  isBatchPlaying = false;
  stopAudio();
  renderAudioQueue();
  renderExtractedTree();
}

function renderAudioQueue() {
  const container = document.getElementById('playlist-queue-list');
  const badge = document.getElementById('queue-count-badge');
  if (badge) badge.innerText = `(${activeAudioQueue.length})`;
  if (!container) return;

  if (activeAudioQueue.length === 0) {
    container.innerHTML = '<div class="text-center py-2 text-gray-500 text-[10px]">Kuyrukta ses yok. Listeden seçin veya Sıralı Çal\'a basın.</div>';
    return;
  }

  container.innerHTML = '';
  activeAudioQueue.forEach((item, idx) => {
    const isCurrent = idx === currentQueueIndex;
    const row = document.createElement('div');
    row.className = `px-2 py-1 rounded flex items-center justify-between gap-1.5 cursor-pointer transition-all ${
      isCurrent
        ? 'bg-emerald-950 text-emerald-300 font-bold border border-emerald-500/50'
        : 'hover:bg-hextech-card text-gray-400 hover:text-gray-200'
    }`;
    row.innerHTML = `
      <div class="flex items-center gap-1.5 truncate">
        <span class="font-mono text-[9px] ${isCurrent ? 'text-emerald-400' : 'text-gray-600'}">${idx + 1}.</span>
        <span class="truncate">${item.name}</span>
      </div>
      ${isCurrent ? `<span class="shrink-0 text-[9px] px-1 rounded bg-emerald-900 text-emerald-200">Çalıyor</span>` : ''}
    `;
    row.onclick = () => playQueueItem(idx);
    container.appendChild(row);
  });
}

function updateBatchPlayButtonState(isPlaying) {
  const icon = document.getElementById('batch-play-icon');
  const text = document.getElementById('batch-play-text');
  if (icon && text) {
    if (isPlaying) {
      icon.setAttribute('data-lucide', 'pause');
      text.innerText = 'Duraklat';
    } else {
      icon.setAttribute('data-lucide', 'play');
      text.innerText = 'Sıralı Çal';
    }
    if (window.lucide) lucide.createIcons();
  }
}

function togglePlay() {
  if (!audioPlayer.src) return;
  if (audioPlayer.paused) {
    audioPlayer.play();
    updatePlayButtonState(true);
    if (isBatchPlaying) updateBatchPlayButtonState(true);
  } else {
    audioPlayer.pause();
    updatePlayButtonState(false);
    if (isBatchPlaying) updateBatchPlayButtonState(false);
  }
}

function stopAudio() {
  if (!audioPlayer.src) return;
  audioPlayer.pause();
  audioPlayer.currentTime = 0;
  updatePlayButtonState(false);
  if (isBatchPlaying) updateBatchPlayButtonState(false);
}

function updatePlayButtonState(isPlaying) {
  if (!playIcon || !playText) return;
  if (isPlaying) {
    playIcon.setAttribute('data-lucide', 'pause');
    playText.innerText = 'Duraklat';
  } else {
    playIcon.setAttribute('data-lucide', 'play');
    playText.innerText = 'Oynat';
  }
  if (window.lucide) lucide.createIcons();
}

function onSeekChange(val) {
  if (audioPlayer.duration) {
    audioPlayer.currentTime = (val / 100) * audioPlayer.duration;
  }
}

function setVolume(val) {
  audioPlayer.volume = val / 100;
}

if (audioPlayer) {
  audioPlayer.ontimeupdate = () => {
    if (audioPlayer.duration) {
      const cur = formatTime(audioPlayer.currentTime);
      const dur = formatTime(audioPlayer.duration);
      playerTime.innerText = `${cur} / ${dur}`;
      audioSeek.value = (audioPlayer.currentTime / audioPlayer.duration) * 100;
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

function formatTime(secs) {
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

// Extraction Actions
async function extractSelectedSkin() {
  if (!selectedChampion || !selectedSkin) return;
  const btn = document.getElementById('btn-extract-selected');
  if (btn) btn.disabled = true;
  if (progressBarContainer) progressBarContainer.classList.remove('hidden');

  const skinVal = selectedSkin.value === "ALL" ? null : selectedSkin.value;
  const targetLabel = selectedSkin.label || selectedSkin.value;
  onLogMessage(`🚀 [${selectedChampion}] - ${targetLabel} için ses çıkarma başlatılıyor...`);

  try {
    const res = await fetch('/api/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ champion: selectedChampion, skin: skinVal })
    });
    const data = await res.json();
    if (data.status === 'busy') {
      onLogMessage(`⚠️ ${data.message}`);
      if (btn) btn.disabled = false;
      if (progressBarContainer) progressBarContainer.classList.add('hidden');
    }
  } catch (err) {
    onLogMessage(`❌ Sunucu bağlantı hatası: ${err}`);
    if (btn) btn.disabled = false;
    if (progressBarContainer) progressBarContainer.classList.add('hidden');
  }
}

async function extractAllSkins() {
  if (!selectedChampion) return;
  const btn = document.getElementById('btn-extract-all');
  if (btn) btn.disabled = true;
  if (progressBarContainer) progressBarContainer.classList.remove('hidden');

  onLogMessage(`🚀 [${selectedChampion}] için TÜM kostümlerin seslerini çıkarma başlatılıyor...`);

  try {
    const res = await fetch('/api/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ champion: selectedChampion, skin: null })
    });
    const data = await res.json();
    if (data.status === 'busy') {
      onLogMessage(`⚠️ ${data.message}`);
      if (btn) btn.disabled = false;
      if (progressBarContainer) progressBarContainer.classList.add('hidden');
    }
  } catch (err) {
    onLogMessage(`❌ Sunucu bağlantı hatası: ${err}`);
    if (btn) btn.disabled = false;
    if (progressBarContainer) progressBarContainer.classList.add('hidden');
  }
}

function clearConsole() {
  if (consoleLogs) consoleLogs.innerHTML = '';
}

function copyConsoleLogs() {
  if (!consoleLogs) return;
  const divs = Array.from(consoleLogs.querySelectorAll('div'));
  let textToCopy = '';
  if (divs.length > 0) {
    textToCopy = divs.map(d => d.innerText.trim()).filter(Boolean).join('\n');
  } else {
    textToCopy = consoleLogs.innerText.trim();
  }

  if (!textToCopy) return;

  const btn = document.getElementById('btn-copy-console');

  function showSuccess() {
    if (btn) {
      btn.innerHTML = `<i data-lucide="check" class="w-3 h-3 text-emerald-400"></i><span class="text-emerald-400 font-bold">Kopyalandı!</span>`;
      lucide.createIcons();
      setTimeout(() => {
        btn.innerHTML = `<i data-lucide="copy" class="w-3 h-3 text-hextech-gold"></i><span id="btn-copy-console-text">Kopyala</span>`;
        lucide.createIcons();
      }, 1800);
    }
  }

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(textToCopy).then(showSuccess).catch(() => {
      fallbackCopyText(textToCopy, showSuccess);
    });
  } else {
    fallbackCopyText(textToCopy, showSuccess);
  }
}

function fallbackCopyText(text, cb) {
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.left = '-999999px';
    ta.style.top = '-999999px';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    if (ok && cb) cb();
  } catch (e) {
    console.error("Copy fallback error:", e);
  }
}

function openOutputFolder(customFolder) {
  let targetFolder = '';
  if (customFolder) {
    targetFolder = customFolder;
  } else if (currentTab === 'references' && selectedRefChampion) {
    targetFolder = `${selectedRefChampion}/${selectedRefChampion}e_Yapilan_Tum_Ozel_Atiflar`;
  } else if (currentTab === 'wallpapers') {
    fetch('/api/wallpapers/open-folder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ champ_name: selectedChampion || '' })
    });
    return;
  } else if (currentTab === 'skinhub') {
    targetFolder = '_CDN_Downloads';
  } else {
    // Sol sidebar veya Ses sekmesi: En son çıkartılan ses hangi karaktere aitse oraya git,
    // hiç ses çıkartılmamışsa genel Champions klasörüne git.
    targetFolder = 'latest';
  }

  fetch('/api/open-folder', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ folder: targetFolder })
  });
}

