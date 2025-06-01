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
    showToast('Your session has expired. Please login again to continue.', 'warning', 'Session Expired');
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
                <span class="user-welcome">Welcome, ${escapeHtml(currentUser.display_name)}</span>
                <button class="logout-btn" onclick="logout()">Logout</button>
            </div>
        `;
    } else {
        userSection.innerHTML = `
            <button class="auth-prompt-btn" onclick="scrollToSection('authSection')">Login / Sign Up</button>
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
    showToast('You\'ve been safely logged out. Thanks for visiting!', 'success', 'See You Soon!');
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
        showToast('Please enter a valid email address to continue.', 'error', 'Invalid Email');
        return;
    }
    
    if (!password) {
        showToast('Please enter your password to login.', 'error', 'Password Required');
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
            
            showToast(`Welcome back, ${data.user.display_name || 'there'}! Great to see you again.`, 'success', 'Login Successful!');
            showUserSection();
            this.reset();
        } else {
            const errorMessages = {
                401: 'Invalid email or password. Please check your credentials and try again.',
                404: 'Account not found. Please check your email or create a new account.',
                429: 'Too many login attempts. Please wait a moment before trying again.',
                500: 'Server error. Please try again in a moment.'
            };
            showToast(errorMessages[response.status] || data.detail || 'Unable to login right now. Please try again.', 'error', 'Login Failed');
        }
    } catch (error) {
        console.error('Login error:', error);
        showToast('Connection error. Please check your internet and try again.', 'error', 'Connection Problem');
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
        showToast('Please enter a valid email address to create your account.', 'error', 'Invalid Email');
        return;
    }
    
    if (!validatePassword(password)) {
        showToast('Password must be at least 12 characters and include uppercase, lowercase, numbers, and special characters for your security.', 'error', 'Password Too Weak');
        return;
    }
    
    if (!ageVerified || !termsAgreed) {
        showToast('Please confirm your age and agree to our terms to continue.', 'warning', 'Agreement Required');
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
            showToast('Welcome to our community! Your account has been created successfully. Please login with your new credentials.', 'success', 'Account Created!');
            switchAuth('login');
            this.reset();
        } else {
            const errorMessages = {
                409: 'An account with this email already exists. Try logging in instead.',
                400: 'Please check your information and try again.',
                500: 'Server error. Please try again in a moment.'
            };
            showToast(errorMessages[response.status] || data.detail || 'Unable to create account right now. Please try again.', 'error', 'Registration Failed');
        }
    } catch (error) {
        console.error('Registration error:', error);
        showToast('Connection error. Please check your internet and try again.', 'error', 'Connection Problem');
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