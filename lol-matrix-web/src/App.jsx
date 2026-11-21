import React, { useState, useEffect, useMemo, useRef } from 'react';
import Navbar from './components/Navbar';
import MatrixCards from './components/MatrixCards';
import VersusMode from './components/VersusMode';
import RankingsView from './components/RankingsView';
import ChampionVoicesView from './components/ChampionVoicesView';
import PairInteractionsView from './components/PairInteractionsView';
import FcpxmlFontSimulatorView from './components/FcpxmlFontSimulatorView';
import DaVinciExportModal from './components/DaVinciExportModal';
import TranscriptGeneratorModal from './components/TranscriptGeneratorModal';
import { 
  Search, ArrowDownLeft, ArrowUpRight, Sparkles, Filter, RotateCcw, 
  MessageSquare, User, Users, ChevronRight, Layers, Volume2, Volume1, Copy, Check, Hash,
  Play, Square, Loader2, VolumeX, CheckSquare, Film, X, Brain
} from 'lucide-react';

export default function App() {
  const [gameMode, setGameModeState] = useState(() => {
    try {
      const saved = localStorage.getItem('lol_matrix_game_mode');
      return saved === 'lor' ? 'lor' : 'lol';
    } catch (e) {
      return 'lol';
    }
  });

  const setGameMode = (mode) => {
    setGameModeState(mode);
    try {
      localStorage.setItem('lol_matrix_game_mode', mode);
    } catch (e) {}
  };

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // URL Hash & LocalStorage tab persistence (Madde 3 - F5 atınca sekme ve şampiyon kaybolmaz)
  const getInitialTab = () => {
    try {
      const hash = window.location.hash.replace('#', '').toLowerCase();
      if (['matrix', 'voices', 'pair_dialogues', 'versus', 'rankings', 'font_studio'].includes(hash)) {
        return hash;
      }
      const saved = localStorage.getItem('lol_matrix_active_tab');
      if (saved && ['matrix', 'voices', 'pair_dialogues', 'versus', 'rankings', 'font_studio'].includes(saved)) {
        return saved;
      }
    } catch (e) {}
    return 'voices'; // Doğrudan Karakter Replikleri ile başlar
  };

  const [activeTab, setActiveTabState] = useState(getInitialTab);

  const setActiveTab = (tab) => {
    setActiveTabState(tab);
    try {
      window.location.hash = tab;
      localStorage.setItem('lol_matrix_active_tab', tab);
    } catch (e) {}
  };

  useEffect(() => {
    if (!window.location.hash || window.location.hash === '#') {
      window.location.hash = activeTab;
    }
    const handleHash = () => {
      const h = window.location.hash.replace('#', '').toLowerCase();
      if (['matrix', 'voices', 'pair_dialogues', 'versus', 'rankings', 'font_studio'].includes(h)) {
        setActiveTabState(h);
      }
    };
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, [activeTab]);

  // Seçili şampiyonu da hatırlayalım
  const [selectedChampName, setSelectedChampNameState] = useState(() => {
    try {
      return localStorage.getItem('lol_matrix_selected_champ') || 'Yasuo';
    } catch (e) {
      return 'Yasuo';
    }
  });

  const setSelectedChampName = (name) => {
    setSelectedChampNameState(name);
    try {
      localStorage.setItem('lol_matrix_selected_champ', name);
    } catch (e) {}
  };

  const [direction, setDirection] = useState('incoming'); // 'incoming' (Tersine / Hedef) vs 'outgoing' (Giden)
  const [matrixFilter, setMatrixFilter] = useState('all'); // 'all', 'base_to_base', etc.
  const [actionFilter, setActionFilter] = useState('all');
  const [speakerSkinFilter, setSpeakerSkinFilter] = useState('all');
  const [targetSkinFilter, setTargetSkinFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [tableSearch, setTableSearch] = useState('');
  const [champSort, setChampSort] = useState('incoming'); // 'incoming', 'outgoing', 'alpha'

  // On-Demand JIT Audio Player State (Zero-Disk Footprint)
  const [playingId, setPlayingId] = useState(null);
  const [audioLoadingId, setAudioLoadingId] = useState(null);
  const audioInstanceRef = useRef(null);

  // Global Ses Seviyesi State'i (0 - 100, LoR ve LoL için geçerli)
  const [audioVolume, setAudioVolumeState] = useState(() => {
    try {
      const saved = localStorage.getItem('lol_matrix_audio_volume');
      return saved !== null ? parseInt(saved, 10) : 85;
    } catch (e) {
      return 85;
    }
  });

  const setAudioVolume = (val) => {
    const clamped = Math.max(0, Math.min(100, val));
    setAudioVolumeState(clamped);
    try {
      localStorage.setItem('lol_matrix_audio_volume', String(clamped));
    } catch (e) {}
    if (audioInstanceRef.current) {
      audioInstanceRef.current.volume = clamped / 100;
    }
    window.__lolAudioVolume = clamped;
  };

  useEffect(() => {
    window.__lolAudioVolume = audioVolume;
  }, [audioVolume]);

  // Lightweight Reference Copy State
  const [copiedId, setCopiedId] = useState(null);

  // DaVinci Selection & Export State
  const [selectedMap, setSelectedMap] = useState(new Map());
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const [isTranscriptModalOpen, setIsTranscriptModalOpen] = useState(false);

  // Dinamik Zoom & Metin Boyutu Yönetimi (Madde 4 - Kalıcı LocalStorage)
  const [zoomLevel, setZoomLevel] = useState(() => {
    try {
      const saved = localStorage.getItem('lol_matrix_zoom');
      if (saved) {
        const val = parseFloat(saved);
        if (!isNaN(val) && val >= 0.75 && val <= 1.6) return val;
      }
    } catch (e) {}
    return 1.0;
  });

  useEffect(() => {
    try {
      document.documentElement.style.zoom = zoomLevel;
      localStorage.setItem('lol_matrix_zoom', String(zoomLevel));
    } catch (e) {}
  }, [zoomLevel]);

  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(1.6, Math.round((prev + 0.05) * 100) / 100));
  };

  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(0.75, Math.round((prev - 0.05) * 100) / 100));
  };

  const handleResetZoom = () => {
    setZoomLevel(1.0);
  };

  // Global Klavye Kısayolları (Ctrl +, Ctrl -, Ctrl 0)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey || e.metaKey) {
        if (e.key === '=' || e.key === '+' || e.code === 'NumpadAdd') {
          e.preventDefault();
          handleZoomIn();
        } else if (e.key === '-' || e.key === '_' || e.code === 'NumpadSubtract') {
          e.preventDefault();
          handleZoomOut();
        } else if (e.key === '0' || e.code === 'Numpad0') {
          e.preventDefault();
          handleResetZoom();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const dataUrl = gameMode === 'lor' ? '/data/lor_matrix_data.json' : '/data/lol_matrix_data.json';
    fetch(dataUrl)
      .then(res => {
        if (!res.ok) throw new Error('Veritabanı yüklenemedi');
        return res.json();
      })
      .then(json => {
        setData(json);
        setLoading(false);
        if (json.champions && json.champions.length > 0) {
          const savedChamp = localStorage.getItem('lol_matrix_selected_champ');
          const exists = savedChamp && json.champions.some(c => c.name.toLowerCase() === savedChamp.toLowerCase());
          if (!exists) {
            setSelectedChampName(json.champions[0].name);
          }
        }
      })
      .catch(err => {
        console.error(err);
        setError(err.message);
        setLoading(false);
      });
  }, [gameMode]);

  const champions = data?.champions || [];

  // Filtered and sorted champions for the left list
  const filteredChamps = useMemo(() => {
    let list = [...champions];
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(c => c.name.toLowerCase().includes(q));
    }
    list.sort((a, b) => {
      if (champSort === 'incoming') return b.total_incoming - a.total_incoming;
      if (champSort === 'outgoing') return b.total_outgoing - a.total_outgoing;
      return a.name.localeCompare(b.name);
    });
    return list;
  }, [champions, searchQuery, champSort]);

  // Selected champion object
  const currentChamp = useMemo(() => {
    return champions.find(c => c.name.toLowerCase() === selectedChampName.toLowerCase()) || champions[0];
  }, [champions, selectedChampName]);

  // Active items (incoming vs outgoing)
  const rawItems = useMemo(() => {
    if (!currentChamp) return [];
    return direction === 'incoming' 
      ? (currentChamp.incoming_items || []) 
      : (currentChamp.outgoing_items || []);
  }, [currentChamp, direction]);

  const activeMatrix = useMemo(() => {
    if (!currentChamp) return {};
    return direction === 'incoming' 
      ? (currentChamp.matrix_incoming || {}) 
      : (currentChamp.matrix_outgoing || {});
  }, [currentChamp, direction]);

  const activeActions = useMemo(() => {
    if (!currentChamp) return {};
    return direction === 'incoming' 
      ? (currentChamp.actions_incoming || {}) 
      : (currentChamp.actions_outgoing || {});
  }, [currentChamp, direction]);

  // Available skins in current rawItems for selective dropdown filtering
  const availableSpeakerSkins = useMemo(() => {
    const map = new Map();
    rawItems.forEach(it => {
      if (it.speaker_skin_name) {
        map.set(it.speaker_skin_name, (map.get(it.speaker_skin_name) || 0) + 1);
      }
    });
    return Array.from(map.entries()).sort((a, b) => b[1] - a[1]);
  }, [rawItems]);

  const availableTargetSkins = useMemo(() => {
    const map = new Map();
    rawItems.forEach(it => {
      if (it.target_skin_name) {
        map.set(it.target_skin_name, (map.get(it.target_skin_name) || 0) + 1);
      }
    });
    return Array.from(map.entries()).sort((a, b) => b[1] - a[1]);
  }, [rawItems]);

  // Filtered items for table
  const filteredItems = useMemo(() => {
    let items = rawItems;
    if (matrixFilter === 'target_base') {
      items = items.filter(it => it.target_is_base);
    } else if (matrixFilter === 'target_skin') {
      items = items.filter(it => !it.target_is_base);
    } else if (matrixFilter !== 'all') {
      items = items.filter(it => it.matrix_type === matrixFilter);
    }
    if (actionFilter !== 'all') {
      items = items.filter(it => it.action_type === actionFilter);
    }
    if (speakerSkinFilter !== 'all') {
      items = items.filter(it => it.speaker_skin_name === speakerSkinFilter);
    }
    if (targetSkinFilter !== 'all') {
      items = items.filter(it => it.target_skin_name === targetSkinFilter);
    }
    if (tableSearch.trim()) {
      const q = tableSearch.toLowerCase().trim();
      items = items.filter(it => 
        it.speaker_champ.toLowerCase().includes(q) ||
        it.target_champ.toLowerCase().includes(q) ||
        it.speaker_skin_name.toLowerCase().includes(q) ||
        it.target_skin_name.toLowerCase().includes(q) ||
        (it.transcript && it.transcript.toLowerCase().includes(q)) ||
        it.raw_event.toLowerCase().includes(q) ||
        (it.ref_id && it.ref_id.toLowerCase().includes(q))
      );
    }
    return items;
  }, [rawItems, matrixFilter, actionFilter, speakerSkinFilter, targetSkinFilter, tableSearch]);

  const resetFilters = () => {
    setMatrixFilter('all');
    setActionFilter('all');
    setSpeakerSkinFilter('all');
    setTargetSkinFilter('all');
    setTableSearch('');
  };

  const copyRefId = (refId) => {
    if (!refId) return;
    navigator.clipboard.writeText(refId);
    setCopiedId(refId);
    setTimeout(() => {
      setCopiedId(null);
    }, 2000);
  };

  const getItemKey = (it, idx) => {
    return it.ref_id || `${it.speaker_champ}_${it.raw_event}_${it.wem_id || idx}`;
  };

  const toggleSelectItem = (it, idx) => {
    const key = getItemKey(it, idx);
    setSelectedMap(prev => {
      const next = new Map(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.set(key, it);
      }
      return next;
    });
  };

  const selectAllCurrent = (items) => {
    setSelectedMap(prev => {
      const next = new Map(prev);
      const allSelected = items.length > 0 && items.every((it, idx) => next.has(getItemKey(it, idx)));
      if (allSelected) {
        items.forEach((it, idx) => next.delete(getItemKey(it, idx)));
      } else {
        items.forEach((it, idx) => next.set(getItemKey(it, idx), it));
      }
      return next;
    });
  };

  const clearSelection = () => {
    setSelectedMap(new Map());
  };

  const playVoice = (it, rowIdx) => {
    const cueId = `${it.speaker_champ}_${it.raw_event}_${it.wem_id || rowIdx}`;

    if (playingId === cueId && audioInstanceRef.current && !audioInstanceRef.current.paused) {
      audioInstanceRef.current.pause();
      audioInstanceRef.current.currentTime = 0;
      setPlayingId(null);
      return;
    }

    if (audioInstanceRef.current) {
      audioInstanceRef.current.pause();
    }

    setAudioLoadingId(cueId);
    const wemParam = it.wem_id ? `&wem_id=${encodeURIComponent(it.wem_id)}` : '';
    const audioUrl = `http://127.0.0.1:8080/api/audio-play?speaker=${encodeURIComponent(it.speaker_champ)}&event=${encodeURIComponent(it.raw_event)}&target=${encodeURIComponent(it.target_champ)}${wemParam}`;
    console.log("🎧 [JIT Audio Play] URL:", audioUrl, "WEM ID:", it.wem_id);
    const audio = new Audio(audioUrl);
    audio.volume = (audioVolume ?? 85) / 100;
    audioInstanceRef.current = audio;

    audio.oncanplay = () => {
      setAudioLoadingId(null);
    };

    audio.play().then(() => {
      setAudioLoadingId(null);
      setPlayingId(cueId);
    }).catch(err => {
      console.warn("Ses çalma hatası (Ses sunucusu açık mı?):", err);
      setAudioLoadingId(null);
      setPlayingId(null);
    });

    audio.onended = () => {
      setPlayingId(null);
      audioInstanceRef.current = null;
    };

    audio.onerror = () => {
      setAudioLoadingId(null);
      setPlayingId(null);
    };
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#030812] flex flex-col items-center justify-center space-y-4">
        <div className="w-16 h-16 rounded-2xl border-2 border-amber-400/30 border-t-amber-400 animate-spin"></div>
        <div className="text-center">
          <h2 className="text-xl font-bold font-['Cinzel'] text-amber-300">HEXTECH ATIF VERİTABANI YÜKLENİYOR</h2>
          <p className="text-sm text-slate-300 mt-1">174 Şampiyon ve 16.900+ Atıf İlişkisi Belleğe Aktarılıyor...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#030812] flex items-center justify-center p-4">
        <div className="glass-panel p-6 rounded-2xl max-w-md text-center border-rose-500/40">
          <h3 className="text-rose-400 font-bold mb-2">Veritabanı Yükleme Hatası</h3>
          <p className="text-sm text-slate-300">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#1e222d] flex flex-col h-screen overflow-hidden text-slate-100">
      {/* Top Navigation */}
      <Navbar 
        gameMode={gameMode}
        setGameMode={setGameMode}
        activeTab={activeTab} 
        setActiveTab={setActiveTab} 
        globalStats={data?.metadata || data} 
        totalChamps={champions.length}
        zoomLevel={zoomLevel}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onResetZoom={handleResetZoom}
        audioVolume={audioVolume}
        setAudioVolume={setAudioVolume}
      />

      {/* Main Content Area */}
      <main className="flex-1 flex overflow-hidden p-3.5 gap-3.5 max-w-[1850px] w-full mx-auto min-h-0">
        
        {/* VIEW 1: MATRIX & DETAILS HUB */}
        {activeTab === 'matrix' && (
          <>
            {/* LEFT: 174 Champions List Panel */}
            <div className="w-88 lg:w-[420px] glass-panel rounded-2xl p-3.5 flex flex-col shrink-0 border-slate-700/60 overflow-hidden">
              {/* Search Bar */}
              <div className="relative mb-2.5">
                <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Şampiyon ara (Yasuo, Ahri, Yone...)"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  className="w-full bg-[#2a3040] border border-slate-600/70 focus:border-indigo-400 rounded-xl pl-10 pr-3.5 py-2.5 text-sm text-slate-100 outline-none transition font-medium placeholder:text-slate-400"
                />
              </div>

              {/* Sort Tabs */}
              <div className="flex items-center justify-between pb-2.5 mb-2 border-b border-slate-800 text-xs font-semibold">
                <div className="flex items-center space-x-1.5">
                  <button
                    onClick={() => setChampSort('incoming')}
                    className={`px-2.5 py-1 rounded-lg text-xs font-bold transition cursor-pointer ${
                      champSort === 'incoming' ? 'bg-amber-500/25 text-amber-300 border border-amber-500/50' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Hedef (Atıf Alan)
                  </button>
                  <button
                    onClick={() => setChampSort('outgoing')}
                    className={`px-2.5 py-1 rounded-lg text-xs font-bold transition cursor-pointer ${
                      champSort === 'outgoing' ? 'bg-cyan-500/25 text-cyan-300 border border-cyan-500/50' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Konuşan
                  </button>
                  <button
                    onClick={() => setChampSort('alpha')}
                    className={`px-2.5 py-1 rounded-lg text-xs font-bold transition cursor-pointer ${
                      champSort === 'alpha' ? 'bg-purple-500/25 text-purple-300 border border-purple-500/50' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    A-Z
                  </button>
                </div>
                <span className="text-slate-400 font-mono text-xs font-bold">{filteredChamps.length} Şampiyon</span>
              </div>

              {/* Champion Cards List Scroll */}
              <div className="flex-1 overflow-y-auto space-y-2 pr-1">
                {filteredChamps.map(c => {
                  const isSelected = currentChamp?.name.toLowerCase() === c.name.toLowerCase();
                  return (
                    <div
                      key={c.name}
                      onClick={() => {
                        setSelectedChampName(c.name);
                        resetFilters();
                      }}
                      className={`p-2.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between group ${
                        isSelected
                          ? 'bg-gradient-to-r from-amber-500/25 to-amber-600/15 border-amber-400 shadow-lg ring-1 ring-amber-400/50'
                          : 'bg-[#061022]/80 hover:bg-[#08152c] border-slate-700/60 hover:border-slate-500'
                      }`}
                    >
                      <div className="flex items-center space-x-3 min-w-0">
                        <img
                          src={c.icon_url}
                          alt={c.name}
                          className={`w-11 h-11 rounded-xl object-cover border-2 transition shrink-0 ${
                            isSelected ? 'border-amber-300' : 'border-slate-700 group-hover:border-slate-400'
                          }`}
                        />
                        <div className="truncate">
                          <div className={`font-extrabold text-sm truncate ${isSelected ? 'text-amber-200' : 'text-slate-100 group-hover:text-white'}`}>
                            {c.name}
                          </div>
                          <div className="text-xs text-slate-300 font-mono flex items-center space-x-1.5 mt-0.5">
                            <span className="text-emerald-400 font-bold">{c.matrix_incoming?.base_to_base || 0} Kanon</span>
                            <span>•</span>
                            <span>{c.unique_speakers_incoming} konuşan</span>
                          </div>
                        </div>
                      </div>

                      <div className="text-right shrink-0 pl-2">
                        <div className={`text-sm font-mono font-black ${isSelected ? 'text-amber-300' : 'text-slate-200'}`}>
                          {c.total_incoming}
                        </div>
                        <div className="text-[10px] text-slate-400 uppercase font-extrabold">Atıf</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* RIGHT: Selected Champion Analytics Dashboard */}
            <div className="flex-1 flex flex-col space-y-3.5 overflow-hidden min-h-0">
              
              {/* Champion Hero Banner */}
              <div className="glass-panel rounded-2xl p-4.5 border-slate-700/80 bg-gradient-to-r from-[#061022]/95 via-[#07142a]/85 to-[#040A18]/95 shrink-0 shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-3.5">
                <div className="flex items-center space-x-4">
                  <div className="relative w-18 h-18 rounded-2xl overflow-hidden border-2 border-amber-400 shadow-xl shrink-0">
                    <img src={currentChamp?.icon_url} alt={currentChamp?.name} className="w-full h-full object-cover" />
                  </div>
                  <div>
                    <div className="flex items-center space-x-3">
                      <h2 className="text-3xl font-black text-amber-300 font-['Cinzel'] tracking-wide">
                        {currentChamp?.name}
                      </h2>
                      <span className="px-3 py-1 rounded-full bg-amber-500/25 text-amber-300 border border-amber-500/50 text-xs font-mono font-extrabold">
                        {direction === 'incoming' ? `${currentChamp?.total_incoming} Gelen Atıf` : `${currentChamp?.total_outgoing} Giden Atıf`}
                      </span>
                    </div>
                    <p className="text-sm text-slate-300 font-medium mt-1">
                      {direction === 'incoming'
                        ? `${currentChamp?.name} hedefine ${currentChamp?.unique_speakers_incoming} farklı şampiyon tarafından söylenen tüm diyaloglar.`
                        : `${currentChamp?.name} karakterinin ${currentChamp?.unique_targets_outgoing} farklı şampiyona söylediği tüm replikler.`
                      }
                    </p>
                  </div>
                </div>

                {/* Perspective Direction Switcher */}
                <div className="flex items-center space-x-2 shrink-0">
                  <div className="inline-flex rounded-xl bg-[#030914] p-1 border border-slate-700">
                    <button
                      onClick={() => { setDirection('incoming'); resetFilters(); }}
                      className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs md:text-sm font-extrabold transition cursor-pointer ${
                        direction === 'incoming'
                          ? 'bg-amber-500/25 text-amber-300 border border-amber-500/50 shadow'
                          : 'text-slate-300 hover:text-white'
                      }`}
                    >
                      <ArrowDownLeft className="w-4 h-4" />
                      <span>Bu Şampiyona Yapılanlar ({currentChamp?.total_incoming})</span>
                    </button>
                    <button
                      onClick={() => { setDirection('outgoing'); resetFilters(); }}
                      className={`flex items-center space-x-2 px-4 py-2 rounded-lg text-xs md:text-sm font-extrabold transition cursor-pointer ${
                        direction === 'outgoing'
                          ? 'bg-cyan-500/25 text-cyan-300 border border-cyan-500/50 shadow'
                          : 'text-slate-300 hover:text-white'
                      }`}
                    >
                      <ArrowUpRight className="w-4 h-4" />
                      <span>Bu Şampiyonun Söyledikleri ({currentChamp?.total_outgoing})</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Core Matrix & Scope Cards */}
              <MatrixCards
                matrix={activeMatrix}
                totalItems={rawItems.length}
                targetBaseCount={rawItems.filter(it => it.target_is_base).length}
                targetSkinCount={rawItems.filter(it => !it.target_is_base).length}
                activeFilter={matrixFilter}
                onSelectFilter={setMatrixFilter}
              />

              {/* Actions & Top Partners Bar */}
              <div className="grid grid-cols-12 gap-3.5 shrink-0">
                {/* Actions Chips */}
                <div className="col-span-5 glass-panel rounded-xl p-3.5 border-slate-700/80 flex flex-col justify-between">
                  <div className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>🎭 Eylem Türü Dağılımı</span>
                    {actionFilter !== 'all' && (
                      <button onClick={() => setActionFilter('all')} className="text-cyan-400 hover:underline text-xs font-semibold cursor-pointer">Filtreyi Temizle</button>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(activeActions).map(([act, cnt]) => {
                      const isActive = actionFilter === act;
                      return (
                        <button
                          key={act}
                          onClick={() => setActionFilter(isActive ? 'all' : act)}
                          className={`px-3 py-1 rounded-full text-xs font-bold border transition cursor-pointer flex items-center space-x-1.5 ${
                            isActive
                              ? 'bg-amber-500/35 text-amber-200 border-amber-400 ring-1 ring-amber-400'
                              : 'bg-[#061022] text-slate-200 border-slate-700 hover:border-slate-500'
                          }`}
                        >
                          <span className="capitalize">{act.replace(/_/g, ' ')}</span>
                          <span className="font-mono text-xs font-black text-amber-300 ml-1">({cnt})</span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Top Dialogue Partners */}
                <div className="col-span-7 glass-panel rounded-xl p-3.5 border-slate-700/80 flex flex-col justify-between">
                  <div className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2 flex items-center justify-between">
                    <span>👑 {direction === 'incoming' ? 'En Çok Atıfta Bulunan Şampiyonlar' : 'En Çok Hedef Alınan Şampiyonlar'}</span>
                    <span className="text-xs font-mono text-amber-300 font-bold">{direction === 'incoming' ? currentChamp?.top_speakers?.length : currentChamp?.top_targets?.length} Şampiyon</span>
                  </div>
                  <div className="flex items-center space-x-2.5 overflow-x-auto pb-1">
                    {(direction === 'incoming' ? currentChamp?.top_speakers : currentChamp?.top_targets)?.map(p => (
                      <div
                        key={p.name}
                        onClick={() => {
                          setTableSearch(p.name);
                        }}
                        className="flex items-center space-x-2.5 px-2.5 py-1.5 rounded-xl bg-[#061022] border border-slate-700 shrink-0 hover:border-amber-400 transition cursor-pointer select-none"
                        title={`${p.name} ile filtrele`}
                      >
                        <img src={p.icon_url} alt={p.name} className="w-7 h-7 rounded-lg object-cover border border-slate-600" />
                        <div className="leading-tight">
                          <div className="text-xs font-extrabold text-slate-100 truncate">{p.name}</div>
                          <div className="text-[11px] font-mono text-cyan-400 font-bold">{p.count} replik</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Detailed Filterable Voice Cues Table with Audio Player */}
              <div className="flex-1 glass-panel rounded-2xl p-4 border-slate-700/80 flex flex-col overflow-hidden min-h-0">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 mb-2.5 border-b border-slate-800 shrink-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="flex items-center space-x-2">
                      <Volume2 className="w-5 h-5 text-amber-400" />
                      <span className="text-sm font-extrabold text-amber-300 font-['Cinzel']">Detaylı Replik & Dinleme Tablosu</span>
                      <span className="px-2.5 py-0.5 rounded-full bg-[#081428] border border-slate-700 text-xs font-mono font-extrabold text-cyan-300">
                        {filteredItems.length} / {rawItems.length} Replik
                      </span>
                    </div>

                    {/* Active Filter Pills */}
                    {matrixFilter !== 'all' && (
                      <span className="px-2.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-xs font-mono font-bold">
                        {matrixFilter === 'target_base' ? '🎯 Orijinal Hedefe Gelenler' :
                         matrixFilter === 'target_skin' ? '✨ Kostümlü Hedefe Gelenler' :
                         matrixFilter === 'base_to_base' ? '🛡️ Saf Kanon (B ➔ B)' :
                         matrixFilter === 'skin_to_base' ? '⚡ Kostümlü ➔ Varsayılan (S ➔ B)' :
                         matrixFilter === 'base_to_skin' ? '👕 Varsayılan ➔ Kostümlü (B ➔ S)' :
                         matrixFilter === 'skin_to_skin' ? '🌌 Kostümlü ➔ Kostümlü (S ➔ S)' :
                         matrixFilter}
                      </span>
                    )}

                    {speakerSkinFilter !== 'all' && (
                      <button
                        onClick={() => setSpeakerSkinFilter('all')}
                        className="px-2.5 py-0.5 rounded-lg bg-amber-500/25 border border-amber-400/60 text-amber-200 text-xs font-mono font-bold flex items-center gap-1 hover:bg-amber-500/40 transition cursor-pointer"
                        title="Konuşan kostüm filtresini kaldır"
                      >
                        <span>🛡️ {speakerSkinFilter}</span>
                        <span className="text-amber-400 font-black ml-1">×</span>
                      </button>
                    )}

                    {targetSkinFilter !== 'all' && (
                      <button
                        onClick={() => setTargetSkinFilter('all')}
                        className="px-2.5 py-0.5 rounded-lg bg-cyan-500/25 border border-cyan-400/60 text-cyan-200 text-xs font-mono font-bold flex items-center gap-1 hover:bg-cyan-500/40 transition cursor-pointer"
                        title="Hedef kostüm filtresini kaldır"
                      >
                        <span>🎯 {targetSkinFilter}</span>
                        <span className="text-cyan-400 font-black ml-1">×</span>
                      </button>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    {/* Speaker Costume Filter Dropdown */}
                    <select
                      value={speakerSkinFilter}
                      onChange={e => setSpeakerSkinFilter(e.target.value)}
                      className={`bg-[#050D1E] border rounded-xl px-2.5 py-1.5 text-xs font-semibold outline-none cursor-pointer max-w-[190px] transition ${
                        speakerSkinFilter !== 'all' 
                          ? 'border-amber-400 text-amber-200 bg-amber-950/30' 
                          : 'border-slate-700 text-slate-300 hover:border-slate-500'
                      }`}
                      title="Konuşan kostüme göre filtrele"
                    >
                      <option value="all">🛡️ Konuşan Kostüm (Tümü)</option>
                      {availableSpeakerSkins.map(([name, count]) => (
                        <option key={name} value={name}>{name} ({count})</option>
                      ))}
                    </select>

                    {/* Target Costume Filter Dropdown */}
                    <select
                      value={targetSkinFilter}
                      onChange={e => setTargetSkinFilter(e.target.value)}
                      className={`bg-[#050D1E] border rounded-xl px-2.5 py-1.5 text-xs font-semibold outline-none cursor-pointer max-w-[190px] transition ${
                        targetSkinFilter !== 'all' 
                          ? 'border-cyan-400 text-cyan-200 bg-cyan-950/30' 
                          : 'border-slate-700 text-slate-300 hover:border-slate-500'
                      }`}
                      title="Hedef kostüme göre filtrele"
                    >
                      <option value="all">🎯 Hedef Kostüm (Tümü)</option>
                      {availableTargetSkins.map(([name, count]) => (
                        <option key={name} value={name}>{name} ({count})</option>
                      ))}
                    </select>

                    <input
                      type="text"
                      placeholder="Ara..."
                      value={tableSearch}
                      onChange={e => setTableSearch(e.target.value)}
                      className="w-44 bg-[#050D1E] border border-slate-700 focus:border-cyan-400 rounded-xl px-3 py-1.5 text-xs text-slate-100 outline-none font-medium"
                    />

                    {(matrixFilter !== 'all' || actionFilter !== 'all' || speakerSkinFilter !== 'all' || targetSkinFilter !== 'all' || tableSearch) && (
                      <button
                        onClick={resetFilters}
                        className="px-3 py-1.5 rounded-xl bg-[#061022] hover:bg-[#08152c] text-xs font-bold text-slate-200 border border-slate-700 flex items-center gap-1.5 cursor-pointer transition shrink-0"
                      >
                        <RotateCcw className="w-3.5 h-3.5" />
                        <span>Sıfırla</span>
                      </button>
                    )}

                    {/* Ses Seviyesi Slider'ı */}
                    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#050D1E] border border-slate-700 text-xs text-slate-200 shadow-sm shrink-0" title={`Ses Seviyesi: %${audioVolume}`}>
                      <button
                        type="button"
                        onClick={() => setAudioVolume(audioVolume === 0 ? 85 : 0)}
                        className="hover:text-amber-400 transition cursor-pointer p-0.5"
                        title={audioVolume === 0 ? "Sesi Aç" : "Sesi Kapat (Mute)"}
                      >
                        {audioVolume === 0 ? (
                          <VolumeX className="w-4 h-4 text-red-400" />
                        ) : audioVolume < 50 ? (
                          <Volume1 className="w-4 h-4 text-amber-300" />
                        ) : (
                          <Volume2 className="w-4 h-4 text-amber-400" />
                        )}
                      </button>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        value={audioVolume}
                        onChange={(e) => setAudioVolume(parseInt(e.target.value))}
                        className="w-16 sm:w-20 h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-amber-400"
                      />
                      <span className="text-[11px] font-mono text-slate-300 w-7 text-right font-bold">
                        %{audioVolume}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Table Rows with Lightweight Reference IDs (Zero-Audio Footprint) */}
                <div className="flex-1 overflow-y-auto pr-1">
                  <table className="w-full text-left border-collapse">
                    <thead className="sticky top-0 bg-[#040C1A] text-slate-300 text-xs uppercase font-mono font-extrabold border-b border-slate-700 z-10">
                      <tr>
                        <th className="py-2.5 px-3 w-10 text-center">
                          <input
                            type="checkbox"
                            checked={filteredItems.length > 0 && filteredItems.every((it, idx) => selectedMap.has(getItemKey(it, idx)))}
                            onChange={() => selectAllCurrent(filteredItems)}
                            title="Filtrelenen tüm replikleri seç veya seçimi kaldır"
                            className="w-4 h-4 accent-amber-400 rounded cursor-pointer"
                          />
                        </th>
                        <th className="py-2.5 px-3 w-24 text-center">İşlem</th>
                        <th className="py-2.5 px-3">Konuşan Şampiyon</th>
                        <th className="py-2.5 px-3">Konuşan Kostüm</th>
                        <th className="py-2.5 px-3">Hedef Şampiyon</th>
                        <th className="py-2.5 px-3">Hedef Kostüm</th>
                        <th className="py-2.5 px-3">Matris Tipi</th>
                        <th className="py-2.5 px-3">Eylem</th>
                        <th className="py-2.5 px-3">Replik / Oyun İçi Event</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/80 text-sm">
                      {filteredItems.length === 0 ? (
                        <tr>
                          <td colSpan="9" className="py-20 text-center text-slate-400 text-sm font-mono">
                            Filtreye uygun atıf kaydı bulunamadı.
                          </td>
                        </tr>
                      ) : (
                        filteredItems.map((it, idx) => {
                          const itemKey = getItemKey(it, idx);
                          const itemRef = it.ref_id || it.raw_event;
                          const isCopied = copiedId === itemRef;
                          const cueId = `${it.speaker_champ}_${it.raw_event}_${it.wem_id || idx}`;
                          const isPlaying = playingId === cueId;
                          const isLoading = audioLoadingId === cueId;
                          const isSelected = selectedMap.has(itemKey);
                          const hasAudio = Boolean(it.wem_id);
                          const isSpeakerFiltered = speakerSkinFilter === it.speaker_skin_name;
                          const isTargetFiltered = targetSkinFilter === it.target_skin_name;

                          return (
                            <tr key={idx} className={`transition group ${isSelected ? 'bg-amber-950/40 ring-1 ring-amber-400/40' : isPlaying ? 'bg-amber-950/30' : isCopied ? 'bg-emerald-950/20' : 'hover:bg-[#091834]'}`}>
                              <td className="py-2.5 px-3 text-center">
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => toggleSelectItem(it, idx)}
                                  title="Bu repliği DaVinci projesine dahil et"
                                  className="w-4 h-4 accent-amber-400 rounded cursor-pointer"
                                />
                              </td>
                              <td className="py-2.5 px-3 text-center">
                                <div className="flex items-center justify-center space-x-1.5">
                                  {/* Play / Listen Button (JIT On-Demand Audio Stream) */}
                                  {hasAudio ? (
                                    <button
                                      onClick={() => playVoice(it, idx)}
                                      disabled={isLoading}
                                      title={isPlaying ? "Durdur" : "Bu repliği dinle (JIT Stream)"}
                                      className={`w-7 h-7 rounded-lg flex items-center justify-center transition cursor-pointer shadow-sm ${
                                        isPlaying
                                          ? 'bg-amber-400 text-slate-950 ring-2 ring-amber-300 animate-pulse'
                                          : 'bg-[#061022] hover:bg-amber-500/30 text-amber-300 border border-slate-700 hover:border-amber-400'
                                      }`}
                                    >
                                      {isLoading ? (
                                        <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-300" />
                                      ) : isPlaying ? (
                                        <Square className="w-3 h-3 fill-current" />
                                      ) : (
                                        <Play className="w-3 h-3 fill-current ml-0.5" />
                                      )}
                                    </button>
                                  ) : (
                                    <div
                                      title="Oyun dosyalarında ses kaydı bulunamadı (Özellik/Tasarım Kaydı - Seslendirilmemiş)"
                                      className="w-7 h-7 rounded-lg flex items-center justify-center bg-slate-900/60 text-slate-500 border border-slate-800 cursor-not-allowed select-none"
                                    >
                                      <VolumeX className="w-3 h-3" />
                                    </div>
                                  )}

                                  {/* Copy Reference ID Button */}
                                  <button
                                    onClick={() => copyRefId(itemRef)}
                                    title={isCopied ? "Panoya Kopyalandı!" : `Referans Kodunu Kopyala: ${itemRef}`}
                                    className={`w-7 h-7 rounded-lg flex items-center justify-center transition cursor-pointer shadow-sm ${
                                      isCopied
                                        ? 'bg-emerald-500 text-slate-950 ring-1 ring-emerald-400'
                                        : 'bg-[#061022] hover:bg-cyan-500/25 text-slate-400 hover:text-cyan-300 border border-slate-700 hover:border-cyan-400'
                                    }`}
                                  >
                                    {isCopied ? (
                                      <Check className="w-3 h-3 stroke-[3]" />
                                    ) : (
                                      <Copy className="w-3 h-3" />
                                    )}
                                  </button>
                                </div>
                              </td>
                              <td className="py-2.5 px-3 font-extrabold text-slate-100">{it.speaker_champ}</td>
                              <td 
                                onClick={() => setSpeakerSkinFilter(isSpeakerFiltered ? 'all' : it.speaker_skin_name)}
                                className={`py-2.5 px-3 text-xs font-semibold truncate max-w-[150px] cursor-pointer transition select-none ${
                                  isSpeakerFiltered
                                    ? 'text-amber-300 bg-amber-500/15 rounded-lg border border-amber-500/40 font-bold'
                                    : 'text-slate-300 hover:text-amber-300 hover:underline'
                                }`}
                                title={`Bu konuşan kostüme göre filtrele: ${it.speaker_skin_name}`}
                              >
                                <div className="flex items-center justify-between">
                                  <span className="truncate">{it.speaker_skin_name}</span>
                                  {isSpeakerFiltered && <span className="text-amber-400 ml-1 font-bold">✓</span>}
                                </div>
                              </td>
                              <td className="py-2.5 px-3 font-extrabold text-amber-300">{it.target_champ}</td>
                              <td 
                                onClick={() => setTargetSkinFilter(isTargetFiltered ? 'all' : it.target_skin_name)}
                                className={`py-2.5 px-3 text-xs font-semibold truncate max-w-[150px] cursor-pointer transition select-none ${
                                  isTargetFiltered
                                    ? 'text-cyan-300 bg-cyan-500/15 rounded-lg border border-cyan-500/40 font-bold'
                                    : 'text-slate-300 hover:text-cyan-300 hover:underline'
                                }`}
                                title={`Bu hedef kostüme göre filtrele: ${it.target_skin_name}`}
                              >
                                <div className="flex items-center justify-between">
                                  <span className="truncate">{it.target_skin_name}</span>
                                  {isTargetFiltered && <span className="text-cyan-400 ml-1 font-bold">✓</span>}
                                </div>
                              </td>
                              <td className="py-2.5 px-3">
                                <span className={`px-2 py-0.5 rounded text-xs font-mono font-extrabold ${
                                  it.matrix_type === 'base_to_base'
                                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/50'
                                    : it.matrix_type === 'skin_to_base'
                                    ? 'bg-cyan-950 text-cyan-300 border border-cyan-500/50'
                                    : it.matrix_type === 'base_to_skin'
                                    ? 'bg-amber-950 text-amber-300 border border-amber-500/50'
                                    : 'bg-purple-950 text-purple-300 border border-purple-500/50'
                                }`}>
                                  {it.matrix_type === 'base_to_base' ? 'Kanon (B➔B)' : it.matrix_type === 'skin_to_base' ? 'Kostüm➔V' : it.matrix_type === 'base_to_skin' ? 'V➔Kostüm' : 'Kostüm➔K'}
                                </span>
                              </td>
                              <td className="py-2.5 px-3">
                                <div className="flex flex-col space-y-1">
                                  <span className="px-2 py-0.5 rounded text-xs font-mono font-bold bg-slate-900 border border-slate-700 text-slate-200 capitalize w-fit">
                                    {it.action_type.replace(/_/g, ' ')}
                                  </span>
                                  {it.variation_total > 1 && (
                                    <span className="px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-300 text-[10px] font-mono w-fit font-bold">
                                      {it.variation_tag || `Varyasyon ${it.variation_index}/${it.variation_total}`}
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="py-2.5 px-3 max-w-[340px]">
                                {it.transcript ? (
                                  <div>
                                    <div className="text-sm font-semibold text-slate-100 italic truncate" title={it.transcript}>
                                      "{it.transcript}"
                                    </div>
                                    <div className="text-xs font-mono text-slate-400 truncate mt-0.5 flex items-center space-x-1.5" title={it.raw_event}>
                                      <span>{it.raw_event}</span>
                                      {it.wem_id && <span className="text-cyan-400 font-bold">#{it.wem_id}</span>}
                                    </div>
                                  </div>
                                ) : (
                                  <div>
                                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800/80 text-amber-300/90 border border-slate-700/60 font-medium">
                                      [Metin Yok - Sadece Etkileşim Kaydı]
                                    </span>
                                    <div className="text-xs font-mono text-slate-400 truncate mt-0.5 flex items-center space-x-1.5" title={it.raw_event}>
                                      <span>{it.raw_event}</span>
                                      {it.wem_id && <span className="text-cyan-400 font-bold">#{it.wem_id}</span>}
                                    </div>
                                  </div>
                                )}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

            </div>
          </>
        )}

        {/* VIEW 2: VERSUS MODE */}
        {activeTab === 'versus' && (
          <VersusMode 
            champions={champions} 
            onCopyRefId={copyRefId}
            copiedId={copiedId}
            onPlayVoice={playVoice}
            playingId={playingId}
            audioLoadingId={audioLoadingId}
            selectedMap={selectedMap}
            onToggleSelect={toggleSelectItem}
            onSelectAll={selectAllCurrent}
            onClearSelection={clearSelection}
            onOpenExportModal={() => setIsExportModalOpen(true)}
          />
        )}

        {/* VIEW 3: RANKINGS LEADERBOARD */}
        {activeTab === 'rankings' && (
          <RankingsView 
            champions={champions} 
            onSelectChampion={(name) => {
              setSelectedChampName(name);
              setActiveTab('matrix');
            }} 
          />
        )}

        {/* VIEW 4: CHAMPION VOICES & SFX STUDIO */}
        {activeTab === 'voices' && (
          <ChampionVoicesView 
            champions={champions} 
            defaultChamp={selectedChampName}
            gameMode={gameMode}
            audioVolume={audioVolume}
          />
        )}

        {/* VIEW 5: PAIR INTERACTIONS & MULTI-TURN DIALOGUES */}
        {activeTab === 'pair_dialogues' && (
          <PairInteractionsView 
            champions={champions}
            gameMode={gameMode}
            audioVolume={audioVolume}
          />
        )}

        {/* VIEW 6: FCPXML FONT & SCENE SIMULATOR STUDIO */}
        {activeTab === 'font_studio' && (
          <FcpxmlFontSimulatorView />
        )}

      </main>

      {/* Floating Bottom Action Bar for DaVinci Resolve Export */}
      {selectedMap.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-gradient-to-r from-[#06142c]/95 via-[#091e42]/95 to-[#06142c]/95 border-2 border-amber-400/80 rounded-2xl p-3 px-5 shadow-[0_10px_40px_rgba(0,0,0,0.85)] backdrop-blur-xl flex items-center space-x-4 animate-in slide-in-from-bottom-5 duration-200">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/25 border border-amber-400/60 flex items-center justify-center text-amber-300 font-bold shadow">
              <Film className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-black text-amber-300 font-mono flex items-center space-x-1.5">
                <span>{selectedMap.size} Replik Seçildi</span>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
              </div>
              <div className="text-[11px] text-slate-300">
                4K Splash Art &amp; DaVinci Resolve Timeline Hazır
              </div>
            </div>
          </div>

          <div className="h-8 w-px bg-slate-700/80" />

          <button
            onClick={() => setIsTranscriptModalOpen(true)}
            className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 via-indigo-600 to-indigo-500 hover:from-purple-500 hover:to-indigo-400 text-white font-bold text-xs md:text-sm tracking-wide shadow-lg hover:shadow-indigo-500/30 transition flex items-center space-x-2 cursor-pointer transform hover:-translate-y-0.5"
            title="XML üretmeksizin yalnızca seçilen repliklerin metinlerini Çoklu Yapay Zeka & Fonetik Güven Skoru ile çözümleyin ve güncelleyin"
          >
            <Brain className="w-4 h-4 text-purple-200" />
            <span>Sadece Replik Metni Üret</span>
          </button>

          <button
            onClick={() => setIsExportModalOpen(true)}
            className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-amber-400 via-amber-500 to-amber-600 hover:from-amber-300 hover:to-amber-500 text-slate-950 font-black text-xs md:text-sm tracking-wide shadow-lg hover:shadow-amber-500/30 transition flex items-center space-x-2 cursor-pointer transform hover:-translate-y-0.5"
          >
            <Film className="w-4 h-4 fill-slate-950" />
            <span>DaVinci Resolve'a Aktar (FCPXML)</span>
          </button>

          <button
            onClick={clearSelection}
            className="px-3 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-xs font-bold text-slate-300 hover:text-white transition cursor-pointer"
          >
            Seçimi Temizle
          </button>
        </div>
      )}

      {/* DaVinci Timeline Export Modal */}
      <DaVinciExportModal
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
        selectedItems={Array.from(selectedMap.values())}
        defaultTimelineName={`${selectedChampName || 'LoL'}_${direction === 'outgoing' ? 'Soyledikleri' : 'Atiflar'}`}
        layoutMode={direction === 'outgoing' ? 'champion_voices' : 'matrix_default'}
        onClearSelection={clearSelection}
      />

      {/* Çoklu Yapay Zeka & Fonetik Güven Skoru ile Replik Metni Üretme Modalı */}
      <TranscriptGeneratorModal
        isOpen={isTranscriptModalOpen}
        onClose={() => setIsTranscriptModalOpen(false)}
        items={Array.from(selectedMap.values())}
        title="Atıf Matrisi Replik Metni Çözümleme"
        onTranscriptsUpdated={(transcriptsMap) => {
          setSelectedMap(prev => {
            const nextMap = new Map(prev);
            for (const [key, item] of nextMap.entries()) {
              const wid = String(item.wem_id || '').trim();
              const ev = item.raw_event || item.event || '';
              if (transcriptsMap[wid]) {
                item.transcript = transcriptsMap[wid];
                item.text = transcriptsMap[wid];
              } else if (transcriptsMap[ev]) {
                item.transcript = transcriptsMap[ev];
                item.text = transcriptsMap[ev];
              }
            }
            return nextMap;
          });
        }}
      />
    </div>
  );
}
