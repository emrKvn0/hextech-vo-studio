import React, { useState, useMemo } from 'react';
import TranscriptGeneratorModal from './TranscriptGeneratorModal';
import { Swords, ArrowLeftRight, MessageSquare, Shield, Sparkles, Copy, Check, Play, Square, Loader2, VolumeX, CheckSquare, Film, Brain } from 'lucide-react';

export default function VersusMode({ 
  champions, 
  onCopyRefId, 
  copiedId, 
  onPlayVoice, 
  playingId, 
  audioLoadingId,
  selectedMap,
  onToggleSelect,
  onSelectAll,
  onClearSelection,
  onOpenExportModal
}) {
  const [champA, setChampA] = useState('Yasuo');
  const [champB, setChampB] = useState('Yone');
  const [activeFilter, setActiveFilter] = useState('all');
  const [skinFilterA, setSkinFilterA] = useState('all');
  const [skinFilterB, setSkinFilterB] = useState('all');
  const [isTranscriptModalOpen, setIsTranscriptModalOpen] = useState(false);

  const objA = useMemo(() => champions.find(c => c.name.toLowerCase() === champA.toLowerCase()), [champions, champA]);
  const objB = useMemo(() => champions.find(c => c.name.toLowerCase() === champB.toLowerCase()), [champions, champB]);

  // A's lines towards B
  const linesAtoB = useMemo(() => {
    if (!objA) return [];
    return (objA.outgoing_items || []).filter(it => it.target_champ.toLowerCase() === champB.toLowerCase());
  }, [objA, champB]);

  // B's lines towards A
  const linesBtoA = useMemo(() => {
    if (!objB) return [];
    return (objB.outgoing_items || []).filter(it => it.target_champ.toLowerCase() === champA.toLowerCase());
  }, [objB, champA]);

  const swapChamps = () => {
    setChampA(champB);
    setChampB(champA);
    setSkinFilterA('all');
    setSkinFilterB('all');
  };

  const selectClash = (a, b) => {
    setChampA(a);
    setChampB(b);
    setSkinFilterA('all');
    setSkinFilterB('all');
  };

  const skinsA = useMemo(() => {
    const set = new Set();
    linesAtoB.forEach(it => { if (it.speaker_skin_name) set.add(it.speaker_skin_name); });
    linesBtoA.forEach(it => { if (it.target_skin_name) set.add(it.target_skin_name); });
    return Array.from(set).sort();
  }, [linesAtoB, linesBtoA]);

  const skinsB = useMemo(() => {
    const set = new Set();
    linesBtoA.forEach(it => { if (it.speaker_skin_name) set.add(it.speaker_skin_name); });
    linesAtoB.forEach(it => { if (it.target_skin_name) set.add(it.target_skin_name); });
    return Array.from(set).sort();
  }, [linesAtoB, linesBtoA]);

  const popularClashes = [
    ['Yasuo', 'Yone'],
    ['Riven', 'Yasuo'],
    ['Aatrox', 'Pantheon'],
    ['Jinx', 'Vi'],
    ['Garen', 'Darius'],
    ['Lucian', 'Thresh'],
    ['Rengar', 'Khazix'],
    ['Kayle', 'Morgana'],
    ['Nasus', 'Renekton']
  ];

  const filteredLines = useMemo(() => {
    let combined = [
      ...linesAtoB.map(l => ({ ...l, from: 'A' })),
      ...linesBtoA.map(l => ({ ...l, from: 'B' }))
    ];
    if (activeFilter === 'A') combined = combined.filter(l => l.from === 'A');
    if (activeFilter === 'B') combined = combined.filter(l => l.from === 'B');

    if (skinFilterA !== 'all') {
      combined = combined.filter(l => 
        (l.from === 'A' && l.speaker_skin_name === skinFilterA) ||
        (l.from === 'B' && l.target_skin_name === skinFilterA)
      );
    }

    if (skinFilterB !== 'all') {
      combined = combined.filter(l => 
        (l.from === 'B' && l.speaker_skin_name === skinFilterB) ||
        (l.from === 'A' && l.target_skin_name === skinFilterB)
      );
    }

    return combined;
  }, [linesAtoB, linesBtoA, activeFilter, skinFilterA, skinFilterB]);

  return (
    <div className="flex-1 flex flex-col space-y-4 overflow-hidden min-h-0 text-slate-100">
      {/* Popular Clash Quick Chips */}
      <div className="flex items-center space-x-2.5 overflow-x-auto pb-1 shrink-0">
        <span className="text-xs font-bold text-slate-300 shrink-0 uppercase tracking-wider">Popüler Karşılaşmalar:</span>
        {popularClashes.map(([c1, c2]) => (
          <button
            key={`${c1}-${c2}`}
            onClick={() => { setChampA(c1); setChampB(c2); }}
            className={`px-3 py-1.5 rounded-xl text-xs md:text-sm font-bold border transition cursor-pointer shrink-0 ${
              (champA === c1 && champB === c2) || (champA === c2 && champB === c1)
                ? 'bg-amber-500/30 text-amber-300 border-amber-400 ring-1 ring-amber-400/50'
                : 'bg-[#061022] text-slate-300 border-slate-700 hover:text-white hover:border-slate-500'
            }`}
          >
            {c1} vs {c2}
          </button>
        ))}
      </div>

      {/* VS Duel Banner Header */}
      <div className="glass-panel rounded-2xl p-4.5 border border-amber-500/35 bg-gradient-to-r from-blue-950/50 via-[#061022]/95 to-rose-950/50 shrink-0 shadow-xl">
        <div className="grid grid-cols-1 md:grid-cols-11 gap-4 items-center">
          {/* Champion A Card */}
          <div className="md:col-span-5 flex items-center space-x-4 bg-[#050E20]/95 p-4 rounded-2xl border border-blue-500/40">
            <img src={objA?.icon_url} alt={champA} className="w-18 h-18 rounded-2xl object-cover border-2 border-blue-400 shadow-md shrink-0" />
            <div className="flex-1 min-w-0">
              <label className="text-xs uppercase font-extrabold text-blue-400 tracking-wider">1. Şampiyon (Konuşmacı A)</label>
              <select
                value={champA}
                onChange={e => setChampA(e.target.value)}
                className="w-full bg-[#030914] border border-blue-500/50 text-blue-100 font-extrabold text-base rounded-xl px-3 py-1.5 mt-1 outline-none cursor-pointer"
              >
                {champions.map(c => (
                  <option key={c.name} value={c.name}>{c.name}</option>
                ))}
              </select>
              <div className="flex items-center space-x-2 mt-1.5 text-xs">
                <span className="text-slate-300 font-medium">{champB}'ye Atıfları:</span>
                <span className="font-mono font-black text-blue-300 text-sm">{linesAtoB.length} Replik</span>
              </div>
              {/* Champion A Costume Filter */}
              <select
                value={skinFilterA}
                onChange={e => setSkinFilterA(e.target.value)}
                className={`w-full text-xs rounded-xl px-2.5 py-1.5 mt-2 outline-none cursor-pointer transition font-medium ${
                  skinFilterA !== 'all'
                    ? 'bg-blue-950/80 border border-blue-400 text-blue-200'
                    : 'bg-[#030914] border border-blue-500/30 text-slate-300 hover:border-blue-400'
                }`}
              >
                <option value="all">🛡️ Tüm {champA} Kostümleri ({skinsA.length})</option>
                {skinsA.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>

          {/* VS Center Badge & Swap */}
          <div className="md:col-span-1 flex flex-col items-center justify-center">
            <button
              onClick={swapChamps}
              title="Şampiyonları Değiştir"
              className="w-11 h-11 rounded-full bg-amber-500/20 hover:bg-amber-500/40 text-amber-300 border border-amber-500/60 flex items-center justify-center shadow-lg transition cursor-pointer"
            >
              <ArrowLeftRight className="w-5 h-5" />
            </button>
            <span className="text-xs font-black font-['Cinzel'] text-amber-400 mt-1.5">VS</span>
          </div>

          {/* Champion B Card */}
          <div className="md:col-span-5 flex items-center space-x-4 bg-[#050E20]/95 p-4 rounded-2xl border border-rose-500/40">
            <img src={objB?.icon_url} alt={champB} className="w-18 h-18 rounded-2xl object-cover border-2 border-rose-400 shadow-md shrink-0" />
            <div className="flex-1 min-w-0">
              <label className="text-xs uppercase font-extrabold text-rose-400 tracking-wider">2. Şampiyon (Konuşmacı B)</label>
              <select
                value={champB}
                onChange={e => setChampB(e.target.value)}
                className="w-full bg-[#030914] border border-rose-500/50 text-rose-100 font-extrabold text-base rounded-xl px-3 py-1.5 mt-1 outline-none cursor-pointer"
              >
                {champions.map(c => (
                  <option key={c.name} value={c.name}>{c.name}</option>
                ))}
              </select>
              <div className="flex items-center space-x-2 mt-1.5 text-xs">
                <span className="text-slate-300 font-medium">{champA}'ya Atıfları:</span>
                <span className="font-mono font-black text-rose-300 text-sm">{linesBtoA.length} Replik</span>
              </div>
              {/* Champion B Costume Filter */}
              <select
                value={skinFilterB}
                onChange={e => setSkinFilterB(e.target.value)}
                className={`w-full text-xs rounded-xl px-2.5 py-1.5 mt-2 outline-none cursor-pointer transition font-medium ${
                  skinFilterB !== 'all'
                    ? 'bg-rose-950/80 border border-rose-400 text-rose-200'
                    : 'bg-[#030914] border border-rose-500/30 text-slate-300 hover:border-rose-400'
                }`}
              >
                <option value="all">🎯 Tüm {champB} Kostümleri ({skinsB.length})</option>
                {skinsB.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Duel Stream Lines Table */}
      <div className="flex-1 glass-panel rounded-2xl p-4 border border-slate-700/80 flex flex-col overflow-hidden min-h-0">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 mb-2.5 border-b border-slate-800 shrink-0">
          <div className="flex flex-wrap items-center gap-2">
            <MessageSquare className="w-5 h-5 text-amber-400" />
            <h3 className="text-base font-black text-amber-300 font-['Cinzel']">
              {champA} & {champB} Karşılıklı Atışma Akışı
            </h3>
            <span className="px-3 py-1 rounded-full bg-[#081428] border border-slate-700 text-xs font-mono font-extrabold text-cyan-300">
              {filteredLines.length} Replik
            </span>

            {/* Active Costume Filter Pills in Versus */}
            {skinFilterA !== 'all' && (
              <button
                onClick={() => setSkinFilterA('all')}
                className="px-2.5 py-0.5 rounded-lg bg-blue-500/20 border border-blue-400 text-blue-200 text-xs font-mono font-bold flex items-center gap-1 hover:bg-blue-500/30 transition cursor-pointer"
                title={`${champA} kostüm filtresini kaldır`}
              >
                <span>🛡️ {skinFilterA}</span>
                <span className="text-blue-300 font-black ml-1">×</span>
              </button>
            )}

            {skinFilterB !== 'all' && (
              <button
                onClick={() => setSkinFilterB('all')}
                className="px-2.5 py-0.5 rounded-lg bg-rose-500/20 border border-rose-400 text-rose-200 text-xs font-mono font-bold flex items-center gap-1 hover:bg-rose-500/30 transition cursor-pointer"
                title={`${champB} kostüm filtresini kaldır`}
              >
                <span>🎯 {skinFilterB}</span>
                <span className="text-rose-300 font-black ml-1">×</span>
              </button>
            )}
          </div>

          <div className="flex items-center space-x-2 text-xs md:text-sm font-bold flex-wrap gap-y-2">
            <button
              onClick={() => setIsTranscriptModalOpen(true)}
              className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white flex items-center space-x-1.5 cursor-pointer transition shadow-md"
              title="XML üretmeksizin görüntülenen repliklerin metinlerini Çoklu Yapay Zeka & Fonetik Güven Skoru ile çözümleyin ve güncelleyin"
            >
              <Brain className="w-3.5 h-3.5 text-purple-200" />
              <span>Sadece Replik Metni Üret ({selectedMap && selectedMap.size > 0 ? selectedMap.size : filteredLines.length})</span>
            </button>

            {onSelectAll && filteredLines.length > 0 && (
              <button
                onClick={() => onSelectAll(filteredLines)}
                className="px-3 py-1.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/50 flex items-center space-x-1.5 cursor-pointer transition shadow-sm"
                title="Görüntülenen tüm replikleri seç veya seçimi kaldır"
              >
                <CheckSquare className="w-3.5 h-3.5" />
                <span>Tümünü Seç / Kaldır</span>
              </button>
            )}

            <button
              onClick={() => setActiveFilter('all')}
              className={`px-3 py-1.5 rounded-xl font-bold transition cursor-pointer ${
                activeFilter === 'all' ? 'bg-amber-500/25 text-amber-300 border border-amber-500/50' : 'text-slate-400 hover:text-white'
              }`}
            >
              Tümü ({linesAtoB.length + linesBtoA.length})
            </button>
            <button
              onClick={() => setActiveFilter('A')}
              className={`px-3 py-1.5 rounded-xl font-bold transition cursor-pointer ${
                activeFilter === 'A' ? 'bg-blue-500/25 text-blue-300 border border-blue-500/50' : 'text-slate-400 hover:text-white'
              }`}
            >
              Sadece {champA} ➔ {champB} ({linesAtoB.length})
            </button>
            <button
              onClick={() => setActiveFilter('B')}
              className={`px-3 py-1.5 rounded-xl font-bold transition cursor-pointer ${
                activeFilter === 'B' ? 'bg-rose-500/25 text-rose-300 border border-rose-500/50' : 'text-slate-400 hover:text-white'
              }`}
            >
              Sadece {champB} ➔ {champA} ({linesBtoA.length})
            </button>
            {(skinFilterA !== 'all' || skinFilterB !== 'all') && (
              <button
                onClick={() => { setSkinFilterA('all'); setSkinFilterB('all'); }}
                className="px-2.5 py-1.5 rounded-xl bg-[#061022] hover:bg-[#08152c] text-xs font-bold text-slate-200 border border-slate-700 cursor-pointer transition"
              >
                Filtreleri Sıfırla
              </button>
            )}
          </div>
        </div>

        {/* Scrollable Rows with Copy & Play Button */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-2.5">
          {filteredLines.length === 0 ? (
            <div className="py-24 text-center text-slate-400 text-sm font-mono">
              Bu iki şampiyon arasında kayıtlı doğrudan atıf/karşılaşma repliği bulunamadı.
            </div>
          ) : (
            filteredLines.map((it, idx) => {
              const isFromA = it.from === 'A';
              const itemRef = it.ref_id || `${it.speaker_champ}_${it.raw_event}_${it.wem_id || 'vs_' + idx}`;
              const isCopied = copiedId === (it.ref_id || it.raw_event);
              const cueId = `${it.speaker_champ}_${it.raw_event}_${it.wem_id || 'vs_' + idx}`;
              const isPlaying = playingId === cueId;
              const isLoading = audioLoadingId === cueId;
              const isSelected = selectedMap ? selectedMap.has(itemRef) : false;
              const hasAudio = Boolean(it.wem_id);

              return (
                <div
                  key={idx}
                  className={`p-3.5 rounded-xl border transition-all flex items-start justify-between gap-3.5 ${
                    isSelected
                      ? 'bg-amber-950/30 border-amber-400/80 ring-1 ring-amber-400/40'
                      : isFromA
                      ? 'bg-blue-950/25 border-blue-500/40 hover:border-blue-400'
                      : 'bg-rose-950/25 border-rose-500/40 hover:border-rose-400'
                  }`}
                >
                  <div className="flex items-start space-x-3.5">
                    {/* Multi-Select Checkbox */}
                    {onToggleSelect && (
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onToggleSelect(it, itemRef)}
                        title="Bu repliği DaVinci projesine dahil et"
                        className="w-4 h-4 accent-amber-400 rounded cursor-pointer shrink-0 mt-2"
                      />
                    )}

                    <div className="flex items-center space-x-1.5 mt-0.5 shrink-0">
                      {hasAudio ? (
                        onPlayVoice && (
                          <button
                            onClick={() => onPlayVoice(it, it.wem_id || `vs_${idx}`)}
                            disabled={isLoading}
                            title={isPlaying ? "Durdur" : "Dinle (JIT Stream)"}
                            className={`w-8 h-8 rounded-lg flex items-center justify-center transition cursor-pointer shadow ${
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
                        )
                      ) : (
                        <div
                          title="Oyun dosyalarında ses kaydı bulunamadı (Özellik/Tasarım Kaydı - Seslendirilmemiş)"
                          className="w-8 h-8 rounded-lg flex items-center justify-center bg-slate-900/70 text-slate-500 border border-slate-800 cursor-not-allowed select-none"
                        >
                          <VolumeX className="w-3.5 h-3.5" />
                        </div>
                      )}

                      {onCopyRefId && (
                        <button
                          onClick={() => onCopyRefId(it.ref_id || it.raw_event)}
                          title={isCopied ? "Kopyalandı!" : `Referans Kodunu Kopyala: ${it.ref_id || it.raw_event}`}
                          className={`w-8 h-8 rounded-lg flex items-center justify-center transition cursor-pointer shadow ${
                            isCopied
                              ? 'bg-emerald-500 text-slate-950 ring-1 ring-emerald-400'
                              : 'bg-[#061022] hover:bg-cyan-500/25 text-slate-400 hover:text-cyan-300 border border-slate-700 hover:border-cyan-400'
                          }`}
                        >
                          {isCopied ? (
                            <Check className="w-3.5 h-3.5 stroke-[3]" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      )}
                    </div>

                    <div>
                      <div className="flex items-center space-x-2 text-sm flex-wrap gap-y-1">
                        <span className={`font-black text-base ${isFromA ? 'text-blue-300' : 'text-rose-300'}`}>
                          {it.speaker_champ}
                        </span>
                        <span 
                          onClick={() => isFromA ? setSkinFilterA(it.speaker_skin_name) : setSkinFilterB(it.speaker_skin_name)}
                          className="text-xs text-amber-200/90 font-semibold cursor-pointer hover:underline hover:text-amber-300 transition bg-slate-900/80 px-2 py-0.5 rounded border border-slate-700/60"
                          title="Bu konuşan kostüme göre filtrele"
                        >
                          {it.speaker_skin_name}
                        </span>
                        <span className="text-slate-500 font-mono font-bold">➔</span>
                        <span className="font-extrabold text-slate-200">{it.target_champ}</span>
                        <span 
                          onClick={() => isFromA ? setSkinFilterB(it.target_skin_name) : setSkinFilterA(it.target_skin_name)}
                          className="text-xs text-cyan-200/90 font-semibold cursor-pointer hover:underline hover:text-cyan-300 transition bg-slate-900/80 px-2 py-0.5 rounded border border-slate-700/60"
                          title="Bu hedef kostüme göre filtrele"
                        >
                          {it.target_skin_name}
                        </span>
                      </div>

                      {it.transcript ? (
                        <div className="text-base font-semibold text-white italic mt-1.5">
                          "{it.transcript}"
                        </div>
                      ) : (
                        <div className="mt-1">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-mono bg-slate-800/80 text-amber-300/90 border border-slate-700/60 font-medium">
                            [Metin Yok - Sadece Etkileşim Kaydı]
                          </span>
                        </div>
                      )}

                      <div className="text-xs font-mono text-slate-400 mt-1">
                        {it.raw_event}
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-col items-end shrink-0 space-y-1.5">
                    <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold uppercase bg-slate-900 border border-slate-700 text-slate-200">
                      {it.action_type}
                    </span>
                    <span className={`px-2.5 py-0.5 rounded text-xs font-mono font-extrabold ${
                      it.matrix_type === 'base_to_base'
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/50'
                        : it.matrix_type === 'skin_to_base'
                        ? 'bg-cyan-950 text-cyan-300 border border-cyan-500/50'
                        : it.matrix_type === 'base_to_skin'
                        ? 'bg-amber-950 text-amber-300 border border-amber-500/50'
                        : 'bg-purple-950 text-purple-300 border border-purple-500/50'
                    }`}>
                      {it.matrix_type.replace(/_/g, ' ')}
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Çoklu Yapay Zeka & Fonetik Güven Skoru ile Replik Metni Üretme Modalı */}
      <TranscriptGeneratorModal
        isOpen={isTranscriptModalOpen}
        onClose={() => setIsTranscriptModalOpen(false)}
        items={selectedMap && selectedMap.size > 0 ? Array.from(selectedMap.values()) : filteredLines}
        title={`${champA} & ${champB} Versus Replik Metni Çözümleme`}
        onTranscriptsUpdated={(transcriptsMap) => {
          filteredLines.forEach(it => {
            const wid = String(it.wem_id || '').trim();
            const ev = it.raw_event || it.event || '';
            if (transcriptsMap[wid]) {
              it.transcript = transcriptsMap[wid];
              it.text = transcriptsMap[wid];
            } else if (transcriptsMap[ev]) {
              it.transcript = transcriptsMap[ev];
              it.text = transcriptsMap[ev];
            }
          });
        }}
      />
    </div>
  );
}
