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
        console.log('Loading pending stories...'); // Debug log
        const response = await fetch(`${API_BASE_URL}/moderation/pending`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        console.log('Response status:', response.status); // Debug log

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Response data:', data); // Debug log

        // Check if the response has the expected structure
        if (data.success && Array.isArray(data.pending_stories)) {
            displayPendingStories(data.pending_stories);
            updateModerationStats(data.pending_stories);
        } else if (Array.isArray(data.pending_stories)) {
            // Handle case where success field might be missing but data is valid
            displayPendingStories(data.pending_stories);
            updateModerationStats(data.pending_stories);
        } else {
            console.error('Unexpected data structure:', data);
            showStatusMessage('Error: Unexpected data format from server', 'error');
        }
    } catch (error) {
        console.error('Error loading pending stories:', error);
        showStatusMessage('Error loading pending stories: ' + error.message, 'error');
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
        showStatusMessage('Error: Invalid stories data', 'error');
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

    stories.forEach((story, index) => {
        try {
            const card = createPendingStoryCard(story, index);
            grid.appendChild(card);
        } catch (error) {
            console.error('Error creating story card:', error, story);
        }
    });
}

function createPendingStoryCard(story, index) {
    const card = document.createElement('div');
    card.className = `pending-story-card ${story.risk_level || 'minimal'}-risk`;
    card.style.animationDelay = `${index * 0.1}s`;

    const riskLevel = story.risk_level || 'minimal';
    const riskColor = {
        'high': 'risk-high',
        'medium': 'risk-medium',
        'low': 'risk-low',
        'minimal': 'risk-minimal'
    }[riskLevel] || 'risk-minimal';

    const flaggedKeywordsHtml = story.flagged_keywords && story.flagged_keywords.length > 0 ? `
        <div class="flagged-keywords">
            <div class="flagged-keywords-label">🚨 Flagged Keywords:</div>
            ${story.flagged_keywords.map(keyword => `<span class="keyword-tag">${keyword}</span>`).join('')}
        </div>
    ` : '';

    // Handle potentially missing fields gracefully
    const authorName = story.author_name || 'Anonymous';
    const challenge = story.challenge || 'No challenge specified';
    const experience = story.experience || 'No experience details';
    const solution = story.solution || 'No solution specified';
    const generatedStory = story.generated_story || 'No generated story available';
    const createdAt = story.created_at ? new Date(story.created_at).toLocaleDateString() : 'Unknown date';
    const storyId = story._id || story.id;

    card.innerHTML = `
        <div class="story-header">
            <div>
                <strong>By ${authorName}</strong><br>
                <small style="color: var(--text-light);">${createdAt}</small>
            </div>
            <span class="story-risk-badge ${riskColor}">${riskLevel.toUpperCase()} RISK</span>
        </div>
        
        <div class="story-content">
            <div class="story-field">
                <span class="story-field-label">Challenge:</span>
                <div class="story-field-content">${challenge}</div>
            </div>
            
            <div class="story-field">
                <span class="story-field-label">Experience:</span>
                <div class="story-field-content">${experience.substring(0, 200)}${experience.length > 200 ? '...' : ''}</div>
            </div>
            
            <div class="story-field">
                <span class="story-field-label">Solution:</span>
                <div class="story-field-content">${solution.substring(0, 200)}${solution.length > 200 ? '...' : ''}</div>
            </div>
            
            <div class="story-field">
                <span class="story-field-label">Generated Story Preview:</span>
                <div class="story-field-content">${generatedStory.substring(0, 300)}${generatedStory.length > 300 ? '...' : ''}</div>
            </div>
            
            ${flaggedKeywordsHtml}
        </div>
        
        <div class="story-actions">
            <button class="approve-btn" onclick="approveStory('${storyId}')">
                ✅ Approve & Publish
            </button>
            <button class="reject-btn" onclick="rejectStory('${storyId}')">
                ❌ Reject
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

    // You can add total approved count from database if needed
    if (totalApprovedEl) {
        totalApprovedEl.textContent = '—';
    }
}

async function approveStory(storyId) {
    if (!confirm('Are you sure you want to approve and publish this story?')) {
        return {
            "success": True,
            "message": "✅ Story approved and moved to approved_stories"
        }
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
            showStatusMessage('Story approved and published successfully!', 'success');
            loadPendingStories(); // Refresh the list
        } else {
            showStatusMessage('Failed to approve story: ' + (data.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error approving story:', error);
        showStatusMessage('Error approving story: ' + error.message, 'error');
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

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            showStatusMessage('Story rejected', 'success');
            loadPendingStories(); // Refresh the list
        } else {
            showStatusMessage('Failed to reject story: ' + (data.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error rejecting story:', error);
        showStatusMessage('Error rejecting story: ' + error.message, 'error');
    }
}