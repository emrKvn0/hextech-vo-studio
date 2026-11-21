/**
 * Hextech LoLdle Türkiye - Client Application Logic
 * Supports 4 Game Modes: Klasik, Replik, Yetenek, Emoji (Daily & Endless)
 */

// Turkish character normalization helper
function normalizeTr(str) {
    if (!str) return '';
    return str
        .replace(/İ/g, 'i')
        .replace(/I/g, 'i')
        .replace(/ı/g, 'i')
        .toLowerCase()
        .replace(/ğ/g, 'g')
        .replace(/ü/g, 'u')
        .replace(/ş/g, 's')
        .replace(/ö/g, 'o')
        .replace(/ç/g, 'c')
        .replace(/[^a-z0-9]/g, '');
}

class LoLdleApp {
    constructor() {
        this.currentMode = 'classic'; // 'classic' | 'quote' | 'ability' | 'emoji'
        this.playType = 'daily';     // 'daily' | 'endless'
        this.allChampions = [];
        this.currentChallenge = null;
        this.guessHistory = [];
        this.isGameOver = false;
        this.selectedDropdownIndex = -1;

        // Audio player elements
        this.currentAudio = null;
        this.isPlayingAudio = false;

        this.init();
    }

    async init() {
        await this.fetchChampionsList();
        this.bindEvents();
        this.loadStateAndStart();
    }

    async fetchChampionsList() {
        try {
            const res = await fetch('/api/champions');
            this.allChampions = await res.json();
        } catch (err) {
            console.error('Şampiyon listesi yüklenemedi:', err);
        }
    }

    bindEvents() {
        // Mode switch buttons
        document.querySelectorAll('.mode-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const mode = btn.dataset.mode;
                if (mode !== this.currentMode) {
                    hextechAudio.playClick();
                    this.switchMode(mode);
                }
            });
        });

        // Daily / Endless switch buttons
        document.querySelectorAll('.type-toggle-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const type = btn.dataset.type;
                if (type !== this.playType) {
                    hextechAudio.playClick();
                    this.switchPlayType(type);
                }
            });
        });

        // Search box input & autocomplete
        const searchInput = document.getElementById('champSearchInput');
        const dropdown = document.getElementById('autocompleteDropdown');

        searchInput.addEventListener('input', (e) => {
            this.handleSearchInput(e.target.value.trim());
        });

        searchInput.addEventListener('keydown', (e) => {
            this.handleSearchKeydown(e);
        });

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-section')) {
                dropdown.classList.remove('show');
            }
        });

        // Audio play button for Quote Mode
        const playBtn = document.getElementById('quotePlayBtn');
        if (playBtn) {
            playBtn.addEventListener('click', () => {
                this.toggleQuoteAudio();
            });
        }

        // Modal triggers
        document.getElementById('rulesBtn').addEventListener('click', () => {
            hextechAudio.playClick();
            this.openModal('rulesModal');
        });

        document.getElementById('statsBtn').addEventListener('click', () => {
            hextechAudio.playClick();
            this.renderStats();
            this.openModal('statsModal');
        });

        document.querySelectorAll('.modal-close-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                hextechAudio.playClick();
                const modal = e.target.closest('.modal-overlay');
                if (modal) modal.classList.remove('show');
            });
        });

        // Share button in victory modal
        const shareBtn = document.getElementById('shareVictoryBtn');
        if (shareBtn) {
            shareBtn.addEventListener('click', () => {
                this.shareResult();
            });
        }

        // Next round button in endless mode
        const nextRoundBtn = document.getElementById('nextRoundBtn');
        if (nextRoundBtn) {
            nextRoundBtn.addEventListener('click', () => {
                hextechAudio.playClick();
                this.closeAllModals();
                this.startNewChallenge();
            });
        }

        // Next mode button in victory modal
        const nextModeBtn = document.getElementById('nextModeBtn');
        if (nextModeBtn) {
            nextModeBtn.addEventListener('click', () => {
                hextechAudio.playClick();
                this.closeAllModals();
                this.goToNextMode();
            });
        }
    }

    goToNextMode() {
        const modeOrder = ['classic', 'quote', 'ability', 'emoji', 'splash'];
        const currentIndex = modeOrder.indexOf(this.currentMode);
        if (currentIndex >= 0 && currentIndex < modeOrder.length - 1) {
            const nextMode = modeOrder[currentIndex + 1];
            this.switchMode(nextMode);
        } else {
            // All modes completed
            if (this.playType === 'daily') {
                this.showToast('🎉 Tüm günlük modları tamamladın! Sonsuz mod açılıyor...');
                this.switchPlayType('endless');
                this.switchMode('classic');
            } else {
                this.startNewChallenge();
            }
        }
    }

    switchMode(mode) {
        this.currentMode = mode;
        document.querySelectorAll('.mode-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.mode === mode);
        });
        this.loadStateAndStart();
    }

    switchPlayType(type) {
        this.playType = type;
        document.querySelectorAll('.type-toggle-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.type === type);
        });
        this.loadStateAndStart();
    }

    getStorageKey() {
        const today = new Date().toISOString().split('T')[0];
        return `loldle_${this.currentMode}_${this.playType}_${this.playType === 'daily' ? today : 'current'}`;
    }

    async loadStateAndStart() {
        this.isGameOver = false;
        this.guessHistory = [];
        this.stopAudio();
        this.clearUI();

        // Check if daily progress already exists in localStorage
        const storageKey = this.getStorageKey();
        const savedData = localStorage.getItem(storageKey);

        if (savedData && this.playType === 'daily') {
            try {
                const parsed = JSON.parse(savedData);
                this.currentChallenge = parsed.challenge;
                this.guessHistory = parsed.history || [];
                this.isGameOver = parsed.isGameOver || false;
                
                this.renderChallengeUI();
                this.restoreGuessHistory();
                
                if (this.isGameOver && parsed.victoryData) {
                    this.renderInlineVictory(parsed.victoryData, false);
                }
                return;
            } catch (e) {
                console.warn('Kayıtlı veri okunamadı, yeniden başlatılıyor:', e);
            }
        }

        await this.startNewChallenge();
    }

    async startNewChallenge() {
        this.clearUI();
        const endpoint = this.playType === 'daily' ? `/api/daily?mode=${this.currentMode}` : `/api/random?mode=${this.currentMode}`;
        
        try {
            const res = await fetch(endpoint);
            this.currentChallenge = await res.json();
            this.guessHistory = [];
            this.isGameOver = false;

            this.renderChallengeUI();
            this.saveState();
        } catch (err) {
            console.error('Meydan okuma başlatılamadı:', err);
            this.showToast('Sunucu bağlantısında hata oluştu!');
        }
    }

    clearUI() {
        document.getElementById('champSearchInput').value = '';
        document.getElementById('champSearchInput').disabled = false;
        document.getElementById('classicHistory').innerHTML = '';
        document.getElementById('simpleHistory').innerHTML = '';
        document.getElementById('cluesContainer').innerHTML = '';
        
        const banner = document.getElementById('inlineVictoryBanner');
        if (banner) banner.style.display = 'none';

        const skinBadge = document.getElementById('splashSkinBadge');
        if (skinBadge) skinBadge.style.display = 'none';
        
        // Hide all mode panels, then show active
        document.getElementById('classicPanel').style.display = 'none';
        document.getElementById('quotePanel').style.display = 'none';
        document.getElementById('abilityPanel').style.display = 'none';
        document.getElementById('emojiPanel').style.display = 'none';
        document.getElementById('splashPanel').style.display = 'none';
    }

    renderChallengeUI() {
        const c = this.currentChallenge;
        if (!c) return;

        if (this.currentMode === 'classic') {
            document.getElementById('classicPanel').style.display = 'block';
            document.getElementById('modeTitle').innerText = 'Hangi Şampiyon?';
            document.getElementById('modeSubtitle').innerText = 'Şampiyonu bulmak için herhangi bir şampiyon yazarak başla';
        } 
        else if (this.currentMode === 'quote') {
            document.getElementById('quotePanel').style.display = 'block';
            document.getElementById('modeTitle').innerText = 'Hangi Şampiyonun Repliği?';
            document.getElementById('modeSubtitle').innerText = 'Türkçe repliği okuyarak şampiyonu tahmin et!';
            const quoteTextEl = document.getElementById('quoteTextDisplay');
            if (quoteTextEl && c.quote_text) {
                quoteTextEl.innerText = c.quote_text;
            }
            const typeBadge = document.getElementById('quoteTypeBadge');
            if (typeBadge) {
                typeBadge.innerText = c.quote_type ? `🎙️ ${c.quote_type.toUpperCase()}` : '🎙️ REPLİK İPUCU';
            }
            this.updateQuoteAudioLock(this.guessHistory.length, this.isGameOver);
        }
        else if (this.currentMode === 'ability') {
            document.getElementById('abilityPanel').style.display = 'block';
            document.getElementById('modeTitle').innerText = 'Hangi Şampiyonun Yeteneği?';
            document.getElementById('modeSubtitle').innerText = 'Yetenek ikonuna bakarak şampiyonu bul!';
            const iconImg = document.getElementById('abilityIconImg');
            if (iconImg && c.spell_icon_url) {
                iconImg.src = c.spell_icon_url;
            }
        } 
        else if (this.currentMode === 'emoji') {
            document.getElementById('emojiPanel').style.display = 'block';
            document.getElementById('modeTitle').innerText = 'Hangi Şampiyonun Emojileri?';
            document.getElementById('modeSubtitle').innerText = 'Emojileri çözerek şampiyonu tahmin et!';
            this.renderEmojiSlots();
        }
        else if (this.currentMode === 'splash') {
            document.getElementById('splashPanel').style.display = 'flex';
            document.getElementById('modeTitle').innerText = 'Hangi Şampiyonun Görseli?';
            document.getElementById('modeSubtitle').innerText = 'Kırpılmış kostüm / şampiyon görselinden tahmin et!';
            const splashImg = document.getElementById('splashTargetImg');
            const spinner = document.getElementById('splashLoadingSpinner');
            const skinBadge = document.getElementById('splashSkinBadge');
            if (skinBadge) skinBadge.style.display = 'none';

            if (splashImg && c.splash_image_url) {
                if (spinner) spinner.style.display = 'block';
                splashImg.style.opacity = '0';
                splashImg.classList.remove('revealed');
                
                splashImg.onload = () => {
                    if (spinner) spinner.style.display = 'none';
                    splashImg.style.opacity = '1';
                };
                splashImg.onerror = () => {
                    if (spinner) spinner.style.display = 'none';
                    splashImg.style.opacity = '1';
                };
                splashImg.src = c.splash_image_url;

                const cropX = c.crop_x || 50;
                const cropY = c.crop_y || 50;
                splashImg.style.transformOrigin = `${cropX}% ${cropY}%`;
                this.updateSplashZoom(this.guessHistory.length, this.isGameOver);
            }
        }
    }

    updateQuoteAudioLock(guessCount, isGameOver = false) {
        const playBtn = document.getElementById('quotePlayBtn');
        const playIcon = document.getElementById('quotePlayIcon');
        const playLabel = document.getElementById('quotePlayLabel');
        const subtext = document.getElementById('quoteHintSubtext');
        if (!playBtn || !playIcon || !playLabel) return;

        const isUnlocked = isGameOver || guessCount >= 5;

        if (isUnlocked) {
            playBtn.disabled = false;
            playBtn.classList.remove('locked');
            playBtn.classList.add('unlocked');
            playBtn.title = 'Repliğin Orijinal Sesini Dinle';
            if (!this.isPlayingAudio) {
                playIcon.innerText = '🔊';
                playLabel.innerText = 'Ses İpucunu Dinle';
            }
            if (subtext) {
                subtext.innerText = '✨ Ses ipucu açıldı! Repliğin orijinal sesini dinleyebilirsin.';
                subtext.style.color = '#a8ffcc';
            }
        } else {
            playBtn.disabled = true;
            playBtn.classList.remove('unlocked');
            playBtn.classList.add('locked');
            const remaining = 5 - guessCount;
            playBtn.title = `${remaining} yanlış tahminde açılır`;
            playIcon.innerText = '🔒';
            playLabel.innerText = `Ses İpucu (5 Yanlış Tahminde Açılır - ${guessCount}/5)`;
            if (subtext) {
                subtext.innerText = `🔒 Ses ipucu için ${remaining} yanlış tahmin daha gerekli. (${guessCount}/5)`;
                subtext.style.color = '#8c9ba8';
            }
            this.stopAudio();
        }
    }

    updateSplashZoom(guessCount, isGameOver = false) {
        const splashImg = document.getElementById('splashTargetImg');
        const badge = document.getElementById('splashZoomBadge');
        if (!splashImg || !badge) return;

        if (isGameOver) {
            splashImg.classList.add('revealed');
            splashImg.style.transform = 'scale(1)';
            badge.innerText = '✨ Tam Görsel Açıldı!';
            badge.style.color = '#a8ffcc';
            badge.style.borderColor = '#27ae60';
            return;
        }

        // Kademeli zoom out seviyeleri: 5.0x -> 3.5x -> 2.4x -> 1.6x -> 1.2x -> 1.0x
        const zoomLevels = [5.0, 3.5, 2.4, 1.6, 1.2, 1.0];
        const currentLevelIdx = Math.min(guessCount, zoomLevels.length - 1);
        const currentScale = zoomLevels[currentLevelIdx];

        splashImg.classList.remove('revealed');
        splashImg.style.transform = `scale(${currentScale})`;
        badge.innerText = `🔍 Büyütme: ${currentScale.toFixed(1)}x`;
        badge.style.color = 'var(--loldle-gold-bright)';
        badge.style.borderColor = 'var(--loldle-gold)';
    }

    renderEmojiSlots(forceRevealAll = false) {
        const c = this.currentChallenge;
        const emojiRow = document.getElementById('emojisRow');
        if (!emojiRow || !c || !c.emojis) return;

        const total = c.emojis.length;
        // Initially reveal 1 emoji. Each wrong guess reveals +1.
        const revealedCount = (forceRevealAll || this.isGameOver) 
            ? total 
            : Math.min(total, 1 + this.guessHistory.length);

        emojiRow.innerHTML = c.emojis.map((emoji, idx) => {
            const isRevealed = idx < revealedCount;
            if (isRevealed) {
                return `<div class="emoji-slot revealed" title="Emoji ${idx + 1}">${emoji}</div>`;
            } else {
                return `<div class="emoji-slot locked" title="Yanlış tahminde açılır">🔒</div>`;
            }
        }).join('');
    }

    // Autocomplete logic
    handleSearchInput(query) {
        const dropdown = document.getElementById('autocompleteDropdown');
        if (!query || query.length < 1) {
            dropdown.classList.remove('show');
            return;
        }

        const normQuery = normalizeTr(query);
        const guessedIds = new Set(this.guessHistory.map(g => g.guess_champion.id.toLowerCase()));

        const matches = this.allChampions.filter(c => {
            if (guessedIds.has(c.id.toLowerCase())) return false;
            const normName = normalizeTr(c.name);
            const normId = normalizeTr(c.id);
            return normName.includes(normQuery) || normId.includes(normQuery);
        }).slice(0, 10);

        if (matches.length === 0) {
            dropdown.classList.remove('show');
            return;
        }

        this.selectedDropdownIndex = -1;
        dropdown.innerHTML = matches.map((c, idx) => `
            <div class="dropdown-item" data-id="${c.id}" data-idx="${idx}">
                <img src="${c.image}" alt="${c.name}" loading="lazy">
                <div class="dropdown-item-info">
                    <span class="dropdown-item-name">${c.name}</span>
                    <span class="dropdown-item-title">${c.title}</span>
                </div>
            </div>
        `).join('');

        dropdown.querySelectorAll('.dropdown-item').forEach(item => {
            item.addEventListener('click', () => {
                const champId = item.dataset.id;
                this.selectAndSubmitChampion(champId);
            });
        });

        dropdown.classList.add('show');
    }

    handleSearchKeydown(e) {
        const dropdown = document.getElementById('autocompleteDropdown');
        const items = dropdown.querySelectorAll('.dropdown-item');
        if (!dropdown.classList.contains('show') || items.length === 0) return;

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.selectedDropdownIndex = Math.min(items.length - 1, this.selectedDropdownIndex + 1);
            this.updateDropdownHighlight(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.selectedDropdownIndex = Math.max(0, this.selectedDropdownIndex - 1);
            this.updateDropdownHighlight(items);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (this.selectedDropdownIndex >= 0 && items[this.selectedDropdownIndex]) {
                const champId = items[this.selectedDropdownIndex].dataset.id;
                this.selectAndSubmitChampion(champId);
            } else if (items.length > 0) {
                this.selectAndSubmitChampion(items[0].dataset.id);
            }
        } else if (e.key === 'Escape') {
            dropdown.classList.remove('show');
        }
    }

    updateDropdownHighlight(items) {
        items.forEach((item, idx) => {
            item.classList.toggle('highlighted', idx === this.selectedDropdownIndex);
            if (idx === this.selectedDropdownIndex) {
                item.scrollIntoView({ block: 'nearest' });
            }
        });
    }

    async selectAndSubmitChampion(champId) {
        const dropdown = document.getElementById('autocompleteDropdown');
        const searchInput = document.getElementById('champSearchInput');
        dropdown.classList.remove('show');
        searchInput.value = '';
        searchInput.focus();

        if (this.isGameOver || !this.currentChallenge) return;

        const guessCount = this.guessHistory.length + 1;

        try {
            const res = await fetch('/api/guess', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token: this.currentChallenge.token,
                    guess_id: champId,
                    guess_count: guessCount
                })
            });

            if (!res.ok) {
                const err = await res.json();
                this.showToast(err.detail || 'Tahmin gönderilemedi.');
                return;
            }

            const feedback = await res.json();
            this.handleGuessFeedback(feedback);

        } catch (err) {
            console.error('Tahmin hatası:', err);
            this.showToast('Bağlantı hatası!');
        }
    }

    handleGuessFeedback(feedback) {
        this.guessHistory.push(feedback);

        if (feedback.is_correct) {
            this.isGameOver = true;
            document.getElementById('champSearchInput').disabled = true;
            hextechAudio.playCorrect();
        } else {
            hextechAudio.playWrong();
        }

        // Render guess in UI
        if (this.currentMode === 'classic') {
            this.renderClassicRow(feedback, this.guessHistory.length, false);
        } else {
            this.renderSimpleGuess(feedback);
        }

        // Update emoji reveal states
        if (this.currentMode === 'emoji') {
            this.renderEmojiSlots(feedback.is_correct);
        }

        // Update splash zoom state
        if (this.currentMode === 'splash') {
            this.updateSplashZoom(this.guessHistory.length, feedback.is_correct);
        }

        // Update quote audio lock
        if (this.currentMode === 'quote') {
            this.updateQuoteAudioLock(this.guessHistory.length, feedback.is_correct);
        }

        // Update Clues for other modes
        if (feedback.hints && feedback.hints.length > 0) {
            this.renderHints(feedback.hints);
        }

        this.saveState(feedback.victory);

        if (feedback.is_correct && feedback.victory) {
            this.isGameOver = true;
            document.getElementById('champSearchInput').disabled = true;
            const delay = this.currentMode === 'classic' ? 1200 : 300;
            setTimeout(() => {
                this.renderInlineVictory(feedback.victory, true);
            }, delay);
        }
    }

    renderInlineVictory(victoryData, isNewWin = true) {
        const champ = victoryData.champion;
        const banner = document.getElementById('inlineVictoryBanner');
        if (!banner || !champ) return;

        const imgEl = document.getElementById('bannerChampImg');
        const nameEl = document.getElementById('bannerChampName');
        const titleEl = document.getElementById('bannerChampTitle');
        const guessInfoEl = document.getElementById('bannerGuessInfo');
        const openModalBtn = document.getElementById('bannerOpenModalBtn');
        const nextBtn = document.getElementById('bannerNextBtn');

        if (imgEl) imgEl.src = champ.images.square;
        if (nameEl) nameEl.innerText = champ.name;
        if (titleEl) {
            if (this.currentMode === 'splash' && victoryData.skin_name) {
                titleEl.innerText = `🎨 ${victoryData.skin_name}`;
            } else {
                titleEl.innerText = champ.title;
            }
        }
        if (guessInfoEl) {
            guessInfoEl.innerText = `${victoryData.total_guesses}. tahminde doğru bildin!`;
        }

        // Configure next button label
        if (nextBtn) {
            if (this.playType === 'daily') {
                const nextNames = {
                    'classic': 'Replik',
                    'quote': 'Yetenek',
                    'ability': 'Emoji',
                    'emoji': 'Splash',
                    'splash': 'Bitti (Sonsuz)'
                };
                nextBtn.innerText = `Sonraki: ${nextNames[this.currentMode] || 'Diğer'} ➔`;
            } else {
                nextBtn.innerText = 'Yeni Tur ➔';
            }
            nextBtn.onclick = () => {
                hextechAudio.playClick();
                if (this.playType === 'daily') {
                    this.goToNextMode();
                } else {
                    this.startNewChallenge();
                }
            };
        }

        if (openModalBtn) {
            openModalBtn.onclick = () => {
                hextechAudio.playClick();
                this.showVictoryModal(victoryData);
            };
        }

        banner.style.display = 'flex';

        // If Splash mode, reveal full image and show skin badge
        if (this.currentMode === 'splash') {
            this.updateSplashZoom(victoryData.total_guesses, true);
            const skinBadge = document.getElementById('splashSkinBadge');
            if (skinBadge && victoryData.skin_name) {
                skinBadge.innerText = `🎨 Kostüm: ${victoryData.skin_name}`;
                skinBadge.style.display = 'block';
            }
        }

        if (isNewWin) {
            hextechAudio.playVictory();
            this.triggerConfetti();
            this.updateStats(victoryData.total_guesses);
        }
    }

    renderClassicRow(feedback, rowIndex, isRestoring = false) {
        const c = feedback.guess_champion;
        const comp = feedback.comparison;
        const container = document.getElementById('classicHistory');

        const row = document.createElement('div');
        row.className = 'guess-row';

        // Helper: format list attributes as aesthetic chips or single label
        const formatChips = (val) => {
            if (Array.isArray(val)) {
                if (val.length === 1) {
                    return `<span class="tile-value">${val[0]}</span>`;
                }
                return `<div class="tile-chips">${val.map(v => `<span class="tile-chip">${v}</span>`).join('')}</div>`;
            }
            return `<span class="tile-value">${val}</span>`;
        };

        // Year indicator badge
        let yearBadge = '';
        if (comp.release_year.direction === 'higher') {
            yearBadge = '<div class="year-indicator up">⬆️ Daha Yeni</div>';
        } else if (comp.release_year.direction === 'lower') {
            yearBadge = '<div class="year-indicator down">⬇️ Daha Eski</div>';
        } else if (comp.release_year.status === 'exact') {
            yearBadge = '<div class="year-indicator exact">✓ Tam Yıl</div>';
        }

        const tilesData = [
            { 
                class: 'tile-champion', 
                html: `
                    <div class="champ-tile-avatar">
                        <img src="${c.image}" alt="${c.name}">
                    </div>
                    <span class="champ-tile-label">${c.name}</span>
                ` 
            },
            { class: comp.gender.status, html: `<span class="tile-value">${comp.gender.value}</span>` },
            { class: comp.positions.status, html: formatChips(comp.positions.value) },
            { class: comp.species.status, html: formatChips(comp.species.value) },
            { class: comp.resource.status, html: `<span class="tile-value">${comp.resource.value}</span>` },
            { class: comp.range_type.status, html: formatChips(comp.range_type.value) },
            { class: comp.regions.status, html: formatChips(comp.regions.value) },
            { 
                class: comp.release_year.status, 
                html: `
                    <div class="year-tile-body">
                        <span class="year-number">${comp.release_year.value}</span>
                        ${yearBadge}
                    </div>
                ` 
            }
        ];

        tilesData.forEach((t, idx) => {
            const tileEl = document.createElement('div');
            tileEl.className = `tile ${t.class}`;
            tileEl.innerHTML = t.html;

            if (!isRestoring) {
                // Staggered Flip animation with synchronized tactile audio
                const delaySeconds = (idx * 0.16).toFixed(2);
                tileEl.style.animationDelay = `${delaySeconds}s`;
                setTimeout(() => {
                    hextechAudio.playTileReveal(idx);
                }, idx * 160);
            } else {
                tileEl.style.animation = 'none';
                tileEl.style.opacity = '1';
                tileEl.style.transform = 'none';
            }
            row.appendChild(tileEl);
        });

        // Prepend to show latest guess on top
        container.insertBefore(row, container.firstChild);
    }

    renderSimpleGuess(feedback) {
        const container = document.getElementById('simpleHistory');
        const c = feedback.guess_champion;
        const isCorrect = feedback.is_correct;

        const item = document.createElement('div');
        item.className = `simple-guess-item ${isCorrect ? 'correct' : 'wrong'}`;
        item.innerHTML = `
            <div style="display:flex; align-items:center; gap:10px;">
                <img src="${c.image}" alt="${c.name}">
                <span>${c.name} (${c.title})</span>
            </div>
            <span>${isCorrect ? '🟩 Doğru!' : '🟥 Yanlış'}</span>
        `;
        container.insertBefore(item, container.firstChild);
    }

    renderHints(hints) {
        const container = document.getElementById('cluesContainer');
        container.innerHTML = hints.map(h => `
            <div class="clue-card">
                <span class="clue-label">${h.label}</span>
                <span class="clue-value">${h.value}</span>
            </div>
        `).join('');
    }

    restoreGuessHistory() {
        this.guessHistory.forEach((feedback, idx) => {
            if (this.currentMode === 'classic') {
                this.renderClassicRow(feedback, idx + 1, true);
            } else {
                this.renderSimpleGuess(feedback);
            }
            if (feedback.hints) {
                this.renderHints(feedback.hints);
            }
        });
        if (this.currentMode === 'emoji') {
            this.renderEmojiSlots(this.isGameOver);
        }
        if (this.currentMode === 'splash') {
            this.updateSplashZoom(this.guessHistory.length, this.isGameOver);
        }
        if (this.currentMode === 'quote') {
            this.updateQuoteAudioLock(this.guessHistory.length, this.isGameOver);
        }
    }

    // Audio controls for Quote Mode
    toggleQuoteAudio() {
        const isUnlocked = this.isGameOver || this.guessHistory.length >= 5;
        if (!isUnlocked) {
            this.showToast('🔒 Ses ipucu 5 yanlış tahmin sonrasında açılır!');
            return;
        }

        if (this.isPlayingAudio) {
            this.stopAudio();
            return;
        }

        if (!this.currentChallenge || !this.currentChallenge.audio_url) return;

        this.currentAudio = new Audio(this.currentChallenge.audio_url);
        const wave = document.getElementById('soundwaveAnim');
        const playIcon = document.getElementById('quotePlayIcon');
        const playLabel = document.getElementById('quotePlayLabel');

        this.isPlayingAudio = true;
        if (wave) wave.classList.add('playing');
        if (playIcon) playIcon.innerText = '⏸️';
        if (playLabel) playLabel.innerText = 'Durdur';

        this.currentAudio.play().catch(e => {
            console.warn('Audio play error:', e);
            this.stopAudio();
        });

        this.currentAudio.onended = () => {
            this.stopAudio();
        };
    }

    stopAudio() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio.currentTime = 0;
            this.currentAudio = null;
        }
        this.isPlayingAudio = false;
        const wave = document.getElementById('soundwaveAnim');
        const playIcon = document.getElementById('quotePlayIcon');
        const playLabel = document.getElementById('quotePlayLabel');
        if (wave) wave.classList.remove('playing');
        if (playIcon) playIcon.innerText = '🔊';
        if (playLabel) playLabel.innerText = 'Ses İpucunu Dinle';
    }

    // Victory & Stats Modals
    showVictoryModal(victoryData, isNewWin = false) {
        const champ = victoryData.champion;
        const splashUrl = victoryData.splash_url || champ.images.splash;
        document.getElementById('victorySplashImg').src = splashUrl;
        document.getElementById('victoryChampName').innerText = champ.name;
        if (victoryData.skin_name) {
            document.getElementById('victoryChampTitle').innerText = `${champ.title} • 🎨 ${victoryData.skin_name}`;
        } else {
            document.getElementById('victoryChampTitle').innerText = champ.title;
        }
        document.getElementById('victoryTotalGuesses').innerText = victoryData.total_guesses;
        document.getElementById('victoryLore').innerText = champ.blurb;

        // Configure Next Mode / Next Round buttons
        const nextModeBtn = document.getElementById('nextModeBtn');
        const nextModeText = document.getElementById('nextModeText');
        const nextRoundBtn = document.getElementById('nextRoundBtn');

        if (nextRoundBtn) {
            nextRoundBtn.style.display = (this.playType === 'endless') ? 'flex' : 'none';
        }

        if (nextModeBtn && nextModeText) {
            if (this.playType === 'daily') {
                if (this.currentMode === 'classic') {
                    nextModeText.innerText = 'Sonraki Mod: 🎙️ Replik ➔';
                } else if (this.currentMode === 'quote') {
                    nextModeText.innerText = 'Sonraki Mod: ⚡ Yetenek ➔';
                } else if (this.currentMode === 'ability') {
                    nextModeText.innerText = 'Sonraki Mod: ✨ Emoji ➔';
                } else if (this.currentMode === 'emoji') {
                    nextModeText.innerText = 'Sonraki Mod: 🖼️ Splash ➔';
                } else if (this.currentMode === 'splash') {
                    nextModeText.innerText = '🎉 Günlük Modlar Bitti! ♾️ Sonsuz Modu Oyna ➔';
                }
            } else {
                const nextNames = {
                    'classic': '🎙️ Replik',
                    'quote': '⚡ Yetenek',
                    'ability': '✨ Emoji',
                    'emoji': '🖼️ Splash',
                    'splash': '🎯 Klasik'
                };
                nextModeText.innerText = `Sonraki Mod: ${nextNames[this.currentMode] || 'Diğer'} ➔`;
            }
        }

        // Play champion audio on victory
        const champVoiceBtn = document.getElementById('playChampVoiceBtn');
        if (champVoiceBtn) {
            champVoiceBtn.onclick = () => {
                const aud = new Audio(champ.quotes.choose_audio_url);
                aud.play();
            };
        }

        if (isNewWin) {
            this.updateStats(victoryData.total_guesses);
            this.triggerConfetti();
        }

        this.openModal('victoryModal');
    }

    shareResult() {
        const lastFeedback = this.guessHistory[this.guessHistory.length - 1];
        if (!lastFeedback || !lastFeedback.victory) return;

        const shareText = lastFeedback.victory.share_text;
        navigator.clipboard.writeText(shareText).then(() => {
            this.showToast('📋 Sonuç panoya kopyalandı!');
        }).catch(() => {
            this.showToast('Kopyalama başarısız!');
        });
    }

    triggerConfetti() {
        const colors = ['#c8aa6e', '#0ac8b9', '#f0e6d2', '#2ecc71', '#e74c3c'];
        for (let i = 0; i < 40; i++) {
            const conf = document.createElement('div');
            conf.style.position = 'fixed';
            conf.style.top = '-10px';
            conf.style.left = `${Math.random() * 100}vw`;
            conf.style.width = `${Math.random() * 10 + 6}px`;
            conf.style.height = `${Math.random() * 10 + 6}px`;
            conf.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            conf.style.borderRadius = '50%';
            conf.style.zIndex = '9999';
            conf.style.pointerEvents = 'none';
            conf.style.transform = `rotate(${Math.random() * 360}deg)`;
            conf.style.transition = `all ${Math.random() * 2 + 2}s cubic-bezier(0.25, 1, 0.5, 1)`;
            document.body.appendChild(conf);

            setTimeout(() => {
                conf.style.top = '105vh';
                conf.style.transform = `rotate(${Math.random() * 720}deg) scale(0.5)`;
                conf.style.opacity = '0';
            }, 20);

            setTimeout(() => {
                conf.remove();
            }, 4500);
        }
    }

    // Stats Management
    updateStats(guesses) {
        const key = `loldle_stats_${this.currentMode}`;
        let stats = JSON.parse(localStorage.getItem(key)) || {
            played: 0,
            won: 0,
            currentStreak: 0,
            maxStreak: 0,
            distribution: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, '6+': 0 }
        };

        stats.played += 1;
        stats.won += 1;
        stats.currentStreak += 1;
        stats.maxStreak = Math.max(stats.maxStreak, stats.currentStreak);

        const distKey = guesses <= 5 ? String(guesses) : '6+';
        stats.distribution[distKey] = (stats.distribution[distKey] || 0) + 1;

        localStorage.setItem(key, JSON.stringify(stats));
    }

    renderStats() {
        const key = `loldle_stats_${this.currentMode}`;
        const stats = JSON.parse(localStorage.getItem(key)) || {
            played: 0,
            won: 0,
            currentStreak: 0,
            maxStreak: 0,
            distribution: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, '6+': 0 }
        };

        document.getElementById('statPlayed').innerText = stats.played;
        const winRate = stats.played > 0 ? Math.round((stats.won / stats.played) * 100) : 0;
        document.getElementById('statWinRate').innerText = `${winRate}%`;
        document.getElementById('statCurrentStreak').innerText = stats.currentStreak;
        document.getElementById('statMaxStreak').innerText = stats.maxStreak;

        // Render Distribution Bars
        const distContainer = document.getElementById('statsDistributionBars');
        if (distContainer) {
            const maxVal = Math.max(1, ...Object.values(stats.distribution));
            distContainer.innerHTML = Object.entries(stats.distribution).map(([num, count]) => {
                const pct = Math.max(8, Math.round((count / maxVal) * 100));
                return `
                    <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px; font-size:0.85rem;">
                        <span style="width:20px; font-weight:bold; color:var(--border-gold);">${num}</span>
                        <div style="flex:1; background:rgba(255,255,255,0.08); border-radius:3px; overflow:hidden;">
                            <div style="width:${pct}%; background:var(--hextech-cyan); color:#000; padding:2px 8px; font-weight:bold; text-align:right; border-radius:3px;">
                                ${count}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
    }

    saveState(victoryData = null) {
        if (this.playType !== 'daily') return;
        const storageKey = this.getStorageKey();
        const dataToSave = {
            challenge: this.currentChallenge,
            history: this.guessHistory,
            isGameOver: this.isGameOver,
            victoryData: victoryData
        };
        localStorage.setItem(storageKey, JSON.stringify(dataToSave));
    }

    openModal(id) {
        const m = document.getElementById(id);
        if (m) m.classList.add('show');
    }

    closeAllModals() {
        document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('show'));
    }

    showToast(msg) {
        const toast = document.getElementById('toastMsg');
        if (toast) {
            toast.innerText = msg;
            toast.style.display = 'block';
            setTimeout(() => {
                toast.style.display = 'none';
            }, 2500);
        }
    }
}

// Instantiate on DOM load
window.addEventListener('DOMContentLoaded', () => {
    window.app = new LoLdleApp();
});
