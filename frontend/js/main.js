// Main JavaScript - Core functionality
const API_BASE_URL = 'http://localhost:8000';
let currentUser = null;
let authToken = null;

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeAuth();
    loadApprovedStories();
    
    // Initialize new systems
    if (typeof InteractiveTour !== 'undefined') {
        tour = new InteractiveTour();
    }
    if (typeof GuidedPrompts !== 'undefined') {
        guidedPrompts = new GuidedPrompts();
    }
    themeManager = new ThemeManager();
    
    // Add smooth scroll to nav links
    document.querySelectorAll('.nav-links a[href^="#"]').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const targetSection = document.getElementById(targetId);
            
            if (targetSection) {
                targetSection.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

// Toast Notification System
function showToast(message, type = 'success', title = '') {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }

    const configs = {
        success: { title: title || 'Success!', icon: '✓', duration: 4000 },
        error: { title: title || 'Oops!', icon: '!', duration: 6000 },
        warning: { title: title || 'Heads up!', icon: '⚠', duration: 5000 }
    };
    
    const config = configs[type] || configs.success;
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    toast.innerHTML = `
        <div class="toast-icon">${config.icon}</div>
        <div class="toast-content">
            <div class="toast-title">${config.title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="closeToast(this)">×</button>
    `;
    
    container.appendChild(toast);
    setTimeout(() => toast.parentNode && closeToast(toast.querySelector('.toast-close')), config.duration);
}

function closeToast(closeBtn) {
    const toast = closeBtn.closest('.toast');
    toast.classList.add('toast-exit');
    setTimeout(() => toast.parentNode && toast.remove(), 400);
}

// Modal utilities
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
    document.body.style.overflow = 'auto';
}

// Navigation utilities
function scrollToSection(sectionId) {
    document.getElementById(sectionId).scrollIntoView({ 
        behavior: 'smooth',
        block: 'start'
    });
}

// Info modals
function showTerms() {
    alert('Terms of Service: By using this platform, you agree to use it respectfully and understand that content is user-generated and not professional medical advice. You must be 18 or older to use this service.');
}

function showPrivacy() {
    alert('Privacy Policy: We protect your personal information and only use it to provide our services. Stories are anonymous by default. We do not share personal data with third parties.');
}

function showCrisisResources() {
    openModal('crisisModal');
}

// Date utility
function getTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffTime = Math.abs(now - date);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    
    if (diffDays === 1) return '1 day ago';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} week${Math.floor(diffDays / 7) > 1 ? 's' : ''} ago`;
    return `${Math.floor(diffDays / 30)} month${Math.floor(diffDays / 30) > 1 ? 's' : ''} ago`;
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modals = document.getElementsByClassName('modal');
    for (let modal of modals) {
        if (event.target === modal) {
            modal.style.display = 'none';
            document.body.style.overflow = 'auto';
        }
    }
}

// Dark Mode System
class ThemeManager {
    constructor() {
        this.currentTheme = localStorage.getItem('theme') || 'light';
        this.init();
    }
    
    init() {
        this.applyTheme(this.currentTheme);
        this.createToggleButton();
    }
    
    createToggleButton() {
        const button = document.createElement('button');
        button.className = 'theme-toggle';
        button.innerHTML = this.currentTheme === 'dark' ? '☀️' : '🌙';
        button.onclick = () => this.toggleTheme();
        document.body.appendChild(button);
    }
    
    toggleTheme() {
        this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(this.currentTheme);
        localStorage.setItem('theme', this.currentTheme);
        document.querySelector('.theme-toggle').innerHTML = this.currentTheme === 'dark' ? '☀️' : '🌙';
    }
    
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
    }
}