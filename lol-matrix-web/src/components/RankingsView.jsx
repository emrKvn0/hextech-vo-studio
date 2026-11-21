import React, { useState } from 'react';
import { Trophy, Flame, Mic, Shield, ArrowUpRight, ArrowDownLeft } from 'lucide-react';

export default function RankingsView({ champions, onSelectChampion }) {
  const [rankingType, setRankingType] = useState('incoming'); // 'incoming', 'outgoing', 'kanon'
  const [kanonDirection, setKanonDirection] = useState('outgoing'); // 'outgoing' (Yaptığı Kanon Atıf) | 'incoming' (Aldığı Kanon Atıf)

  // Sortings - Tüm şampiyonları kapsar (Top 30 sınırı kaldırıldı)
  const sorted = [...champions].sort((a, b) => {
    if (rankingType === 'incoming') return b.total_incoming - a.total_incoming;
    if (rankingType === 'outgoing') return b.total_outgoing - a.total_outgoing;
    if (rankingType === 'kanon') {
      const valA = kanonDirection === 'outgoing'
        ? (a.matrix_outgoing?.base_to_base || 0)
        : (a.matrix_incoming?.base_to_base || 0);
      const valB = kanonDirection === 'outgoing'
        ? (b.matrix_outgoing?.base_to_base || 0)
        : (b.matrix_incoming?.base_to_base || 0);
      if (valB !== valA) return valB - valA;
      return (b.total_outgoing || 0) - (a.total_outgoing || 0);
    }
    return 0;
  });

  return (
    <div className="flex-1 glass-panel rounded-2xl p-4.5 border border-slate-700/80 flex flex-col overflow-hidden min-h-0 text-slate-100">
      {/* Header & Tabs */}
      <div className="flex flex-col xl:flex-row items-start xl:items-center justify-between gap-3.5 pb-3.5 mb-3.5 border-b border-slate-800 shrink-0">
        <div className="flex items-center space-x-3">
          <Trophy className="w-6 h-6 text-amber-400" />
          <div>
            <h2 className="text-lg font-black text-amber-300 font-['Cinzel'] tracking-wide">
              Şampiyon Atıf & Etkileşim Lider Tablosu (Tüm {sorted.length} Şampiyon)
            </h2>
            <p className="text-xs text-slate-300 font-medium">
              En çok atıfta bulunulan, en çok konuşan ve en çok kanon (Varsayılan ➔ Varsayılan) repliğe sahip tüm karakterler
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          {rankingType === 'kanon' && (
            <div className="inline-flex rounded-xl bg-[#040b18] p-1 border border-emerald-500/40 text-xs">
              <button
                onClick={() => setKanonDirection('outgoing')}
                className={`px-3 py-1.5 rounded-lg font-extrabold transition cursor-pointer flex items-center space-x-1.5 ${
                  kanonDirection === 'outgoing'
                    ? 'bg-emerald-500/25 text-emerald-300 border border-emerald-500/50 shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Karakterin kendi varsayılan kostümünden diğer varsayılan karakterlere yaptığı kanon atıf sayısı"
              >
                <ArrowUpRight className="w-3.5 h-3.5 text-emerald-400" />
                <span>Yaptığı Kanon Atıf (Giden B➔B)</span>
              </button>
              <button
                onClick={() => setKanonDirection('incoming')}
                className={`px-3 py-1.5 rounded-lg font-extrabold transition cursor-pointer flex items-center space-x-1.5 ${
                  kanonDirection === 'incoming'
                    ? 'bg-teal-500/25 text-teal-300 border border-teal-500/50 shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
                title="Diğer varsayılan karakterlerin bu karakterin varsayılan haline yaptığı kanon atıf sayısı"
              >
                <ArrowDownLeft className="w-3.5 h-3.5 text-teal-400" />
                <span>Aldığı Kanon Atıf (Gelen B➔B)</span>
              </button>
            </div>
          )}

          <div className="inline-flex rounded-xl bg-[#061022] p-1 border border-slate-700 text-xs md:text-sm">
            <button
              onClick={() => setRankingType('incoming')}
              className={`px-3.5 py-2 rounded-lg font-extrabold transition cursor-pointer flex items-center space-x-2 ${
                rankingType === 'incoming'
                  ? 'bg-amber-500/25 text-amber-300 border border-amber-500/50 shadow'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <Flame className="w-4 h-4 text-amber-400" />
              <span>En Çok Hedef Alınanlar</span>
            </button>

            <button
              onClick={() => setRankingType('outgoing')}
              className={`px-3.5 py-2 rounded-lg font-extrabold transition cursor-pointer flex items-center space-x-2 ${
                rankingType === 'outgoing'
                  ? 'bg-cyan-500/25 text-cyan-300 border border-cyan-500/50 shadow'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <Mic className="w-4 h-4 text-cyan-400" />
              <span>En Çok Konuşanlar</span>
            </button>

            <button
              onClick={() => setRankingType('kanon')}
              className={`px-3.5 py-2 rounded-lg font-extrabold transition cursor-pointer flex items-center space-x-2 ${
                rankingType === 'kanon'
                  ? 'bg-emerald-500/25 text-emerald-300 border border-emerald-500/50 shadow'
                  : 'text-slate-300 hover:text-white'
              }`}
            >
              <Shield className="w-4 h-4 text-emerald-400" />
              <span>En Çok Kanon Atıf (B➔B)</span>
            </button>
          </div>
        </div>
      </div>

      {/* Rankings Grid / Table */}
      <div className="flex-1 overflow-y-auto pr-1">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {sorted.map((champ, idx) => {
            let primaryVal = 0;
            let primaryLabel = '';
            let valColor = 'text-amber-300';

            if (rankingType === 'incoming') {
              primaryVal = champ.total_incoming;
              primaryLabel = 'Gelen Atıf';
              valColor = 'text-amber-300';
            } else if (rankingType === 'outgoing') {
              primaryVal = champ.total_outgoing;
              primaryLabel = 'Giden Atıf';
              valColor = 'text-cyan-300';
            } else {
              if (kanonDirection === 'outgoing') {
                primaryVal = champ.matrix_outgoing?.base_to_base || 0;
                primaryLabel = 'Giden Kanon (B➔B)';
                valColor = 'text-emerald-300';
              } else {
                primaryVal = champ.matrix_incoming?.base_to_base || 0;
                primaryLabel = 'Gelen Kanon (B➔B)';
                valColor = 'text-teal-300';
              }
            }

            const isTop3 = idx < 3;
            const rankBadges = ['🥇', '🥈', '🥉'];

            return (
              <div
                key={champ.name}
                onClick={() => onSelectChampion(champ.name)}
                className={`p-3.5 rounded-2xl border transition-all cursor-pointer flex items-center justify-between group ${
                  isTop3
                    ? 'bg-amber-950/25 border-amber-500/50 hover:border-amber-400 hover:bg-amber-950/35'
                    : 'bg-[#061022]/85 border-slate-700/60 hover:border-slate-500 hover:bg-[#08152c]'
                }`}
              >
                <div className="flex items-center space-x-3.5 min-w-0">
                  <div className="w-9 text-center font-mono font-black text-base text-slate-300 shrink-0">
                    {isTop3 ? rankBadges[idx] : `#${idx + 1}`}
                  </div>

                  <img
                    src={champ.icon_url}
                    alt={champ.name}
                    className="w-13 h-13 rounded-xl object-cover border-2 border-slate-700 group-hover:border-amber-400 transition shrink-0"
                  />

                  <div className="truncate">
                    <div className="font-extrabold text-base text-slate-100 group-hover:text-amber-300 transition truncate">
                      {champ.name}
                    </div>
                    <div className="text-xs text-slate-300 font-medium flex items-center gap-1.5 mt-0.5">
                      <span>{champ.unique_speakers_incoming} konuşan</span>
                      <span>•</span>
                      <span>{champ.unique_targets_outgoing} hedef</span>
                      {rankingType === 'kanon' && (
                        <>
                          <span>•</span>
                          <span className="text-emerald-400/90 font-semibold">
                            {kanonDirection === 'outgoing'
                              ? `Gelen: ${champ.matrix_incoming?.base_to_base || 0}`
                              : `Giden: ${champ.matrix_outgoing?.base_to_base || 0}`}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                <div className="text-right shrink-0 pl-2">
                  <div className={`text-2xl font-mono font-black ${valColor}`}>
                    {primaryVal.toLocaleString('tr-TR')}
                  </div>
                  <div className="text-[10px] uppercase tracking-wider text-slate-400 font-extrabold">
                    {primaryLabel}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

