// Moderation functionality
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
        
        const data = await response.json();
        
        if (data.success) {
            displayPendingStories(data.pending_stories);
            updateModerationStats(data.pending_stories);
        } else {
            console.error('Failed to load pending stories:', data);
        }
    } catch (error) {
        console.error('Error loading pending stories:', error);
        showStatusMessage('Error loading pending stories', 'error');
    }
}

function displayPendingStories(stories) {
    const grid = document.getElementById('pendingStoriesGrid');
    
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
    
    stories.forEach((story, index) => {
        const card = createPendingStoryCard(story, index);
        grid.appendChild(card);
    });
}

function createPendingStoryCard(story, index) {
    const card = document.createElement('div');
    card.className = `pending-story-card ${story.risk_level}-risk`;
    card.style.animationDelay = `${index * 0.1}s`;
    
    const riskColor = {
        'high': 'risk-high',
        'medium': 'risk-medium', 
        'low': 'risk-low',
        'minimal': 'risk-minimal'
    }[story.risk_level] || 'risk-minimal';
    
    const flaggedKeywordsHtml = story.flagged_keywords && story.flagged_keywords.length > 0 ? `
        <div class="flagged-keywords">
            <div class="flagged-keywords-label">🚨 Flagged Keywords:</div>
            ${story.flagged_keywords.map(keyword => `<span class="keyword-tag">${keyword}</span>`).join('')}
        </div>
    ` : '';
    
    card.innerHTML = `
        <div class="story-header">
            <div>
                <strong>By ${story.author_name}</strong><br>
                <small style="color: var(--text-light);">${new Date(story.created_at).toLocaleDateString()}</small>
            </div>
            <span class="story-risk-badge ${riskColor}">${story.risk_level.toUpperCase()} RISK</span>
        </div>
        
        <div class="story-content">
            <div class="story-field">
                <span class="story-field-label">Challenge:</span>
                <div class="story-field-content">${story.challenge}</div>
            </div>
            
            <div class="story-field">
                <span class="story-field-label">Experience:</span>
                <div class="story-field-content">${story.experience.substring(0, 200)}${story.experience.length > 200 ? '...' : ''}</div>
            </div>
            
            <div class="story-field">
                <span class="story-field-label">Solution:</span>
                <div class="story-field-content">${story.solution.substring(0, 200)}${story.solution.length > 200 ? '...' : ''}</div>
            </div>
            
            <div class="story-field">
                <span class="story-field-label">Generated Story Preview:</span>
                <div class="story-field-content">${story.generated_story.substring(0, 300)}${story.generated_story.length > 300 ? '...' : ''}</div>
            </div>
            
            ${flaggedKeywordsHtml}
        </div>
        
        <div class="story-actions">
            <button class="approve-btn" onclick="approveStory('${story._id}')">
                ✅ Approve & Publish
            </button>
            <button class="reject-btn" onclick="rejectStory('${story._id}')">
                ❌ Reject
            </button>
        </div>
    `;
    
    return card;
}

function updateModerationStats(stories) {
    document.getElementById('pendingCount').textContent = stories.length;
    
    const highRiskCount = stories.filter(s => s.risk_level === 'high').length;
    document.getElementById('highRiskCount').textContent = highRiskCount;
    
    // You can add total approved count from database if needed
    document.getElementById('totalApproved').textContent = '—';
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
        
        const data = await response.json();
        
        if (data.success) {
            showStatusMessage('Story approved and published successfully!', 'success');
            loadPendingStories(); // Refresh the list
        } else {
            showStatusMessage('Failed to approve story: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error approving story:', error);
        showStatusMessage('Error approving story', 'error');
    }
}

async function rejectStory(storyId) {
    const reason = prompt('Reason for rejection (optional):');
    if (reason === null) return; // User cancelled
    
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
        
        const data = await response.json();
        
        if (data.success) {
            showStatusMessage('Story rejected', 'success');
            loadPendingStories(); // Refresh the list
        } else {
            showStatusMessage('Failed to reject story: ' + data.message, 'error');
        }
    } catch (error) {
        console.error('Error rejecting story:', error);
        showStatusMessage('Error rejecting story', 'error');
    }
}