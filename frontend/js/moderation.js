// Moderation functionality - Redesigned
function checkAdminAccess() {
    if (currentUser && (currentUser.role === 'admin' || currentUser.role === 'moderator')) {
        document.getElementById('moderationSection').style.display = 'block';

        // Add moderation tab to navigation
        const navLinks = document.querySelector('.nav-links');
        if (!document.getElementById('moderationLink')) {
            const moderationLi = document.createElement('li');
            moderationLi.innerHTML = '<a href="#moderation" id="moderationLink">Moderation</a>';
            navLinks.appendChild(moderationLi);

            // Add click handler
            document.getElementById('moderationLink').addEventListener('click', () => {
                scrollToSection('moderationSection');
                loadPendingStories();
            });
        }

        loadPendingStories();
    }
}

async function loadPendingStories() {
    if (!currentUser || (currentUser.role !== 'admin' && currentUser.role !== 'moderator')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/moderation/pending`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success && Array.isArray(data.pending_stories)) {
            displayPendingStories(data.pending_stories);
            updateModerationStats(data.pending_stories);
        } else if (Array.isArray(data.pending_stories)) {
            displayPendingStories(data.pending_stories);
            updateModerationStats(data.pending_stories);
        } else {
            console.error('Unexpected data structure:', data);
            showToast('Error: Unexpected data format from server', 'error', 'Data Error');
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

    if (!Array.isArray(stories)) {
        console.error('Stories is not an array:', stories);
        showToast('Error: Invalid stories data', 'error', 'Data Error');
        return;
    }

    if (stories.length === 0) {
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
            grid.appendChild(card);
        } catch (error) {
            console.error('Error creating story card:', error, story);
        }
    });
}

function createCompactStoryCard(story, index) {
    const card = document.createElement('div');
    card.className = `pending-story-card-compact ${story.risk_level || 'minimal'}-risk`;
    card.style.animationDelay = `${index * 0.1}s`;

    const riskLevel = story.risk_level || 'minimal';
    const riskColor = {
        'high': 'risk-high',
        'medium': 'risk-medium', 
        'low': 'risk-low',
        'minimal': 'risk-minimal'
    }[riskLevel] || 'risk-minimal';

    const authorName = story.author_name || 'Anonymous';
    const challenge = story.challenge || 'No challenge specified';
    const createdAt = story.created_at ? new Date(story.created_at).toLocaleDateString() : 'Unknown date';
    const storyId = story._id || story.id;
    const preview = story.experience ? story.experience.substring(0, 150) + '...' : 'No experience details';

    card.innerHTML = `
        <div class="story-card-header">
            <div class="story-meta-info">
                <h4 class="story-title">${challenge}</h4>
                <p class="story-author">By ${authorName} • ${createdAt}</p>
            </div>
            <span class="story-risk-badge ${riskColor}">${riskLevel.toUpperCase()}</span>
        </div>
        
        <div class="story-preview-text">
            ${preview}
        </div>
        
        <div class="story-card-actions">
            <button class="read-more-btn" onclick="openStoryDetailModal('${storyId}')">
                Read Full Story →
            </button>
        </div>
    `;

    return card;
}

function updateModerationStats(stories) {
    const pendingCountEl = document.getElementById('pendingCount');
    const highRiskCountEl = document.getElementById('highRiskCount');
    const totalApprovedEl = document.getElementById('totalApproved');

    if (pendingCountEl) {
        pendingCountEl.textContent = stories.length;
    }

    if (highRiskCountEl) {
        const highRiskCount = stories.filter(s => s.risk_level === 'high').length;
        highRiskCountEl.textContent = highRiskCount;
    }

    if (totalApprovedEl) {
        totalApprovedEl.textContent = '—';
    }
}

async function openStoryDetailModal(storyId) {
    try {
        const response = await fetch(`${API_BASE_URL}/moderation/story/${storyId}`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
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
    
    const riskLevel = story.risk_level || 'minimal';
    const riskColor = {
        'high': 'risk-high',
        'medium': 'risk-medium',
        'low': 'risk-low', 
        'minimal': 'risk-minimal'
    }[riskLevel] || 'risk-minimal';

    const authorName = story.author_name || 'Anonymous';
    const challenge = story.challenge || 'No challenge specified';
    const experience = story.experience || 'No experience details';
    const solution = story.solution || 'No solution specified';
    const advice = story.advice || 'No advice provided';
    const generatedStory = story.generated_story || 'No generated story available';
    const createdAt = story.created_at ? new Date(story.created_at).toLocaleDateString() : 'Unknown date';
    const storyId = story._id || story.id;

    const flaggedKeywordsHtml = story.flagged_keywords && story.flagged_keywords.length > 0 ? `
        <div class="flagged-keywords-section">
            <h4>🚨 Flagged Keywords</h4>
            <div class="keyword-tags">
                ${story.flagged_keywords.map(keyword => `<span class="keyword-tag">${keyword}</span>`).join('')}
            </div>
        </div>
    ` : '';

    modal.querySelector('.modal-content').innerHTML = `
        <span class="close" onclick="closeModal('storyDetailModal')">&times;</span>
        
        <div class="story-detail-header">
            <div class="story-title-section">
                <h2>${challenge}</h2>
                <div class="story-meta">
                    <span>By ${authorName} • ${createdAt}</span>
                    <span class="story-risk-badge ${riskColor}">${riskLevel.toUpperCase()} RISK</span>
                </div>
            </div>
        </div>

        <div class="story-detail-content">
            <div class="story-section">
                <h3>Original Submission</h3>
                <div class="story-field">
                    <label>Experience:</label>
                    <div class="field-content">${experience}</div>
                </div>
                
                <div class="story-field">
                    <label>Solution:</label>
                    <div class="field-content">${solution}</div>
                </div>
                
                ${advice ? `
                <div class="story-field">
                    <label>Advice to Others:</label>
                    <div class="field-content">${advice}</div>
                </div>
                ` : ''}
            </div>

            <div class="story-section">
                <h3>Generated Story Preview</h3>
                <div class="generated-story-preview">
                    ${generatedStory}
                </div>
            </div>

            ${flaggedKeywordsHtml}
        </div>

        <div class="story-detail-actions">
            <button class="approve-btn-modern" onclick="approveStory('${storyId}')">
                <span class="btn-icon">✓</span>
                Approve & Publish
            </button>
            <button class="reject-btn-modern" onclick="rejectStory('${storyId}')">
                <span class="btn-icon">✗</span>
                Reject Story
            </button>
        </div>
    `;

    modal.style.display = 'block';
    document.body.style.overflow = 'hidden';
}

function createStoryDetailModal() {
    const modal = document.createElement('div');
    modal.id = 'storyDetailModal';
    modal.className = 'modal story-detail-modal';
    modal.innerHTML = `<div class="modal-content story-detail-modal-content"></div>`;
    document.body.appendChild(modal);
    return modal;
}

async function approveStory(storyId) {
    if (!confirm('Are you sure you want to approve and publish this story?')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/moderation/approve/${storyId}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                notes: "Approved via admin interface"
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            showToast('Story approved and published successfully! It\'s now live for the community to see.', 'success', 'Story Published!');
            closeModal('storyDetailModal');
            loadPendingStories();
        } else {
            showToast('Failed to approve story: ' + (data.message || 'Unknown error'), 'error', 'Approval Failed');
        }
    } catch (error) {
        console.error('Error approving story:', error);
        showToast('Error approving story: ' + error.message, 'error', 'Approval Error');
    }
}

async function rejectStory(storyId) {
    const reason = prompt('Reason for rejection (optional):');
    if (reason === null) return;

    try {
        const response = await fetch(`${API_BASE_URL}/moderation/reject/${storyId}`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                reason: reason || "Does not meet community guidelines"
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            showToast('Story has been rejected and removed from the review queue.', 'success', 'Story Rejected');
            closeModal('storyDetailModal');
            loadPendingStories();
        } else {
            showToast('Failed to reject story: ' + (data.message || 'Unknown error'), 'error', 'Rejection Failed');
        }
    } catch (error) {
        console.error('Error rejecting story:', error);
        showToast('Error rejecting story: ' + error.message, 'error', 'Rejection Error');
    }
}