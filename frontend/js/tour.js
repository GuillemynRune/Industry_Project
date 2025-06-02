// Interactive Tour System
class InteractiveTour {
    constructor() {
        this.steps = [
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
                target: '.btn-primary',
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
        
        this.currentStep = 0;
        this.isActive = false;
        this.overlay = null;
        this.tooltip = null;
        
        this.createTourElements();
    }
    
    createTourElements() {
        // Create overlay
        this.overlay = document.createElement('div');
        this.overlay.className = 'tour-overlay';
        
        // Create tooltip
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'tour-tooltip';
        
        document.body.appendChild(this.overlay);
        document.body.appendChild(this.tooltip);
    }
    
    start() {
        if (this.isActive) return;
        
        this.isActive = true;
        this.currentStep = 0;
        this.showStep();
        
        // Track tour completion
        localStorage.setItem('tourCompleted', 'false');
    }
    
    showStep() {
        const step = this.steps[this.currentStep];
        const target = document.querySelector(step.target);
        
        if (!target) {
            this.next();
            return;
        }
        
        // Show overlay
        this.overlay.style.display = 'block';
        this.createSpotlight(target);
        
        // Position and show tooltip
        this.positionTooltip(target, step);
        this.tooltip.style.display = 'block';
        
        // Add pulse animation to target
        target.classList.add('tour-highlight');
    }
    
    createSpotlight(target) {
        const rect = target.getBoundingClientRect();
        const padding = 10;
        
        // Clear previous spotlight
        this.overlay.innerHTML = '';
        
        // Create spotlight hole
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
        const tooltip = this.tooltip;
        
        tooltip.innerHTML = `
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
                            '<button class="tour-btn tour-btn-primary" onclick="tour.end()">Finish Tour</button>'
                        }
                    </div>
                </div>
            </div>
        `;
        
        // Position tooltip
        if (step.position === 'bottom') {
            tooltip.style.top = (rect.bottom + 20) + 'px';
            tooltip.style.left = (rect.left + rect.width / 2) + 'px';
            tooltip.style.transform = 'translateX(-50%)';
        } else {
            tooltip.style.top = (rect.top - 20) + 'px';
            tooltip.style.left = (rect.left + rect.width / 2) + 'px';
            tooltip.style.transform = 'translateX(-50%) translateY(-100%)';
        }
        
        // Ensure tooltip is within viewport
        const tooltipRect = tooltip.getBoundingClientRect();
        if (tooltipRect.left < 10) {
            tooltip.style.left = '10px';
            tooltip.style.transform = 'none';
        } else if (tooltipRect.right > window.innerWidth - 10) {
            tooltip.style.left = (window.innerWidth - tooltipRect.width - 10) + 'px';
            tooltip.style.transform = 'none';
        }
    }
    
    next() {
        this.clearHighlight();
        if (this.currentStep < this.steps.length - 1) {
            this.currentStep++;
            setTimeout(() => this.showStep(), 300);
        } else {
            this.end();
        }
    }
    
    previous() {
        this.clearHighlight();
        if (this.currentStep > 0) {
            this.currentStep--;
            setTimeout(() => this.showStep(), 300);
        }
    }
    
    clearHighlight() {
        document.querySelectorAll('.tour-highlight').forEach(el => {
            el.classList.remove('tour-highlight');
        });
    }
    
    end() {
        this.isActive = false;
        this.clearHighlight();
        this.overlay.style.display = 'none';
        this.tooltip.style.display = 'none';
        
        // Mark tour as completed
        localStorage.setItem('tourCompleted', 'true');
        
        showToast('Tour completed! Explore the platform and share your story when you\'re ready.', 'success', 'Welcome!');
    }
    
    // Check if user should see tour
    shouldShowTour() {
        return !localStorage.getItem('tourCompleted') || localStorage.getItem('tourCompleted') === 'false';
    }
}

// Initialize tour
let tour;

// Auto-start tour for new users
document.addEventListener('DOMContentLoaded', function() {
    tour = new InteractiveTour();
    
    // Start tour after page loads for new users
    setTimeout(() => {
        if (tour.shouldShowTour() && !currentUser) {
            tour.start();
        }
    }, 2000);
});

// Manual tour trigger
function startTour() {
    if (!tour) tour = new InteractiveTour();
    tour.start();
}