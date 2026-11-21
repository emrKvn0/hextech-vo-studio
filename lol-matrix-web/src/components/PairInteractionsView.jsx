import React, { useState, useEffect, useMemo, useRef } from 'react';
import DaVinciExportModal from './DaVinciExportModal';
import TranscriptGeneratorModal from './TranscriptGeneratorModal';
import {
  Swords, Play, Square, Loader2, Sparkles,
  CheckSquare, Film, ArrowLeftRight, MessageSquare,
  Users, Wand2, Filter, ChevronDown, ChevronRight,
  Search, LayoutGrid, ListFilter,
  Volume2, Volume1, VolumeX,
  Edit3, Check, X, Globe, Brain
} from 'lucide-react';

// Bilinen çok turlu (Chat1 -> Chat2) karşılıklı diyalog çiftleri
const MULTI_TURN_CHAT_PAIRS = new Set([
  'rakan__xayah',
  'kayle__morgana',
  'lucian__senna',
  'yasuo__yone',
  'caitlyn__vi',
  'jinx__vi',
  'darius__garen',
  'diana__leona',
  'ashe__tryndamere',
  'nasus__renekton',
  'khazix__rengar',
  'shen__zed'
]);

const ACTION_LABELS_TR = {
  karsilasma: 'İlk Karşılaşma',
  katletme: 'Katletme',
  kiskirtma: 'Kışkırtma',
  saka: 'Şaka',
  hareket: 'Beraber Yürüyüş',
  yetenek: 'Yetenek / Kalkan',
  saldiri: 'Saldırı',
  asist: 'Asist / Skor',
  olum: 'Ölüm',
  secim: 'Seçim',
  diger: 'Oyun İçi Etkileşim'
};

export default function PairInteractionsView({ champions = [], gameMode = 'lol' }) {
  const [champA, setChampA] = useState(gameMode === 'lor' ? 'Yasuo' : 'Rakan');
  const [champB, setChampB] = useState(gameMode === 'lor' ? 'Riven' : 'Xayah');
  const [pairData, setPairData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [cachedSummaries, setCachedSummaries] = useState({});

  // Sol/Geniş Eşleşme Rehberi (Tüm Karakterlerin Kendi Aralarındaki Diyalog Matrisi)
  const [showFullExplorer, setShowFullExplorer] = useState(false);
  const [pairSearchQuery, setPairSearchQuery] = useState('');
  const [pairTypeFilter, setPairTypeFilter] = useState('mutual'); // 'all' | 'mutual' | 'chat'
  const [pairFocusChamp, setPairFocusChamp] = useState('all');

  // Sağ Diyalog Görünümü Filtreleri
  const [activeViewSection, setActiveViewSection] = useState('all'); // 'all', 'dialogues', 'one_way', 'first_encounter', 'kills', 'taunts_jokes', 'other_gameplay'
  const [activeDialogueCategory, setActiveDialogueCategory] = useState('all');
  const [skinPairFilter, setSkinPairFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [collapsedBlocks, setCollapsedBlocks] = useState({});

  // Ses Oynatıcı & Sıralı Diyalog Oynatıcı
  const [playingWemKey, setPlayingWemKey] = useState(null);
  const [loadingWemKey, setLoadingWemKey] = useState(null);
  const [playingChainId, setPlayingChainId] = useState(null);
  const audioRef = useRef(null);
  const chainAbortRef = useRef(false);

  // Genel Ses Seviyesi (Volume Slider) & Mute
  const [volume, setVolume] = useState(() => {
    const saved = localStorage.getItem('lol_audio_volume');
    return saved !== null ? parseFloat(saved) : 0.5;
  });
  const [isMuted, setIsMuted] = useState(false);

  const handleVolumeChange = (newVol) => {
    setVolume(newVol);
    localStorage.setItem('lol_audio_volume', newVol.toString());
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : newVol;
    }
  };

  const toggleMute = () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    if (audioRef.current) {
      audioRef.current.volume = nextMuted ? 0 : volume;
    }
  };

  // Repliklerin her zaman büyük harfle başlamasını garanti eden formatlayıcı
  const formatTranscript = (text) => {
    if (!text || typeof text !== 'string') return text;
    const trimmed = text.trim();
    if (!trimmed) return trimmed;
    if (trimmed.startsWith('[') || trimmed.startsWith('(')) return trimmed;
    const first = trimmed.charAt(0);
    const trUpper = { i: 'İ', ı: 'I', ç: 'Ç', ş: 'Ş', ğ: 'Ğ', ü: 'Ü', ö: 'Ö' }[first] || first.toUpperCase();
    return trUpper + trimmed.slice(1);
  };

  // Canlı Replik Düzenleme State'i (Inline Transcript Edit)
  const [editingWemId, setEditingWemId] = useState(null);
  const [editingText, setEditingText] = useState('');
  const [savingWemId, setSavingWemId] = useState(null);

  const startEditing = (wemId, currentText) => {
    setEditingWemId(wemId);
    setEditingText(currentText || '');
  };

  const cancelEditing = () => {
    setEditingWemId(null);
    setEditingText('');
  };

  const saveTranscript = async (wemId) => {
    if (!wemId || !editingText.trim()) return;
    setSavingWemId(wemId);
    try {
      const res = await fetch('http://127.0.0.1:8080/api/update-transcript', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          wem_id: wemId,
          transcript: formatTranscript(editingText),
          champA,
          champB
        })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setPairData(prev => {
          if (!prev) return prev;
          const updated = JSON.parse(JSON.stringify(prev));
          for (const c of updated.dialogue_chains || []) {
            for (const t of c.turns || []) {
              if (String(t.wem_id) === String(wemId)) {
                t.transcript = data.transcript;
              }
            }
          }
          for (const s of updated.sections || []) {
            for (const g of s.groups || []) {
              for (const q of g.quotes || []) {
                if (String(q.wem_id) === String(wemId)) {
                  q.transcript = data.transcript;
                }
              }
            }
          }
          return updated;
        });
        setEditingWemId(null);
      }
    } catch (err) {
      console.error('Transcript save error:', err);
    } finally {
      setSavingWemId(null);
    }
  };

  // DaVinci Resolve Seçim Haritası
  const [selectedTurnsMap, setSelectedTurnsMap] = useState(new Map());
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const [isTranscriptModalOpen, setIsTranscriptModalOpen] = useState(false);

  // Eksik Transkript Çözümleme Durumu
  const [transcribing, setTranscribing] = useState(false);

  // Önbellekteki Gerçek WPK/BNK veya LoR Diyalog & Ses Sayılarını Yükle
  useEffect(() => {
    setCachedSummaries({});
    if (gameMode === 'lor') {
      setChampA('Yasuo');
      setChampB('Riven');
    } else {
      setChampA('Rakan');
      setChampB('Xayah');
    }
    fetch(`http://127.0.0.1:8080/api/featured-pairs?game=${gameMode}`)
      .then(r => r.json())
      .then(d => {
        if (d && d.cached_summaries) {
          setCachedSummaries(prev => ({ ...prev, ...d.cached_summaries }));
        }
      })
      .catch(() => {});
  }, [gameMode]);

  // ---------------------------------------------------------------------------
  // 1. ŞAMPİYON İKON HARİTASI (champions prop içindeki icon_url)
  // ---------------------------------------------------------------------------
  const champIconMap = useMemo(() => {
    const map = new Map();
    champions.forEach(c => {
      if (c?.name && c?.icon_url) {
        map.set(c.name.toLowerCase(), c.icon_url);
        map.set(c.name.toLowerCase().replace(/[^a-z0-9]/g, ''), c.icon_url);
      }
    });
    return map;
  }, [champions]);

  const getChampIcon = (name) => {
    if (!name) return 'https://raw.communitydragon.org/latest/plugins/rcp-be-lol-game-data/global/default/v1/champion-icons/-1.png';
    const key = name.toLowerCase();
    const cleanKey = key.replace(/[^a-z0-9]/g, '');
    return (
      champIconMap.get(key) ||
      champIconMap.get(cleanKey) ||
      `https://ddragon.leagueoflegends.com/cdn/14.24.1/img/champion/${name.replace(/\s+/g, '')}.png`
    );
  };

  // ---------------------------------------------------------------------------
  // 2. TÜM KARAKTERLERİN KENDİ ARALARINDAKİ DİYALOGLARININ OTOMATİK ANALİZİ
  //    (174 Şampiyonun tamamındaki A ⇄ B ve A ➔ B etkileşimlerini hesaplar)
  // ---------------------------------------------------------------------------
  const allChampionPairs = useMemo(() => {
    if (!champions || champions.length === 0) return [];
    const pairMap = new Map();

    const ensurePair = (n1, n2) => {
      const [first, second] = [n1, n2].sort((a, b) => a.localeCompare(b));
      const pKey = `${first.toLowerCase()}__${second.toLowerCase()}`;
      if (!pairMap.has(pKey)) {
        pairMap.set(pKey, {
          pairKey: pKey,
          champA: first,
          champB: second,
          iconA: getChampIcon(first),
          iconB: getChampIcon(second),
          aToBCount: 0,
          bToACount: 0,
          totalCount: 0,
          isMutual: false,
          hasMultiTurnChat: MULTI_TURN_CHAT_PAIRS.has(pKey),
          actions: {},
          sampleQuotes: [],
          skinsInvolved: new Set()
        });
      }
      return pairMap.get(pKey);
    };

    champions.forEach(c => {
      const spk = c.name;
      (c.outgoing_items || []).forEach(item => {
        const tgt = item.target_champ;
        if (!tgt || tgt.toLowerCase() === spk.toLowerCase()) return;

        const entry = ensurePair(spk, tgt);
        if (spk.toLowerCase() === entry.champA.toLowerCase()) {
          entry.aToBCount += 1;
        } else {
          entry.bToACount += 1;
        }
        entry.totalCount += 1;

        const act = item.base_action || item.action_type || 'diger';
        entry.actions[act] = (entry.actions[act] || 0) + 1;

        if (item.speaker_skin_name && !item.speaker_is_base) {
          entry.skinsInvolved.add(item.speaker_skin_name);
        }
        if (item.transcript && entry.sampleQuotes.length < 2) {
          entry.sampleQuotes.push({
            speaker: spk,
            target: tgt,
            text: item.transcript,
            action: ACTION_LABELS_TR[act] || act
          });
        }
      });
    });

    // Gerçek WPK/BNK önbellek istatistiklerini (cachedSummaries) birleştir
    const list = Array.from(pairMap.values()).map(p => {
      const cached = cachedSummaries[p.pairKey];
      const exactTotal = cached ? (cached.total_interactions || (cached.dialogue_turns_count || 0) + (cached.one_way_quotes_count || 0)) : null;
      const dialogueChainsCount = cached ? (cached.dialogue_chains_count ?? cached.total_dialogue_chains ?? 0) : 0;
      const dialogueTurnsCount = cached ? (cached.dialogue_turns_count ?? cached.total_dialogue_turns ?? 0) : 0;
      const oneWayCount = cached ? (cached.one_way_quotes_count ?? cached.total_one_way_quotes ?? 0) : 0;

      const isMutual = (p.aToBCount > 0 && p.bToACount > 0) || dialogueChainsCount > 0;
      const hasMultiTurnChat = p.hasMultiTurnChat || dialogueChainsCount > 0;
      const displayTotal = exactTotal && exactTotal > p.totalCount ? exactTotal : p.totalCount;

      const topActions = Object.entries(p.actions)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([k, cnt]) => ({ label: ACTION_LABELS_TR[k] || k, count: cnt }));

      return {
        ...p,
        isMutual,
        hasMultiTurnChat,
        displayTotal,
        hasExactWpkStats: Boolean(exactTotal),
        dialogueChainsCount,
        dialogueTurnsCount,
        oneWayCount,
        skinCount: p.skinsInvolved.size,
        topActions
      };
    });

    // Sıralama: Önce çok turlu sohbeti olanlar, sonra karşılıklı (A ⇄ B) olanlar ve toplam ses sayısı yüksek olanlar
    list.sort((x, y) => {
      if (x.hasMultiTurnChat !== y.hasMultiTurnChat) return x.hasMultiTurnChat ? -1 : 1;
      if (x.isMutual !== y.isMutual) return x.isMutual ? -1 : 1;
      return y.displayTotal - x.displayTotal;
    });

    return list;
  }, [champions, champIconMap, cachedSummaries]);

  // Eşleşme Rehberi Filtrelenmiş Liste
  const filteredPairCards = useMemo(() => {
    let list = allChampionPairs;
    if (pairTypeFilter === 'mutual') {
      list = list.filter(p => p.isMutual || p.hasMultiTurnChat);
    } else if (pairTypeFilter === 'chat') {
      list = list.filter(p => p.hasMultiTurnChat);
    }
    if (pairFocusChamp !== 'all') {
      const fc = pairFocusChamp.toLowerCase();
      list = list.filter(p => p.champA.toLowerCase() === fc || p.champB.toLowerCase() === fc);
    }
    if (pairSearchQuery.trim()) {
      const q = pairSearchQuery.toLowerCase().trim();
      list = list.filter(p =>
        p.champA.toLowerCase().includes(q) ||
        p.champB.toLowerCase().includes(q) ||
        p.sampleQuotes.some(sq => sq.text.toLowerCase().includes(q))
      );
    }
    return list;
  }, [allChampionPairs, pairTypeFilter, pairFocusChamp, pairSearchQuery]);

  // ---------------------------------------------------------------------------
  // 3. SEÇİLİ İKİLİNİN WPK/BNK DETAYLI DİYALOG VERİSİNİ ÇEK
  // ---------------------------------------------------------------------------
  const fetchPairData = (cA, cB, forceRefresh = false) => {
    if (!cA || !cB) return;
    setLoading(true);
    setError(null);
    stopAudio();

    const url = `http://127.0.0.1:8080/api/pair-interactions?champA=${encodeURIComponent(cA)}&champB=${encodeURIComponent(cB)}&game=${gameMode}${forceRefresh ? '&refresh=true' : ''}`;
    fetch(url)
      .then(res => {
        if (!res.ok) throw new Error(`Sunucu hatası: ${res.status}`);
        return res.json();
      })
      .then(json => {
        setPairData(json);
        if (json?.summary) {
          const [first, second] = [cA.toLowerCase(), cB.toLowerCase()].sort();
          setCachedSummaries(prev => ({
            ...prev,
            [`${first}__${second}`]: json.summary
          }));
        }
        setSkinPairFilter('all');
        setActiveDialogueCategory('all');
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setError('İkili diyalog verisi alınamadı. Lütfen ses sunucusunun (Port 8080) açık olduğundan emin olun.');
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchPairData(champA, champB);
    return () => stopAudio();
  }, [champA, champB, gameMode]);

  const stopAudio = () => {
    chainAbortRef.current = true;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setPlayingWemKey(null);
    setLoadingWemKey(null);
    setPlayingChainId(null);
  };

  const playSingleTurn = (turn) => {
    const key = `${turn.speaker_champ}_${turn.raw_event}_${turn.wem_id}`;
    if (playingWemKey === key && !playingChainId) {
      stopAudio();
      return;
    }
    stopAudio();
    chainAbortRef.current = false;
    setLoadingWemKey(key);

    const url = `http://127.0.0.1:8080/api/audio-play?speaker=${encodeURIComponent(turn.speaker_champ)}&event=${encodeURIComponent(turn.raw_event)}&target=${encodeURIComponent(turn.target_champ || '')}&wem_id=${encodeURIComponent(turn.wem_id || '')}`;
    const audio = new Audio(url);
    audio.volume = isMuted ? 0 : volume;
    audioRef.current = audio;

    audio.oncanplaythrough = () => {
      setLoadingWemKey(null);
      setPlayingWemKey(key);
      audio.play().catch(() => setPlayingWemKey(null));
    };
    audio.onended = () => {
      setPlayingWemKey(null);
      audioRef.current = null;
    };
    audio.onerror = () => {
      setLoadingWemKey(null);
      setPlayingWemKey(null);
      audioRef.current = null;
    };
  };

  // Sıralı Oynatıcı (İster tek bir 2-3'lü diyalog, ister tüm kategori bloğu)
  const playTurnsSequentially = async (blockId, turnsList) => {
    if (playingChainId === blockId) {
      stopAudio();
      return;
    }
    stopAudio();
    chainAbortRef.current = false;
    setPlayingChainId(blockId);

    for (let i = 0; i < turnsList.length; i++) {
      if (chainAbortRef.current) break;
      const turn = turnsList[i];
      const key = `${turn.speaker_champ}_${turn.raw_event}_${turn.wem_id}`;
      setLoadingWemKey(key);

      await new Promise((resolve) => {
        const url = `http://127.0.0.1:8080/api/audio-play?speaker=${encodeURIComponent(turn.speaker_champ)}&event=${encodeURIComponent(turn.raw_event)}&target=${encodeURIComponent(turn.target_champ || '')}&wem_id=${encodeURIComponent(turn.wem_id || '')}`;
        const audio = new Audio(url);
        audio.volume = isMuted ? 0 : volume;
        audioRef.current = audio;

        audio.oncanplaythrough = () => {
          if (chainAbortRef.current) {
            resolve();
            return;
          }
          setLoadingWemKey(null);
          setPlayingWemKey(key);
          audio.play().catch(() => resolve());
        };
        audio.onended = () => {
          setPlayingWemKey(null);
          setTimeout(resolve, 220);
        };
        audio.onerror = () => {
          setLoadingWemKey(null);
          setPlayingWemKey(null);
          resolve();
        };
      });
    }

    if (!chainAbortRef.current) {
      setPlayingChainId(null);
      setPlayingWemKey(null);
      setLoadingWemKey(null);
    }
  };

  // Sade ve Anlaşılır Eylem Başlığı Üretici (Madde 2)
  const simplifyActionTitle = (title, groupTitle) => {
    const raw = (title || groupTitle || '').toLowerCase();
    if (raw.includes('dost') || raw.includes('ally')) return '🤝 Dost Karşılaşması';
    if (raw.includes('düşman') || raw.includes('dusman') || raw.includes('enemy')) return '⚔️ Düşman Karşılaşması';
    if (raw.includes('katlet') || raw.includes('ölüm') || raw.includes('olum') || raw.includes('kill')) return '💀 Katletme';
    if (raw.includes('kışkırt') || raw.includes('kiskirt') || raw.includes('taunt')) return '🔥 Kışkırtma';
    if (raw.includes('şaka') || raw.includes('saka') || raw.includes('joke')) return '😄 Şaka';
    if (raw.includes('blok') || raw.includes('savunma') || raw.includes('guard')) return '🛡️ Savunma & Blok';
    if (raw.includes('büyü') || raw.includes('buyu') || raw.includes('spell') || raw.includes('saldırı') || raw.includes('saldiri')) return '⚡ Büyü & Saldırı';
    return '✨ Karşılaşma';
  };

  // Benzersiz Turn Anahtarı (Madde 1 & 5: Aynı repliğin farklı şampiyon diyaloglarında çakışmasını önler)
  const getTurnKey = (turn) => {
    const chId = turn.chain_id || 'turn';
    const partner = turn.partner_champ || turn.target_champ || '';
    return `${chId}_${turn.speaker_champ}_${partner}_${turn.raw_event}_${turn.wem_id}`;
  };

  // DaVinci FCPXML Seçim Yardımcıları
  const buildDaVinciItem = (turn, contextLabel = '') => {
    const key = getTurnKey(turn);
    const isLeftSpeaker = turn.speaker_champ.toLowerCase() === champA.toLowerCase();
    const partner = turn.partner_champ || (isLeftSpeaker ? (champB === 'ALL' ? (turn.target_champ || 'Diğer') : champB) : champA);
    const targetName = turn.target_champ && turn.target_champ !== 'Diğer' ? turn.target_champ : partner;
    const cleanAction = simplifyActionTitle(contextLabel, turn.action_name);

    return {
      key,
      ref_id: key,
      chain_id: turn.chain_id || '',
      speaker_champ: turn.speaker_champ,
      speaker_skin_num: turn.speaker_skin_num || 0,
      speaker_skin_name: turn.speaker_skin_name || `Varsayılan ${turn.speaker_champ}`,
      speaker_splash_url: turn.speaker_splash_url || '',
      target_champ: targetName,
      target_skin_num: turn.target_skin_num || 0,
      target_skin_name: turn.target_skin_name || (champB === 'ALL' ? targetName : ''),
      target_splash_url: turn.target_splash_url || '',
      dialogue_side: isLeftSpeaker ? 'left' : 'right',
      left_champ: champA,
      right_champ: champB === 'ALL' ? targetName : champB,
      partner_champ: targetName,
      action_type: cleanAction,
      action_name: cleanAction,
      raw_event: turn.raw_event,
      wem_id: turn.wem_id,
      transcript: turn.transcript || ''
    };
  };

  const toggleSelectTurn = (turn, contextLabel = '') => {
    const item = buildDaVinciItem(turn, contextLabel);
    setSelectedTurnsMap(prev => {
      const next = new Map(prev);
      if (next.has(item.key)) next.delete(item.key);
      else next.set(item.key, item);
      return next;
    });
  };

  const toggleSelectTurnsBatch = (turnsList, contextLabel = '') => {
    const items = turnsList.map(t => buildDaVinciItem(t, contextLabel));
    setSelectedTurnsMap(prev => {
      const next = new Map(prev);
      const allIn = items.length > 0 && items.every(it => next.has(it.key));
      if (allIn) {
        items.forEach(it => next.delete(it.key));
      } else {
        items.forEach(it => next.set(it.key, it));
      }
      return next;
    });
  };

  // Eksik Türkçe Metinleri Whisper large-v3-turbo ile Çözümle
  const handleTranscribeMissing = async () => {
    if (!pairData || transcribing) return;
    const missing = [];
    (pairData.dialogue_chains || []).forEach(c => {
      c.turns.forEach(t => {
        if (!t.transcript) missing.push(t);
      });
    });
    (pairData.sections || []).forEach(sec => {
      sec.groups.forEach(g => {
        g.quotes.forEach(q => {
          if (!q.transcript) missing.push(q);
        });
      });
    });

    if (missing.length === 0) return;
    setTranscribing(true);
    try {
      const res = await fetch('http://127.0.0.1:8080/api/transcribe-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: missing.slice(0, 1000) })
      });
      if (res.ok) {
        fetchPairData(champA, champB, true);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setTranscribing(false);
    }
  };

  // Mevcut Kostüm Çiftleri Listesi
  const availableSkinPairs = useMemo(() => {
    if (!pairData) return [];
    const map = new Map();
    (pairData.dialogue_chains || []).forEach(c => {
      const k = `${c.skinA_name} ⇄ ${c.skinB_name}`;
      map.set(k, (map.get(k) || 0) + c.turn_count);
    });
    (pairData.sections || []).forEach(sec => {
      sec.groups.forEach(g => {
        const k = g.direction === 'A_to_B'
          ? `${g.speaker_skin_name} ⇄ ${g.target_skin_name}`
          : `${g.target_skin_name} ⇄ ${g.speaker_skin_name}`;
        map.set(k, (map.get(k) || 0) + g.quotes.length);
      });
    });
    return Array.from(map.entries());
  }, [pairData]);

  // ---------------------------------------------------------------------------
  // 4. KARŞILIKLI DİYALOGLARI KATEGORİZE ET VE TEKİL COMPACT BLOKLARDA BİRLEŞTİR
  // ---------------------------------------------------------------------------
  const categorizedDialogueBlocks = useMemo(() => {
    if (!pairData?.dialogue_chains) return [];
    let list = pairData.dialogue_chains;
    if (skinPairFilter !== 'all') {
      list = list.filter(c => `${c.skinA_name} ⇄ ${c.skinB_name}` === skinPairFilter);
    }
    if (activeDialogueCategory !== 'all') {
      list = list.filter(c => c.group_id === activeDialogueCategory);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(c =>
        c.title.toLowerCase().includes(q) ||
        c.group_title.toLowerCase().includes(q) ||
        c.skinA_name.toLowerCase().includes(q) ||
        c.skinB_name.toLowerCase().includes(q) ||
        c.turns.some(t => (t.transcript || '').toLowerCase().includes(q) || t.raw_event.toLowerCase().includes(q))
      );
    }

    const blockMap = new Map();
    list.forEach((chain) => {
      const partner = chain.partner_champ || '';
      const bKey = champB === 'ALL' && partner
        ? `${partner}__${chain.group_id}__${chain.skinA_num}`
        : `${chain.group_id}__${chain.skinA_num}__${chain.skinB_num}`;
      if (!blockMap.has(bKey)) {
        blockMap.set(bKey, {
          blockKey: bKey,
          group_id: chain.group_id,
          group_title: chain.group_title,
          partner_champ: partner,
          skinA_num: chain.skinA_num,
          skinA_name: chain.skinA_name,
          skinA_splash: chain.skinA_splash,
          skinB_num: chain.skinB_num,
          skinB_name: partner || chain.skinB_name,
          skinB_splash: chain.skinB_splash,
          exchanges: [],
          allTurns: []
        });
      }
      const blk = blockMap.get(bKey);
      const exchangeNumber = blk.exchanges.length + 1;
      const enrichedTurns = chain.turns.map((t, idx) => ({
        ...t,
        partner_champ: partner,
        exchangeNumber,
        exchangeTitle: chain.title,
        chain_id: chain.chain_id,
        isFirstInExchange: idx === 0,
        isLastInExchange: idx === chain.turns.length - 1,
        exchangeTurnCount: chain.turns.length,
        exchangeTurns: chain.turns
      }));
      blk.exchanges.push({
        exchangeNumber,
        chain_id: chain.chain_id,
        title: chain.title,
        partner_champ: partner,
        turns: enrichedTurns
      });
      blk.allTurns.push(...enrichedTurns);
    });

    return Array.from(blockMap.values());
  }, [pairData, skinPairFilter, activeDialogueCategory, searchQuery, champB]);

  // Diyalog Alt Kategori Sekmeleri
  const dialogueCategoryPills = useMemo(() => {
    if (!pairData?.dialogue_chains) return [];
    const counts = new Map();
    pairData.dialogue_chains.forEach(c => {
      const prev = counts.get(c.group_id) || { id: c.group_id, title: c.group_title, chains: 0, turns: 0 };
      prev.chains += 1;
      prev.turns += c.turn_count;
      counts.set(c.group_id, prev);
    });
    return Array.from(counts.values());
  }, [pairData]);

  // Filtrelenmiş Birebir Etkileşim Bölümleri (First Encounter, Kills, Taunts/Jokes, Other Gameplay)
  const filteredSections = useMemo(() => {
    if (!pairData?.sections) return [];
    let secs = pairData.sections;
    if (activeViewSection !== 'all' && activeViewSection !== 'dialogues' && activeViewSection !== 'one_way') {
      secs = secs.filter(s => s.id === activeViewSection);
    }
    return secs.map(sec => {
      let groups = sec.groups;
      if (skinPairFilter !== 'all') {
        groups = groups.filter(g => {
          const pairLabel = g.direction === 'A_to_B'
            ? `${g.speaker_skin_name} ⇄ ${g.target_skin_name}`
            : `${g.target_skin_name} ⇄ ${g.speaker_skin_name}`;
          return pairLabel === skinPairFilter;
        });
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase().trim();
        groups = groups.map(g => ({
          ...g,
          quotes: g.quotes.filter(qt =>
            (qt.transcript || '').toLowerCase().includes(q) ||
            qt.raw_event.toLowerCase().includes(q) ||
            g.sub_category.toLowerCase().includes(q) ||
            g.speaker_skin_name.toLowerCase().includes(q) ||
            g.target_skin_name.toLowerCase().includes(q)
          )
        })).filter(g => g.quotes.length > 0);
      }
      return { ...sec, groups };
    }).filter(sec => sec.groups.length > 0);
  }, [pairData, activeViewSection, skinPairFilter, searchQuery]);

  // Tek Tıkla Tüm Diyalogları veya Tüm Sayfayı Seçme Yardımcıları (Madde 3)
  const allVisibleDialogueTurns = useMemo(() => {
    const arr = [];
    categorizedDialogueBlocks.forEach(blk => {
      blk.allTurns.forEach(t => {
        arr.push({ turn: t, label: simplifyActionTitle(t.exchangeTitle, blk.group_title) });
      });
    });
    return arr;
  }, [categorizedDialogueBlocks]);

  const allVisibleOneWayQuotes = useMemo(() => {
    const arr = [];
    filteredSections.forEach(sec => {
      sec.groups.forEach(grp => {
        grp.quotes.forEach(q => {
          arr.push({ turn: q, label: simplifyActionTitle(grp.sub_category, sec.title) });
        });
      });
    });
    return arr;
  }, [filteredSections]);

  const areAllDialoguesSelected = useMemo(() => {
    if (allVisibleDialogueTurns.length === 0) return false;
    return allVisibleDialogueTurns.every(({ turn }) =>
      selectedTurnsMap.has(getTurnKey(turn))
    );
  }, [allVisibleDialogueTurns, selectedTurnsMap]);

  const areAllEverythingSelected = useMemo(() => {
    const combined = [...allVisibleDialogueTurns, ...allVisibleOneWayQuotes];
    if (combined.length === 0) return false;
    return combined.every(({ turn }) =>
      selectedTurnsMap.has(getTurnKey(turn))
    );
  }, [allVisibleDialogueTurns, allVisibleOneWayQuotes, selectedTurnsMap]);

  const handleToggleAllDialogues = () => {
    if (allVisibleDialogueTurns.length === 0) return;
    setSelectedTurnsMap(prev => {
      const next = new Map(prev);
      if (areAllDialoguesSelected) {
        allVisibleDialogueTurns.forEach(({ turn }) => {
          next.delete(getTurnKey(turn));
        });
      } else {
        allVisibleDialogueTurns.forEach(({ turn, label }) => {
          const item = buildDaVinciItem(turn, label);
          next.set(item.key, item);
        });
      }
      return next;
    });
  };

  const handleToggleAllEverything = () => {
    const combined = [...allVisibleDialogueTurns, ...allVisibleOneWayQuotes];
    if (combined.length === 0) return;
    setSelectedTurnsMap(prev => {
      const next = new Map(prev);
      if (areAllEverythingSelected) {
        combined.forEach(({ turn }) => {
          next.delete(getTurnKey(turn));
        });
      } else {
        combined.forEach(({ turn, label }) => {
          const item = buildDaVinciItem(turn, label);
          next.set(item.key, item);
        });
      }
      return next;
    });
  };

  const summaryChainsCount = pairData?.summary?.dialogue_chains_count ?? pairData?.summary?.total_dialogue_chains ?? (pairData?.dialogue_chains?.length || 0);
  const summaryTurnsCount = pairData?.summary?.dialogue_turns_count ?? pairData?.summary?.total_dialogue_turns ?? 0;
  const summaryOneWayCount = pairData?.summary?.one_way_quotes_count ?? pairData?.summary?.total_one_way_quotes ?? 0;
  const summaryTotalAll = summaryTurnsCount + summaryOneWayCount;

  const toggleCollapseBlock = (bKey) => {
    setCollapsedBlocks(prev => ({ ...prev, [bKey]: !prev[bKey] }));
  };

  const selectPair = (cA, cB) => {
    setChampA(cA);
    setChampB(cB);
    setShowFullExplorer(false);
  };

  const swapChampions = () => {
    setChampA(champB);
    setChampB(champA);
  };

  return (
    <div className="flex-1 flex overflow-hidden bg-[#1e222d] text-slate-100 rounded-2xl border border-slate-700/60 shadow-xl min-h-0">
      
      {/* =======================================================================
          SOL PANEL: TÜM KARAKTER EŞLEŞMELERİ & DİYALOG ANALİZ REHBERİ
         ======================================================================= */}
      <aside className={`${showFullExplorer ? 'w-full' : 'w-84 lg:w-[390px] border-r border-slate-700/60'} bg-[#232836] flex flex-col shrink-0 transition-all duration-200 min-h-0`}>
        
        {/* Sol Başlık ve Tam Ekran Matris Butonu */}
        <div className="p-3.5 border-b border-slate-700/60 space-y-2.5 bg-[#262c3c]">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-extrabold text-slate-100 flex items-center gap-2">
                <Users className="w-4 h-4 text-indigo-300" />
                <span>Tüm Diyalog Eşleşmeleri ({filteredPairCards.length})</span>
              </h2>
              <p className="text-[11px] text-slate-300">
                Kim kime ne demiş, kaç karşılıklı diyalog ve ses var otomatik analiz
              </p>
            </div>
            <button
              onClick={() => setShowFullExplorer(!showFullExplorer)}
              className={`px-2.5 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition cursor-pointer border ${
                showFullExplorer
                  ? 'bg-indigo-500 text-white border-indigo-400 shadow'
                  : 'bg-[#2f364a] hover:bg-[#384057] text-indigo-200 border-slate-600/70'
              }`}
              title={showFullExplorer ? 'Normal Görünüme Dön' : 'Tüm Eşleşmeleri Geniş Ekranda İncele'}
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span>{showFullExplorer ? 'Diyaloğa Dön' : 'Geniş Rehber'}</span>
            </button>
          </div>

          {/* Arama ve Şampiyon Filtresi */}
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
              <input
                type="text"
                value={pairSearchQuery}
                onChange={e => setPairSearchQuery(e.target.value)}
                placeholder="İkili veya replik ara (Rakan, Yasuo...)"
                className="w-full bg-[#1e222d] border border-slate-600/70 focus:border-indigo-400 rounded-xl pl-8 pr-2.5 py-1.5 text-xs text-slate-100 outline-none placeholder:text-slate-400"
              />
            </div>
            <select
              value={pairFocusChamp}
              onChange={e => setPairFocusChamp(e.target.value)}
              className="bg-[#1e222d] border border-slate-600/70 rounded-xl px-2.5 py-1.5 text-xs font-semibold text-slate-200 outline-none cursor-pointer max-w-[130px]"
              title="Belirli bir şampiyonun tüm diyalog eşleşmelerini filtrele"
            >
              <option value="all">Tüm Şampiyonlar</option>
              {champions.map(c => (
                <option key={c.name} value={c.name}>{c.name}</option>
              ))}
            </select>
          </div>

          {/* Eşleşme Türü Sekmeleri */}
          <div className="flex items-center gap-1.5 text-[11px] font-bold">
            <button
              onClick={() => setPairTypeFilter('mutual')}
              className={`flex-1 py-1.5 px-2 rounded-lg transition cursor-pointer border text-center ${
                pairTypeFilter === 'mutual'
                  ? 'bg-indigo-500/25 text-indigo-200 border-indigo-400/50'
                  : 'bg-[#1e222d]/60 text-slate-300 border-transparent hover:text-white'
              }`}
            >
              Karşılıklı (A ⇄ B)
            </button>
            <button
              onClick={() => setPairTypeFilter('chat')}
              className={`flex-1 py-1.5 px-2 rounded-lg transition cursor-pointer border text-center ${
                pairTypeFilter === 'chat'
                  ? 'bg-violet-500/25 text-violet-200 border-violet-400/50'
                  : 'bg-[#1e222d]/60 text-slate-300 border-transparent hover:text-white'
              }`}
            >
              Soru-Cevap Sohbet
            </button>
            <button
              onClick={() => setPairTypeFilter('all')}
              className={`flex-1 py-1.5 px-2 rounded-lg transition cursor-pointer border text-center ${
                pairTypeFilter === 'all'
                  ? 'bg-sky-500/25 text-sky-200 border-sky-400/50'
                  : 'bg-[#1e222d]/60 text-slate-300 border-transparent hover:text-white'
              }`}
            >
              Tümü ({allChampionPairs.length})
            </button>
          </div>
        </div>

        {/* Eşleşme Kartları Listesi */}
        <div className={`flex-1 overflow-y-auto p-3 scrollbar-thin ${
          showFullExplorer ? 'grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-3 content-start' : 'space-y-2'
        }`}>
          {filteredPairCards.map(pair => {
            const isSelected =
              (pair.champA.toLowerCase() === champA.toLowerCase() && pair.champB.toLowerCase() === champB.toLowerCase()) ||
              (pair.champA.toLowerCase() === champB.toLowerCase() && pair.champB.toLowerCase() === champA.toLowerCase());

            return (
              <div
                key={pair.pairKey}
                onClick={() => selectPair(pair.champA, pair.champB)}
                className={`p-3 rounded-xl border transition-all cursor-pointer flex flex-col justify-between gap-2 ${
                  isSelected
                    ? 'bg-[#2f374d] border-indigo-400 shadow-md ring-1 ring-indigo-400/30'
                    : 'bg-[#282e3e] border-slate-700/70 hover:bg-[#2d3446] hover:border-slate-500/80'
                }`}
              >
                {/* Üst Satır: İki Karakterin İkonu + İsimleri + Gerçek Ses/Diyalog Sayısı */}
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <div className="flex items-center -space-x-2 shrink-0">
                      <img
                        src={pair.iconA}
                        alt={pair.champA}
                        className="w-9 h-9 rounded-full object-cover border-2 border-sky-400/80 bg-slate-800 shadow-sm"
                        loading="lazy"
                      />
                      <img
                        src={pair.iconB}
                        alt={pair.champB}
                        className="w-9 h-9 rounded-full object-cover border-2 border-violet-400/80 bg-slate-800 shadow-sm"
                        loading="lazy"
                      />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 text-xs font-extrabold text-slate-100 truncate">
                        <span className="text-sky-200 truncate">{pair.champA}</span>
                        <span className="text-slate-400 font-mono">{pair.isMutual ? '⇄' : '➔'}</span>
                        <span className="text-violet-200 truncate">{pair.champB}</span>
                      </div>
                      {pair.hasExactWpkStats ? (
                        <div className="flex items-center gap-1.5 text-[10px] text-slate-300 font-mono mt-0.5">
                          <span className="text-violet-200 font-semibold">{pair.dialogueChainsCount} Diyalog ({pair.dialogueTurnsCount} Söz)</span>
                          <span>•</span>
                          <span className="text-sky-200">{pair.oneWayCount} Tekil</span>
                        </div>
                      ) : (
                        <div className="flex items-center gap-1.5 text-[10px] text-slate-300 font-mono mt-0.5">
                          <span>{pair.champA}: <b>{pair.aToBCount}</b></span>
                          <span>•</span>
                          <span>{pair.champB}: <b>{pair.bToACount}</b></span>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="text-right shrink-0">
                    <span className={`px-2 py-0.5 rounded-lg text-xs font-mono font-bold ${
                      pair.hasMultiTurnChat
                        ? 'bg-violet-500/25 text-violet-200 border border-violet-400/40'
                        : 'bg-[#1e222d] text-slate-200 border border-slate-600/60'
                    }`}>
                      {pair.displayTotal} {pair.hasExactWpkStats ? 'Ses' : 'Olay'}
                    </span>
                    {pair.hasMultiTurnChat && (
                      <div className="text-[9px] text-violet-300 font-bold mt-0.5">
                        {pair.dialogueChainsCount > 0 ? `${pair.dialogueChainsCount} Sohbet Zinciri` : 'Sıralı Sohbet'}
                      </div>
                    )}
                  </div>
                </div>

                {/* Kategori Özeti Rozetleri */}
                {pair.topActions.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1">
                    {pair.topActions.map(act => (
                      <span
                        key={act.label}
                        className="px-2 py-0.5 rounded-md bg-[#1e222d]/80 text-[10px] text-slate-300 border border-slate-700/60"
                      >
                        {act.label}: <b className="text-slate-100">{act.count}</b>
                      </span>
                    ))}
                  </div>
                )}

                {/* Örnek Replik Önizlemesi */}
                {pair.sampleQuotes.length > 0 && (
                  <div className="text-[11px] text-slate-300/90 italic bg-[#1e222d]/60 px-2.5 py-1.5 rounded-lg border border-slate-700/50 whitespace-normal break-words">
                    <span className="font-bold not-italic text-sky-300">{pair.sampleQuotes[0].speaker}: </span>
                    "{pair.sampleQuotes[0].text}"
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </aside>

      {/* =======================================================================
          SAĞ ANA BÖLÜM: SEÇİLİ İKİLİNİN KATEGORİZE & ALT ALTA DİYALOG LİSTESİ
         ======================================================================= */}
      {!showFullExplorer && (
        <div className="flex-1 flex flex-col overflow-hidden min-h-0 bg-[#1e222d]">
          
          {/* ÜST BAŞLIK: İKİ ŞAMPİYONUN İKONU, SEÇİCİSİ VE FİLTRELER */}
          <div className="p-4 bg-[#252a3a] border-b border-slate-700/60 shrink-0 space-y-3">
            
            <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-3">
              {/* Şampiyon A ⇄ Şampiyon B İkonlu Kartlar + Tıklanabilir Filtre Rozetleri */}
              <div className="flex flex-wrap items-center gap-2.5">
                {/* Sol Şampiyon (A) */}
                <div className="flex items-center space-x-2.5 bg-[#1e222d] border border-sky-400/40 rounded-xl p-2 pr-3 shadow-sm">
                  <img
                    src={getChampIcon(champA)}
                    alt={champA}
                    className="w-10 h-10 rounded-full object-cover border-2 border-sky-300 bg-slate-800 shrink-0"
                  />
                  <div>
                    <div className="text-[10px] font-mono uppercase text-sky-300 font-bold">1. Karakter</div>
                    <select
                      value={champA}
                      onChange={e => setChampA(e.target.value)}
                      className="bg-transparent text-sm font-extrabold text-slate-100 outline-none cursor-pointer"
                    >
                      {champions.map(c => (
                        <option key={c.name} value={c.name} className="bg-[#232836] text-slate-100">
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <button
                  onClick={swapChampions}
                  className="p-2.5 rounded-xl bg-[#2f364a] hover:bg-[#384057] border border-slate-600/70 text-slate-200 transition cursor-pointer"
                  title="Karakterlerin Yönünü Değiştir"
                >
                  <ArrowLeftRight className="w-4 h-4" />
                </button>

                {/* Sağ Şampiyon (B) */}
                <div className={`flex items-center space-x-2.5 bg-[#1e222d] border ${champB === 'ALL' ? 'border-amber-400/80 bg-amber-500/10' : 'border-violet-400/40'} rounded-xl p-2 pr-3 shadow-sm transition`}>
                  {champB === 'ALL' ? (
                    <div className="w-10 h-10 rounded-full bg-amber-500/20 border-2 border-amber-300 flex items-center justify-center text-amber-300 font-bold shrink-0">
                      <Globe className="w-5 h-5" />
                    </div>
                  ) : (
                    <img
                      src={getChampIcon(champB)}
                      alt={champB}
                      className="w-10 h-10 rounded-full object-cover border-2 border-violet-300 bg-slate-800 shrink-0"
                    />
                  )}
                  <div>
                    <div className={`text-[10px] font-mono uppercase ${champB === 'ALL' ? 'text-amber-300 font-extrabold' : 'text-violet-300 font-bold'}`}>
                      2. Karakter {champB === 'ALL' ? '(Tüm Etkileşimler)' : '(Hedef)'}
                    </div>
                    <select
                      value={champB}
                      onChange={e => setChampB(e.target.value)}
                      className={`bg-transparent text-sm font-extrabold outline-none cursor-pointer ${champB === 'ALL' ? 'text-amber-300' : 'text-slate-100'}`}
                    >
                      <option value="ALL" className="bg-[#232836] text-amber-300 font-bold">
                        🌐 Tümü ({champA} ile Etkileşime Giren Herkes)
                      </option>
                      {champions.map(c => (
                        <option key={c.name} value={c.name} className="bg-[#232836] text-slate-100">
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                {/* Hızlı Buton: Tüm Etkileşenleri Listele / Tekil Mod */}
                <button
                  type="button"
                  onClick={() => {
                    if (champB === 'ALL') {
                      setChampB(gameMode === 'lor' ? (champA === 'Azir' ? 'Sivir' : 'Riven') : 'Xayah');
                    } else {
                      setChampB('ALL');
                    }
                  }}
                  className={`px-3 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 transition cursor-pointer border ${
                    champB === 'ALL'
                      ? 'bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border-amber-400 shadow-sm ring-1 ring-amber-400/40'
                      : 'bg-[#2b3142] hover:bg-[#363e54] text-slate-200 border-slate-600/70'
                  }`}
                  title={champB === 'ALL' ? 'Tekil karakter ikilisine dön' : `${champA} ile diyaloğu ve repliği olan tüm karakterleri sağda listele`}
                >
                  <Globe className={`w-3.5 h-3.5 ${champB === 'ALL' ? 'text-amber-300' : 'text-indigo-300'}`} />
                  <span>{champB === 'ALL' ? '🌐 Tümü Listeleniyor' : '🌐 Tümünü Listele'}</span>
                </button>

                {/* Tıklanabilir Özet & Filtre Butonları (Madde 4: Karşılıklı Diyalog & Tekil Etkileşim Butonları) */}
                {pairData?.summary && (
                  <div className="flex flex-wrap items-center gap-2 pl-1">
                    <button
                      type="button"
                      onClick={() => setActiveViewSection(prev => prev === 'dialogues' ? 'all' : 'dialogues')}
                      className={`px-3 py-1.5 rounded-xl border text-xs font-bold transition cursor-pointer flex items-center gap-1.5 ${
                        activeViewSection === 'dialogues'
                          ? 'bg-violet-500 text-white border-violet-300 shadow-md'
                          : 'bg-indigo-500/20 hover:bg-indigo-500/30 border-indigo-400/50 text-indigo-200'
                      }`}
                      title="Sadece Karşılıklı Sıralı Diyalogları Göster / Tümüne Dön"
                    >
                      <MessageSquare className="w-3.5 h-3.5" />
                      <span>{summaryChainsCount} Karşılıklı Diyalog ({summaryTurnsCount} Söz)</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setActiveViewSection(prev => prev === 'one_way' ? 'all' : 'one_way')}
                      className={`px-3 py-1.5 rounded-xl border text-xs font-bold transition cursor-pointer flex items-center gap-1.5 ${
                        activeViewSection === 'one_way'
                          ? 'bg-sky-500 text-slate-950 border-sky-300 shadow-md font-extrabold'
                          : 'bg-[#1e222d] hover:bg-[#2f364a] border-slate-600/70 text-slate-200 hover:border-sky-400/50'
                      }`}
                      title="Sadece Tekil Etkileşimleri (İlk Karşılaşma, Katletme, Şaka, Diğer) Göster / Tümüne Dön"
                    >
                      <Swords className="w-3.5 h-3.5 text-sky-300" />
                      <span>{summaryOneWayCount} Tekil Etkileşim</span>
                    </button>
                  </div>
                )}
              </div>

              {/* Sağ Aksiyon Butonları: Tüm Diyalogları Seç + Tümünü Seç + Whisper large-v3-turbo + DaVinci FCPXML */}
              <div className="flex flex-wrap items-center gap-2">
                {allVisibleDialogueTurns.length > 0 && (
                  <button
                    type="button"
                    onClick={handleToggleAllDialogues}
                    className={`px-3 py-2 rounded-xl border text-xs font-bold flex items-center space-x-1.5 transition cursor-pointer ${
                      areAllDialoguesSelected
                        ? 'bg-violet-500 text-white border-violet-300 shadow-sm'
                        : 'bg-[#1e222d] hover:bg-[#2f364a] text-violet-200 border-violet-400/50'
                    }`}
                    title="Ekrandaki tüm karşılıklı diyalog zincirlerini DaVinci FCPXML için tek tıkla seç veya kaldır"
                  >
                    <CheckSquare className="w-3.5 h-3.5" />
                    <span>{areAllDialoguesSelected ? 'Diyalog Seçimini Kaldır' : `Tüm Diyalogları Seç (${allVisibleDialogueTurns.length})`}</span>
                  </button>
                )}

                <button
                  type="button"
                  onClick={handleToggleAllEverything}
                  className={`px-3 py-2 rounded-xl border text-xs font-bold flex items-center space-x-1.5 transition cursor-pointer ${
                    areAllEverythingSelected
                      ? 'bg-sky-500 text-slate-950 border-sky-300 font-extrabold shadow-sm'
                      : 'bg-[#1e222d] hover:bg-[#2f364a] text-sky-200 border-sky-400/50'
                  }`}
                  title="Sayfadaki tüm diyalogları ve tekil etkileşimleri tek tıkla seç veya kaldır"
                >
                  <CheckSquare className="w-3.5 h-3.5" />
                  <span>{areAllEverythingSelected ? 'Tüm Seçimi Kaldır' : `Sayfadaki Tümünü Seç (${allVisibleDialogueTurns.length + allVisibleOneWayQuotes.length})`}</span>
                </button>

                <button
                  onClick={() => setIsTranscriptModalOpen(true)}
                  className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold flex items-center space-x-1.5 transition cursor-pointer shadow-md"
                  title="XML üretmeksizin yalnızca diyalogların metinlerini Çoklu Yapay Zeka & Fonetik Güven Skoru ile çözümleyin ve güncelleyin"
                >
                  <Brain className="w-3.5 h-3.5 text-purple-200" />
                  <span>Sadece Replik Metni Üret ({selectedTurnsMap.size > 0 ? selectedTurnsMap.size : (allVisibleDialogueTurns.length + allVisibleOneWayQuotes.length)})</span>
                </button>

                <button
                  onClick={handleTranscribeMissing}
                  disabled={transcribing}
                  className="px-3 py-2 rounded-xl bg-teal-500/20 hover:bg-teal-500/30 border border-teal-400/40 text-teal-200 text-xs font-bold flex items-center space-x-1.5 transition cursor-pointer disabled:opacity-50"
                  title="Metni görünmeyen sesleri Faster-Whisper large-v3-turbo ile Türkçe metne çevir"
                >
                  {transcribing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wand2 className="w-3.5 h-3.5" />}
                  <span>{transcribing ? 'large-v3-turbo Çözüyor...' : 'Eksik Metinleri Çöz (Turbo)'}</span>
                </button>

                <button
                  onClick={() => setIsExportModalOpen(true)}
                  disabled={selectedTurnsMap.size === 0}
                  className={`px-3.5 py-2 rounded-xl text-xs font-extrabold flex items-center space-x-1.5 transition cursor-pointer ${
                    selectedTurnsMap.size > 0
                      ? 'bg-indigo-500 hover:bg-indigo-400 text-white shadow-md'
                      : 'bg-[#1e222d] text-slate-400 border border-slate-700 cursor-not-allowed'
                  }`}
                >
                  <Film className="w-3.5 h-3.5" />
                  <span>DaVinci FCPXML ({selectedTurnsMap.size})</span>
                </button>

                {/* Genel Ses Seviyesi Slider'ı (Volume Control) */}
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#1e222d] border border-slate-700/80 text-xs text-slate-200 shadow-sm" title={`Ses Seviyesi: %${Math.round((isMuted ? 0 : volume) * 100)}`}>
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
                    className="w-20 sm:w-24 h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-amber-400"
                  />
                  <span className="text-[11px] font-mono text-slate-300 w-8 text-right font-bold">
                    {isMuted ? '%0' : `%${Math.round(volume * 100)}`}
                  </span>
                </div>
              </div>
            </div>

            {/* KATEGORİ SEKMELERİ + KOSTÜM ÇİFTİ FİLTRESİ + ARAMA */}
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-2.5 pt-2 border-t border-slate-700/50">
              <div className="flex flex-wrap items-center gap-1.5">
                {[
                  { id: 'all', label: `Tüm Etkileşimler (${summaryTotalAll})` },
                  { id: 'dialogues', label: `Karşılıklı Diyaloglar (${summaryChainsCount} Diyalog • ${summaryTurnsCount} Söz)` },
                  { id: 'one_way', label: `Tekil Etkileşimler (${summaryOneWayCount})` },
                  { id: 'first_encounter', label: 'İlk Karşılaşma' },
                  { id: 'kills', label: 'Katletmeler (Kills)' },
                  { id: 'taunts_jokes', label: 'Kışkırtma & Şaka' },
                  { id: 'other_gameplay', label: 'Diğer Oyun İçi' }
                ].map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveViewSection(tab.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer border ${
                      activeViewSection === tab.id
                        ? 'bg-indigo-500/25 text-indigo-200 border-indigo-400/50 shadow-sm'
                        : 'bg-[#1e222d] text-slate-300 border-slate-700/70 hover:text-white'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <div className="flex items-center space-x-1.5 bg-[#1e222d] border border-slate-600/70 rounded-xl px-2.5 py-1.5">
                  <Filter className="w-3.5 h-3.5 text-indigo-300" />
                  <select
                    value={skinPairFilter}
                    onChange={e => setSkinPairFilter(e.target.value)}
                    className="bg-transparent text-xs font-bold text-slate-200 outline-none cursor-pointer max-w-[230px]"
                  >
                    <option value="all" className="bg-[#232836]">Tüm Kostüm Eşleşmeleri ({availableSkinPairs.length})</option>
                    {availableSkinPairs.map(([pairLabel, cnt]) => (
                      <option key={pairLabel} value={pairLabel} className="bg-[#232836]">
                        {pairLabel} ({cnt} ses)
                      </option>
                    ))}
                  </select>
                </div>

                <input
                  type="text"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="Replik veya kostüm filtrele..."
                  className="bg-[#1e222d] border border-slate-600/70 focus:border-indigo-400 rounded-xl px-3 py-1.5 text-xs text-slate-100 outline-none w-48 placeholder:text-slate-400"
                />
              </div>
            </div>

            {/* KARŞILIKLI DİYALOG ALT KATEGORİ FİLTRESİ */}
            {dialogueCategoryPills.length > 1 && (activeViewSection === 'all' || activeViewSection === 'dialogues') && (
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-thin">
                <span className="text-[11px] font-bold text-slate-300 shrink-0 flex items-center gap-1 mr-1">
                  <ListFilter className="w-3.5 h-3.5 text-violet-300" />
                  <span>Diyalog Konusu:</span>
                </span>
                <button
                  onClick={() => setActiveDialogueCategory('all')}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-bold whitespace-nowrap transition cursor-pointer border ${
                    activeDialogueCategory === 'all'
                      ? 'bg-violet-500/25 text-violet-200 border-violet-400/50'
                      : 'bg-[#1e222d] text-slate-300 border-slate-700/60 hover:text-white'
                  }`}
                >
                  Tüm Konular ({pairData?.dialogue_chains?.length || 0})
                </button>
                {dialogueCategoryPills.map(cat => (
                  <button
                    key={cat.id}
                    onClick={() => setActiveDialogueCategory(cat.id)}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-bold whitespace-nowrap transition cursor-pointer border ${
                      activeDialogueCategory === cat.id
                        ? 'bg-violet-500/25 text-violet-200 border-violet-400/50'
                        : 'bg-[#1e222d] text-slate-300 border-slate-700/60 hover:text-white'
                    }`}
                  >
                    {cat.title} ({cat.chains} Diyalog • {cat.turns} Söz)
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* ANA KAYDIRILABİLİR DİYALOG LİSTESİ */}
          <div className="flex-1 overflow-y-auto p-5 space-y-6 scrollbar-thin">
            
            {loading && (
              <div className="h-64 flex flex-col items-center justify-center space-y-3">
                <Loader2 className="w-8 h-8 text-indigo-300 animate-spin" />
                <div className="text-sm font-bold text-slate-200">
                  {champA} ⇄ {champB} Diyalogları Hazırlanıyor...
                </div>
              </div>
            )}

            {error && !loading && (
              <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-400/40 text-rose-200 text-xs">
                {error}
              </div>
            )}

            {/* =================================================================
                1. BÖLÜM: KATEGORİZE EDİLMİŞ ALT ALTA KARŞILIKLI DİYALOG BLOKLARI
               ================================================================= */}
            {!loading && !error && (activeViewSection === 'all' || activeViewSection === 'dialogues') && categorizedDialogueBlocks.length > 0 && (
              <section className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700/60 pb-2">
                  <div>
                    <h3 className="text-sm md:text-base font-extrabold text-slate-100 flex items-center gap-2">
                      <MessageSquare className="w-4 h-4 text-violet-300" />
                      <span>Karşılıklı Diyaloglar (Konularına ve Kostümlere Göre Kategorize)</span>
                    </h3>
                    <p className="text-xs text-slate-300">
                      Her kategori bloğunun içinde 2'li / 3'lü karşılıklı konuşmalar sırasıyla alt alta dizilmiştir. İster tek satırı, ister 2'li diyaloğu, ister tüm kategoriyi sırayla dinleyebilirsiniz.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleToggleAllDialogues}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition cursor-pointer border ${
                      areAllDialoguesSelected
                        ? 'bg-violet-500 text-white border-violet-300 shadow'
                        : 'bg-[#2b3040] hover:bg-[#343a4d] text-violet-200 border-violet-400/50'
                    }`}
                  >
                    <CheckSquare className="w-3.5 h-3.5" />
                    <span>{areAllDialoguesSelected ? 'Tüm Diyalog Seçimini Kaldır' : `Birebir Sohbetteki Tüm Diyalogları Seç (${allVisibleDialogueTurns.length} Söz)`}</span>
                  </button>
                </div>

                <div className="space-y-4">
                  {categorizedDialogueBlocks.map(block => {
                    const isCollapsed = !!collapsedBlocks[block.blockKey];
                    const isBlockPlaying = playingChainId === block.blockKey;
                    const blockKeys = block.allTurns.map(t => getTurnKey(t));
                    const isBlockSelected = blockKeys.length > 0 && blockKeys.every(k => selectedTurnsMap.has(k));

                    return (
                      <div
                        key={block.blockKey}
                        className="rounded-xl bg-[#252936] border border-slate-700/70 shadow-md overflow-hidden"
                      >
                        {/* KATEGORİ BLOĞU ÜST BAŞLIĞI (Resimdeki "[Icon] Xayah to Rakan / Kills and Objectives > ..." görünümü) */}
                        <div className="px-4 py-3 bg-[#2b3040] border-b border-slate-700/70 flex flex-wrap items-center justify-between gap-3">
                          <div
                            onClick={() => toggleCollapseBlock(block.blockKey)}
                            className="flex items-center gap-3 cursor-pointer select-none min-w-0"
                          >
                            <div className="flex items-center -space-x-2 shrink-0">
                              <img
                                src={getChampIcon(champA)}
                                alt={champA}
                                className="w-8 h-8 rounded-full object-cover border-2 border-sky-300 bg-slate-800"
                              />
                              <img
                                src={getChampIcon(block.partner_champ || block.skinB_name || (champB === 'ALL' ? 'Pyke' : champB))}
                                alt={block.partner_champ || block.skinB_name || champB}
                                className="w-8 h-8 rounded-full object-cover border-2 border-violet-300 bg-slate-800"
                              />
                            </div>

                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-1.5 text-sm font-bold">
                                <span className="text-sky-300">{block.skinA_name}</span>
                                <span className="text-slate-400 font-normal text-xs">⇄</span>
                                <span className="text-violet-300">{block.partner_champ || block.skinB_name}</span>
                                {block.partner_champ && (
                                  <span className="px-2 py-0.5 rounded-md text-[10px] font-extrabold bg-amber-500/20 text-amber-300 border border-amber-400/40 shadow-xs">
                                    {block.partner_champ}
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-slate-300 font-medium flex items-center gap-1.5 mt-0.5">
                                <span>{block.group_title}</span>
                                <span>›</span>
                                <span className="text-slate-200 font-semibold">
                                  {block.exchanges.length} Karşılıklı Diyalog ({block.allTurns.length} Replik Satırı)
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => playTurnsSequentially(block.blockKey, block.allTurns)}
                              className={`px-3 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 transition cursor-pointer border ${
                                isBlockPlaying
                                  ? 'bg-violet-500 text-white border-violet-300'
                                  : 'bg-[#343a4d] hover:bg-[#3f465c] text-violet-200 border-slate-600/70'
                              }`}
                            >
                              {isBlockPlaying ? (
                                <>
                                  <Square className="w-3 h-3 fill-current" />
                                  <span>Durdur</span>
                                </>
                              ) : (
                                <>
                                  <Play className="w-3 h-3 fill-current" />
                                  <span>Tüm Grubu Sırayla Dinle ({block.allTurns.length})</span>
                                </>
                              )}
                            </button>

                            <button
                              onClick={() => toggleSelectTurnsBatch(block.allTurns, simplifyActionTitle(block.group_title))}
                              className={`px-2.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1 transition cursor-pointer border ${
                                isBlockSelected
                                  ? 'bg-indigo-500 text-white border-indigo-300'
                                  : 'bg-[#1e222d] hover:bg-[#343a4d] text-slate-200 border-slate-600/70'
                              }`}
                            >
                              <CheckSquare className="w-3.5 h-3.5" />
                              <span>{isBlockSelected ? 'Seçildi' : 'Grubu Seç'}</span>
                            </button>

                            <button
                              onClick={() => toggleCollapseBlock(block.blockKey)}
                              className="p-1.5 rounded-lg bg-[#1e222d] hover:bg-[#343a4d] text-slate-300 border border-slate-700 cursor-pointer"
                              title={isCollapsed ? 'Genişlet' : 'Daralt'}
                            >
                              {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            </button>
                          </div>
                        </div>

                        {/* ALT ALTA SIRALI REPLİK SATIRLARI (Resimdeki temiz tablo/satır görünümü) */}
                        {!isCollapsed && (
                          <div className="divide-y divide-[#323748]">
                            {block.allTurns.map((turn, idx) => {
                              const isLeft = turn.speaker_champ.toLowerCase() === champA.toLowerCase();
                              const playKey = `${turn.speaker_champ}_${turn.raw_event}_${turn.wem_id}`;
                              const turnKey = getTurnKey(turn);
                              const isPlaying = playingWemKey === playKey;
                              const isLoading = loadingWemKey === playKey;
                              const isSelected = selectedTurnsMap.has(turnKey);
                              const isExchangePlaying = playingChainId === turn.chain_id;

                              return (
                                <div
                                  key={`${turnKey}_${idx}`}
                                  className={`px-4 py-2.5 flex items-center justify-between gap-3 transition ${
                                    isPlaying
                                      ? 'bg-indigo-500/20'
                                      : isSelected
                                      ? 'bg-sky-500/15'
                                      : turn.exchangeNumber % 2 === 1
                                      ? 'bg-[#232734] hover:bg-[#2a2f3f]'
                                      : 'bg-[#262b39] hover:bg-[#2d3344]'
                                  } ${turn.isLastInExchange ? 'border-b-2 border-b-[#3b4256]' : ''}`}
                                >
                                  {/* Sol Taraf: Checkbox + Oynat Butonu + Karakter İkonu + "Rakan: Replik Metni" */}
                                  <div className="flex items-center gap-3 min-w-0 flex-1">
                                    <input
                                      type="checkbox"
                                      checked={isSelected}
                                      onChange={() => toggleSelectTurn(turn, simplifyActionTitle(turn.exchangeTitle, block.group_title))}
                                      className="w-3.5 h-3.5 accent-indigo-400 rounded cursor-pointer shrink-0"
                                    />

                                    <button
                                      onClick={() => playSingleTurn(turn)}
                                      className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition cursor-pointer ${
                                        isPlaying
                                          ? 'bg-violet-400 text-slate-950 shadow'
                                          : 'bg-[#34394c] hover:bg-[#434961] text-violet-300 border border-violet-400/30'
                                      }`}
                                      title="Bu satırı dinle"
                                    >
                                      {isLoading ? (
                                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                      ) : isPlaying ? (
                                        <Square className="w-2.5 h-2.5 fill-current" />
                                      ) : (
                                        <Play className="w-3 h-3 fill-current ml-0.5" />
                                      )}
                                    </button>

                                    <img
                                      src={getChampIcon(turn.speaker_champ)}
                                      alt={turn.speaker_champ}
                                      className={`w-6 h-6 rounded-full object-cover shrink-0 border ${
                                        isLeft ? 'border-sky-300' : 'border-violet-300'
                                      }`}
                                      loading="lazy"
                                    />

                                    <div className="min-w-0 flex-1 text-xs md:text-sm leading-relaxed flex items-center gap-1.5 flex-wrap">
                                      <span className={`font-bold mr-1 ${isLeft ? 'text-sky-300' : 'text-violet-300'}`}>
                                        {turn.speaker_champ}:
                                      </span>
                                      {editingWemId === turn.wem_id ? (
                                        <div className="flex items-center gap-1.5 flex-1 min-w-[200px]">
                                          <input
                                            type="text"
                                            value={editingText}
                                            onChange={(e) => setEditingText(e.target.value)}
                                            onKeyDown={(e) => {
                                              if (e.key === 'Enter') saveTranscript(turn.wem_id);
                                              if (e.key === 'Escape') cancelEditing();
                                            }}
                                            autoFocus
                                            className="px-2 py-1 bg-slate-900 border border-amber-400/80 rounded text-amber-200 text-xs w-full outline-none font-medium"
                                          />
                                          <button
                                            type="button"
                                            onClick={() => saveTranscript(turn.wem_id)}
                                            disabled={savingWemId === turn.wem_id}
                                            className="p-1 rounded bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/40 border border-emerald-500/40 cursor-pointer"
                                            title="Kaydet (Enter)"
                                          >
                                            {savingWemId === turn.wem_id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                                          </button>
                                          <button
                                            type="button"
                                            onClick={cancelEditing}
                                            className="p-1 rounded bg-slate-700/50 text-slate-300 hover:bg-slate-700 cursor-pointer"
                                            title="İptal (Esc)"
                                          >
                                            <X className="w-3.5 h-3.5" />
                                          </button>
                                        </div>
                                      ) : (
                                        <div className="group/edit inline-flex items-center gap-1.5">
                                          {turn.transcript ? (
                                            <span 
                                              onDoubleClick={() => startEditing(turn.wem_id, turn.transcript)}
                                              className="text-slate-100 font-medium cursor-text"
                                              title="Çift tıklayarak veya kalem butonuna basarak metni düzenle"
                                            >
                                              "{formatTranscript(turn.transcript)}"
                                            </span>
                                          ) : (
                                            <span 
                                              onDoubleClick={() => startEditing(turn.wem_id, '')}
                                              className="text-slate-400 italic font-mono text-xs cursor-text"
                                              title="Çift tıklayarak metin ekle"
                                            >
                                              [Ses Kaydı #{turn.wem_id} — Dinlemek için ▶ butonuna tıklayın]
                                            </span>
                                          )}
                                          <button
                                            type="button"
                                            onClick={() => startEditing(turn.wem_id, turn.transcript)}
                                            className="opacity-0 group-hover/edit:opacity-100 p-0.5 text-slate-400 hover:text-amber-400 transition cursor-pointer"
                                            title="Replik Metnini Canlı Düzenle"
                                          >
                                            <Edit3 className="w-3 h-3" />
                                          </button>
                                        </div>
                                      )}
                                    </div>
                                  </div>

                                  {/* Sağ Taraf: Kaçıncı Diyalog & Kaçıncı Söz Rozeti + İkiliyi Sırayla Dinle */}
                                  <div className="flex items-center gap-2 shrink-0">
                                    {turn.isFirstInExchange && (
                                      <button
                                        onClick={() => playTurnsSequentially(turn.chain_id, turn.exchangeTurns)}
                                        className={`px-2 py-0.5 rounded-md text-[10px] font-bold flex items-center gap-1 transition cursor-pointer border ${
                                          isExchangePlaying
                                            ? 'bg-violet-500 text-white border-violet-300'
                                            : 'bg-[#303648] hover:bg-[#3b4258] text-slate-200 border-slate-600/70'
                                        }`}
                                        title="Bu 2'li / 3'lü mini diyaloğu arka arkaya dinle"
                                      >
                                        <Play className="w-2.5 h-2.5 fill-current" />
                                        <span>Diyalog #{turn.exchangeNumber} ({turn.exchangeTurnCount} Söz)</span>
                                      </button>
                                    )}
                                    <span className="px-2 py-0.5 rounded bg-[#1e222d] text-[10px] font-mono text-slate-300 border border-slate-700/70">
                                      #{turn.exchangeNumber} • {turn.step}. Söz
                                    </span>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {/* =================================================================
                2. BÖLÜM: TEK YÖNLÜ ETKİLEŞİMLER (İlk Karşılaşma, Katletme, Şaka, Diğer)
                   (Resimdeki gibi [Icon] Xayah to Rakan başlığı altında alt alta liste)
               ================================================================= */}
            {!loading && !error && activeViewSection !== 'dialogues' && filteredSections.map(section => (
              <section key={section.id} className="space-y-3">
                <div className="border-b border-slate-700/60 pb-2 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm md:text-base font-extrabold text-slate-100">
                      {section.title}
                    </h3>
                    <p className="text-xs text-slate-300">{section.subtitle}</p>
                  </div>
                  <span className="text-xs font-mono text-slate-300">
                    {section.groups.length} Grup
                  </span>
                </div>

                <div className="space-y-3">
                  {section.groups.map((grp, gIdx) => {
                    const grpKeys = grp.quotes.map(q => getTurnKey(q));
                    const isGrpSelected = grpKeys.length > 0 && grpKeys.every(k => selectedTurnsMap.has(k));
                    const isAToB = grp.direction === 'A_to_B';
                    const grpBlockId = `sec_${section.id}_${gIdx}`;
                    const isGrpPlaying = playingChainId === grpBlockId;

                    return (
                      <div
                        key={`${section.id}_${gIdx}_${grp.speaker_skin_num}_${grp.target_skin_num}_${grp.sub_category}`}
                        className="rounded-xl bg-[#252936] border border-slate-700/70 shadow-sm overflow-hidden"
                      >
                        {/* Üst Başlık: Resimdeki "[Icon] Xayah to Rakan / Kills and Objectives › Killing Xayah" */}
                        <div className="px-4 py-2.5 bg-[#2b3040] border-b border-slate-700/70 flex flex-wrap items-center justify-between gap-2">
                          <div className="flex items-center gap-2.5 min-w-0">
                            <img
                              src={getChampIcon(grp.speaker_champ)}
                              alt={grp.speaker_champ}
                              className={`w-7 h-7 rounded-full object-cover border-2 shrink-0 ${
                                isAToB ? 'border-sky-300' : 'border-violet-300'
                              }`}
                            />
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-1.5 text-xs md:text-sm font-bold">
                                <span className={isAToB ? 'text-sky-300' : 'text-violet-300'}>
                                  {grp.speaker_skin_name}
                                </span>
                                <span className="text-slate-400 font-normal text-xs">➔</span>
                                <span className="text-slate-200">
                                  {grp.target_skin_name}
                                </span>
                              </div>
                              <div className="text-[11px] text-slate-300">
                                {section.title.split('(')[0].trim()} › <span className="text-slate-200 font-semibold">{grp.sub_category}</span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => playTurnsSequentially(grpBlockId, grp.quotes)}
                              className={`px-2.5 py-1 rounded-lg text-xs font-bold flex items-center gap-1 transition cursor-pointer border ${
                                isGrpPlaying
                                  ? 'bg-violet-500 text-white border-violet-300'
                                  : 'bg-[#343a4d] hover:bg-[#3f465c] text-violet-200 border-slate-600/70'
                              }`}
                            >
                              <Play className="w-3 h-3 fill-current" />
                              <span>{isGrpPlaying ? 'Durdur' : `Sırayla Dinle (${grp.quotes.length})`}</span>
                            </button>

                            <button
                              onClick={() => toggleSelectTurnsBatch(grp.quotes, simplifyActionTitle(grp.sub_category, section.title))}
                              className={`px-2.5 py-1 rounded-lg text-xs font-bold flex items-center gap-1 transition cursor-pointer border ${
                                isGrpSelected
                                  ? 'bg-indigo-500 text-white border-indigo-300'
                                  : 'bg-[#1e222d] hover:bg-[#343a4d] text-slate-200 border-slate-600/70'
                              }`}
                            >
                              <CheckSquare className="w-3.5 h-3.5" />
                              <span>{isGrpSelected ? 'Seçildi' : 'Grubu Seç'}</span>
                            </button>
                          </div>
                        </div>

                        {/* Alt Alta Replik Satırları */}
                        <div className="divide-y divide-[#323748]">
                          {grp.quotes.map((qt, qIdx) => {
                            const playKey = `${qt.speaker_champ}_${qt.raw_event}_${qt.wem_id}`;
                            const turnKey = getTurnKey(qt);
                            const isPlaying = playingWemKey === playKey;
                            const isLoading = loadingWemKey === playKey;
                            const isSelected = selectedTurnsMap.has(turnKey);

                            return (
                              <div
                                key={`${turnKey}_${qIdx}`}
                                className={`px-4 py-2.5 flex items-center justify-between gap-3 transition ${
                                  isPlaying
                                    ? 'bg-indigo-500/20'
                                    : isSelected
                                    ? 'bg-sky-500/15'
                                    : 'bg-[#232734] hover:bg-[#2a2f3f]'
                                }`}
                              >
                                <div className="flex items-center gap-3 min-w-0 flex-1">
                                  <input
                                    type="checkbox"
                                    checked={isSelected}
                                    onChange={() => toggleSelectTurn(qt, simplifyActionTitle(grp.sub_category, section.title))}
                                    className="w-3.5 h-3.5 accent-indigo-400 rounded cursor-pointer shrink-0"
                                  />

                                  <button
                                    onClick={() => playSingleTurn(qt)}
                                    className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition cursor-pointer ${
                                      isPlaying
                                        ? 'bg-violet-400 text-slate-950 shadow'
                                        : 'bg-[#34394c] hover:bg-[#434961] text-violet-300 border border-violet-400/30'
                                    }`}
                                  >
                                    {isLoading ? (
                                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                    ) : isPlaying ? (
                                      <Square className="w-2.5 h-2.5 fill-current" />
                                    ) : (
                                      <Play className="w-3 h-3 fill-current ml-0.5" />
                                    )}
                                  </button>

                                  <img
                                    src={getChampIcon(qt.speaker_champ)}
                                    alt={qt.speaker_champ}
                                    className={`w-6 h-6 rounded-full object-cover shrink-0 border ${
                                      isAToB ? 'border-sky-300' : 'border-violet-300'
                                    }`}
                                    loading="lazy"
                                  />

                                  <div className="min-w-0 flex-1 text-xs md:text-sm leading-relaxed flex items-center gap-1.5 flex-wrap">
                                    <span className={`font-bold mr-1 ${isAToB ? 'text-sky-300' : 'text-violet-300'}`}>
                                      {qt.speaker_champ}:
                                    </span>
                                    {editingWemId === qt.wem_id ? (
                                        <div className="flex items-center gap-1.5 flex-1 min-w-[200px]">
                                          <input
                                            type="text"
                                            value={editingText}
                                            onChange={(e) => setEditingText(e.target.value)}
                                            onKeyDown={(e) => {
                                              if (e.key === 'Enter') saveTranscript(qt.wem_id);
                                              if (e.key === 'Escape') cancelEditing();
                                            }}
                                            autoFocus
                                            className="px-2 py-1 bg-slate-900 border border-amber-400/80 rounded text-amber-200 text-xs w-full outline-none font-medium"
                                          />
                                          <button
                                            type="button"
                                            onClick={() => saveTranscript(qt.wem_id)}
                                            disabled={savingWemId === qt.wem_id}
                                            className="p-1 rounded bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/40 border border-emerald-500/40 cursor-pointer"
                                            title="Kaydet (Enter)"
                                          >
                                            {savingWemId === qt.wem_id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                                          </button>
                                          <button
                                            type="button"
                                            onClick={cancelEditing}
                                            className="p-1 rounded bg-slate-700/50 text-slate-300 hover:bg-slate-700 cursor-pointer"
                                            title="İptal (Esc)"
                                          >
                                            <X className="w-3.5 h-3.5" />
                                          </button>
                                        </div>
                                    ) : (
                                        <div className="group/edit inline-flex items-center gap-1.5">
                                          {qt.transcript ? (
                                            <span 
                                              onDoubleClick={() => startEditing(qt.wem_id, qt.transcript)}
                                              className="text-slate-100 font-medium cursor-text"
                                              title="Çift tıklayarak veya kalem butonuna basarak metni düzenle"
                                            >
                                              "{formatTranscript(qt.transcript)}"
                                            </span>
                                          ) : (
                                            <span 
                                              onDoubleClick={() => startEditing(qt.wem_id, '')}
                                              className="text-slate-400 font-mono text-xs cursor-text"
                                              title="Çift tıklayarak metin ekle"
                                            >
                                              {qt.raw_event} (Varyasyon {qt.variation_index}/{qt.variation_total})
                                            </span>
                                          )}
                                          <button
                                            type="button"
                                            onClick={() => startEditing(qt.wem_id, qt.transcript)}
                                            className="opacity-0 group-hover/edit:opacity-100 p-0.5 text-slate-400 hover:text-amber-400 transition cursor-pointer"
                                            title="Replik Metnini Canlı Düzenle"
                                          >
                                            <Edit3 className="w-3 h-3" />
                                          </button>
                                        </div>
                                    )}
                                  </div>
                                </div>

                                <span className="text-[10px] font-mono text-slate-400 shrink-0">
                                  #{qt.wem_id}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            ))}

            {!loading && !error && categorizedDialogueBlocks.length === 0 && filteredSections.length === 0 && (
              <div className="h-64 flex flex-col items-center justify-center space-y-2 text-slate-300 text-sm">
                <Users className="w-8 h-8 text-slate-500" />
                <p>{champA} ve {champB} arasında bu filtreye uygun birebir etkileşim bulunamadı.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* YÜZEN ALT ÇUBUK: BİREBİR DİYALOG DAVINCI RESOLVE FCPXML AKTARIMI */}
      {selectedTurnsMap.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-[#262c3d]/95 border border-indigo-400/70 rounded-2xl p-3 px-5 shadow-2xl backdrop-blur-xl flex items-center space-x-4">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/25 border border-indigo-400/50 flex items-center justify-center text-indigo-200 font-bold">
              <Film className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-extrabold text-indigo-200 font-mono flex items-center space-x-1.5">
                <span>{selectedTurnsMap.size} Diyalog Satırı Seçildi</span>
              </div>
              <div className="text-[11px] text-slate-300">
                Sol ({champA}) &amp; Sağ ({champB}) Aralıklı Kartlar • Sırayla Konuşanın Altında Replik
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
            onClick={() => setIsExportModalOpen(true)}
            className="px-4 py-2.5 rounded-xl bg-indigo-500 hover:bg-indigo-400 text-white font-extrabold text-xs md:text-sm tracking-wide shadow-md transition flex items-center space-x-2 cursor-pointer"
          >
            <Film className="w-4 h-4" />
            <span>DaVinci Resolve'a Aktar (Birebir Diyalog Layout)</span>
          </button>

          <button
            onClick={() => setSelectedTurnsMap(new Map())}
            className="px-3 py-2 rounded-xl bg-[#343b4f] hover:bg-[#3f475e] text-xs font-bold text-slate-200 hover:text-white transition cursor-pointer"
          >
            Seçimi Temizle
          </button>
        </div>
      )}

      {/* DaVinci Resolve Export Modal (Layout 2: versus_dialogue) */}
      <DaVinciExportModal
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
        selectedItems={Array.from(selectedTurnsMap.values())}
        defaultTimelineName={`${champA}_vs_${champB}_Birebir_Diyaloglar`}
        layoutMode="versus_dialogue"
        onClearSelection={() => setSelectedTurnsMap(new Map())}
      />

      {/* Çoklu Yapay Zeka & Fonetik Güven Skoru ile Replik Metni Üretme Modalı */}
      <TranscriptGeneratorModal
        isOpen={isTranscriptModalOpen}
        onClose={() => setIsTranscriptModalOpen(false)}
        items={selectedTurnsMap.size > 0 ? Array.from(selectedTurnsMap.values()) : allVisibleDialogueTurns.concat(allVisibleOneWayQuotes)}
        title={`${champA} & ${champB} Karşılıklı Diyalog Metin Çözümleme`}
        onTranscriptsUpdated={(transcriptsMap) => {
          setSelectedTurnsMap(prev => {
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
          setInteractionsData(prev => {
            if (!prev) return prev;
            const next = { ...prev };
            if (next.dialogue_chains) {
              next.dialogue_chains = next.dialogue_chains.map(ch => ({
                ...ch,
                turns: ch.turns?.map(t => {
                  const wid = String(t.wem_id || '').trim();
                  const ev = t.raw_event || t.event || '';
                  if (transcriptsMap[wid]) {
                    return { ...t, transcript: transcriptsMap[wid], text: transcriptsMap[wid] };
                  } else if (transcriptsMap[ev]) {
                    return { ...t, transcript: transcriptsMap[ev], text: transcriptsMap[ev] };
                  }
                  return t;
                })
              }));
            }
            return next;
          });
        }}
      />
    </div>
  );
}
