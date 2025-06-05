// Enhanced Speech Recognition System - Fixed Version
class SpeechRecognitionManager {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.currentTextarea = null;
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.dataArray = null;
        this.animationId = null;
        this.mediaStream = null;
        this.init();
    }

    init() {
        // Check browser support
        const hasNativeSpeech = ('webkitSpeechRecognition' in window) || ('SpeechRecognition' in window);
        
        if (!hasNativeSpeech) {
            console.warn('Speech Recognition not supported in this browser');
            this.addMicrophoneButtonsToTextareas();
            return;
        }

        // Initialize Speech Recognition
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = new SpeechRecognition();
        
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';

        this.setupRecognitionEvents();
        this.addMicrophoneButtonsToTextareas();
    }

    setupRecognitionEvents() {
        let finalTranscript = '';
        let interimTranscript = '';

        this.recognition.onstart = () => {
            console.log('Speech recognition started');
            finalTranscript = '';
            interimTranscript = '';
        };

        this.recognition.onresult = (event) => {
            interimTranscript = '';
            
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
                const fullText = existingText + finalTranscript + interimTranscript;
                this.currentTextarea.value = fullText;
                
                // Trigger input event for character counting
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
            if (typeof showToast !== 'undefined') {
                showToast(message, 'error', 'Speech Recognition Error');
            } else {
                alert(message);
            }
        };
    }

    addMicrophoneButtonsToTextareas() {
        // Add to existing textareas
        document.querySelectorAll('textarea').forEach(textarea => {
            this.enhanceTextarea(textarea);
        });

        // Watch for new textareas
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

    createListeningOverlay(textarea, micContainer) {
            // Remove existing overlay
            const existingOverlay = document.querySelector('.speech-overlay');
            if (existingOverlay) existingOverlay.remove();

            const overlay = document.createElement('div');
            overlay.className = 'speech-overlay';
            
            overlay.innerHTML = `
                <div class="speech-overlay-content">
                    <div class="pulse-ring"></div>
                    <div class="speech-mic-large">
                        <div class="mic-icon-large">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                                <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                                <line x1="12" y1="19" x2="12" y2="23"></line>
                                <line x1="8" y1="23" x2="16" y2="23"></line>
                            </svg>
                        </div>
                    </div>
                    <div class="speech-status"> Listening...</div>
                    <button class="speech-stop-btn" onclick="speechManager.stopListening()">Stop Recording</button>
                </div>
            `;

            document.body.appendChild(overlay);

            // ESC key handler
            const escHandler = (e) => {
                if (e.key === 'Escape') {
                    this.stopListening();
                    document.removeEventListener('keydown', escHandler);
                }
            };
            document.addEventListener('keydown', escHandler);
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
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                        <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                        <line x1="12" y1="19" x2="12" y2="23"></line>
                        <line x1="8" y1="23" x2="16" y2="23"></line>
                    </svg>
                </div>
                <span class="voice-text">Voice</span>
                <div class="volume-bars">
                    <div class="bar"></div>
                    <div class="bar"></div>
                    <div class="bar"></div>
                </div>
            </button>
        `;

        // Position the container
        const textareaParent = textarea.parentNode;
        textareaParent.style.position = 'relative';
        textareaParent.appendChild(micContainer);

        // Add click handler
        const micBtn = micContainer.querySelector('.speech-mic-btn');
        micBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (!isSupported) {
                const message = 'Speech recognition is not supported in this browser. Please try Chrome, Edge, or Safari.';
                if (typeof showToast !== 'undefined') {
                    showToast(message, 'warning', 'Browser Not Supported');
                } else {
                    alert(message);
                }
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
                // Store original text
                textarea.dataset.originalText = textarea.value;
                this.currentTextarea = textarea;

                // Request microphone permission first
                await navigator.mediaDevices.getUserMedia({ audio: true });

                // Start recognition
                this.recognition.start();
                this.isListening = true;

                // Add visual feedback
                micContainer.classList.add('listening');
                textarea.classList.add('speech-active');

                // Create full-screen overlay with animation
                this.createListeningOverlay(textarea, micContainer);

                // Setup audio visualization
                this.setupAudioVisualization();

                if (typeof showToast !== 'undefined') {
                    showToast('Listening... Speak now!', 'success', 'Voice Input Active');
                }

            } catch (error) {
                console.error('Error starting speech recognition:', error);
                const message = 'Unable to access microphone. Please check your browser settings and try again.';
                if (typeof showToast !== 'undefined') {
                    showToast(message, 'error', 'Microphone Error');
                } else {
                    alert(message);
                }
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
            this.microphone = this.audioContext.createMediaStreamSource(this.mediaStream);
            
            this.analyser.fftSize = 128;
            this.analyser.smoothingTimeConstant = 0.8;
            this.microphone.connect(this.analyser);
            
            const bufferLength = this.analyser.frequencyBinCount;
            this.dataArray = new Uint8Array(bufferLength);
            
            this.animateVolumeBars();
        } catch (error) {
            console.error('Error setting up audio visualization:', error);
        }
    }

    animateVolumeBars() {
            if (!this.isListening || !this.analyser) return;

            this.analyser.getByteFrequencyData(this.dataArray);
            
            // Calculate volume level
            let sum = 0;
            for (let i = 0; i < this.dataArray.length; i++) {
                sum += this.dataArray[i] * this.dataArray[i];
            }
            const rms = Math.sqrt(sum / this.dataArray.length);
            const normalizedVolume = Math.min(rms / 100, 1);

            // Update small volume bars (in button)
            const bars = document.querySelectorAll('.speech-mic-container.listening .bar');
            bars.forEach((bar, index) => {
                const barHeight = Math.max(0.2, normalizedVolume * (0.5 + index * 0.3));
                bar.style.transform = `scaleY(${barHeight})`;
            });

            // Update large volume bars (in overlay)
            const largeBars = document.querySelectorAll('.volume-bars-large .bar-large');
            largeBars.forEach((bar, index) => {
                const barHeight = Math.max(0.2, normalizedVolume * (0.6 + index * 0.15));
                bar.style.transform = `scaleY(${barHeight})`;
            });

            this.animationId = requestAnimationFrame(() => this.animateVolumeBars());
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

            if (this.audioContext && this.audioContext.state !== 'closed') {
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

            // Remove overlay with fade animation
            const overlay = document.querySelector('.speech-overlay');
            if (overlay) {
                overlay.classList.add('fade-out');
                setTimeout(() => overlay.remove(), 300);
            }

            this.currentTextarea = null;
        }
}

// Initialize when DOM is ready
let speechManager;

document.addEventListener('DOMContentLoaded', () => {
    speechManager = new SpeechRecognitionManager();
});

// Global function for guided prompts
function handleGuidedSpeech(button) {
    const textarea = document.querySelector('#guided-' + document.querySelector('.guided-step').getAttribute('data-step') + ' textarea') || 
                    document.querySelector('.guided-input-group textarea');
    
    if (textarea && speechManager) {
        const micContainer = button.closest('.guided-nav-center') || button.parentNode;
        
        if (speechManager.isListening && speechManager.currentTextarea === textarea) {
            speechManager.stopListening();
        } else {
            speechManager.startListening(textarea, micContainer);
        }
    }
}

// Make globally available
window.speechManager = speechManager;
window.handleGuidedSpeech = handleGuidedSpeech;