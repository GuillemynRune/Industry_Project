// Enhanced Speech Recognition System
class SpeechRecognitionManager {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.currentTextarea = null;
        this.audioContext = null;
        this.analyser = null;
        this.mediaStream = null;
        this.animationId = null;
        this.init();
    }

    init() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!SpeechRecognition) {
            console.warn('Speech Recognition not supported');
            this.addMicrophoneButtonsToTextareas();
            return;
        }

        this.recognition = new SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.setupRecognitionEvents();
        this.addMicrophoneButtonsToTextareas();
    }

    setupRecognitionEvents() {
        let finalTranscript = '';

        this.recognition.onstart = () => {
            console.log('Speech recognition started');
            finalTranscript = '';
        };

        this.recognition.onresult = (event) => {
            let interimTranscript = '';
            
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interimTranscript += transcript;
                }
            }

            if (this.currentTextarea) {
                const existingText = this.currentTextarea.dataset.originalText || '';
                this.currentTextarea.value = existingText + finalTranscript + interimTranscript;
                this.currentTextarea.dispatchEvent(new Event('input', { bubbles: true }));
            }
        };

        this.recognition.onend = () => {
            if (this.currentTextarea && finalTranscript) {
                this.currentTextarea.dataset.originalText = this.currentTextarea.value;
            }
            this.stopListening();
        };

        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.stopListening();
            
            const errorMessages = {
                'not-allowed': 'Microphone access denied. Please enable microphone permissions.',
                'no-speech': 'No speech detected. Please try speaking closer to your microphone.',
                'network': 'Network error. Please check your internet connection.',
                'service-not-allowed': 'Speech service not allowed. Try refreshing the page.'
            };
            
            const message = errorMessages[event.error] || `Speech recognition error: ${event.error}`;
            showToast(message, 'error', 'Speech Recognition Error');
        };
    }

    addMicrophoneButtonsToTextareas() {
        document.querySelectorAll('textarea').forEach(textarea => {
            this.enhanceTextarea(textarea);
        });

        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) {
                        const textareas = node.querySelectorAll ? node.querySelectorAll('textarea') : [];
                        textareas.forEach(textarea => this.enhanceTextarea(textarea));
                        
                        if (node.tagName === 'TEXTAREA') {
                            this.enhanceTextarea(node);
                        }
                    }
                });
            });
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }

    enhanceTextarea(textarea) {
        if (textarea.dataset.speechEnhanced) return;
        textarea.dataset.speechEnhanced = 'true';

        const micContainer = document.createElement('div');
        micContainer.className = 'speech-mic-container';
        
        const isSupported = this.recognition !== null;
        const buttonTitle = isSupported ? 'Click to use voice input' : 'Speech recognition not supported in this browser';
        
        micContainer.innerHTML = `
            <button type="button" class="speech-mic-btn" aria-label="Voice input" title="${buttonTitle}" ${!isSupported ? 'disabled' : ''}>
                <div class="mic-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                        <path d="M12 1a4 4 0 0 0-4 4v7a4 4 0 0 0 8 0V5a4 4 0 0 0-4-4z" fill="currentColor"/>
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                </div>
                <div class="volume-bars">
                    ${Array(5).fill('<div class="bar"></div>').join('')}
                </div>
            </button>
        `;

        const textareaParent = textarea.parentNode;
        textareaParent.style.position = 'relative';
        textareaParent.appendChild(micContainer);

        const micBtn = micContainer.querySelector('.speech-mic-btn');
        micBtn.addEventListener('click', () => {
            if (!isSupported) {
                showToast('Speech recognition is not supported in this browser. Please try Chrome, Edge, or Safari.', 'warning', 'Browser Not Supported');
                return;
            }
            
            if (this.isListening && this.currentTextarea === textarea) {
                this.stopListening();
            } else {
                this.startListening(textarea, micContainer);
            }
        });
    }

    async startListening(textarea, micContainer) {
        try {
            textarea.dataset.originalText = textarea.value;
            this.currentTextarea = textarea;

            await this.setupAudioVisualization();

            this.recognition.start();
            this.isListening = true;

            micContainer.classList.add('listening');
            textarea.classList.add('speech-active');

            this.createListeningOverlay();

            showToast('Listening... Speak now!', 'success', 'Voice Input Active');

        } catch (error) {
            console.error('Error starting speech recognition:', error);
            showToast('Unable to access microphone. Please check your browser settings.', 'error', 'Microphone Error');
        }
    }

    async setupAudioVisualization() {
        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            const microphone = this.audioContext.createMediaStreamSource(this.mediaStream);
            
            this.analyser.fftSize = 128;
            this.analyser.smoothingTimeConstant = 0.8;
            microphone.connect(this.analyser);
            
            this.animateVolumeBars();
        } catch (error) {
            console.error('Error setting up audio visualization:', error);
        }
    }

    animateVolumeBars() {
        if (!this.isListening || !this.analyser) return;

        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(dataArray);
        
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i] * dataArray[i];
        }
        const rms = Math.sqrt(sum / dataArray.length);
        const normalizedVolume = Math.min(rms / 100, 1);

        // Update volume bars
        const bars = document.querySelectorAll('.speech-mic-container.listening .bar');
        bars.forEach((bar, index) => {
            const barHeight = Math.max(0.2, normalizedVolume * (0.5 + index * 0.2));
            bar.style.transform = `scaleY(${barHeight})`;
        });

        const largeBars = document.querySelectorAll('.volume-bars-large .bar-large');
        largeBars.forEach((bar, index) => {
            const barHeight = Math.max(0.2, normalizedVolume * (0.6 + index * 0.15));
            bar.style.transform = `scaleY(${barHeight})`;
        });

        this.animationId = requestAnimationFrame(() => this.animateVolumeBars());
    }

    createListeningOverlay() {
        const existingOverlay = document.querySelector('.speech-overlay');
        if (existingOverlay) existingOverlay.remove();

        const overlay = document.createElement('div');
        overlay.className = 'speech-overlay';
        
        overlay.innerHTML = `
            <div class="speech-overlay-content">
                <div class="pulse-ring"></div>
                <div class="speech-mic-large">
                    <div class="mic-icon-large">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                            <path d="M12 1a4 4 0 0 0-4 4v7a4 4 0 0 0 8 0V5a4 4 0 0 0-4-4z" fill="currentColor"/>
                            <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                    </div>
                    <div class="volume-bars-large">
                        ${Array(5).fill('<div class="bar-large"></div>').join('')}
                    </div>
                </div>
                <div class="speech-status">Listening...</div>
                <button class="speech-stop-btn">Stop Recording</button>
            </div>
        `;

        document.body.appendChild(overlay);

        overlay.querySelector('.speech-stop-btn').addEventListener('click', () => {
            this.stopListening();
        });

        const escHandler = (e) => {
            if (e.key === 'Escape') {
                this.stopListening();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }

    stopListening() {
        this.isListening = false;

        if (this.recognition) {
            this.recognition.stop();
        }

        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        // Remove visual feedback
        document.querySelectorAll('.speech-mic-container').forEach(container => {
            container.classList.remove('listening');
        });

        document.querySelectorAll('textarea').forEach(textarea => {
            textarea.classList.remove('speech-active');
        });

        // Remove overlay
        const overlay = document.querySelector('.speech-overlay');
        if (overlay) {
            overlay.classList.add('fade-out');
            setTimeout(() => overlay.remove(), 300);
        }

        this.currentTextarea = null;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (!window.speechManager) {
        window.speechManager = new SpeechRecognitionManager();
    }
});

// Make globally available
window.speechManager = window.speechManager;