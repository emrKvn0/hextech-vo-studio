import React from 'react';
import { Shield, Sparkles, Shirt, Zap, Globe, Target } from 'lucide-react';

export default function MatrixCards({ matrix, totalItems, targetBaseCount, targetSkinCount, activeFilter, onSelectFilter }) {
  const m = matrix || { base_to_base: 0, skin_to_base: 0, base_to_skin: 0, skin_to_skin: 0 };
  const total = totalItems || (m.base_to_base + m.skin_to_base + m.base_to_skin + m.skin_to_skin);
  const tgtBase = targetBaseCount !== undefined ? targetBaseCount : (m.base_to_base + m.skin_to_base);
  const tgtSkin = targetSkinCount !== undefined ? targetSkinCount : (m.base_to_skin + m.skin_to_skin);

  const primaryTabs = [
    {
      id: 'all',
      title: 'Tüm Atıflar',
      desc: 'Tüm Karakterler & Kostümler',
      count: total,
      icon: Globe,
      color: 'amber'
    },
    {
      id: 'target_base',
      title: 'Varsayılan Hedefe Gelenler',
      desc: 'Orijinal Şampiyona Söylenen TÜM Replikler',
      badge: 'Video Listesi',
      count: tgtBase,
      icon: Target,
      color: 'emerald'
    },
    {
      id: 'target_skin',
      title: 'Kostümlü Hedefe Gelenler',
      desc: 'Kostümlere Özel Karşılaşmalar',
      count: tgtSkin,
      icon: Zap,
      color: 'purple'
    }
  ];

  const subCards = [
    {
      type: 'base_to_base',
      title: 'Saf Kanon (Orijinal)',
      badge: 'B ➔ B',
      desc: 'Varsayılan ➔ Varsayılan',
      count: m.base_to_base || 0,
      icon: Shield,
      color: 'emerald',
      activeClass: 'ring-2 ring-emerald-400 bg-emerald-950/60 border-emerald-500'
    },
    {
      type: 'skin_to_base',
      title: 'Kostümlü ➔ Varsayılan',
      badge: 'S ➔ B',
      desc: 'Kostümlü ➔ Orijinal Hedef',
      count: m.skin_to_base || 0,
      icon: Sparkles,
      color: 'cyan',
      activeClass: 'ring-2 ring-cyan-400 bg-cyan-950/60 border-cyan-500'
    },
    {
      type: 'base_to_skin',
      title: 'Varsayılan ➔ Kostümlü',
      badge: 'B ➔ S',
      desc: 'Orijinal ➔ Hedefin Kostümüne',
      count: m.base_to_skin || 0,
      icon: Shirt,
      color: 'amber',
      activeClass: 'ring-2 ring-amber-400 bg-amber-950/60 border-amber-500'
    },
    {
      type: 'skin_to_skin',
      title: 'Kostümlü ➔ Kostümlü',
      badge: 'S ➔ S',
      desc: 'Alternatif Evren Karşılaşmaları',
      count: m.skin_to_skin || 0,
      icon: Zap,
      color: 'purple',
      activeClass: 'ring-2 ring-purple-400 bg-purple-950/60 border-purple-500'
    }
  ];

  return (
    <div className="space-y-2.5">
      {/* Primary Scope Buttons (All vs Target Base vs Target Skin) */}
      <div className="grid grid-cols-3 gap-2.5">
        {primaryTabs.map(t => {
          const Icon = t.icon;
          const isActive = activeFilter === t.id;
          return (
            <button
              key={t.id}
              onClick={() => onSelectFilter(t.id)}
              className={`p-2.5 rounded-xl border text-left transition cursor-pointer flex items-center justify-between ${
                isActive
                  ? 'bg-gradient-to-r from-amber-500/20 to-amber-600/15 border-amber-400 ring-1 ring-amber-400/60'
                  : 'bg-[#061022]/90 hover:bg-[#091834] border-slate-700/70 hover:border-slate-500'
              }`}
            >
              <div className="flex items-center space-x-2.5 truncate">
                <div className={`p-1.5 rounded-lg ${isActive ? 'bg-amber-400 text-slate-950' : 'bg-slate-800 text-slate-300'}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="truncate">
                  <div className="flex items-center space-x-1.5">
                    <span className={`text-xs md:text-sm font-bold truncate ${isActive ? 'text-amber-200' : 'text-slate-200'}`}>
                      {t.title}
                    </span>
                    {t.badge && (
                      <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 px-1.5 py-0.2 rounded font-extrabold uppercase">
                        {t.badge}
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-slate-400 truncate">{t.desc}</div>
                </div>
              </div>
              <div className={`font-mono text-lg font-black shrink-0 pl-2 ${isActive ? 'text-amber-300' : 'text-slate-300'}`}>
                {t.count}
              </div>
            </button>
          );
        })}
      </div>

      {/* 4 Detailed Sub-Matrix Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5">
        {subCards.map(c => {
          const Icon = c.icon;
          const isActive = activeFilter === c.type;
          return (
            <button
              key={c.type}
              onClick={() => onSelectFilter(isActive ? 'all' : c.type)}
              className={`p-3 rounded-xl border text-left transition cursor-pointer group ${
                isActive
                  ? c.activeClass
                  : 'bg-[#061022]/80 border-slate-700/60 hover:border-slate-500 hover:bg-[#091834]'
              }`}
            >
              <div className="flex items-center justify-between text-xs text-slate-300 font-bold mb-1">
                <span className="flex items-center gap-1.5 truncate">
                  <Icon className={`w-3.5 h-3.5 text-${c.color}-400 shrink-0`} />
                  <span className="truncate">{c.title}</span>
                </span>
                <span className={`text-[10px] font-mono text-${c.color}-300 shrink-0 font-extrabold bg-black/40 px-1.5 py-0.5 rounded border border-${c.color}-500/30`}>
                  {c.badge}
                </span>
              </div>

              <div className="flex items-baseline justify-between mt-0.5">
                <div className={`text-2xl font-mono font-black text-${c.color}-300 tracking-tight`}>
                  {c.count.toLocaleString('tr-TR')}
                </div>
                <div className="text-[11px] text-slate-400 font-semibold group-hover:text-slate-200 transition">
                  {isActive ? '✓ Aktif' : 'Filtrele'}
                </div>
              </div>

              <div className="text-[11px] text-slate-400 truncate mt-1">
                {c.desc}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
