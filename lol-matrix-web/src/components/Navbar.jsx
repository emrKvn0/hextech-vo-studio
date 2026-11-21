import React from 'react';
import { Crosshair, Swords, Trophy, Sparkles, Database, Layers, MessageSquare, Type, Volume2, VolumeX, Volume1 } from 'lucide-react';

export default function Navbar({ 
  gameMode = 'lol',
  setGameMode,
  activeTab, 
  setActiveTab, 
  globalStats, 
  totalChamps,
  zoomLevel = 1.0,
  onZoomIn,
  onZoomOut,
  onResetZoom,
  audioVolume = 85,
  setAudioVolume
}) {
  const m = globalStats || {};
  const isLor = gameMode === 'lor';
  return (
    <header className="border-b border-slate-700/60 bg-[#232836]/95 backdrop-blur-md sticky top-0 z-50 px-5 py-2.5 shrink-0 shadow-sm">
      <div className="max-w-[1850px] mx-auto flex flex-col md:flex-row items-center justify-between gap-3">
        {/* Brand & Game Switcher */}
        <div className="flex items-center space-x-3.5">
          <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${isLor ? 'from-amber-400 to-orange-500' : 'from-indigo-400 to-sky-500'} p-[1.5px] shadow-md shrink-0`}>
            <div className="w-full h-full bg-[#232836] rounded-[10px] flex items-center justify-center">
              <Crosshair className={`w-6 h-6 ${isLor ? 'text-amber-300' : 'text-indigo-300'}`} />
            </div>
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-base font-black text-slate-100 tracking-wider font-['Cinzel'] flex items-center gap-2">
                <span>HEXTECH MATRIX</span>
              </h1>
              {/* Oyun Seçici Sekme (League of Legends / Legends of Runeterra) */}
              <div className="flex items-center bg-[#181c26] p-0.5 rounded-xl border border-slate-600/70 shadow-inner">
                <button
                  type="button"
                  onClick={() => setGameMode && setGameMode('lol')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-extrabold transition-all cursor-pointer flex items-center gap-1.5 ${
                    !isLor
                      ? 'bg-gradient-to-r from-indigo-500 to-sky-500 text-white shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span>⚔️ League of Legends</span>
                </button>
                <button
                  type="button"
                  onClick={() => setGameMode && setGameMode('lor')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-extrabold transition-all cursor-pointer flex items-center gap-1.5 ${
                    isLor
                      ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 shadow'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span>🃏 Legends of Runeterra</span>
                </button>
              </div>
            </div>
            <p className="text-xs text-slate-300 font-medium mt-0.5">
              {isLor
                ? `${totalChamps || 660} LoR Şampiyon & Takipçi Kartı Arasındaki Tüm Türkçe Replik ve Karşılıklı Diyaloglar`
                : '174 LoL Şampiyonu & 2.140+ Kostüm Arasındaki Tüm Tersine Atıf & Diyalog İlişkileri'}
            </p>
          </div>
        </div>

        {/* Global Metric Pills */}
        <div className="hidden xl:flex items-center space-x-2.5 text-xs font-medium">
          <div className="px-3.5 py-1.5 rounded-xl bg-[#2b3142] border border-slate-600/50 flex items-center space-x-2">
            <Database className="w-4 h-4 text-sky-300" />
            <span className="text-slate-300">{isLor ? 'Karakter / Kart:' : 'Şampiyon:'}</span>
            <span className="font-mono font-bold text-sky-200 text-sm">{totalChamps || 174}</span>
          </div>

          <div className="px-3.5 py-1.5 rounded-xl bg-[#2b3142] border border-slate-600/50 flex items-center space-x-2">
            <Layers className="w-4 h-4 text-indigo-300" />
            <span className="text-slate-300">Toplam Atıf:</span>
            <span className="font-mono font-bold text-indigo-200 text-sm">{m.total_interactions?.toLocaleString('tr-TR') || '...'}</span>
          </div>

          <div className="px-3.5 py-1.5 rounded-xl bg-[#2b3142] border border-slate-600/50 flex items-center space-x-2">
            <Sparkles className="w-4 h-4 text-teal-300" />
            <span className="text-slate-300">Kanon (B➔B):</span>
            <span className="font-mono font-bold text-teal-200 text-sm">{m.global_matrix?.base_to_base?.toLocaleString('tr-TR') || '0'}</span>
          </div>
        </div>

        {/* Right Section: Zoom Controls & Mode Switcher Tabs */}
        <div className="flex items-center space-x-3">
          
          {/* Dinamik Zoom & Yazı Boyutu Kontrolü */}
          <div className="flex items-center space-x-1 bg-[#2b3142] p-1 px-2 rounded-xl border border-slate-600/60 shadow-sm" title="Görünüm ve Yazı Boyutu Yakınlaştırma (Ctrl + / - / 0)">
            <span className="text-[11px] font-semibold text-slate-300 px-1 select-none hidden sm:inline">Ölçek:</span>
            <button
              type="button"
              onClick={onZoomOut}
              className="w-6 h-6 rounded-lg bg-[#343b4f] hover:bg-indigo-500/30 text-slate-200 hover:text-indigo-200 border border-slate-600/60 flex items-center justify-center text-xs font-bold transition cursor-pointer select-none active:scale-95"
              title="Yazıları ve Görünümü Küçült (Ctrl -)"
            >
              −
            </button>
            <button
              type="button"
              onClick={onResetZoom}
              className="px-2 py-0.5 rounded-lg text-xs font-mono font-bold text-indigo-200 hover:bg-[#343b4f] transition cursor-pointer select-none"
              title="Varsayılana Sıfırla (%100 - Ctrl 0)"
            >
              %{Math.round(zoomLevel * 100)}
            </button>
            <button
              type="button"
              onClick={onZoomIn}
              className="w-6 h-6 rounded-lg bg-[#343b4f] hover:bg-indigo-500/30 text-slate-200 hover:text-indigo-200 border border-slate-600/60 flex items-center justify-center text-xs font-bold transition cursor-pointer select-none active:scale-95"
              title="Yazıları ve Görünümü Büyüt (Ctrl +)"
            >
              +
            </button>
          </div>

          {/* Dinamik Ses Seviyesi Kontrolü (LoR & LoL JIT Stream) */}
          <div className="flex items-center space-x-2 bg-[#2b3142] p-1 px-2.5 rounded-xl border border-slate-600/60 shadow-sm" title={`Ses Seviyesi: %${audioVolume}`}>
            <button
              type="button"
              onClick={() => setAudioVolume && setAudioVolume(audioVolume === 0 ? 85 : 0)}
              className="text-slate-300 hover:text-amber-300 transition cursor-pointer"
              title={audioVolume === 0 ? "Sesi Aç" : "Sesi Kapat"}
            >
              {audioVolume === 0 ? (
                <VolumeX className="w-4 h-4 text-rose-400" />
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
              onChange={(e) => setAudioVolume && setAudioVolume(parseInt(e.target.value))}
              className="w-16 md:w-20 h-1.5 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-amber-400"
            />
            <span className="text-[11px] font-mono font-bold text-amber-200 select-none w-7 text-right">
              %{audioVolume}
            </span>
          </div>

          {/* Mode Switcher Tabs */}
          <div className="flex flex-wrap items-center bg-[#2b3142] p-1 rounded-xl border border-slate-600/60 gap-0.5">
            <button
              onClick={() => setActiveTab('matrix')}
              className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'matrix'
                  ? 'bg-indigo-500/25 text-indigo-200 border border-indigo-400/50 shadow-sm'
                  : 'text-slate-300 hover:text-white border border-transparent'
              }`}
            >
              <Crosshair className="w-4 h-4 text-indigo-300" />
              <span>Atıf Matrisi</span>
            </button>

            <button
              onClick={() => setActiveTab('voices')}
              className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'voices'
                  ? 'bg-teal-500/25 text-teal-200 border border-teal-400/50 shadow-sm'
                  : 'text-slate-300 hover:text-white border border-transparent'
              }`}
            >
              <Sparkles className="w-4 h-4 text-teal-300" />
              <span>Karakter Replikleri</span>
            </button>

            <button
              onClick={() => setActiveTab('pair_dialogues')}
              className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'pair_dialogues'
                  ? 'bg-violet-500/25 text-violet-200 border border-violet-400/50 shadow-sm'
                  : 'text-slate-300 hover:text-white border border-transparent'
              }`}
            >
              <MessageSquare className="w-4 h-4 text-violet-300" />
              <span>Birebir Diyaloglar</span>
            </button>

            <button
              onClick={() => setActiveTab('versus')}
              className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'versus'
                  ? 'bg-sky-500/25 text-sky-200 border border-sky-400/50 shadow-sm'
                  : 'text-slate-300 hover:text-white border border-transparent'
              }`}
            >
              <Swords className="w-4 h-4 text-sky-300" />
              <span>Vs Karşılaştırma</span>
            </button>

            <button
              onClick={() => setActiveTab('rankings')}
              className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'rankings'
                  ? 'bg-amber-500/25 text-amber-200 border border-amber-400/50 shadow-sm'
                  : 'text-slate-300 hover:text-white border border-transparent'
              }`}
            >
              <Trophy className="w-4 h-4 text-amber-300" />
              <span>Lider Tablosu</span>
            </button>

            <button
              onClick={() => setActiveTab('font_studio')}
              className={`flex items-center space-x-1.5 px-3 py-2 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                activeTab === 'font_studio'
                  ? 'bg-rose-500/25 text-rose-200 border border-rose-400/50 shadow-sm'
                  : 'text-slate-300 hover:text-white border border-transparent'
              }`}
            >
              <Type className="w-4 h-4 text-rose-300" />
              <span>FCPXML Font &amp; Sahne</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
