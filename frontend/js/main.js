// Main JavaScript - Core functionality with FIXED API_BASE_URL
// FIXED: Ensure API_BASE_URL is correctly set
const API_BASE_URL = 'http://localhost:8000';

// Debug the API URL immediately
console.log('🔧 API_BASE_URL Configuration:');
console.log('🔧 window.location:', window.location);
console.log('🔧 window.location.port:', window.location.port);
console.log('🔧 Final API_BASE_URL:', API_BASE_URL);

let currentUser = null;
let authToken = null;

// Initialize app
document.addEventListener('DOMContentLoaded', async function() {
    console.log('🚀 App initializing...');
    console.log('🔧 Confirming API_BASE_URL during init:', API_BASE_URL);
    
    initializeAuth();
    
    // Wait a moment for the backend to be ready, then load stories
    setTimeout(async () => {
        await loadApprovedStories();
    }, 1000);
    
    // Initialize new systems
    if (typeof GuidedPrompts !== 'undefined') {
        guidedPrompts = new GuidedPrompts();
    }
    
    // Initialize theme manager
    if (typeof ThemeManager !== 'undefined') {
        themeManager = new ThemeManager();
    }

    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        console.log('Speech recognition not supported - microphone buttons will be hidden');
    }
    
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

// Debug function to test API connectivity - MOVED FROM STORIES.JS
function debugApiConnection() {
    console.log('🔧 Debug: Testing API connection...');
    console.log('🔧 Current API_BASE_URL:', API_BASE_URL);
    console.log('🔧 Current window.location:', window.location);
    console.log('🔧 Current authToken:', authToken ? 'Present' : 'Not present');
    
    // Test basic connectivity
    const healthUrl = `${API_BASE_URL}/health`;
    console.log('🔧 Testing health endpoint:', healthUrl);
    
    fetch(healthUrl)
        .then(response => {
            console.log('🔧 Health check response:', response.status);
            console.log('🔧 Health check URL that worked:', response.url);
            return response.json();
        })
        .then(data => {
            console.log('🔧 Health check data:', data);
        })
        .catch(error => {
            console.error('🔧 Health check failed:', error);
        });
}

// Make debug function globally available
window.debugApiConnection = debugApiConnection;

// Enhanced API health check function
async function checkApiHealth() {
    console.log('🏥 Checking API health...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/health`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const healthData = await response.json();
            console.log('✅ API Health Check:', healthData);
            return true;
        } else {
            console.warn('⚠️ API Health Check failed:', response.status);
            return false;
        }
    } catch (error) {
        console.error('❌ API Health Check error:', error);
        return false;
    }
}

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
        this.setupNavToggle();
    }
    
    setupNavToggle() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.createNavToggle());
        } else {
            this.createNavToggle();
        }
    }
    
    createNavToggle() {
        const existingToggle = document.getElementById('themeToggleNav');
        if (existingToggle) {
            existingToggle.innerHTML = this.currentTheme === 'dark' ? '☀️' : '🌙';
            existingToggle.onclick = () => this.toggleTheme();
            return;
        }
        
        // If the nav toggle doesn't exist in HTML, create it
        const navControls = document.querySelector('.nav-controls');
        if (navControls && !document.getElementById('themeToggleNav')) {
            const button = document.createElement('button');
            button.id = 'themeToggleNav';
            button.className = 'theme-toggle-nav';
            button.title = 'Toggle dark/light mode';
            button.innerHTML = this.currentTheme === 'dark' ? '☀️' : '🌙';
            button.onclick = () => this.toggleTheme();
            
            // Insert before user section
            const userSection = document.getElementById('userSection');
            navControls.insertBefore(button, userSection);
        }
    }
    
    toggleTheme() {
        this.currentTheme = this.currentTheme === 'light' ? 'dark' : 'light';
        this.applyTheme(this.currentTheme);
        localStorage.setItem('theme', this.currentTheme);
        
        const toggle = document.getElementById('themeToggleNav');
        if (toggle) {
            toggle.innerHTML = this.currentTheme === 'dark' ? '☀️' : '🌙';
        }
    }
    
    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
    }
}