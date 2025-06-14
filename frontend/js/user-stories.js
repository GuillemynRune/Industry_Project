// User Stories Management
let userStories = [];
let userStoriesStats = {
    total: 0,
    pending: 0,
    approved: 0,
    rejected: 0
};

// Main function to show user's stories modal
async function showMyStories() {
    if (!currentUser) {
        showToast('Please login to view your stories.', 'warning', 'Login Required');
        openModal('authModal');
        return;
    }
    
    openModal('myStoriesModal');
    await loadUserStories();
}

// Load user's stories from backend
async function loadUserStories() {
    const container = document.getElementById('userStoriesContainer');
    
    // Show loading state
    container.innerHTML = `
        <div class="loading-placeholder">
            <div class="loading-spinner"></div>
            <p>Loading your stories...</p>
        </div>
    `;
    
    try {
        const response = await makeAuthenticatedRequest(`${API_BASE_URL}/stories/user/stories`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            userStories = data.stories || [];
            userStoriesStats = {
                total: data.total_count || 0,
                pending: data.pending_count || 0,
                approved: data.approved_count || 0,
                rejected: userStories.filter(s => s.status === 'rejected').length
            };
            
            displayUserStories();
        } else {
            throw new Error(data.message || 'Failed to load stories');
        }
    } catch (error) {
        console.error('Error loading user stories:', error);
        showErrorState(container, error.message);
    }
}

// Display user stories in the modal
function displayUserStories() {
    const container = document.getElementById('userStoriesContainer');
    
    if (userStories.length === 0) {
        container.innerHTML = `
            <div class="no-stories-message">
                <h3>📝 No Stories Yet</h3>
                <p>You haven't shared any stories with our community yet.</p>
                <button class="btn btn-primary" onclick="startGuidedStory(); closeModal('myStoriesModal')">
                    ✨ Share Your First Story
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = `
        <!-- Stats Section -->
        <div class="user-stories-stats">
            <div class="stat-card">
                <div class="stat-number">${userStoriesStats.total}</div>
                <div class="stat-label">Total Stories</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${userStoriesStats.pending}</div>
                <div class="stat-label">Pending Review</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${userStoriesStats.approved}</div>
                <div class="stat-label">Published</div>
            </div>
            ${userStoriesStats.rejected > 0 ? `
                <div class="stat-card">
                    <div class="stat-number">${userStoriesStats.rejected}</div>
                    <div class="stat-label">Rejected</div>
                </div>
            ` : ''}
        </div>
        
        <!-- Stories Grid -->
        <div class="user-stories-grid">
            ${userStories.map(story => createUserStoryCard(story)).join('')}
        </div>
    `;
}

// Create individual story card
function createUserStoryCard(story) {
    const statusInfo = getStatusInfo(story.status);
    const date = story.created_at ? new Date(story.created_at).toLocaleDateString() : 'Unknown date';
    const preview = story.experience ? story.experience.substring(0, 120) + '...' : 'No preview available';
    
    return `
        <div class="user-story-card status-${story.status}" data-story-id="${story.id}">
            <div class="story-card-header">
                <div class="story-info">
                    <h4 class="story-title">${story.challenge || 'Untitled Story'}</h4>
                    <p class="story-date">${date}</p>
                </div>
                <span class="status-badge status-${story.status}">
                    ${statusInfo.icon} ${statusInfo.label}
                </span>
            </div>
            
            <div class="story-preview">
                ${preview}
            </div>
            
            <div class="story-card-footer">
                <div class="status-info">
                    <small>${statusInfo.description}</small>
                </div>
                <button class="btn-link" onclick="viewUserStoryDetail('${story.id}')">
                    View Details →
                </button>
            </div>
        </div>
    `;
}

// Get status information for display
function getStatusInfo(status) {
    const statusMap = {
        'pending': {
            label: 'Pending Review',
            icon: '⏳',
            description: 'Your story is being reviewed by our team'
        },
        'approved': {
            label: 'Published',
            icon: '✅',
            description: 'Your story is live and helping others'
        },
        'rejected': {
            label: 'Not Approved',
            icon: '❌',
            description: 'Story did not meet community guidelines'
        }
    };
    
    return statusMap[status] || statusMap['pending'];
}

// View detailed story information
function viewUserStoryDetail(storyId) {
    const story = userStories.find(s => s.id === storyId);
    if (!story) {
        showToast('Story not found', 'error', 'Error');
        return;
    }
    
    showUserStoryDetailModal(story);
}

// Show detailed story modal
function showUserStoryDetailModal(story) {
    const modal = document.getElementById('userStoryDetailModal') || createUserStoryDetailModal();
    const statusInfo = getStatusInfo(story.status);
    
    const content = modal.querySelector('.modal-content');
    content.innerHTML = `
        <span class="close" onclick="closeModal('userStoryDetailModal')">&times;</span>
        
        <!-- Story Status Banner -->
        <div class="story-status-banner status-${story.status}">
            <div class="status-info">
                <span class="status-badge status-${story.status}">
                    ${statusInfo.icon} ${statusInfo.label}
                </span>
                <p>${statusInfo.description}</p>
            </div>
            <div class="submission-date">
                <small>Submitted: ${story.created_at ? new Date(story.created_at).toLocaleDateString() : 'Unknown'}</small>
            </div>
        </div>
        
        <!-- Story Content -->
        <div class="story-detail-content">
            <div class="story-section">
                <h3>Your Original Submission</h3>
                
                <div class="story-field">
                    <label>Challenge:</label>
                    <div class="field-content">${story.challenge || 'Not specified'}</div>
                </div>
                
                <div class="story-field">
                    <label>Your Experience:</label>
                    <div class="field-content">${story.experience || 'Not provided'}</div>
                </div>
                
                <div class="story-field">
                    <label>What Helped:</label>
                    <div class="field-content">${story.solution || 'Not specified'}</div>
                </div>
                
                ${story.advice ? `
                    <div class="story-field">
                        <label>Your Advice:</label>
                        <div class="field-content">${story.advice}</div>
                    </div>
                ` : ''}
            </div>
            
            ${story.generated_story ? `
                <div class="story-section">
                    <h3>Generated Story Preview</h3>
                    <div class="generated-story-preview">
                        ${story.generated_story}
                    </div>
                </div>
            ` : ''}
            
            ${story.status === 'approved' && story.approved_at ? `
                <div class="story-section">
                    <h3>Publication Details</h3>
                    <p><strong>Approved:</strong> ${new Date(story.approved_at).toLocaleDateString()}</p>
                    <p><strong>Status:</strong> Your story is now live and helping other parents in our community!</p>
                </div>
            ` : ''}
        </div>
        
        <div class="story-viewer-actions">
            <button class="btn btn-secondary" onclick="closeModal('userStoryDetailModal')">
                Close
            </button>
            ${story.status === 'approved' ? `
                <button class="btn btn-primary" onclick="viewPublishedStory('${story.id}')">
                    View Published Story
                </button>
            ` : ''}
        </div>
    `;
    
    openModal('userStoryDetailModal');
}

// Create user story detail modal if it doesn't exist
function createUserStoryDetailModal() {
    const modal = document.createElement('div');
    modal.id = 'userStoryDetailModal';
    modal.className = 'modal story-detail-modal';
    modal.innerHTML = '<div class="modal-content story-detail-modal-content"></div>';
    document.body.appendChild(modal);
    return modal;
}

// View published story in the main story viewer
async function viewPublishedStory(storyId) {
    closeModal('userStoryDetailModal');
    closeModal('myStoriesModal');
    
    try {
        await viewFullStory(storyId);
    } catch (error) {
        showToast('Could not load published story', 'error', 'Error');
    }
}

// Refresh user stories
async function refreshMyStories() {
    showToast('Refreshing your stories...', 'success', 'Refreshing');
    await loadUserStories();
}

// Show error state
function showErrorState(container, errorMessage) {
    container.innerHTML = `
        <div class="no-stories-message">
            <h3>⚠️ Error Loading Stories</h3>
            <p>${errorMessage}</p>
            <button class="btn btn-secondary" onclick="refreshMyStories()">
                Try Again
            </button>
        </div>
    `;
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Show/hide My Stories nav item based on login status
    const updateMyStoriesNav = () => {
        const myStoriesNavItem = document.getElementById('myStoriesNavItem');
        if (myStoriesNavItem) {
            myStoriesNavItem.style.display = currentUser ? 'block' : 'none';
        }
    };
    
    // Initial update
    updateMyStoriesNav();
    
    // Update when auth state changes
    const originalShowUserSection = window.showUserSection;
    if (originalShowUserSection) {
        window.showUserSection = function() {
            originalShowUserSection();
            updateMyStoriesNav();
        };
    }
    
    const originalShowAuthSection = window.showAuthSection;
    if (originalShowAuthSection) {
        window.showAuthSection = function() {
            originalShowAuthSection();
            updateMyStoriesNav();
        };
    }
});