import React, { useState, useEffect, useMemo, useRef } from 'react';
import DaVinciExportModal from './DaVinciExportModal';
import TranscriptGeneratorModal from './TranscriptGeneratorModal';
import { 
  Search, Play, Square, Loader2, Sparkles, Volume2, Volume1, VolumeX, 
  Copy, Check, ChevronRight, Layers, MessageSquare, Zap, Shield, 
  Flame, Crown, Users, ShoppingBag, Smile, Skull, Compass, Activity,
  Filter, SlidersHorizontal, RefreshCw, CheckCircle2, AlertCircle,
  Download, FolderDown, FolderOpen, CheckSquare, X, Film, Brain
} from 'lucide-react';

const CATEGORY_ICONS = {
  "0_Secim_ve_Ozel_Sesler": Sparkles,
  "1_Q_Yetenegi": Zap,
  "2_W_Yetenegi": Shield,
  "3_E_Yetenegi": Flame,
  "4_R_Ulti": Crown,
  "5_Ozel_Karsilasmalar_ve_Atiflar": Users,
  "6_Esya_Alimi_ve_Magaza": ShoppingBag,
  "7_Saka_Kiskirtma_Kahkaha": Smile,
  "8_Donus_ve_Olum": Skull,
  "9_Hareket_ve_Saldiri": Compass,
  "10_Genel_Replikler": MessageSquare,
  "11_Efektler_ve_Homurtular": Activity
};

const CATEGORY_COLORS = {
  "0_Secim_ve_Ozel_Sesler": "amber",
  "1_Q_Yetenegi": "cyan",
  "2_W_Yetenegi": "blue",
  "3_E_Yetenegi": "orange",
  "4_R_Ulti": "rose",
  "5_Ozel_Karsilasmalar_ve_Atiflar": "purple",
  "6_Esya_Alimi_ve_Magaza": "emerald",
  "7_Saka_Kiskirtma_Kahkaha": "yellow",
  "8_Donus_ve_Olum": "red",
  "9_Hareket_ve_Saldiri": "teal",
  "10_Genel_Replikler": "slate",
  "11_Efektler_ve_Homurtular": "pink"
};

export default function ChampionVoicesView({ champions = [], defaultChamp = 'Yasuo', gameMode = 'lol', audioVolume = 85 }) {
  const [selectedChamp, setSelectedChamp] = useState(defaultChamp);
  const [selectedSkinNum, setSelectedSkinNum] = useState(0);
  const [includeSfx, setIncludeSfx] = useState(true);
  
  const [voiceData, setVoiceData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [champSearch, setChampSearch] = useState('');
  const [voiceSearch, setVoiceSearch] = useState('');
  const [activeCategoryFilter, setActiveCategoryFilter] = useState('all');
  const [skinFilterMode, setSkinFilterMode] = useState('all'); // 'all' vs 'unique_only'

  // Oyun modu değiştiğinde ilk şampiyonu seç
  useEffect(() => {
    if (champions.length > 0 && !champions.some(c => c.name.toLowerCase() === selectedChamp.toLowerCase())) {
      setSelectedChamp(champions[0].name);
      setSelectedSkinNum(0);
    }
  }, [champions, gameMode]);

  // Seçili kostümün detaylı dublaj durumu ve video potansiyeli
  const currentSkinObj = useMemo(() => {
    return voiceData?.skins?.find(s => s.skin_num === selectedSkinNum) || voiceData?.skins?.[0] || null;
  }, [voiceData, selectedSkinNum]);

  // Kostüm listesi (Eşsiz dublaj filtresi desteği)
  const availableSkins = useMemo(() => {
    const list = voiceData?.skins || [];
    if (skinFilterMode === 'unique_only') {
      return list.filter(s => s.is_unique || s.skin_num === 0);
    }
    return list;
  }, [voiceData, skinFilterMode]);

  // Audio Player State
  const [playingId, setPlayingId] = useState(null);
  const [audioLoadingId, setAudioLoadingId] = useState(null);
  const audioInstanceRef = useRef(null);

  // Genel Ses Seviyesi (Volume Slider) & Mute
  const [volume, setVolume] = useState(() => {
    try {
      const saved = localStorage.getItem('lol_audio_volume');
      return saved !== null ? parseFloat(saved) : (audioVolume ? audioVolume / 100 : 0.85);
    } catch(e) {
      return 0.85;
    }
  });
  const [isMuted, setIsMuted] = useState(false);

  const handleVolumeChange = (newVol) => {
    setVolume(newVol);
    try {
      localStorage.setItem('lol_audio_volume', newVol.toString());
      localStorage.setItem('lol_matrix_audio_volume', String(Math.round(newVol * 100)));
    } catch(e) {}
    if (audioInstanceRef.current) {
      audioInstanceRef.current.volume = isMuted ? 0 : newVol;
    }
  };

  const toggleMute = () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    if (audioInstanceRef.current) {
      audioInstanceRef.current.volume = nextMuted ? 0 : volume;
    }
  };

  useEffect(() => {
    if (audioInstanceRef.current) {
      audioInstanceRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  // Copy state
  const [copiedId, setCopiedId] = useState(null);

  // Download & Batch State
  const [downloadingBatch, setDownloadingBatch] = useState(false);
  const [batchSuccess, setBatchSuccess] = useState(null);
  const [singleDownloadAlert, setSingleDownloadAlert] = useState(null);
  const [downloadingSingleId, setDownloadingSingleId] = useState(null);
  const [folderOpening, setFolderOpening] = useState(false);
  const [selectionMode, setSelectionMode] = useState(true);
  const [selectedWems, setSelectedWems] = useState(new Set());
  const [isDaVinciModalOpen, setIsDaVinciModalOpen] = useState(false);
  const [isTranscriptModalOpen, setIsTranscriptModalOpen] = useState(false);
  const [groupByCategory, setGroupByCategory] = useState(true);
  const [batchModalOpen, setBatchModalOpen] = useState(false);
  const [batchModalItems, setBatchModalItems] = useState([]);
  const [batchModalTitle, setBatchModalTitle] = useState('');

  // Şampiyon filtreleme
  const filteredChamps = useMemo(() => {
    if (!champSearch.trim()) return champions;
    const q = champSearch.toLowerCase().trim();
    return champions.filter(c => c.name.toLowerCase().includes(q));
  }, [champions, champSearch]);

  // Şampiyon veya kostüm değiştiğinde ses verisini çek
  useEffect(() => {
    if (!selectedChamp) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    const url = `http://127.0.0.1:8080/api/champion-voices?champion=${encodeURIComponent(selectedChamp)}&skin_num=${selectedSkinNum}&include_sfx=${includeSfx}&game=${gameMode}`;

    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error(`Sunucu hatası: ${res.status}`);
        return res.json();
      })
      .then(json => {
        if (isMounted) {
          setVoiceData(json);
          setLoading(false);
        }
      })
      .catch(err => {
        if (isMounted) {
          console.error("Ses verisi çekme hatası:", err);
          setError("Şampiyon sesleri yüklenirken hata oluştu. Lütfen ses sunucusunun (Port 8080) çalıştığından emin olun.");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedChamp, selectedSkinNum, includeSfx]);

  // Ses çalma motoru
  const playAudio = (item, wem) => {
    const uniquePlayKey = `${item.raw_event}_${wem.wem_id || '0'}`;

    if (playingId === uniquePlayKey) {
      if (audioInstanceRef.current) {
        audioInstanceRef.current.pause();
        audioInstanceRef.current = null;
      }
      setPlayingId(null);
      return;
    }

    if (audioInstanceRef.current) {
      audioInstanceRef.current.pause();
      audioInstanceRef.current = null;
    }

    setAudioLoadingId(uniquePlayKey);

    const playUrl = `http://127.0.0.1:8080/api/audio-play?speaker=${encodeURIComponent(selectedChamp)}&event=${encodeURIComponent(item.raw_event)}&wem_id=${wem.wem_id || ''}`;
    const audio = new Audio(playUrl);
    audio.volume = isMuted ? 0 : volume;
    audioInstanceRef.current = audio;

    audio.oncanplaythrough = () => {
      setAudioLoadingId(null);
      setPlayingId(uniquePlayKey);
      audio.play().catch(e => {
        console.error("Audio play error:", e);
        setPlayingId(null);
      });
    };

    audio.onended = () => {
      setPlayingId(null);
      audioInstanceRef.current = null;
    };

    audio.onerror = () => {
      setAudioLoadingId(null);
      setPlayingId(null);
      audioInstanceRef.current = null;
    };
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  // Tekil WAV İndir (Doğrudan Klasöre Kaydeder ve Ekranda Alert + Klasörü Gör Butonu Gösterir)
  const handleDownloadSingle = async (item, wem, catTitle = '') => {
    const playKey = `${item.raw_event}_${wem.wem_id || '0'}`;
    setDownloadingSingleId(playKey);
    
    try {
      const res = await fetch('http://127.0.0.1:8080/api/save-single-wav', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          speaker: selectedChamp,
          event: item.raw_event,
          wem_id: wem.wem_id || '',
          action_name: item.action_name,
          category_title: catTitle || 'Genel',
          open_folder: false
        })
      });

      if (!res.ok) throw new Error(`Sunucu hatası: ${res.status}`);
      const data = await res.json();
      
      // Kullanıcıya şık alert bildirimi ver
      setSingleDownloadAlert({
        action_name: item.action_name || 'Replik',
        speaker: selectedChamp,
        folder_path: data.folder_path,
        file_path: data.file_path,
        filename: data.filename,
        category_title: catTitle || data.category_title,
        transcript: wem.transcript
      });
    } catch (err) {
      console.error("Tekil indirme hatası:", err);
      alert("Ses indirilirken bir hata oluştu: " + err.message);
    } finally {
      setDownloadingSingleId(null);
    }
  };

  // Toplu WAV Klasörüne Aktar (ZIP'siz - Doğrudan Diske ve Klasör Aç)
  const handleExecuteBatchExport = async (itemsToExport, customFolderName = '') => {
    if (!itemsToExport || itemsToExport.length === 0) return;
    setDownloadingBatch(true);
    setBatchSuccess(null);

    try {
      const payload = {
        champion: selectedChamp,
        folder_name: customFolderName || selectedChamp,
        group_by_category: groupByCategory,
        open_folder: true,
        items: itemsToExport.map(it => ({
          speaker: selectedChamp,
          event: it.raw_event,
          wem_id: it.wem_id || '',
          action_name: it.action_name,
          category_title: it.category_title || it.category_id || 'Genel'
        }))
      };

      const res = await fetch('http://127.0.0.1:8080/api/batch-export-wavs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error(`Sunucu hatası: ${res.status}`);
      const data = await res.json();
      setBatchSuccess(data);
      setBatchModalOpen(false);
    } catch (err) {
      console.error("Toplu indirme hatası:", err);
      alert("Toplu ses aktarımı sırasında bir hata oluştu: " + err.message);
    } finally {
      setDownloadingBatch(false);
    }
  };

  // Windows Klasörünü Doğrudan Aç (İsteğe bağlı dosyayı seçili olarak açar)
  const handleOpenFolder = async (folderPath, filePath = '') => {
    setFolderOpening(true);
    try {
      await fetch('http://127.0.0.1:8080/api/open-folder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder_path: folderPath, file_path: filePath })
      });
    } catch (e) {
      console.error("Klasör açma hatası:", e);
    } finally {
      setTimeout(() => setFolderOpening(false), 2000);
    }
  };

  // Çoklu Seçim Toggle
  const toggleSelectWem = (uniqueKey) => {
    setSelectedWems(prev => {
      const next = new Set(prev);
      if (next.has(uniqueKey)) next.delete(uniqueKey);
      else next.add(uniqueKey);
      return next;
    });
  };

  // Kategori İndirme Başlat
  const startCategoryBatchExport = (cat) => {
    const items = [];
    cat.items.forEach(item => {
      item.wems.forEach(wem => {
        items.push({
          raw_event: item.raw_event,
          wem_id: wem.wem_id,
          action_name: item.action_name,
          category_title: cat.title,
          category_id: cat.id
        });
      });
    });
    setBatchModalItems(items);
    setBatchModalTitle(`${cat.title} (${items.length} WAV Ses)`);
    setBatchModalOpen(true);
  };

  // Tüm Şampiyon Seslerini İndirme Başlat
  const startAllVoicesBatchExport = () => {
    if (!voiceData || !voiceData.categories) return;
    const items = [];
    voiceData.categories.forEach(cat => {
      cat.items.forEach(item => {
        item.wems.forEach(wem => {
          items.push({
            raw_event: item.raw_event,
            wem_id: wem.wem_id,
            action_name: item.action_name,
            category_title: cat.title,
            category_id: cat.id
          });
        });
      });
    });
    setBatchModalItems(items);
    setBatchModalTitle(`Tüm ${selectedChamp} Sesleri (${items.length} WAV Ses)`);
    setBatchModalOpen(true);
  };

  // Seçilenleri İndirme Başlat
  const startSelectedBatchExport = () => {
    if (!voiceData || !voiceData.categories || selectedWems.size === 0) return;
    const items = [];
    voiceData.categories.forEach(cat => {
      cat.items.forEach(item => {
        item.wems.forEach(wem => {
          const key = `${item.raw_event}_${wem.wem_id || '0'}`;
          if (selectedWems.has(key)) {
            items.push({
              raw_event: item.raw_event,
              wem_id: wem.wem_id,
              action_name: item.action_name,
              category_title: cat.title,
              category_id: cat.id
            });
          }
        });
      });
    });
    setBatchModalItems(items);
    setBatchModalTitle(`Seçilen ${items.length} Adet Ses`);
    setBatchModalOpen(true);
  };

  // Kategori Bazlı Çoklu Seç / Kaldır
  const toggleSelectCategory = (cat) => {
    setSelectionMode(true);
    setSelectedWems(prev => {
      const next = new Set(prev);
      const catKeys = [];
      cat.items.forEach(it => {
        it.wems.forEach(w => {
          catKeys.push(`${it.raw_event}_${w.wem_id || '0'}`);
        });
      });
      const allSelected = catKeys.length > 0 && catKeys.every(k => next.has(k));
      if (allSelected) {
        catKeys.forEach(k => next.delete(k));
      } else {
        catKeys.forEach(k => next.add(k));
      }
      return next;
    });
  };

  // Görünür Tüm Replikleri Seç / Temizle
  const toggleSelectAllVisible = () => {
    if (!displayedCategories || displayedCategories.length === 0) return;
    setSelectionMode(true);
    setSelectedWems(prev => {
      const next = new Set(prev);
      const allKeys = [];
      displayedCategories.forEach(cat => {
        cat.items.forEach(it => {
          it.wems.forEach(w => {
            allKeys.push(`${it.raw_event}_${w.wem_id || '0'}`);
          });
        });
      });
      const allSelected = allKeys.length > 0 && allKeys.every(k => next.has(k));
      if (allSelected) {
        allKeys.forEach(k => next.delete(k));
      } else {
        allKeys.forEach(k => next.add(k));
      }
      return next;
    });
  };

  // DaVinci Resolve FCPXML için seçilen replikleri zengin objelere dönüştür
  const selectedDaVinciItems = useMemo(() => {
    if (!voiceData || !voiceData.categories || selectedWems.size === 0) return [];
    const list = [];
    const spkSkinName = voiceData.skin_name || `Varsayılan ${selectedChamp}`;
    voiceData.categories.forEach(cat => {
      cat.items.forEach(item => {
        item.wems.forEach(wem => {
          const key = `${item.raw_event}_${wem.wem_id || '0'}`;
          if (selectedWems.has(key)) {
            list.push({
              speaker_champ: selectedChamp,
              speaker_skin_num: selectedSkinNum,
              speaker_skin_name: spkSkinName,
              target_champ: item.target_champ || '',
              target_skin_num: item.target_skin_num || 0,
              target_skin_name: item.target_skin_name || '',
              raw_event: item.raw_event,
              action_type: item.action_name,
              action_name: item.action_name,
              wem_id: wem.wem_id,
              transcript: wem.transcript || ''
            });
          }
        });
      });
    });
    return list;
  }, [voiceData, selectedWems, selectedChamp, selectedSkinNum, gameMode]);

  // Şampiyona ait tüm repliklerin DaVinci/Transkript listesi (seçim olmasa da çözümleme için)
  const allCategoryDaVinciItems = useMemo(() => {
    if (!voiceData || !voiceData.categories) return [];
    const list = [];
    const spkSkinName = voiceData.skin_name || `Varsayılan ${selectedChamp}`;
    voiceData.categories.forEach(cat => {
      cat.items?.forEach(item => {
        item.wems?.forEach(wem => {
          list.push({
            speaker_champ: selectedChamp,
            speaker_skin_num: selectedSkinNum,
            speaker_skin_name: spkSkinName,
            target_champ: item.target_champ || '',
            target_skin_num: item.target_skin_num || 0,
            target_skin_name: item.target_skin_name || '',
            raw_event: item.raw_event,
            action_type: item.action_name,
            action_name: item.action_name,
            wem_id: wem.wem_id,
            transcript: wem.transcript || '',
            game: gameMode
          });
        });
      });
    });
    return list;
  }, [voiceData, selectedChamp, selectedSkinNum, gameMode]);

  // Kategorilere göre filtrelenmiş ve arama yapılmış sesler
  const displayedCategories = useMemo(() => {
    if (!voiceData || !voiceData.categories) return [];

    let cats = voiceData.categories;
    if (activeCategoryFilter !== 'all') {
      cats = cats.filter(c => c.id === activeCategoryFilter);
    }

    if (voiceSearch.trim()) {
      const q = voiceSearch.toLowerCase().trim();
      cats = cats.map(cat => ({
        ...cat,
        items: cat.items.filter(it => 
          it.raw_event.toLowerCase().includes(q) ||
          it.action_name.toLowerCase().includes(q) ||
          it.wems.some(w => (w.transcript || '').toLowerCase().includes(q) || String(w.wem_id).includes(q))
        )
      })).filter(cat => cat.items.length > 0);
    }

    return cats;
  }, [voiceData, activeCategoryFilter, voiceSearch]);

  const totalItemsCount = useMemo(() => {
    if (!voiceData || !voiceData.categories) return 0;
    return voiceData.categories.reduce((acc, c) => acc + c.count, 0);
  }, [voiceData]);

  const totalWemsCount = useMemo(() => {
    if (!voiceData || !voiceData.categories) return 0;
    return voiceData.categories.reduce((acc, c) => acc + c.total_wems, 0);
  }, [voiceData]);

  return (
    <div className="flex-1 flex flex-col lg:flex-row overflow-hidden bg-[#1e222d] text-slate-100 rounded-2xl border border-slate-700/60 shadow-xl min-h-0">
      
      {/* SOL PANEL: ŞAMPİYON LİSTESİ */}
      <aside className="w-full lg:w-80 border-b lg:border-b-0 lg:border-r border-slate-700/60 bg-[#232836] flex flex-col shrink-0 max-h-[38vh] lg:max-h-none">
        
        {/* Arama & Başlık */}
        <div className="p-3.5 border-b border-slate-700/60 space-y-2 bg-[#262c3c]">
          <div className="flex items-center justify-between">
            <span className="text-xs font-extrabold uppercase tracking-wider text-indigo-200 font-['Cinzel'] flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-indigo-300" />
              <span>Şampiyon Seçimi</span>
            </span>
            <span className="text-[11px] font-mono text-slate-300 bg-[#1e222d] px-2 py-0.5 rounded-full border border-slate-700/70">
              {filteredChamps.length} / {champions.length}
            </span>
          </div>

          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={champSearch}
              onChange={e => setChampSearch(e.target.value)}
              placeholder="Şampiyon ara (örn: Yasuo, Zed)..."
              className="w-full bg-[#1e222d] border border-slate-600/70 focus:border-indigo-400 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 outline-none transition placeholder:text-slate-400 font-medium"
            />
          </div>
        </div>

        {/* Şampiyon Listesi */}
        <div className="flex-1 overflow-y-auto divide-y divide-slate-700/40 p-2 space-y-1 scrollbar-thin">
          {filteredChamps.map(c => {
            const isSelected = c.name.toLowerCase() === selectedChamp.toLowerCase();
            return (
              <button
                key={c.name}
                onClick={() => {
                  setSelectedChamp(c.name);
                  setSelectedSkinNum(0); // Şampiyon değişince varsayılana dön
                }}
                className={`w-full flex items-center justify-between p-2 rounded-xl transition cursor-pointer text-left ${
                  isSelected
                    ? 'bg-[#2f374d] border border-indigo-400/80 shadow-md'
                    : 'hover:bg-[#2a3042] border border-transparent'
                }`}
              >
                <div className="flex items-center space-x-2.5">
                  <div className="relative">
                    <img
                      src={c.icon_url}
                      alt={c.name}
                      className={`w-9 h-9 rounded-lg object-cover border ${
                        isSelected ? 'border-indigo-300 ring-2 ring-indigo-400/30' : 'border-slate-600'
                      }`}
                      loading="lazy"
                      onError={e => { e.target.src = 'https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/-1.png'; }}
                    />
                  </div>
                  <div>
                    <div className={`text-xs font-extrabold tracking-wide ${isSelected ? 'text-indigo-200' : 'text-slate-200'}`}>
                      {c.name}
                    </div>
                    <div className="text-[10px] text-slate-300 font-mono">
                      {c.total_incoming || 0} atıf • {c.unique_speakers_incoming || 0} konuşmacı
                    </div>
                  </div>
                </div>

                <ChevronRight className={`w-4 h-4 transition ${isSelected ? 'text-indigo-300 translate-x-0.5' : 'text-slate-500'}`} />
              </button>
            );
          })}
        </div>
      </aside>

      {/* SAĞ PANEL: ŞAMPİYON REPLİK VE SFX STÜDYOSU */}
      <main className="flex-1 flex flex-col overflow-hidden bg-[#1e222d]">
        
        {/* Şampiyon Başlık Banner & Filtreler */}
        <header className="border-b border-slate-700/60 bg-[#252a3a] p-4 lg:p-5 shrink-0 space-y-4">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            
            {/* Şampiyon Bilgisi */}
            <div className="flex items-center space-x-4">
              <div className="relative shrink-0">
                <img
                  src={voiceData?.splash_url || `https://ddragon.leagueoflegends.com/cdn/img/champion/splash/${selectedChamp}_0.jpg`}
                  alt={selectedChamp}
                  className="w-16 h-16 lg:w-20 lg:h-20 rounded-2xl object-cover object-top border-2 border-indigo-400/80 shadow-md"
                  onError={e => { e.target.src = 'https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/-1.png'; }}
                />
                <span className="absolute -bottom-1 -right-1 px-1.5 py-0.5 rounded-md bg-indigo-500 text-white text-[10px] font-black font-mono shadow">
                  VO
                </span>
              </div>

              <div>
                <div className="flex items-center space-x-2.5">
                  <h2 className="text-xl lg:text-2xl font-black text-slate-100 font-['Cinzel'] tracking-wide">
                    {selectedChamp}
                  </h2>
                  <span className="px-2.5 py-0.5 rounded-full bg-teal-500/20 text-teal-200 border border-teal-400/40 text-[11px] font-extrabold font-mono">
                    {voiceData?.skin_name || `Varsayılan ${selectedChamp}`}
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-1 font-medium">
                  Yetenek naraları, şakalar, kışkırtmalar, yürüme ve dövüş sesleri • %100 Deterministik HIRC
                </p>
              </div>
            </div>

            {/* Üst İşlemler & İstatistikler */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="hidden sm:flex items-center space-x-2 text-xs font-mono">
                <div className="px-3 py-1.5 rounded-xl bg-[#1e222d] border border-slate-600/70 flex items-center space-x-2">
                  <Activity className="w-3.5 h-3.5 text-sky-300" />
                  <span className="text-slate-300">Olay:</span>
                  <span className="font-bold text-sky-200 text-sm">{totalItemsCount}</span>
                </div>
                <div className="px-3 py-1.5 rounded-xl bg-[#1e222d] border border-slate-600/70 flex items-center space-x-2">
                  <Volume2 className="w-3.5 h-3.5 text-indigo-300" />
                  <span className="text-slate-300">Ses:</span>
                  <span className="font-bold text-indigo-200 text-sm">{totalWemsCount}</span>
                </div>
              </div>

              {/* Çoklu Seçim Modu Butonu */}
              <button
                onClick={() => {
                  setSelectionMode(!selectionMode);
                  if (selectionMode) setSelectedWems(new Set());
                }}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer border ${
                  selectionMode
                    ? 'bg-sky-500/20 text-sky-200 border-sky-400/60 ring-1 ring-sky-400/30'
                    : 'bg-[#1e222d] hover:bg-[#2f364a] text-slate-200 border-slate-600/70'
                }`}
                title="Sesleri tek tek veya kategoriyle seçip DaVinci Resolve FCPXML veya WAV olarak aktarmak için tıkla"
              >
                <CheckSquare className="w-3.5 h-3.5 text-sky-300" />
                <span>{selectionMode ? `Seçim Modu (${selectedWems.size})` : 'Çoklu Seç'}</span>
              </button>

              {/* Görünür Tümünü Seç / Kaldır */}
              <button
                onClick={toggleSelectAllVisible}
                disabled={totalWemsCount === 0}
                className="px-3 py-1.5 rounded-xl bg-[#1e222d] hover:bg-[#2f364a] text-indigo-200 border border-indigo-400/50 text-xs font-bold transition flex items-center space-x-1.5 cursor-pointer disabled:opacity-50"
                title="Ekrandaki tüm replikleri DaVinci Resolve veya WAV aktarımı için seç/bırak"
              >
                <CheckSquare className="w-3.5 h-3.5 text-indigo-300" />
                <span>Tümünü Seç</span>
              </button>

              {/* Replik Metinlerini Üret Butonu (Seçim varsa seçilenleri, yoksa tüm şampiyon repliklerini çözer) */}
              <button
                onClick={() => setIsTranscriptModalOpen(true)}
                disabled={allCategoryDaVinciItems.length === 0}
                className="px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-extrabold text-xs transition flex items-center space-x-1.5 cursor-pointer shadow-md disabled:opacity-50"
                title="XML üretmeksizin repliklerin metinlerini Çoklu Yapay Zeka & Fonetik Güven Skoru ile çözümleyin ve arayüzde gösterin"
              >
                <Brain className="w-3.5 h-3.5 text-purple-200" />
                <span>Replik Metinlerini Üret ({selectedWems.size > 0 ? selectedWems.size : allCategoryDaVinciItems.length})</span>
              </button>

              {/* Seçilenleri DaVinci Resolve'a Aktar (FCPXML Layout 1) */}
              {selectedWems.size > 0 && (
                <button
                  onClick={() => setIsDaVinciModalOpen(true)}
                  className="px-3.5 py-1.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white font-extrabold text-xs transition flex items-center space-x-1.5 cursor-pointer shadow-md"
                  title="Seçilen replikleri Karakter Replikleri Özel Layout'u (%100 Tam Ekran / Hedef Varsa %50-%50 Bölünmüş) ile DaVinci FCPXML olarak aktar"
                >
                  <Film className="w-3.5 h-3.5" />
                  <span>DaVinci FCPXML ({selectedWems.size})</span>
                </button>
              )}

              {/* Seçilenleri Klasöre Aktar (Seçim varsa) */}
              {selectedWems.size > 0 && (
                <button
                  onClick={startSelectedBatchExport}
                  className="px-3 py-1.5 rounded-xl bg-sky-500 hover:bg-sky-400 text-slate-950 font-extrabold text-xs transition flex items-center space-x-1.5 cursor-pointer shadow-md"
                >
                  <FolderDown className="w-3.5 h-3.5" />
                  <span>WAV İndir ({selectedWems.size})</span>
                </button>
              )}

              {/* Tüm Sesleri Klasöre Aktar Butonu */}
              <button
                onClick={startAllVoicesBatchExport}
                disabled={totalWemsCount === 0}
                className="px-3.5 py-1.5 rounded-xl bg-[#1e222d] hover:bg-[#2f364a] text-slate-200 border border-slate-600/70 font-bold text-xs transition flex items-center space-x-1.5 cursor-pointer disabled:opacity-50"
                title="Tüm sesleri ZIP olmadan doğrudan bilgisayarınızdaki bir klasöre WAV olarak aktarır"
              >
                <FolderDown className="w-3.5 h-3.5 text-indigo-300" />
                <span>Tümünü WAV Aktar</span>
              </button>

              {/* Genel Ses Seviyesi Slider'ı (Volume Control) */}
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#1e222d] border border-slate-600/70 text-xs text-slate-200 shadow-sm" title={`Ses Seviyesi: %${Math.round((isMuted ? 0 : volume) * 100)}`}>
                <button
                  type="button"
                  onClick={toggleMute}
                  className="hover:text-amber-400 transition cursor-pointer p-0.5"
                  title={isMuted ? "Sesi Aç" : "Sesi Kapat (Mute)"}
                >
                  {isMuted || volume === 0 ? (
                    <VolumeX className="w-4 h-4 text-red-400" />
                  ) : volume < 0.5 ? (
                    <Volume1 className="w-4 h-4 text-amber-300" />
                  ) : (
                    <Volume2 className="w-4 h-4 text-amber-400" />
                  )}
                </button>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={isMuted ? 0 : volume}
                  onChange={(e) => handleVolumeChange(parseFloat(e.target.value))}
                  className="w-16 sm:w-20 h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-amber-400"
                />
                <span className="text-[11px] font-mono text-slate-300 w-7 text-right font-bold">
                  {isMuted ? '%0' : `%${Math.round(volume * 100)}`}
                </span>
              </div>
            </div>
          </div>

          {/* Başarılı Klasöre Aktarma Bildirimi */}
          {batchSuccess && (
            <div className="p-3.5 rounded-xl bg-teal-500/15 border border-teal-400/50 flex items-center justify-between gap-3 animate-in fade-in">
              <div className="flex items-center space-x-2.5 min-w-0">
                <CheckCircle2 className="w-5 h-5 text-teal-300 shrink-0" />
                <div className="min-w-0">
                  <div className="text-xs font-bold text-teal-200">
                    Toplam {batchSuccess.exported_count} Adet WAV Sesi Başarıyla Klasöre Aktarıldı! (ZIP'siz)
                  </div>
                  <div className="text-[11px] font-mono text-slate-300 truncate">
                    📁 {batchSuccess.folder_path}
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2 shrink-0">
                <button
                  onClick={() => handleOpenFolder(batchSuccess.folder_path)}
                  className="px-3 py-1.5 rounded-lg bg-teal-500 hover:bg-teal-400 text-slate-950 font-black text-xs flex items-center space-x-1.5 transition cursor-pointer"
                >
                  <FolderOpen className="w-3.5 h-3.5" />
                  <span>Klasörü Aç</span>
                </button>
                <button
                  onClick={() => setBatchSuccess(null)}
                  className="p-1 rounded-lg hover:bg-slate-700 text-slate-300 hover:text-white transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* Kontrol Çubuğu: Kostüm Seçici & SFX Toggle & Arama & Video Potansiyeli Etiketleri */}
          <div className="flex flex-col gap-2.5 pt-2 border-t border-slate-700/60">
            <div className="flex flex-wrap items-center justify-between gap-3">
              
              {/* Sol Taraf: Kostüm Seçici & Eşsiz Dublaj Filtresi */}
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs font-bold text-slate-300">Kostüm:</span>
                <select
                  value={selectedSkinNum}
                  onChange={e => setSelectedSkinNum(Number(e.target.value))}
                  className="bg-[#1e222d] border border-slate-600/70 focus:border-indigo-400 rounded-lg px-3 py-1.5 text-xs font-bold text-indigo-200 outline-none cursor-pointer transition max-w-[280px] truncate shadow-sm"
                >
                  {(availableSkins.length > 0 ? availableSkins : [{ skin_num: 0, name: `Varsayılan ${selectedChamp}`, is_base: true }]).map(s => {
                    const tagPrefix = s.is_unique 
                      ? '👑 [EŞSİZ DUBLAJ] ' 
                      : s.voice_type === 'filtered' 
                      ? '🎛️ [AYNI REPLİK+EFEKT] ' 
                      : s.is_base || s.skin_num === 0
                      ? '🛡️ [ANA DUBLAJ] ' 
                      : '❌ [TEMEL SES] ';
                    return (
                      <option key={s.skin_num} value={s.skin_num} className="bg-[#232836] text-slate-200">
                        {tagPrefix}{s.name}
                      </option>
                    );
                  })}
                </select>

                {/* Sadece Eşsiz Dublajlıları Filtreleme Butonu */}
                <button
                  type="button"
                  onClick={() => setSkinFilterMode(prev => prev === 'all' ? 'unique_only' : 'all')}
                  className={`px-2.5 py-1.5 rounded-lg text-xs font-extrabold transition flex items-center space-x-1.5 cursor-pointer border ${
                    skinFilterMode === 'unique_only'
                      ? 'bg-teal-500 text-slate-950 border-teal-300 shadow-sm'
                      : 'bg-[#1e222d] text-teal-200 border-teal-400/40 hover:bg-teal-500/15'
                  }`}
                  title="Yalnızca sıfırdan kaydedilmiş yeni replikleri olan (Efsanevi vb.) kostümleri listeler"
                >
                  <Crown className="w-3.5 h-3.5" />
                  <span>{skinFilterMode === 'unique_only' ? '👑 Eşsizler Açık' : '👑 Eşsizleri Filtrele'}</span>
                </button>
              </div>

              {/* Sağ Taraf: SFX Toggle Switch & Arama */}
              <div className="flex flex-wrap items-center gap-3">
                <label className="flex items-center space-x-2 text-xs font-bold text-slate-200 cursor-pointer select-none bg-[#1e222d] px-3 py-1.5 rounded-lg border border-slate-600/70 hover:border-slate-500 transition">
                  <input
                    type="checkbox"
                    checked={includeSfx}
                    onChange={e => setIncludeSfx(e.target.checked)}
                    className="w-3.5 h-3.5 accent-indigo-400 rounded cursor-pointer"
                  />
                  <span className="flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5 text-amber-300" />
                    <span>Ses Efektleri & Homurtular</span>
                  </span>
                </label>

                <div className="relative w-56">
                  <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                  <input
                    type="text"
                    value={voiceSearch}
                    onChange={e => setVoiceSearch(e.target.value)}
                    placeholder="Replik veya event ara..."
                    className="w-full bg-[#1e222d] border border-slate-600/70 focus:border-indigo-400 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 outline-none transition placeholder:text-slate-400 font-medium"
                  />
                </div>
              </div>
            </div>

            {/* Seçili Kostüm Dublaj Durum Bilgi Rozeti */}
            {currentSkinObj && (
              <div className={`p-2 px-3 rounded-xl border flex flex-wrap items-center justify-between gap-2 text-xs transition ${
                currentSkinObj.is_unique
                  ? 'bg-teal-500/15 border-teal-400/50 text-teal-200'
                  : currentSkinObj.voice_type === 'filtered'
                  ? 'bg-sky-500/15 border-sky-400/50 text-sky-200'
                  : currentSkinObj.is_base || currentSkinObj.skin_num === 0
                  ? 'bg-indigo-500/15 border-indigo-400/40 text-indigo-200'
                  : 'bg-[#1e222d] border-slate-600/70 text-slate-300'
              }`}>
                <div className="flex items-center space-x-2">
                  <span className="font-extrabold text-xs flex items-center gap-1.5">
                    {currentSkinObj.voice_badge}
                  </span>
                  <span className="text-slate-400">•</span>
                  <span className="font-medium text-slate-200">
                    {currentSkinObj.is_unique
                      ? 'Sıfırdan Kayıt Bağımsız Dublaj & Özel Atıflar (Video Potansiyeli Çok Yüksek 🔥)'
                      : currentSkinObj.voice_type === 'filtered'
                      ? 'Standart Türkçe seslendirme üzerine kostüme özel vokal filtre uygulanmıştır (Replik metinleri aynıdır).'
                      : currentSkinObj.is_base || currentSkinObj.skin_num === 0
                      ? 'Şampiyonun orijinal varsayılan ana Türkçe seslendirmesi.'
                      : 'Ayrı bir ses bankası yoktur, şampiyonun standart temel repliklerini kullanır.'}
                  </span>
                </div>
                <div className="flex items-center space-x-2 text-[11px] font-mono text-slate-300">
                  <span>{currentSkinObj.rarity_tr || 'Standart'}</span>
                  {currentSkinObj.is_unique && (
                    <span className="px-2 py-0.5 rounded-full bg-teal-500/20 text-teal-200 border border-teal-400/40 font-bold font-sans">
                      Video İçin Önerilir
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>

          {/* Kategori Filtre Butonları */}
          <div className="flex items-center space-x-1.5 overflow-x-auto pb-2 pt-1 scrollbar-thin">
            <button
              onClick={() => setActiveCategoryFilter('all')}
              className={`px-3 py-1.5 rounded-lg text-xs font-extrabold whitespace-nowrap transition cursor-pointer border ${
                activeCategoryFilter === 'all'
                  ? 'bg-indigo-500/25 text-indigo-200 border-indigo-400/60 shadow-sm'
                  : 'bg-[#1e222d] text-slate-300 border-slate-700/70 hover:border-slate-500 hover:text-white'
              }`}
            >
              Tüm Replikler ({totalItemsCount})
            </button>

            {(voiceData?.categories || []).map(cat => {
              const IconComp = CATEGORY_ICONS[cat.id] || Sparkles;
              const isActive = activeCategoryFilter === cat.id;
              return (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategoryFilter(cat.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-bold whitespace-nowrap transition cursor-pointer border flex items-center space-x-1.5 ${
                    isActive
                      ? 'bg-sky-500/25 text-sky-200 border-sky-400/60 shadow-sm'
                      : 'bg-[#1e222d] text-slate-300 border-slate-700/70 hover:border-slate-500 hover:text-white'
                  }`}
                >
                  <IconComp className="w-3.5 h-3.5" />
                  <span>{cat.title}</span>
                  <span className="font-mono text-[10px] px-1.5 py-0.2 rounded-full bg-[#262c3c] border border-slate-600/70 text-slate-200">
                    {cat.count}
                  </span>
                </button>
              );
            })}
          </div>
        </header>

        {/* Replik Listesi Ana Gövde */}
        <div className="flex-1 overflow-y-auto p-4 lg:p-6 space-y-6 scrollbar-thin">
          
          {loading && (
            <div className="h-64 flex flex-col items-center justify-center space-y-3">
              <Loader2 className="w-8 h-8 text-indigo-300 animate-spin" />
              <div className="text-sm font-bold text-indigo-200 font-mono tracking-wide">
                WAD Arşivinden Replikler & Sesler Çıkarılıyor...
              </div>
              <p className="text-xs text-slate-300">
                Wwise HIRC grafiği deterministik olarak taranıyor.
              </p>
            </div>
          )}

          {error && !loading && (
            <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-400/50 text-rose-200 text-xs flex items-center space-x-3">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!loading && !error && displayedCategories.length === 0 && (
            <div className="h-64 flex flex-col items-center justify-center space-y-2 text-slate-400 text-xs">
              <VolumeX className="w-8 h-8 stroke-[1.5]" />
              <p>Arama kriterlerine uygun replik veya ses bulunamadı.</p>
            </div>
          )}

          {!loading && !error && displayedCategories.map(cat => {
            const IconComp = CATEGORY_ICONS[cat.id] || Sparkles;
            return (
              <section key={cat.id} className="space-y-3">
                
                {/* Kategori Başlığı */}
                <div className="flex items-center justify-between border-b border-slate-700/60 pb-2">
                  <div className="flex items-center space-x-2">
                    <div className="w-7 h-7 rounded-lg bg-indigo-500/20 border border-indigo-400/40 flex items-center justify-center text-indigo-300">
                      <IconComp className="w-4 h-4" />
                    </div>
                    <h3 className="text-sm font-extrabold text-slate-100 uppercase tracking-wide">
                      {cat.title}
                    </h3>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono text-slate-300 font-medium hidden sm:inline">
                      {cat.items.length} Olay • {cat.items.reduce((acc, it) => acc + it.wems.length, 0)} Ses
                    </span>
                    <button
                      onClick={() => toggleSelectCategory(cat)}
                      className="px-2.5 py-1 rounded-lg bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-200 border border-indigo-400/40 text-[11px] font-bold flex items-center space-x-1.5 transition cursor-pointer shadow-sm"
                      title="Bu kategorideki tüm sesleri DaVinci Resolve FCPXML için seç / kaldır"
                    >
                      <CheckSquare className="w-3.5 h-3.5 text-indigo-300" />
                      <span>Kategoriyi Seç</span>
                    </button>
                    <button
                      onClick={() => startCategoryBatchExport(cat)}
                      className="px-2.5 py-1 rounded-lg bg-[#252a3a] hover:bg-sky-500/20 text-slate-200 hover:text-sky-200 border border-slate-600/70 hover:border-sky-400/50 text-[11px] font-bold flex items-center space-x-1.5 transition cursor-pointer shadow-sm"
                      title="Bu kategorideki tüm sesleri ZIP olmadan klasöre aktar"
                    >
                      <FolderDown className="w-3.5 h-3.5 text-sky-300" />
                      <span>WAV İndir ({cat.items.reduce((acc, it) => acc + it.wems.length, 0)})</span>
                    </button>
                  </div>
                </div>

                {/* Kategori İçi Replik Kartları Gallery / Masonry Sistemi */}
                <div className="columns-1 md:columns-2 xl:columns-3 gap-3.5 [column-fill:_balance]">
                  {cat.items.map(item => (
                    <div
                      key={item.raw_event}
                      className="break-inside-avoid mb-3.5 p-3.5 rounded-xl bg-[#252936] border border-slate-700/70 hover:border-slate-500/80 transition flex flex-col space-y-3 group shadow-sm"
                    >
                      {/* Üst Kısım: Başlık & Eylem Adı */}
                      <div className="space-y-1.5">
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-xs font-extrabold text-sky-300 tracking-wide line-clamp-1">
                            {item.action_name}
                          </span>
                          <div className="flex items-center space-x-1 shrink-0">
                            {item.target_champ ? (
                              <span
                                className="px-1.5 py-0.5 rounded bg-violet-500/20 text-violet-200 border border-violet-400/40 text-[9px] font-mono font-bold"
                                title={`DaVinci Layout: Sol %50 ${selectedChamp} | Sağ %50 ${item.target_skin_name || item.target_champ}`}
                              >
                                %50 Sol / %50 Sağ: {item.target_skin_name || item.target_champ}
                              </span>
                            ) : (
                              <span
                                className="px-1.5 py-0.5 rounded bg-teal-500/15 text-teal-200 border border-teal-400/30 text-[9px] font-mono font-bold"
                                title="DaVinci Layout: %100 Tam Ekran Ana Karakter"
                              >
                                %100 Tam Ekran
                              </span>
                            )}
                            {item.is_sfx && (
                              <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-200 border border-amber-400/40 text-[9px] font-mono font-bold shrink-0">
                                SFX / Efor
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Raw Event Kodu */}
                        <div className="flex items-center justify-between text-[10px] font-mono text-slate-300">
                          <span className="truncate max-w-[210px]" title={item.raw_event}>
                            {item.raw_event}
                          </span>
                          <button
                            onClick={() => copyToClipboard(item.raw_event, item.raw_event)}
                            className="text-slate-400 hover:text-slate-200 p-0.5 transition"
                            title="Olay Kodunu Kopyala"
                          >
                            {copiedId === item.raw_event ? <Check className="w-3 h-3 text-teal-300" /> : <Copy className="w-3 h-3" />}
                          </button>
                        </div>
                      </div>

                      {/* WEM Ses Varyasyonları */}
                      <div className="space-y-1.5 pt-2 border-t border-slate-700/60">
                        {item.wems.map(wem => {
                          const playKey = `${item.raw_event}_${wem.wem_id || '0'}`;
                          const isPlaying = playingId === playKey;
                          const isLoading = audioLoadingId === playKey;
                          const isSelected = selectedWems.has(playKey);

                          return (
                            <div
                              key={wem.wem_id || wem.variation_index}
                              className={`p-2 rounded-lg flex items-center justify-between space-x-2 transition ${
                                isPlaying
                                  ? 'bg-indigo-500/25 border border-indigo-400/70'
                                  : isSelected
                                  ? 'bg-sky-500/20 border border-sky-400/60'
                                  : 'bg-[#1e222d] border border-slate-700/70 hover:bg-[#2a2f3f]'
                              }`}
                            >
                              <div className="flex items-center space-x-2 min-w-0">
                                {selectionMode && (
                                  <input
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={() => toggleSelectWem(playKey)}
                                    className="w-3.5 h-3.5 accent-indigo-400 rounded cursor-pointer shrink-0"
                                  />
                                )}

                                {/* Oynat Butonu */}
                                <button
                                  onClick={() => playAudio(item, wem)}
                                  className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition cursor-pointer shadow-sm ${
                                    isPlaying
                                      ? 'bg-violet-400 text-slate-950'
                                      : 'bg-[#34394c] text-violet-300 hover:bg-[#434961] border border-violet-400/30'
                                  }`}
                                  title={isPlaying ? "Durdur" : "Dinle"}
                                >
                                  {isLoading ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin text-violet-300" />
                                  ) : isPlaying ? (
                                    <Square className="w-2.5 h-2.5 fill-current" />
                                  ) : (
                                    <Play className="w-3 h-3 fill-current ml-0.5" />
                                  )}
                                </button>

                                {/* İndir Butonu */}
                                <button
                                  onClick={() => handleDownloadSingle(item, wem, cat.title)}
                                  disabled={downloadingSingleId === playKey}
                                  className="w-7 h-7 rounded-lg bg-[#2b3040] hover:bg-sky-500/25 text-slate-300 hover:text-sky-200 border border-slate-600/60 flex items-center justify-center shrink-0 transition cursor-pointer disabled:opacity-60"
                                  title="Bu Repliği Bilgisayara İndir (.WAV)"
                                >
                                  {downloadingSingleId === playKey ? (
                                    <Loader2 className="w-3.5 h-3.5 animate-spin text-sky-300" />
                                  ) : (
                                    <Download className="w-3.5 h-3.5" />
                                  )}
                                </button>

                                {/* Transkript / Varyasyon Bilgisi */}
                                <div className="min-w-0 flex-1 flex flex-col justify-center">
                                  {wem.transcript ? (
                                    <div className="flex items-center flex-wrap gap-2">
                                      <p className="text-sm text-slate-100 font-sans font-normal not-italic tracking-wide whitespace-normal break-words leading-relaxed select-text">
                                        “{wem.transcript}”
                                      </p>
                                      {(wem.needs_review || (wem.confidence_score && wem.confidence_score < 80)) && (
                                        <span className="inline-flex items-center gap-1 text-[10px] font-mono font-medium px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-300 border border-amber-500/30 shrink-0" title="Güven skoru düşük veya akustik doğrulama gerekiyor">
                                          ⚠️ İnceleme Gerekli
                                        </span>
                                      )}
                                    </div>
                                  ) : (
                                    <span className="text-xs font-mono text-slate-400">
                                      Varyasyon {wem.variation_index} / {wem.variation_total}
                                    </span>
                                  )}
                                </div>
                              </div>

                              {/* WEM ID Etiketi */}
                              <div className="flex items-center space-x-1 shrink-0">
                                {wem.wem_id && (
                                  <span className="text-[9px] font-mono text-slate-400 bg-[#252936] px-1.5 py-0.5 rounded border border-slate-700/70">
                                    #{wem.wem_id}
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                      </div>

                    </div>
                  ))}
                </div>
              </section>
            );
          })}
        </div>

        {/* Toplu İndirme / Klasöre Aktarma Modalı */}
        {batchModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="relative w-full max-w-md bg-[#252936] border border-indigo-400/50 rounded-2xl shadow-2xl overflow-hidden p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-700/70 pb-3">
                <div className="flex items-center space-x-2.5">
                  <div className="w-9 h-9 rounded-xl bg-indigo-500/20 text-indigo-200 border border-indigo-400/40 flex items-center justify-center">
                    <FolderDown className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-100">
                      WAV Seslerini Klasöre Aktar
                    </h3>
                    <p className="text-[11px] text-slate-300">
                      ZIP yok • Doğrudan WAV Dosyaları
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setBatchModalOpen(false)}
                  className="text-slate-300 hover:text-white p-1 rounded-lg transition"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="text-xs text-slate-200 space-y-2">
                <p className="font-bold text-slate-100 flex items-center space-x-2">
                  <span className="w-2 h-2 rounded-full bg-sky-300"></span>
                  <span>{batchModalTitle}</span>
                </p>
                <p className="text-slate-300 leading-relaxed text-[11px]">
                  Tüm sesler ZIP arşivi yapılmadan, doğrudan bilgisayarınızda <span className="text-indigo-200 font-mono font-bold">Indirilen_Sesler/{selectedChamp}/</span> altına saf WAV dosyaları olarak kopyalanır ve işlem bitince klasör otomatik açılır.
                </p>
              </div>

              {/* Klasörleme Seçeneği */}
              <div className="p-3.5 rounded-xl bg-[#1e222d] border border-slate-700/70 space-y-2.5 text-xs">
                <div className="font-extrabold text-indigo-300 uppercase tracking-wider text-[10px]">
                  Klasörleme Düzeni
                </div>
                <label className="flex items-start space-x-2.5 cursor-pointer text-slate-200 group">
                  <input
                    type="radio"
                    name="group_mode"
                    checked={groupByCategory}
                    onChange={() => setGroupByCategory(true)}
                    className="accent-indigo-400 mt-0.5"
                  />
                  <div>
                    <div className="font-bold group-hover:text-indigo-200 transition">
                      Kategorilere Göre Alt Klasörlere Ayır
                    </div>
                    <div className="text-[10px] text-slate-300 font-mono mt-0.5">
                      Örn: <code>Indirilen_Sesler/{selectedChamp}/1_Q_Yetenegi/*.wav</code>
                    </div>
                  </div>
                </label>
                <label className="flex items-start space-x-2.5 cursor-pointer text-slate-200 group pt-1 border-t border-slate-700/60">
                  <input
                    type="radio"
                    name="group_mode"
                    checked={!groupByCategory}
                    onChange={() => setGroupByCategory(false)}
                    className="accent-indigo-400 mt-0.5"
                  />
                  <div>
                    <div className="font-bold group-hover:text-indigo-200 transition">
                      Tüm Sesleri Aynı Tek Klasörde Topla
                    </div>
                    <div className="text-[10px] text-slate-300 font-mono mt-0.5">
                      Örn: <code>Indirilen_Sesler/{selectedChamp}/*.wav</code>
                    </div>
                  </div>
                </label>
              </div>

              {/* Butonlar */}
              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  onClick={() => setBatchModalOpen(false)}
                  disabled={downloadingBatch}
                  className="px-4 py-2 rounded-xl bg-[#343a4d] hover:bg-[#3f465c] text-xs font-bold text-slate-200 transition cursor-pointer"
                >
                  İptal
                </button>
                <button
                  onClick={() => handleExecuteBatchExport(batchModalItems)}
                  disabled={downloadingBatch}
                  className="px-5 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white font-extrabold text-xs transition flex items-center space-x-2 cursor-pointer shadow-md disabled:opacity-50"
                >
                  {downloadingBatch ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin text-white" />
                      <span>WAV Dosyaları Çıkarılıyor...</span>
                    </>
                  ) : (
                    <>
                      <FolderDown className="w-4 h-4" />
                      <span>Klasöre Aktar ve Aç ({batchModalItems.length} WAV)</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tekil İndirme Alert Bildirimi */}
        {singleDownloadAlert && (
          <div className="fixed bottom-6 right-6 z-50 max-w-sm w-full bg-[#252936]/95 backdrop-blur-md border border-teal-400/60 rounded-2xl shadow-2xl p-4 space-y-3 animate-in slide-in-from-bottom-5 duration-200">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-teal-500/20 text-teal-300 border border-teal-400/40 flex items-center justify-center shrink-0">
                  <CheckCircle2 className="w-4 h-4 stroke-[2.5]" />
                </div>
                <div>
                  <h4 className="text-xs font-extrabold text-teal-200 uppercase tracking-wide">
                    Ses Dosyası İndirildi
                  </h4>
                  <p className="text-xs font-bold text-slate-100">
                    {singleDownloadAlert.speaker} • {singleDownloadAlert.action_name}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSingleDownloadAlert(null)}
                className="text-slate-300 hover:text-white p-1 rounded-lg transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {singleDownloadAlert.transcript && (
              <p className="text-[11px] text-slate-200 italic font-medium line-clamp-2 px-1 border-l-2 border-indigo-400/60">
                "{singleDownloadAlert.transcript}"
              </p>
            )}

            <div className="p-2 rounded-lg bg-[#1e222d] border border-slate-700 text-[10px] font-mono text-slate-300 break-all select-all">
              <span className="text-slate-400 block text-[9px] uppercase font-bold">Kayıt Yeri:</span>
              {singleDownloadAlert.folder_path}\{singleDownloadAlert.filename}
            </div>

            <button
              onClick={() => handleOpenFolder(singleDownloadAlert.folder_path, singleDownloadAlert.file_path)}
              disabled={folderOpening}
              className="w-full py-2.5 px-3 rounded-xl bg-teal-500 hover:bg-teal-400 text-slate-950 font-black text-xs flex items-center justify-center space-x-2 transition cursor-pointer shadow-md disabled:opacity-80"
            >
              {folderOpening ? (
                <>
                  <Check className="w-4 h-4 stroke-[3]" />
                  <span>Klasör Açıldı!</span>
                </>
              ) : (
                <>
                  <FolderOpen className="w-4 h-4" />
                  <span>İndirilen Klasörü Gör</span>
                </>
              )}
            </button>
          </div>
        )}

        {/* Yüzen Alt Çubuk: Karakter Replikleri DaVinci Resolve FCPXML Aktarımı */}
        {selectedWems.size > 0 && (
          <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-[#262c3d]/95 border border-indigo-400/70 rounded-2xl p-3 px-5 shadow-2xl backdrop-blur-xl flex items-center space-x-4 animate-in slide-in-from-bottom-5 duration-200">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-indigo-500/25 border border-indigo-400/50 flex items-center justify-center text-indigo-200 font-bold shadow">
                <Film className="w-5 h-5" />
              </div>
              <div>
                <div className="text-sm font-extrabold text-indigo-200 font-mono flex items-center space-x-1.5">
                  <span>{selectedWems.size} Karakter Repliği Seçildi</span>
                </div>
                <div className="text-[11px] text-slate-300">
                  Genel Replik: %100 Tam Ekran • Atıf Varsa: Sol %50 Ana / Sağ %50 Hedef • Alt Türkçe Eylem
                </div>
              </div>
            </div>

            <div className="h-8 w-px bg-slate-600/80" />

            <button
              onClick={() => setIsTranscriptModalOpen(true)}
              className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 via-indigo-600 to-indigo-500 hover:from-purple-500 hover:to-indigo-400 text-white font-extrabold text-xs md:text-sm tracking-wide shadow-md transition flex items-center space-x-2 cursor-pointer"
              title="XML üretmeksizin yalnızca seçilen repliklerin metinlerini Çoklu Yapay Zeka & Fonetik Güven Skoru ile çözümleyin ve güncelleyin"
            >
              <Brain className="w-4 h-4 text-purple-200" />
              <span>Sadece Replik Metni Üret</span>
            </button>

            <button
              onClick={() => setIsDaVinciModalOpen(true)}
              className="px-4 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white font-extrabold text-xs md:text-sm tracking-wide shadow-md transition flex items-center space-x-2 cursor-pointer"
            >
              <Film className="w-4 h-4" />
              <span>DaVinci Resolve'a Aktar (FCPXML)</span>
            </button>

            <button
              onClick={startSelectedBatchExport}
              className="px-3 py-2 rounded-xl bg-sky-500/20 hover:bg-sky-500/30 text-xs font-bold text-sky-200 border border-sky-400/50 transition cursor-pointer flex items-center space-x-1.5"
            >
              <FolderDown className="w-3.5 h-3.5" />
              <span>WAV İndir</span>
            </button>

            <button
              onClick={() => setSelectedWems(new Set())}
              className="px-3 py-2 rounded-xl bg-[#343b4f] hover:bg-[#3f475e] text-xs font-bold text-slate-200 hover:text-white transition cursor-pointer"
            >
              Temizle
            </button>
          </div>
        )}

        {/* DaVinci Resolve Export Modal (Layout 1: champion_voices) */}
        <DaVinciExportModal
          isOpen={isDaVinciModalOpen}
          onClose={() => setIsDaVinciModalOpen(false)}
          selectedItems={selectedDaVinciItems}
          defaultTimelineName={`${selectedChamp}_Karakter_Replikleri`}
          layoutMode="champion_voices"
          onClearSelection={() => setSelectedWems(new Set())}
        />

        {/* Çoklu Yapay Zeka & Fonetik Güven Skoru ile Replik Metni Üretme Modalı */}
        <TranscriptGeneratorModal
          isOpen={isTranscriptModalOpen}
          onClose={() => setIsTranscriptModalOpen(false)}
          items={selectedDaVinciItems.length > 0 ? selectedDaVinciItems : allCategoryDaVinciItems}
          title={`${selectedChamp} Replik Metinlerini Çözümleme`}
          onTranscriptsUpdated={(transcriptsMap) => {
            setVoiceData(prev => {
              if (!prev) return prev;
              const next = JSON.parse(JSON.stringify(prev));

              const updateWems = (wemsList, rawEvent) => {
                if (!Array.isArray(wemsList)) return wemsList;
                const isSingle = wemsList.length === 1;
                return wemsList.map(wem => {
                  const wid = String(wem.wem_id || '').trim();
                  const ev = rawEvent || '';
                  const keyWithEv = `${ev}_${wid}`;
                  const entry = transcriptsMap[wid] || transcriptsMap[keyWithEv] || (isSingle ? transcriptsMap[ev] : null);
                  if (entry) {
                    const text = typeof entry === 'object' ? entry.text : entry;
                    const needs_review = typeof entry === 'object' ? Boolean(entry.needs_review) : false;
                    const confidence_score = typeof entry === 'object' ? entry.confidence_score : 98;
                    return { ...wem, transcript: text, needs_review, confidence_score };
                  }
                  return wem;
                });
              };

              // 1. Root categories (LoR ve standart format)
              if (Array.isArray(next.categories)) {
                next.categories = next.categories.map(cat => ({
                  ...cat,
                  items: (cat.items || []).map(item => ({
                    ...item,
                    wems: updateWems(item.wems, item.raw_event)
                  }))
                }));
              } else if (next.categories && typeof next.categories === 'object') {
                Object.keys(next.categories).forEach(catKey => {
                  const itemsList = next.categories[catKey];
                  if (Array.isArray(itemsList)) {
                    next.categories[catKey] = itemsList.map(item => ({
                      ...item,
                      wems: updateWems(item.wems, item.raw_event)
                    }));
                  }
                });
              }

              // 2. Skins altındaki categories (varsa)
              if (Array.isArray(next.skins)) {
                next.skins.forEach(sk => {
                  if (sk.categories && typeof sk.categories === 'object') {
                    Object.keys(sk.categories).forEach(catKey => {
                      const itemsList = sk.categories[catKey];
                      if (Array.isArray(itemsList)) {
                        sk.categories[catKey] = itemsList.map(item => ({
                          ...item,
                          wems: updateWems(item.wems, item.raw_event)
                        }));
                      }
                    });
                  }
                });
              }

              return next;
            });
          }}
        />

      </main>
    </div>
  );
}
