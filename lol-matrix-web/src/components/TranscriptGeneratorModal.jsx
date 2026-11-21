import React, { useState, useEffect, useRef } from 'react';
import { Sparkles, Brain, CheckCircle2, AlertTriangle, X, RefreshCw, Zap, ShieldCheck, Terminal, Trash2, Copy, Check } from 'lucide-react';

export default function TranscriptGeneratorModal({
  isOpen,
  onClose,
  items = [],
  onTranscriptsUpdated,
  title = "Yapay Zeka & Fonetik Replik Çözümleme"
}) {
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });
  const [currentLine, setCurrentLine] = useState(null);
  const [resolvedTranscripts, setResolvedTranscripts] = useState({});
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState(null);
  const [isDone, setIsDone] = useState(false);
  const [forceRetranscribe, setForceRetranscribe] = useState(false);
  const [copiedLog, setCopiedLog] = useState(false);
  
  const eventSourceRef = useRef(null);
  const terminalEndRef = useRef(null);

  // Otomatik Terminal Scroll
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  useEffect(() => {
    if (isOpen) {
      setIsProcessing(false);
      setProgress({ current: 0, total: items.length });
      setCurrentLine(null);
      setError(null);
      setIsDone(false);
      setResolvedTranscripts({});
      setLogs([
        `[${new Date().toLocaleTimeString()}] 🚀 Sistem hazır. Toplam ${items.length} replik işleme alınabilir.`,
        `[${new Date().toLocaleTimeString()}] 💡 Model: Whisper Large-v3-Turbo (CTranslate2 CUDA float16 / CPU int8)`
      ]);
    } else {
      if (eventSourceRef.current) {
        eventSourceRef.current.abort?.();
        eventSourceRef.current = null;
      }
    }
  }, [isOpen, items.length]);

  if (!isOpen) return null;

  const appendLog = (msg) => {
    const time = new Date().toLocaleTimeString();
    setLogs(prev => [...prev, `[${time}] ${msg}`]);
  };

  const handleStartTranscribe = async () => {
    if (!items || items.length === 0) return;

    setIsProcessing(true);
    setError(null);
    setIsDone(false);
    setProgress({ current: 0, total: items.length });
    setLogs([
      `[${new Date().toLocaleTimeString()}] 🚀 Transkripsiyon başlatılıyor...`,
      `[${new Date().toLocaleTimeString()}] ⚙️ Parametreler: beam_size=5, Silero VAD=True, temperature=0.0, condition_on_prev=False`,
      `[${new Date().toLocaleTimeString()}] 🔄 Önbellek Baypas: ${forceRetranscribe ? 'AÇIK (Sıfırdan Dinlenecek)' : 'KAPALI (Hızlı Önbellek + Eksikler Dinlenecek)'}`
    ]);
    const collected = {};

    try {
      const controller = new AbortController();
      eventSourceRef.current = controller;

      const response = await fetch('http://127.0.0.1:8080/api/generate-transcripts-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: items.map(it => ({
            speaker_champ: it.speaker_champ || it.speaker || it.speaker_name || '',
            target_champ: it.target_champ || it.target || '',
            raw_event: it.raw_event || it.event || '',
            wem_id: String(it.wem_id || '').trim(),
            transcript: it.transcript || it.text || '',
            game: it.game || 'lol'
          })),
          force_retranscribe: forceRetranscribe
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        throw new Error(`Sunucu hatası: HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          const lines = part.split('\n');
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const payload = JSON.parse(line.slice(6));
                if (payload.type === 'log') {
                  appendLog(payload.message);
                } else if (payload.type === 'progress') {
                  setProgress({ current: payload.current, total: payload.total });
                  setCurrentLine({
                    speaker: payload.speaker,
                    text: payload.text,
                    score: payload.confidence_score,
                    key: payload.key
                  });
                  if (payload.log) {
                    appendLog(payload.log);
                  }
                  if (payload.key && payload.text) {
                    collected[payload.key] = payload.text;
                  }
                } else if (payload.type === 'done') {
                  setIsDone(true);
                  setIsProcessing(false);
                  appendLog(`✅ İŞLEM TAMAMLANDI: Toplam ${payload.count || Object.keys(payload.transcripts || {}).length} replik metni doğrulandı.`);
                  const finalMap = {};
                  Object.entries(payload.transcripts || {}).forEach(([k, v]) => {
                    finalMap[k] = v;
                  });
                  setResolvedTranscripts(finalMap);
                  if (onTranscriptsUpdated) {
                    onTranscriptsUpdated(finalMap);
                  }
                } else if (payload.type === 'error') {
                  const errMsg = payload.message || 'Transkripsiyon hatası oluştu.';
                  setError(errMsg);
                  appendLog(`❌ HATA: ${errMsg}`);
                  setIsProcessing(false);
                }
              } catch (e) {
                console.error("SSE parse hatası:", e);
              }
            }
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        const connErr = `Bağlantı hatası: ${err.message}. Lütfen AudioServer'ın (port 8080) çalıştığından emin olun.`;
        setError(connErr);
        appendLog(`❌ BAĞLANTI KESİLDİ: ${connErr}`);
      }
      setIsProcessing(false);
    }
  };

  const handleCopyLogs = () => {
    navigator.clipboard.writeText(logs.join('\n'));
    setCopiedLog(true);
    setTimeout(() => setCopiedLog(false), 2000);
  };

  const percent = progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-fadeIn">
      <div className="relative w-full max-w-3xl max-h-[92vh] bg-gradient-to-b from-slate-900 to-slate-950 border border-indigo-500/30 rounded-2xl shadow-2xl shadow-indigo-950/50 overflow-hidden flex flex-col">
        {/* Başlık Çubuğu */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50 shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-500 text-white shadow-lg shadow-indigo-500/25">
              <Brain className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white tracking-wide flex items-center gap-2">
                {title}
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Whisper Large-v3-Turbo
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Sadece replik metinlerini çözümleyin ve güncelleyin (XML üretilmez).
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isProcessing}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-50 cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Gövde */}
        <div className="p-6 space-y-4 overflow-y-auto flex-1">
          {/* Bilgi Kartı */}
          <div className="grid grid-cols-3 gap-3 shrink-0">
            <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/50 flex flex-col">
              <span className="text-[11px] text-slate-400 font-medium">Hedef Replik Sayısı</span>
              <span className="text-xl font-black text-amber-300 mt-0.5">{items.length} Ses</span>
            </div>
            <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/50 flex flex-col">
              <span className="text-[11px] text-slate-400 font-medium">Yapay Zeka Modeli</span>
              <span className="text-xs font-bold text-indigo-300 mt-1 flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                Large-v3-Turbo CT2
              </span>
            </div>
            <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-700/50 flex flex-col">
              <span className="text-[11px] text-slate-400 font-medium">Doğrulama Motoru</span>
              <span className="text-xs font-bold text-emerald-300 mt-1 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                Fonetik Güven Skoru
              </span>
            </div>
          </div>

          {/* Ayarlar */}
          {!isProcessing && !isDone && (
            <div className="p-3.5 rounded-xl bg-indigo-950/20 border border-indigo-500/20 space-y-2 shrink-0">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={forceRetranscribe}
                  onChange={(e) => setForceRetranscribe(e.target.checked)}
                  className="w-4 h-4 rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 bg-slate-900 cursor-pointer"
                />
                <div>
                  <span className="text-sm font-semibold text-slate-200">
                    Önbelleği Baypas Et (Yeniden Yapay Zekayla Dinle)
                  </span>
                  <p className="text-xs text-slate-400">
                    Mevcut kayıtlı transkriptleri atlar, Whisper Large-v3-Turbo ile sıfırdan analiz eder.
                  </p>
                </div>
              </label>
            </div>
          )}

          {/* İlerleme Durumu */}
          {isProcessing && (
            <div className="space-y-3 animate-fadeIn shrink-0">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-300 font-medium flex items-center gap-2">
                  <RefreshCw className="w-4 h-4 text-indigo-400 animate-spin" />
                  Sesler Analiz Ediliyor ve Fonetik Skor Hesaplanıyor...
                </span>
                <span className="text-indigo-400 font-mono font-bold">
                  {progress.current} / {progress.total} (%{percent})
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden p-0.5 border border-slate-700/50">
                <div
                  className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-full transition-all duration-300 shadow-lg shadow-indigo-500/50"
                  style={{ width: `${percent}%` }}
                />
              </div>

              {/* Anlık Çözülen Replik Kartı */}
              {currentLine && (
                <div className="p-3 rounded-xl bg-slate-900/90 border border-indigo-500/30 text-xs space-y-1 animate-fadeIn shadow-inner">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-amber-300">
                      {currentLine.speaker || 'Şampiyon'}
                    </span>
                    {currentLine.score > 0 && (
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        currentLine.score >= 85
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      }`}>
                        %{currentLine.score} Fonetik Güven
                      </span>
                    )}
                  </div>
                  <p className="text-slate-200 italic font-serif text-sm">
                    "{currentLine.text || '(Konuşma tespit edilemedi / combat efekti)'}"
                  </p>
                </div>
              )}
            </div>
          )}

          {/* CANLI TERMİNAL ÇIKTISI (LIVE CONSOLE) */}
          <div className="rounded-xl border border-slate-800 bg-[#070b14] overflow-hidden flex flex-col shadow-2xl">
            <div className="flex items-center justify-between px-3.5 py-2 bg-slate-900/90 border-b border-slate-800/80 text-xs">
              <div className="flex items-center gap-2 text-slate-300 font-mono font-bold">
                <Terminal className="w-3.5 h-3.5 text-emerald-400" />
                <span>📟 Canlı Terminal Çıktısı (Live Console)</span>
                {isProcessing && (
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping ml-1" />
                )}
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleCopyLogs}
                  className="px-2 py-1 rounded text-[11px] font-mono text-slate-400 hover:text-white hover:bg-slate-800 transition flex items-center gap-1 cursor-pointer"
                  title="Konsol çıktılarını kopyala"
                >
                  {copiedLog ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedLog ? 'Kopyalandı' : 'Kopyala'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setLogs([])}
                  className="px-2 py-1 rounded text-[11px] font-mono text-slate-400 hover:text-rose-300 hover:bg-slate-800 transition flex items-center gap-1 cursor-pointer"
                  title="Terminali temizle"
                >
                  <Trash2 className="w-3 h-3" />
                  <span>Temizle</span>
                </button>
              </div>
            </div>

            {/* Terminal Monitör Ekranı */}
            <div className="p-3.5 max-h-56 min-h-[140px] overflow-y-auto font-mono text-[11px] leading-relaxed space-y-1 select-text bg-[#03060c]">
              {logs.map((log, i) => {
                let colorClass = "text-slate-300";
                if (log.includes('✅')) colorClass = "text-emerald-300 font-semibold";
                else if (log.includes('❌') || log.includes('HATA')) colorClass = "text-rose-400 font-bold";
                else if (log.includes('⚠️')) colorClass = "text-amber-400";
                else if (log.includes('🎙️')) colorClass = "text-cyan-300";
                else if (log.includes('⚡')) colorClass = "text-indigo-300 font-medium";
                else if (log.includes('🔇')) colorClass = "text-slate-500 italic";

                return (
                  <div key={i} className={`${colorClass} hover:bg-white/[0.02] px-1 py-0.5 rounded transition font-mono whitespace-pre-wrap break-all`}>
                    {log}
                  </div>
                );
              })}
              <div ref={terminalEndRef} />
            </div>
          </div>

          {/* Tamamlandı Bildirimi */}
          {isDone && (
            <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-500/30 flex items-center gap-3 animate-fadeIn">
              <CheckCircle2 className="w-6 h-6 text-emerald-400 shrink-0" />
              <div>
                <h4 className="text-sm font-bold text-white">
                  Replik Metinleri Başarıyla Üretildi ve Doğrulandı!
                </h4>
                <p className="text-xs text-slate-300">
                  Tüm sesler Çoklu Yapay Zeka & Fonetik Güven Skoru ile incelendi ve veritabanlarına kalıcı olarak işlendi.
                </p>
              </div>
            </div>
          )}

          {/* Hata Bildirimi */}
          {error && (
            <div className="p-3.5 rounded-xl bg-rose-950/30 border border-rose-500/30 flex items-start gap-3 text-xs text-rose-300 animate-fadeIn">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold">İşlem Hatası:</span>
                <p className="mt-0.5">{error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Alt Butonlar */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 bg-slate-900/60 shrink-0">
          <button
            onClick={onClose}
            disabled={isProcessing}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-50 cursor-pointer"
          >
            {isDone ? 'Kapat' : 'Vazgeç'}
          </button>

          {!isDone ? (
            <button
              onClick={handleStartTranscribe}
              disabled={isProcessing || items.length === 0}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-purple-600 via-indigo-600 to-indigo-500 hover:from-purple-500 hover:to-indigo-400 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 cursor-pointer"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Çözümleniyor ({progress.current}/{progress.total})...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  <span>Sadece Replik Metinlerini Üret ({items.length} Ses)</span>
                </>
              )}
            </button>
          ) : (
            <button
              onClick={onClose}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-600/30 transition-all cursor-pointer"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Harika, Sayfaya Dön</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
