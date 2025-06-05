// Speech-to-Text functionality using Web Speech API
class SpeechToText {
    constructor() {
        this.recognition = null;
        this.isRecording = false;
        this.isSupported = false;
        this.currentTextarea = null;
        this.audioContext = null;
        this.analyser = null;
        this.microphone = null;
        this.animationFrame = null;
        
        this.init();
    }
    
    init() {
        // Check browser support
        window.SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        
        if (!window.SpeechRecognition) {
            console.warn('Speech Recognition not supported in this browser');
            return;
        }
        
        this.isSupported = true;
        this.setupRecognition();
    }
    
    setupRecognition() {
        this.recognition = new window.SpeechRecognition();
        this.recognition.continuous = true;
        this.recognition.interimResults = true;
        this.recognition.lang = 'en-US';
        
        this.recognition.onstart = () => {
            console.log('Speech recognition started');
        };
        
        this.recognition.onresult = (event) => {
            let finalTranscript = '';
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
                // Get current cursor position
                const cursorPos = this.currentTextarea.selectionStart;
                const currentText = this.currentTextarea.value;
                
                // Add final transcript to the textarea
                if (finalTranscript) {
                    const newText = currentText + finalTranscript;
                    this.currentTextarea.value = newText;
                    this.currentTextarea.setSelectionRange(newText.length, newText.length);
                    
                    // Trigger input event for character count updates
                    this.currentTextarea.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
        };
        
        this.recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            this.stopRecording();
            
            const errorMessages = {
                'network': 'Network error. Please check your connection.',
                'not-allowed': 'Microphone access denied. Please allow microphone access.',
                'no-speech': 'No speech detected. Please try again.',
                'audio-capture': 'Microphone not found. Please check your audio settings.'
            };
            
            showToast(errorMessages[event.error] || 'Speech recognition error. Please try again.', 'error', 'Voice Input Error');
        };
        
        this.recognition.onend = () => {
            this.stopRecording();
        };
    }
    
    async setupAudioVisualization() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            this.analyser = this.audioContext.createAnalyser();
            this.microphone = this.audioContext.createMediaStreamSource(stream);
            
            this.analyser.fftSize = 256;
            this.microphone.connect(this.analyser);
            
            this.startVisualization();
        } catch (error) {
            console.error('Error setting up audio visualization:', error);
        }
    }
    
    startVisualization() {
        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        const bars = document.querySelectorAll('.audio-bar');
        
        const animate = () => {
            if (!this.isRecording) return;
            
            this.analyser.getByteFrequencyData(dataArray);
            
            // Calculate average volume
            const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
            const normalizedVolume = average / 255;
            
            // Update bars based on volume
            bars.forEach((bar, index) => {
                const barHeight = Math.max(20, normalizedVolume * 60 + Math.random() * 20);
                bar.style.height = `${barHeight}px`;
                bar.style.backgroundColor = normalizedVolume > 0.3 ? 
                    `hsl(${210 + index * 30}, 70%, ${50 + normalizedVolume * 30}%)` : 
                    'rgba(168, 216, 234, 0.6)';
            });
            
            this.animationFrame = requestAnimationFrame(animate);
        };
        
        animate();
    }
    
    startRecording(textarea) {
        if (!this.isSupported) {
            showToast('Speech recognition is not supported in this browser. Please use Chrome, Edge, or Safari.', 'warning', 'Browser Not Supported');
            return;
        }
        
        if (this.isRecording) {
            this.stopRecording();
            return;
        }
        
        this.currentTextarea = textarea;
        this.isRecording = true;
        
        // Show recording overlay
        this.showRecordingOverlay();
        
        // Start speech recognition
        this.recognition.start();
        
        // Setup audio visualization
        this.setupAudioVisualization();
    }
    
    stopRecording() {
        if (!this.isRecording) return;
        
        this.isRecording = false;
        
        // Stop speech recognition
        if (this.recognition) {
            this.recognition.stop();
        }
        
        // Stop audio visualization
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
        
        // Clean up audio context
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
        
        // Hide recording overlay
        this.hideRecordingOverlay();
        
        this.currentTextarea = null;
    }
    
    showRecordingOverlay() {
        // Remove existing overlay
        const existingOverlay = document.querySelector('.speech-recording-overlay');
        if (existingOverlay) existingOverlay.remove();
        
        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'speech-recording-overlay';
        overlay.innerHTML = `
            <div class="recording-content">
                <div class="microphone-container">
                    <div class="microphone-icon recording">
                        <svg viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                            <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
                        </svg>
                    </div>
                    <div class="audio-visualization">
                        <div class="audio-bar"></div>
                        <div class="audio-bar"></div>
                        <div class="audio-bar"></div>
                        <div class="audio-bar"></div>
                        <div class="audio-bar"></div>
                    </div>
                </div>
                <div class="recording-text">
                    <h3>Listening...</h3>
                    <p>Speak clearly into your microphone</p>
                    <button class="stop-recording-btn" onclick="speechToText.stopRecording()">
                        Stop Recording
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(overlay);
        
        // Trigger animation
        setTimeout(() => overlay.classList.add('active'), 50);
    }
    
    hideRecordingOverlay() {
        const overlay = document.querySelector('.speech-recording-overlay');
        if (overlay) {
            overlay.classList.remove('active');
            setTimeout(() => overlay.remove(), 300);
        }
    }
    
    addMicrophoneButton(textarea) {
        if (!this.isSupported) return;
        
        // Don't add if already exists
        if (textarea.parentElement.querySelector('.microphone-btn')) return;
        
        const micBtn = document.createElement('button');
        micBtn.type = 'button';
        micBtn.className = 'microphone-btn';
        micBtn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
            </svg>
        `;
        
        micBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.startRecording(textarea);
        });
        
        // Position the button
        const container = textarea.parentElement;
        container.style.position = 'relative';
        container.appendChild(micBtn);
    }
}

// Initialize speech-to-text when DOM is loaded
let speechToText;

document.addEventListener('DOMContentLoaded', function() {
    speechToText = new SpeechToText();
    
    // Auto-add microphone buttons to existing textareas
    document.querySelectorAll('textarea').forEach(textarea => {
        speechToText.addMicrophoneButton(textarea);
    });
    
    // Observer for dynamically added textareas
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) { // Element node
                    const textareas = node.querySelectorAll ? node.querySelectorAll('textarea') : [];
                    textareas.forEach(textarea => {
                        speechToText.addMicrophoneButton(textarea);
                    });
                    
                    if (node.tagName === 'TEXTAREA') {
                        speechToText.addMicrophoneButton(node);
                    }
                }
            });
        });
    });
    
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

// Export for global access
window.speechToText = speechToText;