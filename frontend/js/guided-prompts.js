// Guided Story Creation System
class GuidedPrompts {
    constructor() {
        this.steps = [
            {
                id: 'challenge',
                title: 'What challenge did you face?',
                subtitle: 'Help others understand what you went through',
                placeholder: 'For example: postpartum depression, anxiety, sleep deprivation, bonding difficulties...',
                tips: [
                    'Be specific about your experience',
                    'It\'s okay to mention multiple challenges',
                    'There\'s no judgment here - share what feels right'
                ],
                validation: (value) => value.trim().length >= 10
            },
            {
                id: 'experience',
                title: 'Tell us about your experience',
                subtitle: 'What was it like day-to-day? How did it affect you?',
                placeholder: 'Describe how this challenge impacted your daily life, relationships, or well-being...',
                tips: [
                    'Include specific examples if comfortable',
                    'Mention duration if relevant',
                    'Your honesty helps others feel less alone'
                ],
                validation: (value) => value.trim().length >= 20
            },
            {
                id: 'solution',
                title: 'What helped you recover?',
                subtitle: 'Share the strategies, treatments, or support that made a difference',
                placeholder: 'What specific things helped you get through this? Therapy, medication, support groups, lifestyle changes...',
                tips: [
                    'Include both professional and personal strategies',
                    'Mention what didn\'t work if helpful',
                    'Even small things that helped matter'
                ],
                validation: (value) => value.trim().length >= 15
            },
            {
                id: 'advice',
                title: 'Your advice to others',
                subtitle: 'What would you tell someone going through the same thing?',
                placeholder: 'Words of encouragement, practical tips, or insights you wish you\'d known...',
                tips: [
                    'Speak from the heart',
                    'Share hope and encouragement',
                    'Practical advice is valuable too'
                ],
                validation: (value) => value.trim().length >= 10,
                required: false
            }
        ];
        
        this.currentStep = 0;
        this.formData = {};
        this.isActive = false;
        this.container = null;
        
        this.createGuidedModal();
    }
    
    createGuidedModal() {
        // Remove existing modal if it exists
        const existing = document.getElementById('guidedPromptsModal');
        if (existing) existing.remove();
        
        const modal = document.createElement('div');
        modal.id = 'guidedPromptsModal';
        modal.className = 'modal guided-modal';
        modal.innerHTML = `
            <div class="modal-content guided-modal-content">
                <span class="close" onclick="guidedPrompts.close()">&times;</span>
                <div class="guided-container"></div>
            </div>
        `;
        document.body.appendChild(modal);
        this.container = modal.querySelector('.guided-container');
    }
    
    start() {
        if (!currentUser) {
            showToast('Please create an account or login to share your story.', 'warning', 'Login Required');
            scrollToSection('authSection');
            return;
        }
        
        this.isActive = true;
        this.currentStep = 0;
        this.formData = {};
        this.showStep();
        openModal('guidedPromptsModal');
    }
    
    showStep() {
        const step = this.steps[this.currentStep];
        const progressPercent = ((this.currentStep + 1) / this.steps.length) * 100;
        
        this.container.innerHTML = `
            <div class="guided-step" style="animation: slideInRight 0.5s ease-out;">
                <div class="guided-progress">
                    <div class="guided-progress-bar">
                        <div class="guided-progress-fill" style="width: ${progressPercent}%"></div>
                    </div>
                    <span class="guided-progress-text">Step ${this.currentStep + 1} of ${this.steps.length}</span>
                </div>
                
                <div class="guided-content">
                    <h2>${step.title}</h2>
                    <p class="guided-subtitle">${step.subtitle}</p>
                    
                    <div class="guided-input-group">
                        <textarea 
                            id="guided-${step.id}" 
                            placeholder="${step.placeholder}"
                            rows="6"
                            style="padding-bottom: 60px;"
                        >${this.formData[step.id] || ''}</textarea>
                        <div class="character-count">
                            <span id="charCount">0</span> characters
                        </div>
                    </div>
                    
                    <div class="guided-tips">
                        <h4>💡 Helpful tips:</h4>
                        <ul>
                            ${step.tips.map(tip => `<li>${tip}</li>`).join('')}
                        </ul>
                    </div>
                </div>
                
                <div class="guided-navigation">
                    <div class="guided-nav-left">
                        ${this.currentStep > 0 ? 
                            '<button class="btn btn-secondary" onclick="guidedPrompts.previousStep()">← Previous</button>' : 
                            '<button class="btn btn-secondary" onclick="guidedPrompts.close()">Cancel</button>'
                        }
                    </div>
                    <div class="guided-nav-right">
                        ${this.currentStep < this.steps.length - 1 ? 
                            '<button class="btn btn-primary" onclick="guidedPrompts.nextStep()">Continue →</button>' : 
                            '<button class="btn btn-primary" onclick="guidedPrompts.complete()">Create Story</button>'
                        }
                    </div>
                </div>
            </div>
        `;
        
        // Setup input listeners
        const textarea = document.getElementById(`guided-${step.id}`);
        const charCount = document.getElementById('charCount');
        
        textarea.addEventListener('input', (e) => {
            charCount.textContent = e.target.value.length;
            this.formData[step.id] = e.target.value;
        });
        
        // Initial character count
        charCount.textContent = textarea.value.length;
        
        // Add microphone button
        setTimeout(() => {
            if (window.speechToText) {
                window.speechToText.addMicrophoneButton(textarea);
            }
        }, 100);
        
        // Focus on textarea after animation
        setTimeout(() => textarea.focus(), 500);
    }
    
    nextStep() {
        const step = this.steps[this.currentStep];
        const value = document.getElementById(`guided-${step.id}`).value;
        
        // Validate current step
        if (step.validation && !step.validation(value)) {
            const minLength = step.id === 'experience' ? 20 : step.id === 'solution' ? 15 : 10;
            showToast(`Please provide more detail (at least ${minLength} characters) to help others understand your experience.`, 'warning', 'More Detail Needed');
            return;
        }
        
        this.formData[step.id] = value;
        
        if (this.currentStep < this.steps.length - 1) {
            this.currentStep++;
            this.showStep();
        }
    }
    
    previousStep() {
        if (this.currentStep > 0) {
            this.currentStep--;
            this.showStep();
        }
    }
    
    complete() {
        const step = this.steps[this.currentStep];
        const value = document.getElementById(`guided-${step.id}`).value;
        
        // Validate final step if required
        if (step.validation && !step.validation(value)) {
            showToast('Please provide some advice to complete your story.', 'warning', 'Almost Done');
            return;
        }
        
        this.formData[step.id] = value;
        
        // Submit the story directly
        this.submitGuidedStory();
    }
    
    async submitGuidedStory() {
        const submitData = {
            author_name: currentUser ? currentUser.display_name : 'Anonymous',
            challenge: this.formData.challenge || '',
            experience: this.formData.experience || '',
            solution: this.formData.solution || '',
            advice: this.formData.advice || ''
        };
        
        // Show loading state
        this.container.innerHTML = `
            <div class="guided-step" style="text-align: center; padding: 4rem;">
                <div class="loading-spinner"></div>
                <h2>Creating your story...</h2>
                <p>Please wait while we process your submission.</p>
            </div>
        `;
        
        try {
            const response = await fetch(`${API_BASE_URL}/stories/submit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify(submitData)
            });

            const data = await response.json();
            
            if (data.success) {
                if (data.requires_immediate_support) {
                    this.close();
                    showCrisisResourcesModal(data.crisis_resources);
                } else {
                    showToast('Thank you for sharing your journey! Your story has been submitted and will be reviewed within 24-48 hours.', 'success', 'Story Submitted!');
                    this.close();
                }
            } else {
                showToast(data.message || 'We couldn\'t submit your story right now. Please try again.', 'error', 'Submission Error');
                this.previousStep(); // Go back to allow editing
            }
        } catch (error) {
            showToast('Connection error. Please check your internet and try again.', 'error', 'Connection Problem');
            this.previousStep(); // Go back to allow editing
        }
    }
    
    close() {
        this.isActive = false;
        closeModal('guidedPromptsModal');
    }
}

// Initialize guided prompts
let guidedPrompts;

document.addEventListener('DOMContentLoaded', function() {
    guidedPrompts = new GuidedPrompts();
});

// Function to start guided story creation
function startGuidedStory() {
    if (!guidedPrompts) {
        guidedPrompts = new GuidedPrompts();
    }
    guidedPrompts.start();
}