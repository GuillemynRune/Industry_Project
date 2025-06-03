// Enhanced Moderation functionality with pagination and animations
let currentDisplayedStories = [];
let totalPendingCount = 0;
let displayedOffset = 0;

function checkAdminAccess() {
    if (currentUser && (currentUser.role === 'admin' || currentUser.role === 'moderator')) {
        document.getElementById('moderationSection').style.display = 'block';

        // Add moderation tab to navigation if not exists
        if (!document.getElementById('moderationLink')) {
            const navLinks = document.querySelector('.nav-links');
            const moderationLi = document.createElement('li');
            moderationLi.innerHTML = '<a href="#moderation" id="moderationLink">Moderation</a>';
            navLinks.appendChild(moderationLi);

            document.getElementById('moderationLink').addEventListener('click', () => {
                scrollToSection('moderationSection');
                loadPendingStories();
            });
        }

        loadPendingStories();
        
        // Auto-refresh stats every 30 seconds
        setInterval(refreshModerationStats, 30000);
    }
}

async function loadPendingStories(resetOffset = true) {
    if (!currentUser || (currentUser.role !== 'admin' && currentUser.role !== 'moderator')) {
        return;
    }

    if (resetOffset) {
        displayedOffset = 0;
        currentDisplayedStories = [];
    }

    try {
        const response = await fetch(`${API_BASE_URL}/moderation/pending?limit=4&offset=${displayedOffset}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.success) {
            totalPendingCount = data.total_count;
            const newStories = data.pending_stories || [];
            
            if (resetOffset) {
                currentDisplayedStories = newStories;
                displayPendingStories(currentDisplayedStories);
            } else {
                // Add new stories with animation
                newStories.forEach(story => {
                    currentDisplayedStories.push(story);
                    addStoryWithAnimation(story);
                });
            }
            
            updateModerationStats();
        }
    } catch (error) {
        console.error('Error loading pending stories:', error);
        showToast('Error loading pending stories: ' + error.message, 'error', 'Loading Error');
    }
}

function displayPendingStories(stories) {
    const grid = document.getElementById('pendingStoriesGrid');
    if (!grid) {
        console.error('pendingStoriesGrid element not found');
        return;
    }

    if (!Array.isArray(stories) || stories.length === 0) {
        grid.innerHTML = `
            <div class="no-stories-message">
                <h3>🎉 All caught up!</h3>
                <p>No stories pending review at the moment.</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = '';
    grid.className = 'pending-stories-grid-cards';

    stories.forEach((story, index) => {
        try {
            const card = createCompactStoryCard(story, index);
            card.style.animationDelay = `${index * 0.1}s`;
            grid.appendChild(card);
        } catch (error) {
            console.error('Error creating story card:', error, story);
        }
    });
}

function addStoryWithAnimation(story) {
    const grid = document.getElementById('pendingStoriesGrid');
    if (!grid || grid.querySelector('.no-stories-message')) {
        // If showing "no stories" message, reload completely
        displayPendingStories(currentDisplayedStories);
        return;
    }

    const card = createCompactStoryCard(story, currentDisplayedStories.length - 1);
    card.classList.add('story-card-enter');
    grid.appendChild(card);

    // Remove animation class after animation completes
    setTimeout(() => {
        card.classList.remove('story-card-enter');
    }, 500);
}

function createCompactStoryCard(story, index) {
    const card = document.createElement('div');
    const riskLevel = story.risk_level || 'minimal';
    
    card.className = `pending-story-card-compact ${riskLevel}-risk`;
    card.dataset.storyId = story._id || story.id;

    const storyData = {
        id: story._id || story.id,
        author: story.author_name || 'Anonymous',
        challenge: story.challenge || 'No challenge specified',
        date: story.created_at ? new Date(story.created_at).toLocaleDateString() : 'Unknown date',
        preview: story.experience ? story.experience.substring(0, 150) + '...' : 'No experience details'
    };

    const riskColors = {
        'high': 'risk-high',
        'medium': 'risk-medium', 
        'low': 'risk-low',
        'minimal': 'risk-minimal'
    };

    card.innerHTML = `
        <div class="story-card-header">
            <div class="story-meta-info">
                <h4 class="story-title">${storyData.challenge}</h4>
                <p class="story-author">By ${storyData.author} • ${storyData.date}</p>
            </div>
            <span class="story-risk-badge ${riskColors[riskLevel]}">${riskLevel.toUpperCase()}</span>
        </div>
        
        <div class="story-preview-text">${storyData.preview}</div>
        
        <div class="story-card-actions">
            <button class="read-more-btn" onclick="openStoryDetailModal('${storyData.id}')">
                Read Full Story →
            </button>
        </div>
    `;

    return card;
}

function updateModerationStats() {
    const pendingCountElement = document.getElementById('pendingCount');
    if (pendingCountElement) {
        pendingCountElement.textContent = totalPendingCount;
    }
}

async function refreshModerationStats() {
    if (!currentUser || (currentUser.role !== 'admin' && currentUser.role !== 'moderator')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/moderation/stats`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                totalPendingCount = data.total_pending;
                updateModerationStats();
                
                // If we're showing fewer than 4 stories but there are more available, load them
                if (currentDisplayedStories.length < 4 && currentDisplayedStories.length < totalPendingCount) {
                    const needed = Math.min(4 - currentDisplayedStories.length, totalPendingCount - currentDisplayedStories.length);
                    await loadAdditionalStories(needed);
                }
            }
        }
    } catch (error) {
        console.error('Error refreshing stats:', error);
    }
}

async function loadAdditionalStories(count) {
    try {
        const response = await fetch(`${API_BASE_URL}/moderation/pending?limit=${count}&offset=${currentDisplayedStories.length}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success && data.pending_stories.length > 0) {
                data.pending_stories.forEach(story => {
                    currentDisplayedStories.push(story);
                    addStoryWithAnimation(story);
                });
            }
        }
    } catch (error) {
        console.error('Error loading additional stories:', error);
    }
}

async function removeStoryWithAnimation(storyId) {
    const grid = document.getElementById('pendingStoriesGrid');
    const card = grid.querySelector(`[data-story-id="${storyId}"]`);
    
    if (!card) return;

    // Add exit animation
    card.classList.add('story-card-exit');
    
    // Remove from current displayed stories
    currentDisplayedStories = currentDisplayedStories.filter(s => (s._id || s.id) !== storyId);
    
    // Wait for animation to complete, then remove card
    setTimeout(async () => {
        card.remove();
        
        // If we have fewer than 4 stories displayed and there are more available, load the next one
        if (currentDisplayedStories.length < 4 && currentDisplayedStories.length < totalPendingCount) {
            try {
                const response = await fetch(`${API_BASE_URL}/moderation/pending?limit=1&offset=${currentDisplayedStories.length}`, {
                    headers: { 'Authorization': `Bearer ${authToken}` }
                });
                
                if (response.ok) {
                    const data = await response.json();
                    if (data.success && data.pending_stories.length > 0) {
                        const newStory = data.pending_stories[0];
                        currentDisplayedStories.push(newStory);
                        addStoryWithAnimation(newStory);
                    }
                }
            } catch (error) {
                console.error('Error loading next story:', error);
            }
        }
        
        // Update total count
        totalPendingCount = Math.max(0, totalPendingCount - 1);
        updateModerationStats();
        
        // If no stories left, show empty message
        if (currentDisplayedStories.length === 0) {
            displayPendingStories([]);
        }
    }, 500);
}

async function openStoryDetailModal(storyId) {
    try {
        const response = await fetch(`${API_BASE_URL}/moderation/story/${storyId}`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.success) {
            showStoryDetailModal(data.story);
        } else {
            showToast('Error loading story details', 'error', 'Loading Error');
        }
    } catch (error) {
        console.error('Error loading story details:', error);
        showToast('Error loading story details: ' + error.message, 'error', 'Loading Error');
    }
}

function showStoryDetailModal(story) {
    const modal = document.getElementById('storyDetailModal') || createStoryDetailModal();
    
    const storyData = {
        id: story._id || story.id,
        author: story.author_name || 'Anonymous',
        challenge: story.challenge || 'No challenge specified',
        experience: story.experience || 'No experience details',
        solution: story.solution || 'No solution specified',
        advice: story.advice || 'No advice provided',
        generatedStory: story.generated_story || 'No generated story available',
        date: story.created_at ? new Date(story.created_at).toLocaleDateString() : 'Unknown date',
        riskLevel: story.risk_level || 'minimal',
        flaggedKeywords: story.flagged_keywords || []
    };

    const riskColors = {
        'high': 'risk-high',
        'medium': 'risk-medium',
        'low': 'risk-low', 
        'minimal': 'risk-minimal'
    };

    const flaggedKeywordsSection = storyData.flaggedKeywords.length > 0 ? `
        <div class="flagged-keywords-section">
            <h4>🚨 Flagged Keywords</h4>
            <div class="keyword-tags">
                ${storyData.flaggedKeywords.map(keyword => `<span class="keyword-tag">${keyword}</span>`).join('')}
            </div>
        </div>
    ` : '';

    const sections = [
        { label: 'Experience:', content: storyData.experience },
        { label: 'Solution:', content: storyData.solution },
        storyData.advice && { label: 'Advice to Others:', content: storyData.advice }
    ].filter(Boolean);

    modal.querySelector('.modal-content').innerHTML = `
        <span class="close" onclick="closeModal('storyDetailModal')">&times;</span>
        
        <div class="story-detail-header">
            <div class="story-title-section">
                <h2>${storyData.challenge}</h2>
                <div class="story-meta">
                    <span>By ${storyData.author} • ${storyData.date}</span>
                    <span class="story-risk-badge ${riskColors[storyData.riskLevel]}">${storyData.riskLevel.toUpperCase()} RISK</span>
                </div>
            </div>
        </div>

        <div class="story-detail-content">
            <div class="story-section">
                <h3>Original Submission</h3>
                ${sections.map(section => `
                    <div class="story-field">
                        <label>${section.label}</label>
                        <div class="field-content">${section.content}</div>
                    </div>
                `).join('')}
            </div>

            <div class="story-section">
                <h3>Generated Story Preview</h3>
                <div class="generated-story-preview">${storyData.generatedStory}</div>
            </div>

            ${flaggedKeywordsSection}
        </div>

        <div class="story-detail-actions">
            <button class="approve-btn-modern" onclick="moderateStory('${storyData.id}', 'approve')">
                <span class="btn-icon">✓</span>
                Approve & Publish
            </button>
            <button class="reject-btn-modern" onclick="moderateStory('${storyData.id}', 'reject')">
                <span class="btn-icon">✗</span>
                Reject Story
            </button>
        </div>
    `;

    openModal('storyDetailModal');
}

function createStoryDetailModal() {
    const modal = document.createElement('div');
    modal.id = 'storyDetailModal';
    modal.className = 'modal story-detail-modal';
    modal.innerHTML = `<div class="modal-content story-detail-modal-content"></div>`;
    document.body.appendChild(modal);
    return modal;
}

async function moderateStory(storyId, action) {
    const confirmMessages = {
        approve: 'Are you sure you want to approve and publish this story?',
        reject: 'Are you sure you want to reject this story?'
    };

    if (!confirm(confirmMessages[action])) return;

    const reason = action === 'reject' ? prompt('Reason for rejection (optional):') : null;
    if (action === 'reject' && reason === null) return;

    try {
        const response = await fetch(`${API_BASE_URL}/moderation/${action}/${storyId}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ...(action === 'approve' ? { notes: "Approved via admin interface" } : { reason: reason || "Does not meet community guidelines" })
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            const messages = {
                approve: 'Story approved and published successfully! It\'s now live for the community to see.',
                reject: 'Story has been rejected and removed from the review queue.'
            };
            showToast(messages[action], 'success', action === 'approve' ? 'Story Published!' : 'Story Rejected');
            closeModal('storyDetailModal');
            
            // Remove story with animation
            await removeStoryWithAnimation(storyId);
        } else {
            showToast(`Failed to ${action} story: ${data.message || 'Unknown error'}`, 'error', `${action.charAt(0).toUpperCase() + action.slice(1)} Failed`);
        }
    } catch (error) {
        console.error(`Error ${action}ing story:`, error);
        showToast(`Error ${action}ing story: ${error.message}`, 'error', `${action.charAt(0).toUpperCase() + action.slice(1)} Error`);
    }
}

// Backwards compatibility
async function approveStory(storyId) {
    return moderateStory(storyId, 'approve');
}

async function rejectStory(storyId) {
    return moderateStory(storyId, 'reject');
}