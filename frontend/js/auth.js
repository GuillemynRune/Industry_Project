// Authentication functionality
function initializeAuth() {
    const token = localStorage.getItem('authToken');
    if (token) {
        authToken = token;
        fetchUserInfo();
    } else {
        showAuthSection();
    }
}

async function fetchUserInfo() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });

        if (response.ok) {
            currentUser = await response.json();
            showUserSection();
        } else {
            localStorage.removeItem('authToken');
            authToken = null;
            showAuthSection();
        }
    } catch (error) {
        console.error('Error fetching user info:', error);
        showAuthSection();
    }
}

function showAuthSection() {
    document.getElementById('authSection').style.display = 'block';
    updateUserSection();
}

function showUserSection() {
    document.getElementById('authSection').style.display = 'none';
    updateUserSection();
    checkAdminAccess();
}

function updateUserSection() {
    const userSection = document.getElementById('userSection');
    
    if (currentUser) {
        userSection.innerHTML = `
            <div class="user-info">
                <div class="user-avatar">${currentUser.display_name.charAt(0).toUpperCase()}</div>
                <span>Welcome, ${currentUser.display_name}</span>
                <button class="btn" onclick="logout()" style="margin-left: 1rem; padding: 0.5rem 1rem; background: var(--light-gray); color: var(--text-dark);">Logout</button>
            </div>
        `;
    } else {
        userSection.innerHTML = `
            <button class="btn btn-primary" onclick="scrollToSection('authSection')">Login / Sign Up</button>
        `;
    }
}

function switchAuth(type) {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const loginTab = document.getElementById('loginTab');
    const registerTab = document.getElementById('registerTab');

    if (type === 'login') {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        loginTab.classList.add('active');
        registerTab.classList.remove('active');
    } else {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        loginTab.classList.remove('active');
        registerTab.classList.add('active');
    }
}

function logout() {
    localStorage.removeItem('authToken');
    authToken = null;
    currentUser = null;
    showAuthSection();
    showStatusMessage('Logged out successfully.', 'success');
}

// Handle login
document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();
        
        if (response.ok) {
            authToken = data.access_token;
            currentUser = data.user;
            localStorage.setItem('authToken', authToken);
            
            showStatusMessage('Login successful! Welcome back.', 'success');
            showUserSection();
            this.reset();
        } else {
            showStatusMessage(data.detail || 'Login failed', 'error');
        }
    } catch (error) {
        showStatusMessage('Login failed. Please try again.', 'error');
    }
});

// Handle registration
document.getElementById('registerForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const displayName = document.getElementById('displayName').value;
    const ageVerified = document.getElementById('ageVerification').checked;
    const termsAgreed = document.getElementById('termsAgreement').checked;
    
    if (!ageVerified || !termsAgreed) {
        showStatusMessage('Please confirm your age and agree to the terms.', 'error');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email,
                password,
                display_name: displayName || null,
                age_verified: ageVerified,
                agrees_to_terms: termsAgreed
            })
        });

        const data = await response.json();
        
        if (response.ok) {
            showStatusMessage('Account created! Please login with your credentials.', 'success');
            switchAuth('login');
            this.reset();
        } else {
            showStatusMessage(data.detail || 'Registration failed', 'error');
        }
    } catch (error) {
        showStatusMessage('Registration failed. Please try again.', 'error');
    }
});