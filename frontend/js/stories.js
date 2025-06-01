// Stories functionality with carousel
let storyCarousel = null;

class StoryCarousel {
    constructor(container, options = {}) {
        this.container = container;
        this.track = container.querySelector('.stories-track');
        this.prevBtn = document.getElementById('prevBtn');
        this.nextBtn = document.getElementById('nextBtn');
        this.dotsContainer = document.getElementById('dotsContainer');
        this.autoPlayInterval = options.autoPlayInterval || 5000;
        this.storiesPerSlide = 3;
        this.currentSlide = 0;
        this.totalSlides = 0;
        this.isPlaying = true;
        this.autoPlayTimer = null;
        this.stories = [];
        this.bindEvents();
    }
    
    bindEvents() {
        this.prevBtn.addEventListener('click', () => this.navigate('prev'));
        this.nextBtn.addEventListener('click', () => this.navigate('next'));
        this.container.addEventListener('mouseenter', () => this.pauseAutoPlay());
        this.container.addEventListener('mouseleave', () => this.resumeAutoPlay());
        
        // Touch support
        let startX = 0;
        this.track.addEventListener('touchstart', (e) => startX = e.touches[0].clientX);
        this.track.addEventListener('touchend', (e) => {
            const diff = startX - e.changedTouches[0].clientX;
            if (Math.abs(diff) > 50) {
                this.navigate(diff > 0 ? 'next' : 'prev');
            }
        });
    }
    
    navigate(direction) {
        if (direction === 'next') this.nextSlide();
        else this.previousSlide();
        this.resetAutoPlay();
    }
    
    loadStories(stories) {
        this.stories = stories;
        this.createSlides();
        this.createDots();
        this.startAutoPlay();
        this.updateControls();
    }
    
    createSlides() {
        this.totalSlides = Math.ceil(this.stories.length / this.storiesPerSlide);
        this.track.innerHTML = '';
        
        for (let i = 0; i < this.totalSlides; i++) {
            const slide = document.createElement('div');
            slide.className = 'stories-slide';
            
            const startIndex = i * this.storiesPerSlide;
            const slideStories = this.stories.slice(startIndex, startIndex + this.storiesPerSlide);
            
            slideStories.forEach((story, index) => {
                slide.appendChild(this.createStoryCard(story, startIndex + index));
            });
            
            this.track.appendChild(slide);
        }
    }
    
    createStoryCard(story, index) {
        const card = document.createElement('div');
        card.className = 'story-card';
        card.style.animationDelay = `${(index % this.storiesPerSlide) * 0.1}s`;
        
        const preview = story.generated_story?.substring(0, 200) + '...' || 
                       story.preview || 
                       story.experience?.substring(0, 200) + '...' || 
                       'A recovery story...';
        
        const title = story.challenge || story.title || 'A Recovery Journey';
        const author = story.author_name || story.author || 'Anonymous';
        const time = story.created_at ? getTimeAgo(story.created_at) : story.time || 'Recently';
        const storyId = story._id || story.id || '';
        
        const readMoreAction = storyId ? 
            `onclick="viewFullStory('${storyId}', event)"` :
            `onclick="showSampleStoryMessage()"`;
        
        card.innerHTML = `
            <div class="story-title">${title}</div>
            <div class="story-preview">${preview}</div>
            <div class="story-meta">
                <span>By ${author} • ${time}</span>
                <a href="javascript:void(0)" class="read-more" ${readMoreAction}>Read more →</a>
            </div>
        `;
        
        return card;
    }
    
    createDots() {
        this.dotsContainer.innerHTML = '';
        for (let i = 0; i < this.totalSlides; i++) {
            const dot = document.createElement('div');
            dot.className = 'dot';
            if (i === 0) dot.classList.add('active');
            dot.addEventListener('click', () => {
                this.goToSlide(i);
                this.resetAutoPlay();
            });
            this.dotsContainer.appendChild(dot);
        }
    }
    
    goToSlide(index) {
        this.currentSlide = index;
        this.track.style.transform = `translateX(${-index * 100}%)`;
        this.updateControls();
    }
    
    nextSlide() {
        this.goToSlide((this.currentSlide + 1) % this.totalSlides);
    }
    
    previousSlide() {
        this.goToSlide(this.currentSlide === 0 ? this.totalSlides - 1 : this.currentSlide - 1);
    }
    
    updateControls() {
        this.dotsContainer.querySelectorAll('.dot').forEach((dot, index) => {
            dot.classList.toggle('active', index === this.currentSlide);
        });
    }
    
    startAutoPlay() {
        if (!this.isPlaying || this.totalSlides <= 1) return;
        this.autoPlayTimer = setTimeout(() => {
            this.nextSlide();
            this.startAutoPlay();
        }, this.autoPlayInterval);
    }
    
    stopAutoPlay() {
        if (this.autoPlayTimer) {
            clearTimeout(this.autoPlayTimer);
            this.autoPlayTimer = null;
        }
    }
    
    pauseAutoPlay() {
        this.isPlaying = false;
        this.stopAutoPlay();
    }
    
    resumeAutoPlay() {
        this.isPlaying = true;
        this.startAutoPlay();
    }
    
    resetAutoPlay() {
        this.stopAutoPlay();
        if (this.isPlaying) this.startAutoPlay();
    }
}

// Story loading functions
async function loadApprovedStories() {
    try {
        const response = await fetch(`${API_BASE_URL}/stories?limit=9&random=true`);
        const data = await response.json();
        
        if (data.success && data.stories.length > 0) {
            displayStories(data.stories);
        } else {
            displaySampleStories();
        }
    } catch (error) {
        console.error('Error loading stories:', error);
        displaySampleStories();
    }
}

function displayStories(stories) {
    const carousel = document.getElementById('storiesCarousel');
    if (!carousel) return;
    
    if (!storyCarousel) {
        storyCarousel = new StoryCarousel(carousel);
    }
    storyCarousel.loadStories(stories);
}

function displaySampleStories() {
    const sampleStories = [
        {
            title: "Finding Light in Dark Days",
            preview: "Sarah's journey through the fog of early motherhood, where simple tasks felt mountainous and joy seemed distant. But small moments of connection with her baby became stepping stones back to herself...",
            author: "Sarah", time: "3 days ago"
        },
        {
            title: "The Weight of Expectations",
            preview: "Emma thought she'd feel instant maternal bliss, but instead found herself grieving her old life while trying to love her new reality. Her story of accepting imperfection and finding support...",
            author: "Emma", time: "1 week ago"
        },
        {
            title: "Sleepless Nights, Hopeful Days",
            preview: "When Maria's baby wouldn't sleep, neither could she. The exhaustion felt endless, but connecting with other parents online became her lifeline during those 3 AM feeding sessions...",
            author: "Maria", time: "2 weeks ago"
        },
        {
            title: "Breaking Through the Silence",
            preview: "Alex struggled with postpartum anxiety in silence for months, afraid to admit she wasn't enjoying motherhood. Finally opening up to her partner changed everything...",
            author: "Alex", time: "1 month ago"
        },
        {
            title: "From Isolation to Connection",
            preview: "Living far from family, Jamie felt utterly alone with her newborn. Joining a local parent group seemed impossible at first, but it became her greatest source of strength...",
            author: "Jamie", time: "2 months ago"
        },
        {
            title: "Healing One Day at a Time",
            preview: "Recovery wasn't linear for Kate. Some days were harder than others, but celebrating small victories - a shower, a walk, a genuine smile - helped her rebuild her sense of self...",
            author: "Kate", time: "3 months ago"
        },
        {
            title: "The Power of Professional Help",
            preview: "David was hesitant to seek therapy, thinking he should be able to handle everything himself. But working with a counselor gave him tools he never knew he needed...",
            author: "David", time: "4 months ago"
        },
        {
            title: "Rebuilding My Identity",
            preview: "After becoming a mother, Lisa felt like she'd lost herself completely. Through small daily practices and self-compassion, she learned to honor both her old and new selves...",
            author: "Lisa", time: "5 months ago"
        },
        {
            title: "Finding Strength in Vulnerability",
            preview: "When Rachel finally shared her struggles with her family, she was surprised by how much support was waiting for her. Sometimes the first step is just saying 'I need help'...",
            author: "Rachel", time: "6 months ago"
        }
    ];
    displayStories(sampleStories);
}

// Story viewing functions
async function viewFullStory(storyId, event) {
    if (event) event.preventDefault();
    if (!storyId) {
        showToast('Story not found', 'error', 'Error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/stories/${storyId}`);
        
        if (!response.ok) {
            const errorMessages = {
                404: 'This story is no longer available.',
                500: 'Server error loading story. Our team has been notified.'
            };
            showToast(errorMessages[response.status] || `Error loading story (${response.status}). Please try again.`, 'error', 'Loading Error');
            return;
        }

        const data = await response.json();
        if (data.success && data.story) {
            showFullStoryModal(data.story);
        } else {
            showToast('Story not found', 'error', 'Story Not Found');
        }
    } catch (error) {
        console.error('Error loading story:', error);
        const errorMessage = error instanceof TypeError && error.message.includes('fetch') ?
            'Connection error. Please check your internet and try again.' :
            'Unable to load story. Please try again.';
        showToast(errorMessage, 'error', 'Loading Error');
    }
}

function showFullStoryModal(story) {
    const modal = document.getElementById('fullStoryModal') || createStoryModal('fullStoryModal');
    
    const content = {
        title: story.challenge || story.title || 'Recovery Story',
        author: story.author_name || story.author || 'Anonymous',
        story: story.generated_story || story.story || 'Story content not available',
        date: story.created_at ? new Date(story.created_at).toLocaleDateString() : 'Recently',
        experience: story.experience || '',
        solution: story.solution || '',
        advice: story.advice || ''
    };

    const sections = [
        { title: 'Recovery Story', content: `<div class="generated-story-preview">${content.story}</div>` },
        content.experience && { title: 'Original Experience', content: `<div class="field-content">${content.experience}</div>` },
        content.solution && { title: 'What Helped', content: `<div class="field-content">${content.solution}</div>` },
        content.advice && { title: 'Advice to Others', content: `<div class="field-content">${content.advice}</div>` }
    ].filter(Boolean);

    modal.querySelector('.modal-content').innerHTML = `
        <span class="close" onclick="closeModal('fullStoryModal')">&times;</span>
        <div class="story-detail-header">
            <div class="story-title-section">
                <h2>${content.title}</h2>
                <div class="story-meta">
                    <span>By ${content.author} • ${content.date}</span>
                </div>
            </div>
        </div>
        <div class="story-detail-content">
            ${sections.map(section => `
                <div class="story-section">
                    <h3>${section.title}</h3>
                    ${section.content}
                </div>
            `).join('')}
        </div>
        <div class="story-viewer-actions">
            <button class="btn btn-secondary" onclick="closeModal('fullStoryModal')">Close Story</button>
        </div>
    `;

    openModal('fullStoryModal');
}

function createStoryModal(modalId) {
    const modal = document.createElement('div');
    modal.id = modalId;
    modal.className = 'modal story-detail-modal';
    modal.innerHTML = `<div class="modal-content story-detail-modal-content"></div>`;
    document.body.appendChild(modal);
    return modal;
}

// Search functionality
async function searchSimilarStories() {
    const searchInput = document.getElementById('searchInput').value;
    if (!searchInput.trim()) {
        alert('Please describe what you\'re looking for to find similar stories.');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/search-similar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
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

// Story sharing
function handleShareStoryClick() {
    if (!currentUser) {
        showToast('Please create an account or login to share your story with our community.', 'warning', 'Login Required');
        scrollToSection('authSection');
        return;
    }
    openModal('shareModal');
}

function showSampleStoryMessage() {
    showToast('This is a sample story for demonstration. Real community stories will be available once members start sharing their experiences!', 'warning', 'Sample Story');
}

function showCrisisResourcesModal(resources) {
    openModal('crisisModal');
}

// Handle story submission
document.getElementById('shareForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    if (!currentUser) {
        showToast('Please login to share your story with our supportive community.', 'warning', 'Login Required');
        return;
    }
    
    const formData = {
        author_name: document.getElementById('authorName').value,
        challenge: document.getElementById('challenge').value,
        experience: document.getElementById('experience').value,
        solution: document.getElementById('solution').value,
        advice: document.getElementById('advice').value
    };
    
    if (!formData.challenge.trim() || !formData.experience.trim() || !formData.solution.trim()) {
        showToast('Please fill in your challenge, experience, and solution to help others understand your journey.', 'warning', 'More Details Needed');
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
            body: JSON.stringify(formData)
        });

        const data = await response.json();
        
        if (data.success) {
            if (data.requires_immediate_support) {
                closeModal('shareModal');
                showCrisisResourcesModal(data.crisis_resources);
            } else {
                showToast('Thank you for sharing your journey! Your story has been submitted and will be reviewed within 24-48 hours before being shared with our community.', 'success', 'Story Submitted!');
                this.reset();
                closeModal('shareModal');
            }
        } else {
            showToast(data.message || 'We couldn\'t submit your story right now. Please try again in a moment.', 'error', 'Submission Error');
        }
    } catch (error) {
        showToast('Connection error. Please check your internet and try submitting again.', 'error', 'Connection Problem');
    } finally {
        submitBtn.innerHTML = originalText;
        submitBtn.disabled = false;
    }
});