// Stories functionality with carousel
let storyCarousel = null;

class StoryCarousel {
    constructor(container, options = {}) {
        this.container = container;
        this.track = container.querySelector('.stories-track');
        this.prevBtn = document.getElementById('prevBtn');
        this.nextBtn = document.getElementById('nextBtn');
        this.dotsContainer = document.getElementById('dotsContainer');
        
        // Options
        this.autoPlayInterval = options.autoPlayInterval || 5000;
        this.storiesPerSlide = 3;
        
        // State
        this.currentSlide = 0;
        this.totalSlides = 0;
        this.isPlaying = true;
        this.autoPlayTimer = null;
        this.stories = [];
        
        this.bindEvents();
    }
    
    bindEvents() {
        this.prevBtn.addEventListener('click', () => {
            this.previousSlide();
            this.resetAutoPlay();
        });
        
        this.nextBtn.addEventListener('click', () => {
            this.nextSlide();
            this.resetAutoPlay();
        });
        
        // Hover to pause
        this.container.addEventListener('mouseenter', () => {
            this.pauseAutoPlay();
        });
        
        this.container.addEventListener('mouseleave', () => {
            this.resumeAutoPlay();
        });
        
        // Touch/swipe support
        let startX = 0;
        let endX = 0;
        
        this.track.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
        });
        
        this.track.addEventListener('touchend', (e) => {
            endX = e.changedTouches[0].clientX;
            const diff = startX - endX;
            
            if (Math.abs(diff) > 50) {
                if (diff > 0) {
                    this.nextSlide();
                } else {
                    this.previousSlide();
                }
                this.resetAutoPlay();
            }
        });
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
            const endIndex = Math.min(startIndex + this.storiesPerSlide, this.stories.length);
            const slideStories = this.stories.slice(startIndex, endIndex);
            
            slideStories.forEach((story, index) => {
                const card = this.createStoryCard(story, startIndex + index);
                slide.appendChild(card);
            });
            
            this.track.appendChild(slide);
        }
    }
    
    createStoryCard(story, index) {
        const card = document.createElement('div');
        card.className = 'story-card';
        card.style.animationDelay = `${(index % this.storiesPerSlide) * 0.1}s`;
        
        const preview = story.generated_story ? 
            story.generated_story.substring(0, 200) + '...' : 
            (story.preview || story.experience?.substring(0, 200) + '...' || 'A recovery story...');
        
        const title = story.challenge || story.title || 'A Recovery Journey';
        const author = story.author_name || story.author || 'Anonymous';
        const time = story.created_at ? getTimeAgo(story.created_at) : story.time || 'Recently';
        const storyId = story._id || story.id || '';
        
        card.innerHTML = `
            <div class="story-title">${title}</div>
            <div class="story-preview">${preview}</div>
            <div class="story-meta">
                <span>By ${author} • ${time}</span>
                <a href="#" class="read-more" onclick="viewFullStory('${storyId}')">Read more →</a>
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
        const translateX = -index * 100;
        this.track.style.transform = `translateX(${translateX}%)`;
        this.updateControls();
    }
    
    nextSlide() {
        const nextIndex = (this.currentSlide + 1) % this.totalSlides;
        this.goToSlide(nextIndex);
    }
    
    previousSlide() {
        const prevIndex = this.currentSlide === 0 ? this.totalSlides - 1 : this.currentSlide - 1;
        this.goToSlide(prevIndex);
    }
    
    updateControls() {
        const dots = this.dotsContainer.querySelectorAll('.dot');
        dots.forEach((dot, index) => {
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
        if (this.isPlaying) {
            this.startAutoPlay();
        }
    }
}

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
            author: "Sarah",
            time: "3 days ago"
        },
        {
            title: "The Weight of Expectations",
            preview: "Emma thought she'd feel instant maternal bliss, but instead found herself grieving her old life while trying to love her new reality. Her story of accepting imperfection and finding support...",
            author: "Emma",
            time: "1 week ago"
        },
        {
            title: "Sleepless Nights, Hopeful Days",
            preview: "When Maria's baby wouldn't sleep, neither could she. The exhaustion felt endless, but connecting with other parents online became her lifeline during those 3 AM feeding sessions...",
            author: "Maria",
            time: "2 weeks ago"
        },
        {
            title: "Breaking Through the Silence",
            preview: "Alex struggled with postpartum anxiety in silence for months, afraid to admit she wasn't enjoying motherhood. Finally opening up to her partner changed everything...",
            author: "Alex",
            time: "1 month ago"
        },
        {
            title: "From Isolation to Connection",
            preview: "Living far from family, Jamie felt utterly alone with her newborn. Joining a local parent group seemed impossible at first, but it became her greatest source of strength...",
            author: "Jamie",
            time: "2 months ago"
        },
        {
            title: "Healing One Day at a Time",
            preview: "Recovery wasn't linear for Kate. Some days were harder than others, but celebrating small victories - a shower, a walk, a genuine smile - helped her rebuild her sense of self...",
            author: "Kate",
            time: "3 months ago"
        },
        {
            title: "The Power of Professional Help",
            preview: "David was hesitant to seek therapy, thinking he should be able to handle everything himself. But working with a counselor gave him tools he never knew he needed...",
            author: "David",
            time: "4 months ago"
        },
        {
            title: "Rebuilding My Identity",
            preview: "After becoming a mother, Lisa felt like she'd lost herself completely. Through small daily practices and self-compassion, she learned to honor both her old and new selves...",
            author: "Lisa",
            time: "5 months ago"
        },
        {
            title: "Finding Strength in Vulnerability",
            preview: "When Rachel finally shared her struggles with her family, she was surprised by how much support was waiting for her. Sometimes the first step is just saying 'I need help'...",
            author: "Rachel",
            time: "6 months ago"
        }
    ];
    
    displayStories(sampleStories);
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
        showToast('Please create an account or login to share your story with our community.', 'warning', 'Login Required');
        scrollToSection('authSection');
        return;
    }
    openModal('shareModal');
}

// Handle story submission
document.getElementById('shareForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    if (!currentUser) {
        showToast('Please login to share your story with our supportive community.', 'warning', 'Login Required');
        return;
    }
    
    const authorName = document.getElementById('authorName').value;
    const challenge = document.getElementById('challenge').value;
    const experience = document.getElementById('experience').value;
    const solution = document.getElementById('solution').value;
    const advice = document.getElementById('advice').value;
    
    if (!challenge.trim() || !experience.trim() || !solution.trim()) {
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

function showCrisisResourcesModal(resources) {
    openModal('crisisModal');
}