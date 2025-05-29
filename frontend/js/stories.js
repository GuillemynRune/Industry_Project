// Stories functionality
async function loadApprovedStories() {
    try {
        const response = await fetch(`${API_BASE_URL}/stories?limit=6&random=true`);
        const data = await response.json();
        
        if (data.success) {
            displayStories(data.stories);
        }
    } catch (error) {
        console.error('Error loading stories:', error);
        displaySampleStories();
    }
}

function displayStories(stories) {
    const storiesGrid = document.getElementById('storiesGrid');
    storiesGrid.innerHTML = '';
    
    if (stories.length === 0) {
        displaySampleStories();
        return;
    }
    
    stories.forEach((story, index) => {
        const storyCard = createStoryCard(story, index);
        storiesGrid.appendChild(storyCard);
    });
}

function createStoryCard(story, index) {
    const card = document.createElement('div');
    card.className = 'story-card';
    card.style.animationDelay = `${index * 0.1}s`;
    
    const preview = story.generated_story ? 
        story.generated_story.substring(0, 200) + '...' : 
        story.experience.substring(0, 200) + '...';
    
    card.innerHTML = `
        <div class="story-title">${story.challenge || 'A Recovery Journey'}</div>
        <div class="story-preview">${preview}</div>
        <div class="story-meta">
            <span>By ${story.author_name} • ${getTimeAgo(story.created_at)}</span>
            <a href="#" class="read-more" onclick="viewFullStory('${story._id}')">Read more →</a>
        </div>
    `;
    
    return card;
}

function displaySampleStories() {
    const sampleStories = [
        {
            title: "Finding Light in Dark Days",
            preview: "Sarah's journey through the fog of early motherhood, where simple tasks felt mountainous and joy seemed distant. But small moments of connection with her baby became stepping stones back to herself...",
            time: "3 days ago"
        },
        {
            title: "The Weight of Expectations",
            preview: "Emma thought she'd feel instant maternal bliss, but instead found herself grieving her old life while trying to love her new reality. Her story of accepting imperfection and finding support...",
            time: "1 week ago"
        },
        {
            title: "Sleepless Nights, Hopeful Days",
            preview: "When Maria's baby wouldn't sleep, neither could she. The exhaustion felt endless, but connecting with other parents online became her lifeline during those 3 AM feeding sessions...",
            time: "2 weeks ago"
        },
        {
            title: "Breaking Through the Silence",
            preview: "Alex struggled with postpartum anxiety in silence for months, afraid to admit she wasn't enjoying motherhood. Finally opening up to her partner changed everything...",
            time: "1 month ago"
        },
        {
            title: "From Isolation to Connection",
            preview: "Living far from family, Jamie felt utterly alone with her newborn. Joining a local parent group seemed impossible at first, but it became her greatest source of strength...",
            time: "2 months ago"
        },
        {
            title: "Healing One Day at a Time",
            preview: "Recovery wasn't linear for Kate. Some days were harder than others, but celebrating small victories - a shower, a walk, a genuine smile - helped her rebuild her sense of self...",
            time: "3 months ago"
        }
    ];
    
    const storiesGrid = document.getElementById('storiesGrid');
    storiesGrid.innerHTML = '';
    
    sampleStories.forEach((story, index) => {
        const card = document.createElement('div');
        card.className = 'story-card';
        card.style.animationDelay = `${index * 0.1}s`;
        
        card.innerHTML = `
            <div class="story-title">${story.title}</div>
            <div class="story-preview">${story.preview}</div>
            <div class="story-meta">
                <span>${story.time}</span>
                <a href="#" class="read-more">Read more →</a>
            </div>
        `;
        
        storiesGrid.appendChild(card);
    });
}

function viewFullStory(storyId) {
    alert('Full story view coming soon!');
}

async function searchSimilarStories() {
    const searchInput = document.getElementById('searchInput').value;
    if (!searchInput.trim()) {
        alert('Please describe what you\'re looking for to find similar stories.');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/search-similar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: searchInput })
        });

        const data = await response.json();
        
        if (data.success && data.results.length > 0) {
            displayStories(data.results);
        } else {
            alert('No similar stories found. Try different keywords.');
        }
    } catch (error) {
        console.error('Search error:', error);
        alert('Unable to search right now. Please make sure the backend is running.');
    }
}

function handleShareStoryClick() {
    if (!currentUser) {
        showStatusMessage('Please login or create an account to share your story.', 'warning');
        scrollToSection('authSection');
        return;
    }
    openModal('shareModal');
}

// Handle story submission
document.getElementById('shareForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    if (!currentUser) {
        showStatusMessage('Please login to share your story.', 'error');
        return;
    }
    
    const authorName = document.getElementById('authorName').value;
    const challenge = document.getElementById('challenge').value;
    const experience = document.getElementById('experience').value;
    const solution = document.getElementById('solution').value;
    const advice = document.getElementById('advice').value;
    
    if (!challenge.trim() || !experience.trim() || !solution.trim()) {
        showStatusMessage('Please fill in the challenge, experience, and solution fields.', 'error');
        return;
    }

    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.innerHTML;
    submitBtn.innerHTML = '<span class="loading"></span> Submitting...';
    submitBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/stories/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                author_name: authorName,
                challenge: challenge,
                experience: experience,
                solution: solution,
                advice: advice
            })
        });

        const data = await response.json();
        
        if (data.success) {
            if (data.requires_immediate_support) {
                closeModal('shareModal');
                showCrisisResourcesModal(data.crisis_resources);
            } else {
                showStatusMessage('Thank you for sharing! Your story has been submitted for review and will be published within 24-48 hours.', 'success');
                this.reset();
                closeModal('shareModal');
            }
        } else {
            showStatusMessage(data.message || 'Error submitting story', 'error');
        }
    } catch (error) {
        showStatusMessage('Unable to submit story. Please try again.', 'error');
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
});

function showCrisisResourcesModal(resources) {
    openModal('crisisModal');
}