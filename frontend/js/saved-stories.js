// Fixed Saved Stories Management - Missing function added
let savedStories = [];
let savedStoriesStats = {
    total: 0,
    recent: 0
};

// Main function to show saved stories modal
async function showSavedStories() {
    if (!currentUser) {
        showToast('Please login to view your saved stories.', 'warning', 'Login Required');
        openModal('authModal');
        return;
    }
    
    openModal('savedStoriesModal');
    await loadSavedStories();
}

// Load saved stories from backend
async function loadSavedStories() {
    const container = document.getElementById('savedStoriesContainer');
    
    // Show loading state
    container.innerHTML = `
        <div class="loading-placeholder">
            <div class="loading-spinner"></div>
            <p>Loading your saved stories...</p>
        </div>
    `;
    
    try {
        const response = await makeAuthenticatedRequest(`${API_BASE_URL}/stories/saved/list`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            savedStories = data.saved_stories || [];
            savedStoriesStats = {
                total: data.total_count || 0,
                recent: data.saved_stories?.filter(s => {
                    const savedDate = new Date(s.saved_at);
                    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
                    return savedDate >= weekAgo;
                }).length || 0
            };
            
            displaySavedStories();
        } else {
            throw new Error(data.message || 'Failed to load saved stories');
        }
    } catch (error) {
        console.error('Error loading saved stories:', error);
        showErrorState(container, error.message);
    }
}

// Display saved stories in the modal
function displaySavedStories() {
    const container = document.getElementById('savedStoriesContainer');
    
    if (savedStories.length === 0) {
        container.innerHTML = `
            <div class="no-stories-message">
                <h3>📚 No Saved Stories Yet</h3>
                <p>You haven't saved any stories yet. When you find stories that resonate with you, click the save button to keep them here for easy access.</p>
                <button class="btn btn-primary" onclick="closeModal('savedStoriesModal'); scrollToSection('stories')">
                    🔍 Browse Stories
                </button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = `
        <!-- Stats Section -->
        <div class="saved-stories-stats">
            <div class="stat-card">
                <div class="stat-number">${savedStoriesStats.total}</div>
                <div class="stat-label">Saved Stories</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">${savedStoriesStats.recent}</div>
                <div class="stat-label">Saved This Week</div>
            </div>
        </div>
        
        <!-- Stories Grid -->
        <div class="saved-stories-grid">
            ${savedStories.map(story => createSavedStoryCard(story)).join('')}
        </div>
    `;
}

// Create individual saved story card
function createSavedStoryCard(story) {
    const savedDate = story.saved_at ? new Date(story.saved_at).toLocaleDateString() : 'Unknown date';
    const originalDate = story.created_at ? new Date(story.created_at).toLocaleDateString() : 'Unknown date';
    const preview = story.generated_story ? story.generated_story.substring(0, 150) + '...' : 
                   story.experience ? story.experience.substring(0, 150) + '...' : 
                   'No preview available';
    
    return `
        <div class="saved-story-card" data-story-id="${story.id}">
            <div class="story-card-header">
                <div class="story-info">
                    <h4 class="story-title">${story.challenge || 'Untitled Story'}</h4>
                    <p class="story-metadata">
                        <span class="story-author">By ${story.author_name || 'Anonymous'}</span>
                        <span class="story-date">• ${originalDate}</span>
                    </p>
                </div>
                <div class="story-actions">
                    <button class="save-btn saved" onclick="toggleSaveStory('${story.id}', this)" title="Remove from saved">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M17 3H7c-1.1 0-2 .9-2 2v16l7-3 7 3V5c0-1.1-.9-2-2-2z"/>
                        </svg>
                    </button>
                </div>
            </div>
            
            <div class="story-preview">
                ${preview}
            </div>
            
            <div class="story-card-footer">
                <div class="saved-info">
                    <small>💾 Saved on ${savedDate}</small>
                </div>
                <button class="btn-link" onclick="viewSavedStoryDetail('${story.id}')">
                    Read Story →
                </button>
            </div>
        </div>
    `;
}

// View detailed saved story
function viewSavedStoryDetail(storyId) {
    const story = savedStories.find(s => s.id === storyId);
    if (!story) {
        showToast('Story not found', 'error', 'Error');
        return;
    }
    
    // Close saved stories modal and show story detail
    closeModal('savedStoriesModal');
    showFullStoryModal(story);
}

// Toggle save status of a story
async function toggleSaveStory(storyId, buttonElement) {
    if (!currentUser) {
        showToast('Please login to save stories.', 'warning', 'Login Required');
        openModal('authModal');
        return;
    }
    
    const originalContent = buttonElement.innerHTML;
    const wasSaved = buttonElement.classList.contains('saved');
    
    // Update UI immediately for better UX
    buttonElement.disabled = true;
    buttonElement.innerHTML = '<div class="loading-small"></div>';
    
    try {
        const response = await makeAuthenticatedRequest(`${API_BASE_URL}/stories/saved/toggle`, {
            method: 'POST',
            body: JSON.stringify({ story_id: storyId })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            const isSaved = data.is_saved;
            updateSaveButton(buttonElement, isSaved);
            
            // Show appropriate toast
            const message = isSaved ? 'Story saved for later reading!' : 'Story removed from saved collection';
            const title = isSaved ? 'Story Saved!' : 'Story Removed';
            showToast(message, 'success', title);
            
            // If we're in the saved stories modal and story was unsaved, refresh the view
            if (!isSaved && document.getElementById('savedStoriesModal').style.display === 'block') {
                // Remove the card with animation
                const card = buttonElement.closest('.saved-story-card');
                if (card) {
                    card.style.animation = 'slideOut 0.3s ease-in-out forwards';
                    setTimeout(() => {
                        card.remove();
                        // If no stories left, show empty state
                        if (document.querySelectorAll('.saved-story-card').length === 0) {
                            displaySavedStories();
                        }
                    }, 300);
                }
                // Update stats
                savedStoriesStats.total = Math.max(0, savedStoriesStats.total - 1);
                const statElement = document.querySelector('.saved-stories-stats .stat-number');
                if (statElement) {
                    statElement.textContent = savedStoriesStats.total;
                }
            }
        } else {
            throw new Error(data.message || 'Failed to toggle save status');
        }
    } catch (error) {
        console.error('Error toggling save status:', error);
        
        // Restore original state on error
        updateSaveButton(buttonElement, wasSaved);
        
        showToast('Unable to update save status. Please try again.', 'error', 'Save Error');
    } finally {
        buttonElement.disabled = false;
    }
}

// Update save button appearance
function updateSaveButton(button, isSaved) {
    if (isSaved) {
        button.classList.add('saved');
        button.title = 'Remove from saved';
        button.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M17 3H7c-1.1 0-2 .9-2 2v16l7-3 7 3V5c0-1.1-.9-2-2-2z"/>
            </svg>
        `;
    } else {
        button.classList.remove('saved');
        button.title = 'Save for later';
        button.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>
            </svg>
        `;
    }
}

// Check if story is saved and update button state
async function checkAndUpdateSaveStatus(storyId, button) {
    if (!currentUser) return;
    
    try {
        const response = await makeAuthenticatedRequest(`${API_BASE_URL}/stories/saved/check/${storyId}`);
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                updateSaveButton(button, data.is_saved);
            }
        }
    } catch (error) {
        console.error('Error checking save status:', error);
    }
}

// Refresh saved stories
async function refreshSavedStories() {
    showToast('Refreshing your saved stories...', 'success', 'Refreshing');
    await loadSavedStories();
}

// Show error state
function showErrorState(container, errorMessage) {
    container.innerHTML = `
        <div class="no-stories-message">
            <h3>⚠️ Error Loading Saved Stories</h3>
            <p>${errorMessage}</p>
            <button class="btn btn-secondary" onclick="refreshSavedStories()">
                Try Again
            </button>
        </div>
    `;
}

// ADDED: Missing function that was causing the error
function addSaveButtonsToStoryCards() {
    // This function can be empty or add save buttons to story cards if needed
    // For now, we'll just log that it was called
    console.log('addSaveButtonsToStoryCards called');
    
    // If you want to add save buttons to story cards in the future, implement here
    // For now, save buttons only appear in story detail modals
}

// Initialize saved stories functionality
document.addEventListener('DOMContentLoaded', function() {
    // Create saved stories modal
    createSavedStoriesModal();
    
    // Watch for new story cards being added
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1 && (node.classList?.contains('story-card') || node.querySelector?.('.story-card'))) {
                    setTimeout(addSaveButtonsToStoryCards, 100);
                }
            });
        });
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
});

// Create saved stories modal
function createSavedStoriesModal() {
    // Remove existing modal if it exists
    const existing = document.getElementById('savedStoriesModal');
    if (existing) existing.remove();
    
    const modal = document.createElement('div');
    modal.id = 'savedStoriesModal';
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content saved-stories-modal-content">
            <span class="close" onclick="closeModal('savedStoriesModal')">&times;</span>

            <div class="saved-stories-header">
                <h2>📚 My Saved Stories</h2>
                <p>Stories you've saved for later reading and reflection</p>
                <div class="saved-stories-actions">
                    <button class="btn btn-secondary" onclick="refreshSavedStories()">
                        🔄 Refresh
                    </button>
                    <button class="btn btn-primary" onclick="closeModal('savedStoriesModal'); scrollToSection('stories')">
                        🔍 Browse More Stories
                    </button>
                </div>
            </div>

            <div class="saved-stories-content">
                <div id="savedStoriesContainer">
                    <div class="loading-placeholder">
                        <div class="loading-spinner"></div>
                        <p>Loading your saved stories...</p>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}