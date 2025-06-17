// Enhanced Speech Recognition System with Live Transcription Display
class SpeechRecognitionManager {
    constructor() {
        this.recognition = null;
        this.isListening = false;
        this.currentTextarea = null;
        this.audioContext = null;
        this.analyser = null;
        this.mediaStream = null;
        this.animationId = null;
        this.volumeRings = [];
        this.transcriptionElement = null; // Add this for live transcription
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
            this.updateTranscriptionDisplay('', ''); // Clear transcription display
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

            // Update live transcription display
            this.updateTranscriptionDisplay(finalTranscript, interimTranscript);

            if (this.currentTextarea) {
                const existingText = this.currentTextarea.dataset.originalText || '';
                this.currentTextarea.value = existingText + finalTranscript + interimTranscript;
                
                // Trigger input event for character count updates
                this.currentTextarea.dispatchEvent(new Event('input', { bubbles: true }));
            }
        };

        this.recognition.onend = () => {
            if (this.currentTextarea && finalTranscript) {
                this.currentTextarea.dataset.originalText = this.currentTextarea.value;
            }
            
            // FIX: Ensure button resets when recognition ends
            if (this.currentGuidedButton) {
                updateGuidedSpeechButton(this.currentGuidedButton, false);
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

    // NEW: Method to update live transcription display
    updateTranscriptionDisplay(finalText, interimText) {
        if (!this.transcriptionElement) return;

        const displayText = finalText + interimText;
        
        if (displayText.trim()) {
            this.transcriptionElement.innerHTML = `
                <div class="transcription-content">
                    <span class="final-text">${finalText}</span><span class="interim-text">${interimText}</span>
                </div>
            `;
            this.transcriptionElement.classList.add('visible');
        } else {
            this.transcriptionElement.innerHTML = `
                <div class="transcription-placeholder">
                    Start speaking to see your words appear here...
                </div>
            `;
            this.transcriptionElement.classList.remove('visible');
        }
    }

    addMicrophoneButtonsToTextareas() {
        // Only enhance textareas that are NOT in guided prompts
        document.querySelectorAll('textarea:not([id^="guided-"])').forEach(textarea => {
            this.enhanceTextarea(textarea);
        });

        // Watch for new textareas (excluding guided ones)
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) {
                        const textareas = node.querySelectorAll ? node.querySelectorAll('textarea:not([id^="guided-"])') : [];
                        textareas.forEach(textarea => this.enhanceTextarea(textarea));
                        
                        if (node.tagName === 'TEXTAREA' && !node.id.startsWith('guided-')) {
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
        // Store reference for guided prompts
        textarea.speechManager = this;
    }

    async startListening(textarea, micContainer) {
        try {
            // Store original text
            textarea.dataset.originalText = textarea.value;
            this.currentTextarea = textarea;

            // Setup audio visualization
            await this.setupAudioVisualization();

            // Start recognition
            this.recognition.start();
            this.isListening = true;

            // Add visual feedback with smooth transitions
            setTimeout(() => {
                micContainer.classList.add('listening');
                textarea.classList.add('speech-active');
            }, 100);

            // Create beautiful overlay with transcription
            this.createListeningOverlay();  

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
                    autoGainControl: true,
                    sampleRate: 44100
                }
            });
            
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            const microphone = this.audioContext.createMediaStreamSource(this.mediaStream);
            
            this.analyser.fftSize = 256;
            this.analyser.smoothingTimeConstant = 0.8;
            microphone.connect(this.analyser);
            
            // Start audio visualization
            this.animateAudioVisualization();
        } catch (error) {
            console.error('Error setting up audio visualization:', error);
        }
    }

    animateAudioVisualization() {
        if (!this.isListening || !this.analyser) return;

        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(dataArray);
        
        // Calculate volume level
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i] * dataArray[i];
        }
        const rms = Math.sqrt(sum / dataArray.length);
        const normalizedVolume = Math.min(rms / 128, 1);

        // Update volume rings opacity based on volume
        const rings = document.querySelectorAll('.speech-mic-container.listening .volume-ring');
        rings.forEach((ring, index) => {
            const threshold = (index + 1) * 0.25;
            ring.style.opacity = normalizedVolume > threshold ? '0.8' : '0.2';
        });

        // Update large volume bars in overlay
        const largeBars = document.querySelectorAll('.volume-bars-large .bar-large');
        largeBars.forEach((bar, index) => {
            const minScale = 0.3;
            const maxScale = 1.5;
            const barHeight = minScale + (normalizedVolume * (maxScale - minScale) * (0.8 + index * 0.1));
            bar.style.transform = `scaleY(${barHeight})`;
            bar.style.opacity = 0.6 + (normalizedVolume * 0.4);
        });

        // Continue animation
        this.animationId = requestAnimationFrame(() => this.animateAudioVisualization());
    }

    // UPDATED: Enhanced overlay with live transcription
    createListeningOverlay() {
        // Remove existing overlay
        const existingOverlay = document.querySelector('.speech-overlay');
        if (existingOverlay) existingOverlay.remove();

        const overlay = document.createElement('div');
        overlay.className = 'speech-overlay';
        
        overlay.innerHTML = `
            <div class="speech-overlay-content">
                <!-- Live Transcription Display Above Mic -->
                <div class="live-transcription" id="liveTranscription">
                    <div class="transcription-placeholder">
                        Start speaking to see your words appear here...
                    </div>
                </div>
                
                <div class="speech-mic-large">
                    <div class="mic-icon-large">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
                            <path d="M12 1a4 4 0 0 0-4 4v7a4 4 0 0 0 8 0V5a4 4 0 0 0-4-4z" fill="currentColor"/>
                            <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                        </svg>
                    </div>
                    <div class="volume-bars-large">
                        <div class="bar-large"></div>
                        <div class="bar-large"></div>
                        <div class="bar-large"></div>
                        <div class="bar-large"></div>
                        <div class="bar-large"></div>
                    </div>
                </div>
                
                <div class="speech-status">Listening for your voice...</div>
                
                <button class="speech-stop-btn">
                    <span style="margin-right: 8px;">⏹</span>
                    Stop Recording
                </button>
            </div>
        `;

        // Store reference to transcription element
        document.body.appendChild(overlay);
        this.transcriptionElement = overlay.querySelector('#liveTranscription');

        // Add event listeners
        overlay.querySelector('.speech-stop-btn').addEventListener('click', () => {
            this.stopListening();
        });

        // Close on escape key
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                this.stopListening();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);

        // Prevent clicks outside from closing (intentional UX choice)
        overlay.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }

    stopListening() {
        this.isListening = false;

        // Stop recognition
        if (this.recognition) {
            this.recognition.stop();
        }

        // Stop audio visualization
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }

        // Clean up audio resources
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        if (this.audioContext && this.audioContext.state !== 'closed') {
            this.audioContext.close();
            this.audioContext = null;
        }

        // Remove visual feedback with smooth transitions
        const micContainers = document.querySelectorAll('.speech-mic-container');
        micContainers.forEach(container => {
            container.classList.remove('listening');
        });

        const textareas = document.querySelectorAll('textarea');
        textareas.forEach(textarea => {
            textarea.classList.remove('speech-active');
        });

        // Remove overlay with fade animation
        const overlay = document.querySelector('.speech-overlay');
        if (overlay) {
            overlay.classList.add('fade-out');
            setTimeout(() => {
                if (overlay.parentNode) {
                    overlay.remove();
                }
            }, 400);
        }

        this.currentTextarea = null;
        this.transcriptionElement = null; // Clear reference

        // FIX: Reset guided button state properly
        if (this.currentGuidedButton) {
            updateGuidedSpeechButton(this.currentGuidedButton, false);
            this.currentGuidedButton = null;
        }
    }

    async startGuidedListening(textarea, button) {
        try {
            textarea.dataset.originalText = textarea.value;
            this.currentTextarea = textarea;
            this.currentGuidedButton = button;

            await this.setupAudioVisualization();
            this.recognition.start();
            this.isListening = true;

            updateGuidedSpeechButton(button, true);
            textarea.classList.add('speech-active');
            this.createListeningOverlay();

        } catch (error) {
            console.error('Error starting speech recognition:', error);
            showToast('Unable to access microphone. Please check your browser settings.', 'error', 'Microphone Error');
        }
    }
}

// Initialize enhanced speech manager
document.addEventListener('DOMContentLoaded', () => {
    if (!window.speechManager) {
        window.speechManager = new SpeechRecognitionManager();
    }
});

// Make globally available
window.speechManager = window.speechManager;

// Helper function for guided prompts
function handleGuidedSpeech(button) {
    if (!window.speechManager) {
        showToast('Speech recognition not available', 'error', 'Feature Unavailable');
        return;
    }
    
    if (!window.speechManager.recognition) {
        showToast('Speech recognition is not supported in this browser. Please try Chrome, Edge, or Safari.', 'warning', 'Browser Not Supported');
        return;
    }
    
    // Find the associated textarea
    const container = button.closest('.guided-step');
    const textarea = container ? container.querySelector('textarea') : null;
    
    if (textarea) {
        // Check if currently listening to this textarea
        if (window.speechManager.isListening && window.speechManager.currentTextarea === textarea) {
            window.speechManager.stopListening();
            updateGuidedSpeechButton(button, false);
        } else {
            window.speechManager.startGuidedListening(textarea, button);
        }
    } else {
        showToast('No input field found', 'error', 'Input Error');
    }
}

function updateGuidedSpeechButton(button, isListening) {
    const icon = button.querySelector('.guided-speech-icon');
    const text = button.querySelector('span');
    const volumeBars = button.querySelector('.volume-bars');
    
    if (isListening) {
        button.classList.add('listening');
        icon.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M12 1a4 4 0 0 0-4 4v7a4 4 0 0 0 8 0V5a4 4 0 0 0-4-4z" fill="currentColor"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
        `;
        text.textContent = 'Stop Recording';
        volumeBars.style.opacity = '1';
    } else {
        button.classList.remove('listening');
        icon.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M12 1a4 4 0 0 0-4 4v7a4 4 0 0 0 8 0V5a4 4 0 0 0-4-4z" fill="currentColor"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
        `;
        text.textContent = 'Voice Input';
        volumeBars.style.opacity = '0';
    }
}