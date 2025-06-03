// Updated tour.js - Conditional tour based on user state
class InteractiveTour {
    constructor() {
        this.currentStep = 0;
        this.isActive = false;
        this.overlay = null;
        this.tooltip = null;
        this.steps = [];
        
        this.createTourElements();
    }
    
    getStepsForUser() {
        const baseSteps = [
            {
                target: '.logo',
                title: 'Welcome to Postnatal Stories',
                content: 'A safe space where parents share their recovery journeys and find support.',
                position: 'bottom'
            },
            {
                target: '.hero h1',
                title: 'You\'re Not Alone',
                content: 'Connect with a community that understands your journey through parenthood.',
                position: 'bottom'
            },
            {
                target: '.cta-buttons .btn-primary',
                title: 'Share Your Story',
                content: 'Help others by sharing your experiences and recovery journey.',
                position: 'bottom'
            },
            {
                target: '.search-input',
                title: 'Find Similar Experiences',
                content: 'Search for stories that match what you\'re going through right now.',
                position: 'bottom'
            },
            {
                target: '.crisis-support-section',
                title: 'Get Immediate Help',
                content: 'Access crisis support resources available 24/7 when you need them most.',
                position: 'top'
            }
        ];

        // Add moderation step for admins/moderators
        if (currentUser && (currentUser.role === 'admin' || currentUser.role === 'moderator')) {
            baseSteps.push({
                target: '#moderationSection',
                title: 'Story Moderation',
                content: 'Review and approve community stories before they go live. Keep our community safe and supportive.',
                position: 'top'
            });
        }

        return baseSteps;
    }
    
    createTourElements() {
        // Remove existing elements
        const existingOverlay = document.querySelector('.tour-overlay');
        const existingTooltip = document.querySelector('.tour-tooltip');
        if (existingOverlay) existingOverlay.remove();
        if (existingTooltip) existingTooltip.remove();
        
        this.overlay = document.createElement('div');
        this.overlay.className = 'tour-overlay';
        
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'tour-tooltip';
        
        document.body.appendChild(this.overlay);
        document.body.appendChild(this.tooltip);
    }
    
    start() {
        if (this.isActive) return;
        
        // Get steps based on current user
        this.steps = this.getStepsForUser();
        this.isActive = true;
        this.currentStep = 0;
        this.showStep();
        
        localStorage.setItem('tourCompleted', 'false');
    }
    
    showStep() {
        const step = this.steps[this.currentStep];
        const target = document.querySelector(step.target);
        
        if (!target) {
            // Skip missing targets
            if (this.currentStep < this.steps.length - 1) {
                this.currentStep++;
                setTimeout(() => this.showStep(), 100);
            } else {
                this.end();
            }
            return;
        }
        
        this.clearHighlight();
        
        target.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center',
            inline: 'center'
        });
        
        setTimeout(() => {
            this.overlay.style.display = 'block';
            this.createSpotlight(target);
            this.positionTooltip(target, step);
            this.tooltip.style.display = 'block';
            target.classList.add('tour-highlight');
        }, 600);
    }
    
    createSpotlight(target) {
        const rect = target.getBoundingClientRect();
        const padding = 15;
        
        this.overlay.style.clipPath = `polygon(
            0% 0%, 
            0% 100%, 
            ${rect.left - padding}px 100%, 
            ${rect.left - padding}px ${rect.top - padding}px, 
            ${rect.right + padding}px ${rect.top - padding}px, 
            ${rect.right + padding}px ${rect.bottom + padding}px, 
            ${rect.left - padding}px ${rect.bottom + padding}px, 
            ${rect.left - padding}px 100%, 
            100% 100%, 
            100% 0%
        )`;
    }
    
    positionTooltip(target, step) {
        const rect = target.getBoundingClientRect();
        
        this.tooltip.innerHTML = `
            <div class="tour-content">
                <div class="tour-header">
                    <h3>${step.title}</h3>
                    <button class="tour-close" onclick="tour.end()">×</button>
                </div>
                <p>${step.content}</p>
                <div class="tour-navigation">
                    <div class="tour-progress">
                        <span>${this.currentStep + 1} of ${this.steps.length}</span>
                        <div class="tour-progress-bar">
                            <div class="tour-progress-fill" style="width: ${((this.currentStep + 1) / this.steps.length) * 100}%"></div>
                        </div>
                    </div>
                    <div class="tour-buttons">
                        ${this.currentStep > 0 ? '<button class="tour-btn tour-btn-secondary" onclick="tour.previous()">← Previous</button>' : ''}
                        ${this.currentStep < this.steps.length - 1 ? 
                            '<button class="tour-btn tour-btn-primary" onclick="tour.next()">Next →</button>' : 
                            '<button class="tour-btn tour-btn-primary" onclick="tour.complete()">Finish Tour</button>'
                        }
                    </div>
                </div>
            </div>
        `;
        
        // Position tooltip
        if (step.position === 'bottom') {
            this.tooltip.style.top = (rect.bottom + 20) + 'px';
            this.tooltip.style.left = Math.max(10, rect.left + rect.width / 2 - 175) + 'px';
            this.tooltip.style.transform = 'none';
        } else {
            this.tooltip.style.top = (rect.top - 20) + 'px';
            this.tooltip.style.left = Math.max(10, rect.left + rect.width / 2 - 175) + 'px';
            this.tooltip.style.transform = 'translateY(-100%)';
        }
    }
    
    next() {
        this.clearHighlight();
        if (this.currentStep < this.steps.length - 1) {
            this.currentStep++;
            setTimeout(() => this.showStep(), 300);
        } else {
            this.complete();
        }
    }
    
    previous() {
        this.clearHighlight();
        if (this.currentStep > 0) {
            this.currentStep--;
            setTimeout(() => this.showStep(), 300);
        }
    }
    
    complete() {
        this.cleanup();
        localStorage.setItem('tourCompleted', 'true');
        
        // Smooth scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        setTimeout(() => {
            showToast('Tour completed! Welcome to our community.', 'success', 'Welcome!');
        }, 800);
    }
    
    end() {
        this.cleanup();
        showToast('Tour cancelled.', 'warning', 'Tour Cancelled');
    }
    
    cleanup() {
        this.isActive = false;
        this.clearHighlight();
        this.overlay.style.display = 'none';
        this.tooltip.style.display = 'none';
        this.overlay.style.clipPath = '';
    }
    
    clearHighlight() {
        document.querySelectorAll('.tour-highlight').forEach(el => {
            el.classList.remove('tour-highlight');
        });
    }
    
    shouldShowTour() {
        return !localStorage.getItem('tourCompleted') || localStorage.getItem('tourCompleted') === 'false';
    }
}

let tour;

function startTour() {
    if (!currentUser) {
        showToast('Please login first to take the full tour.', 'warning', 'Login Required');
        scrollToSection('authSection');
        return;
    }
    
    if (!tour) tour = new InteractiveTour();
    tour.start();
}