// Enhanced Authentication functionality with security improvements
let tokenExpiryTimer = null;

function initializeAuth() {
    const token = localStorage.getItem('authToken');
    const tokenExpiry = localStorage.getItem('tokenExpiry');
    
    if (token && tokenExpiry) {
        const now = Date.now();
        const expiry = parseInt(tokenExpiry);
        
        if (now < expiry) {
            authToken = token;
            setupTokenExpiryTimer(expiry - now);
            fetchUserInfo();
        } else {
            handleTokenExpiry();
        }
    } else {
        showAuthSection();
    }
}

function setupTokenExpiryTimer(timeUntilExpiry) {
    // Clear existing timer
    if (tokenExpiryTimer) {
        clearTimeout(tokenExpiryTimer);
    }
    
    // Set timer to refresh token 5 minutes before expiry
    const refreshTime = timeUntilExpiry - (5 * 60 * 1000); // 5 minutes before expiry
    
    if (refreshTime > 0) {
        tokenExpiryTimer = setTimeout(refreshToken, refreshTime);
    } else {
        // Token expires soon, try to refresh immediately
        refreshToken();
    }
}

async function refreshToken() {
    try {
        const response = await makeAuthenticatedRequest(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST'
        });

        if (response.ok) {
            const data = await response.json();
            authToken = data.access_token;
            const expiryTime = Date.now() + (data.expires_in * 1000);
            
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('tokenExpiry', expiryTime.toString());
            
            setupTokenExpiryTimer(data.expires_in * 1000);
            console.log('Token refreshed successfully');
        } else {
            throw new Error('Token refresh failed');
        }
    } catch (error) {
        console.error('Token refresh error:', error);
        handleTokenExpiry();
    }
}

function handleTokenExpiry() {
    // Clear stored auth data
    localStorage.removeItem('authToken');
    localStorage.removeItem('tokenExpiry');
    
    // Clear timer
    if (tokenExpiryTimer) {
        clearTimeout(tokenExpiryTimer);
        tokenExpiryTimer = null;
    }
    
    authToken = null;
    currentUser = null;
    showAuthSection();
    showStatusMessage('Session expired. Please login again.', 'warning');
}

async function makeAuthenticatedRequest(url, options = {}) {
    if (!authToken) {
        throw new Error('No authentication token');
    }
    
    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (response.status === 401) {
            handleTokenExpiry();
            throw new Error('Authentication failed');
        }
        
        return response;
    } catch (error) {
        if (error.message.includes('Authentication failed') || error.message.includes('token')) {
            handleTokenExpiry();
        }
        throw error;
    }
}

async function fetchUserInfo() {
    try {
        const response = await makeAuthenticatedRequest(`${API_BASE_URL}/auth/me`);

        if (response.ok) {
            currentUser = await response.json();
            showUserSection();
        } else {
            handleTokenExpiry();
        }
    } catch (error) {
        console.error('Error fetching user info:', error);
        handleTokenExpiry();
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
                <span>Welcome, ${escapeHtml(currentUser.display_name)}</span>
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

async function logout() {
    try {
        // Call logout endpoint to blacklist token
        if (authToken) {
            await makeAuthenticatedRequest(`${API_BASE_URL}/auth/logout`, {
                method: 'POST'
            });
        }
    } catch (error) {
        console.error('Logout API error:', error);
        // Continue with client-side logout even if API fails
    }
    
    // Clear all auth data
    localStorage.removeItem('authToken');
    localStorage.removeItem('tokenExpiry');
    
    if (tokenExpiryTimer) {
        clearTimeout(tokenExpiryTimer);
        tokenExpiryTimer = null;
    }
    
    authToken = null;
    currentUser = null;
    showAuthSection();
    showStatusMessage('Logged out successfully.', 'success');
}

// Input validation and sanitization
function validateEmail(email) {
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    return emailRegex.test(email);
}

function validatePassword(password) {
    const minLength = 12;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    
    return password.length >= minLength && hasUpperCase && hasLowerCase && hasNumbers && hasSpecialChar;
}

function escapeHtml(unsafe) {
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

function getPasswordStrength(password) {
    let strength = 0;
    if (password.length >= 12) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) strength++;
    
    return strength;
}

function updatePasswordStrength(password) {
    const strengthMeter = document.getElementById('passwordStrength');
    if (!strengthMeter) return;
    
    const strength = getPasswordStrength(password);
    const strengthText = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'][strength];
    const strengthColor = ['#d32f2f', '#f57c00', '#fbc02d', '#689f38', '#388e3c'][strength];
    
    strengthMeter.textContent = `Password Strength: ${strengthText}`;
    strengthMeter.style.color = strengthColor;
}

// Enhanced login form handler
document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    
    // Client-side validation
    if (!validateEmail(email)) {
        showStatusMessage('Please enter a valid email address.', 'error');
        return;
    }
    
    if (!password) {
        showStatusMessage('Please enter your password.', 'error');
        return;
    }
    
    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Logging in...';
    submitBtn.disabled = true;
    
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
            const expiryTime = Date.now() + (data.expires_in * 1000);
            
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('tokenExpiry', expiryTime.toString());
            
            setupTokenExpiryTimer(data.expires_in * 1000);
            
            showStatusMessage('Login successful! Welcome back.', 'success');
            showUserSection();
            this.reset();
        } else {
            showStatusMessage(data.detail || 'Login failed', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showStatusMessage('Login failed. Please try again.', 'error');
    } finally {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
});

// Enhanced registration form handler
document.getElementById('registerForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const email = document.getElementById('registerEmail').value.trim();
    const password = document.getElementById('registerPassword').value;
    const displayName = document.getElementById('displayName').value.trim();
    const ageVerified = document.getElementById('ageVerification').checked;
    const termsAgreed = document.getElementById('termsAgreement').checked;
    
    // Enhanced validation
    if (!validateEmail(email)) {
        showStatusMessage('Please enter a valid email address.', 'error');
        return;
    }
    
    if (!validatePassword(password)) {
        showStatusMessage('Password must be at least 12 characters with uppercase, lowercase, number, and special character.', 'error');
        return;
    }
    
    if (!ageVerified || !termsAgreed) {
        showStatusMessage('Please confirm your age and agree to the terms.', 'error');
        return;
    }
    
    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Creating Account...';
    submitBtn.disabled = true;
    
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
        console.error('Registration error:', error);
        showStatusMessage('Registration failed. Please try again.', 'error');
    } finally {
        submitBtn.textContent = originalText;
        submitBtn.disabled = false;
    }
});

// Add password strength indicator to registration form
document.addEventListener('DOMContentLoaded', function() {
    const passwordField = document.getElementById('registerPassword');
    if (passwordField) {
        // Add password strength indicator
        const strengthIndicator = document.createElement('div');
        strengthIndicator.id = 'passwordStrength';
        strengthIndicator.style.marginTop = '0.5rem';
        strengthIndicator.style.fontSize = '0.9rem';
        passwordField.parentNode.appendChild(strengthIndicator);
        
        passwordField.addEventListener('input', function() {
            updatePasswordStrength(this.value);
        });
    }
});