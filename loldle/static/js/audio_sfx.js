/**
 * Hextech Web Audio API SFX Engine
 * Generates rich synthetic LoL-style sound effects without external audio dependencies.
 */

class HextechAudioEngine {
    constructor() {
        this.ctx = null;
        this.enabled = true;
        this.volume = 0.5;
    }

    init() {
        if (!this.ctx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (AudioContext) {
                this.ctx = new AudioContext();
            }
        }
        if (this.ctx && this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    }

    setVolume(val) {
        this.volume = Math.max(0, Math.min(1, val));
    }

    playClick() {
        if (!this.enabled) return;
        this.init();
        if (!this.ctx) return;

        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'sine';
        osc.frequency.setValueAtTime(800, now);
        osc.frequency.exponentialRampToValueAtTime(300, now + 0.05);

        gain.gain.setValueAtTime(this.volume * 0.2, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + 0.05);
    }

    playTileReveal(index = 0) {
        if (!this.enabled) return;
        this.init();
        if (!this.ctx) return;

        const now = this.ctx.currentTime;

        // 1. Tok ve dolgun gövde (Acoustic soft thud - 150Hz -> 50Hz)
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        // Her sütunda hafif armonik ton yükselişi
        const baseFreq = 135 + (index * 12);
        osc.type = 'sine';
        osc.frequency.setValueAtTime(baseFreq, now);
        osc.frequency.exponentialRampToValueAtTime(45, now + 0.08);

        gain.gain.setValueAtTime(this.volume * 0.32, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + 0.08);

        // 2. Hafif mekanik çıtırtı / kart sürtünmesi (Soft tactile snap / click)
        const clickOsc = this.ctx.createOscillator();
        const clickGain = this.ctx.createGain();

        clickOsc.type = 'triangle';
        clickOsc.frequency.setValueAtTime(950 + (index * 40), now);
        clickOsc.frequency.exponentialRampToValueAtTime(220, now + 0.03);

        clickGain.gain.setValueAtTime(this.volume * 0.12, now);
        clickGain.gain.exponentialRampToValueAtTime(0.001, now + 0.035);

        clickOsc.connect(clickGain);
        clickGain.connect(this.ctx.destination);

        clickOsc.start(now);
        clickOsc.stop(now + 0.035);
    }

    playCorrect() {
        if (!this.enabled) return;
        this.init();
        if (!this.ctx) return;

        const now = this.ctx.currentTime;
        const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6 (Hextech triumph chord)

        notes.forEach((freq, i) => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, now + i * 0.08);

            gain.gain.setValueAtTime(0, now + i * 0.08);
            gain.gain.linearRampToValueAtTime(this.volume * 0.25, now + i * 0.08 + 0.03);
            gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.08 + 0.6);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now + i * 0.08);
            osc.stop(now + i * 0.08 + 0.6);
        });
    }

    playWrong() {
        if (!this.enabled) return;
        this.init();
        if (!this.ctx) return;

        const now = this.ctx.currentTime;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();

        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(160, now);
        osc.frequency.exponentialRampToValueAtTime(110, now + 0.2);

        gain.gain.setValueAtTime(this.volume * 0.18, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.22);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now);
        osc.stop(now + 0.22);
    }

    playHintUnlock() {
        if (!this.enabled) return;
        this.init();
        if (!this.ctx) return;

        const now = this.ctx.currentTime;
        const notes = [440, 554.37, 659.25];

        notes.forEach((freq, i) => {
            const osc = this.ctx.createOscillator();
            const gain = this.ctx.createGain();

            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, now + i * 0.06);

            gain.gain.setValueAtTime(0, now + i * 0.06);
            gain.gain.linearRampToValueAtTime(this.volume * 0.15, now + i * 0.06 + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.06 + 0.3);

            osc.connect(gain);
            gain.connect(this.ctx.destination);

            osc.start(now + i * 0.06);
            osc.stop(now + i * 0.06 + 0.3);
        });
    }
}

const hextechAudio = new HextechAudioEngine();

// Auto-initialize on first user interaction for strict autoplay browser policies
if (typeof window !== 'undefined') {
    window.addEventListener('pointerdown', () => hextechAudio.init(), { once: true });
}
