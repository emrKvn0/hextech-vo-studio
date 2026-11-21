// =========================================================================
// DAVINCI RESOLVE TIMELINE EXPORTER (WITH DYNAMIC GAP & TEXT+ FUSION)
// =========================================================================
let lastDaVinciExportFilePath = '';
let lastDaVinciAudioList = [];

async function exportToDaVinciTimeline() {
  if (!selectedChampion) {
    alert("Lütfen önce bir şampiyon seçin.");
    return;
  }

  const gapInput = document.getElementById('davinci-gap-input');
  let rawGap = gapInput ? String(gapInput.value || '0.8').trim().replace(',', '.') : '0.8';
  let gapSeconds = parseFloat(rawGap);
  if (isNaN(gapSeconds) || gapSeconds < 0) gapSeconds = 0.8;

  const fadeInInput = document.getElementById('davinci-fade-in-input');
  const fadeOutInput = document.getElementById('davinci-fade-out-input');
  const fadeInSec = fadeInInput ? parseFloat(fadeInInput.value) || 1.5 : 1.5;
  const fadeOutSec = fadeOutInput ? parseFloat(fadeOutInput.value) || 0.5 : 0.5;

  const btn = document.getElementById('btn-export-davinci');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin text-amber-300"></i><span>Üretiliyor...</span>`;
    if (window.lucide) lucide.createIcons();
  }

  let audioFilesList = [];
  try {
    if (typeof selectedAudioPaths !== 'undefined' && selectedAudioPaths && selectedAudioPaths.size > 0) {
      audioFilesList = Array.from(selectedAudioPaths);
    }
  } catch (e) {
    audioFilesList = [];
  }
  lastDaVinciAudioList = audioFilesList;

  const skinValue = selectedSkin ? (selectedSkin.value || '') : '';

  try {
    const res = await fetch('/api/export-davinci', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        champion: selectedChampion,
        skin: skinValue,
        gap_seconds: gapSeconds,
        fade_in_seconds: fadeInSec,
        fade_out_seconds: fadeOutSec,
        fps: 60,
        audio_files: audioFilesList
      })
    });

    const data = await res.json();
    if (data && data.status === 'success') {
      openDaVinciModal(data);
    } else {
      alert(data.message || "DaVinci Timeline dosyası oluşturulamadı.");
    }
  } catch (err) {
    console.error("DaVinci export error:", err);
    alert("Bağlantı hatası: " + err.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="film" class="w-3.5 h-3.5 text-amber-200"></i><span>DaVinci Timeline</span>`;
      if (window.lucide) lucide.createIcons();
    }
  }
}

async function checkDaVinciStatus() {
  try {
    const res = await fetch('/api/davinci-status');
    const status = await res.json();
    const badge = document.getElementById('davinci-status-badge');
    if (badge) {
      if (status.connected) {
        badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span><span class="text-emerald-300 font-bold">🟢 DaVinci ${status.version || ''} Bağlı: Proje '${status.project_name || 'Aktif'}'</span>`;
      } else {
        badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-amber-400"></span><span class="text-amber-300">Fusion Text+ & Auto Fade (1.5s In / 0.5s Out) Hazır</span>`;
      }
    }
    return status;
  } catch (e) {
    return { connected: false };
  }
}

function openDaVinciModal(data) {
  lastDaVinciExportFilePath = data.file_path || '';
  
  const fnEl = document.getElementById('davinci-res-filename');
  const countEl = document.getElementById('davinci-res-count');
  const gapEl = document.getElementById('davinci-res-gap');
  const durEl = document.getElementById('davinci-res-duration');

  const clipCount = data.clips_count !== undefined ? data.clips_count : (data.clip_count || 0);
  const totalDur = data.total_duration_sec !== undefined ? data.total_duration_sec : (data.total_duration || 0);

  if (fnEl) {
    fnEl.innerText = data.file_name || 'timeline.xml';
    fnEl.title = data.file_path || '';
  }
  if (countEl) countEl.innerText = `${clipCount} ses parçası`;
  if (gapEl) gapEl.innerText = `${(data.gap_seconds || 0.8).toFixed(2)} saniye`;
  if (durEl) {
    const mins = Math.floor(totalDur / 60);
    const secs = Math.floor(totalDur % 60);
    durEl.innerText = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')} (${totalDur.toFixed(1)} sn)`;
  }

  const clipBanner = document.getElementById('davinci-clipboard-banner');
  if (clipBanner) {
    if (data.clipboard_copied) {
      clipBanner.classList.remove('hidden');
    }
  }

  const modal = document.getElementById('davinci-modal');
  if (modal) modal.classList.remove('hidden');
  if (window.lucide) lucide.createIcons();

  checkDaVinciStatus();
}

function closeDaVinciModal() {
  const modal = document.getElementById('davinci-modal');
  if (modal) modal.classList.add('hidden');
}

async function openDaVinciFileLocation() {
  if (!lastDaVinciExportFilePath) return;
  try {
    await fetch('/api/open-file-location', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_path: lastDaVinciExportFilePath })
    });
  } catch (err) {
    console.error("Open file location error:", err);
  }
}

// ⚡ Direct Push To DaVinci via Python Scripting API
async function directPushToDaVinci() {
  const btn = document.getElementById('btn-davinci-direct-push');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin text-white"></i><span>Aktarılıyor...</span>`;
    if (window.lucide) lucide.createIcons();
  }

  const gapInput = document.getElementById('davinci-gap-input');
  const gapSeconds = gapInput ? parseFloat(gapInput.value) || 0.2 : 0.2;
  const fadeInInput = document.getElementById('davinci-fade-in-input');
  const fadeOutInput = document.getElementById('davinci-fade-out-input');
  const fadeInSec = fadeInInput ? parseFloat(fadeInInput.value) || 1.5 : 1.5;
  const fadeOutSec = fadeOutInput ? parseFloat(fadeOutInput.value) || 0.5 : 0.5;

  const skinValue = selectedSkin ? (selectedSkin.value || '') : '';

  try {
    const res = await fetch('/api/davinci-direct-push', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        champion: selectedChampion,
        skin: skinValue,
        gap_seconds: gapSeconds,
        fade_in_seconds: fadeInSec,
        fade_out_seconds: fadeOutSec,
        fps: 60,
        audio_files: lastDaVinciAudioList
      })
    });
    const result = await res.json();
    if (result.status === 'success') {
      showToast(`🎬 DaVinci'ye Doğrudan Aktarıldı: ${result.clip_count} ses & Text+!`);
      alert(`✨ Başarılı!\n\n${result.message}`);
    } else {
      alert(`⚠️ DaVinci Aktarım Bildirimi:\n\n${result.message}`);
    }
  } catch (e) {
    alert("Bağlantı hatası: " + e.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="play-circle" class="w-4 h-4"></i><span>⚡ DaVinci'ye Doğrudan Aktar</span>`;
      if (window.lucide) lucide.createIcons();
    }
  }
}

// 🔄 Convert Existing Timeline Text to Text+ with Anim Curves Fade
async function convertActiveTimelineTextPlus() {
  const btn = document.getElementById('btn-davinci-convert-text');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin text-white"></i><span>Dönüştürülüyor...</span>`;
    if (window.lucide) lucide.createIcons();
  }

  const fadeInInput = document.getElementById('davinci-fade-in-input');
  const fadeOutInput = document.getElementById('davinci-fade-out-input');
  const fadeInSec = fadeInInput ? parseFloat(fadeInInput.value) || 1.5 : 1.5;
  const fadeOutSec = fadeOutInput ? parseFloat(fadeOutInput.value) || 0.5 : 0.5;

  try {
    const res = await fetch('/api/davinci-convert-textplus', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        fade_in_seconds: fadeInSec,
        fade_out_seconds: fadeOutSec
      })
    });
    const result = await res.json();
    if (result.status === 'success') {
      showToast(`✨ ${result.converted_count} klip Text+ yapıldı!`);
      alert(`🎉 Başarılı!\n\n${result.message}`);
    } else {
      alert(`⚠️ DaVinci Bildirimi:\n\n${result.message}`);
    }
  } catch (e) {
    alert("Bağlantı hatası: " + e.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="refresh-cw" class="w-4 h-4"></i><span>🔄 Açık Metinleri Text+'a Çevir</span>`;
      if (window.lucide) lucide.createIcons();
    }
  }
}

// 🛠️ Install DaVinci Menu Scripts
async function installDaVinciMenuScripts() {
  const btn = document.getElementById('btn-davinci-install-script');
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin text-amber-300"></i><span>Kuruluyor...</span>`;
    if (window.lucide) lucide.createIcons();
  }

  try {
    const res = await fetch('/api/davinci-install-scripts', { method: 'POST' });
    const result = await res.json();
    if (result.status === 'success') {
      showToast("🛠️ DaVinci Workspace menü scriptleri yüklendi!");
      alert(`🎉 DaVinci Resolve Eklentisi Başarıyla Kuruldu!\n\nDaVinci Resolve programını açtığınızda üst menüden:\n👉 Workspace -> Scripts -> Edit -> LoL_Convert_To_TextPlus_Fade\nkomutunu tek tıkla çalıştırarak açık projenizdeki tüm metinleri Text+'a ve 1.5s Fade In / 0.5s Fade Out'a dönüştürebilirsiniz!`);
    } else {
      alert("Hata: " + result.message);
    }
  } catch (e) {
    alert("Kurulum hatası: " + e.message);
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<i data-lucide="download" class="w-3.5 h-3.5 text-hextech-gold"></i><span>DaVinci Menü Eklentisini Kur</span>`;
      if (window.lucide) lucide.createIcons();
    }
  }
}

