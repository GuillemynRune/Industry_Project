// TTS Client for ElevenLabs integration
class TTSClient {
    constructor() {
        this.currentAudio = null;
        this.isPlaying = false;
        this.audioCache = new Map(); // Cache audio to avoid re-generating
    }
    
    async generateSpeech(text, voice = 'sarah') {
        const cacheKey = `${text}_${voice}`;
        
        // Check cache first
        if (this.audioCache.has(cacheKey)) {
            return this.audioCache.get(cacheKey);
        }
        
        try {
            const response = await fetch(`${API_BASE_URL}/tts/generate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text, voice })
            });
            
            if (!response.ok) {
                throw new Error(`TTS API error: ${response.status}`);
            }
            
            const audioBlob = await response.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            
            // Cache the result
            this.audioCache.set(cacheKey, audioUrl);
            
            return audioUrl;
        } catch (error) {
            console.error('TTS generation failed:', error);
            throw error;
        }
    }
    
    async speak(text, options = {}) {
        if (this.isPlaying) {
            this.stop();
        }
        
        try {
            this.showLoadingAnimation();
            
            const audioUrl = await this.generateSpeech(text, options.voice);
            
            this.currentAudio = new Audio(audioUrl);
            this.currentAudio.volume = options.volume || 0.8;
            
            this.currentAudio.onloadeddata = () => {
                this.hideLoadingAnimation();
                this.showPlayingState();
            };
            
            this.currentAudio.onended = () => {
                this.stop();
            };
            
            this.currentAudio.onerror = () => {
                this.stop();
                showToast('Audio playback error', 'error');
            };
            
            await this.currentAudio.play();
            this.isPlaying = true;
            
        } catch (error) {
            this.hideLoadingAnimation();
            
            if (error.message.includes('429')) {
                showToast('Please wait a moment before generating more speech', 'warning');
            } else if (error.message.includes('500')) {
                showToast('Speech service temporarily unavailable', 'warning');
            } else {
                showToast('Unable to generate speech', 'error');
            }
        }
    }
    
    stop() {
        if (this.currentAudio) {
            this.currentAudio.pause();
            this.currentAudio = null;
        }
        this.isPlaying = false;
        this.hideLoadingAnimation();
        this.hidePlayingState();
        
        // Reset all TTS buttons
        document.querySelectorAll('.tts-btn').forEach(btn => {
            btn.innerHTML = '🔊 Listen';
            btn.classList.remove('playing', 'loading');
        });
    }
    
    showLoadingAnimation() {
        document.querySelectorAll('.tts-btn.active').forEach(btn => {
            btn.classList.add('loading');
            btn.innerHTML = '⏳ Generating...';
        });
    }
    
    hideLoadingAnimation() {
        document.querySelectorAll('.tts-btn').forEach(btn => {
            btn.classList.remove('loading');
        });
    }
    
    showPlayingState() {
        document.querySelectorAll('.tts-btn.active').forEach(btn => {
            btn.classList.add('playing');
            btn.innerHTML = '⏸ Stop';
        });
    }
    
    hidePlayingState() {
        document.querySelectorAll('.tts-btn').forEach(btn => {
            btn.classList.remove('playing', 'active');
        });
    }
}

// Initialize TTS client
window.ttsClient = new TTSClient();

// Add TTS buttons to story cards
function addTTSButtons() {
    const style = document.createElement('style');
    style.textContent = `
        .tts-btn {
            background: linear-gradient(45deg, var(--soft-blue), var(--deep-blue));
            color: white;
            border: none;
            padding: 10px 18px;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
            margin-top: 12px;
            transition: all 0.4s ease;
            box-shadow: 0 4px 15px rgba(107, 182, 214, 0.3);
            position: relative;
            overflow: hidden;
        }
        .tts-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(107, 182, 214, 0.4);
        }
        .tts-btn.playing {
            background: linear-gradient(45deg, var(--deep-pink), var(--soft-pink));
            animation: pulseGlow 2s ease-in-out infinite;
        }
        .tts-btn.loading {
            background: linear-gradient(45deg, #ffc107, #ff8f00);
        }
        @keyframes pulseGlow {
            0%, 100% { box-shadow: 0 8px 25px rgba(232, 145, 163, 0.4); }
            50% { box-shadow: 0 12px 35px rgba(232, 145, 163, 0.6); }
        }
    `;
    document.head.appendChild(style);
    
    document.querySelectorAll('.story-card').forEach(card => {
        if (card.querySelector('.tts-btn')) return;
        
        const preview = card.querySelector('.story-preview').textContent;
        const button = document.createElement('button');
        button.className = 'tts-btn';
        button.innerHTML = '🔊 Listen';
        
        button.onclick = async (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (window.ttsClient.isPlaying) {
                window.ttsClient.stop();
            } else {
                button.classList.add('active');
                await window.ttsClient.speak(preview);
            }
        };
        
        card.querySelector('.story-meta').appendChild(button);
    });
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(addTTSButtons, 1000);
    
    // Watch for new stories
    const observer = new MutationObserver(addTTSButtons);
    const storiesContainer = document.getElementById('storiesTrack');
    if (storiesContainer) {
        observer.observe(storiesContainer, { childList: true, subtree: true });
    }
});

window.addTTSButtons = addTTSButtons;