// Authentication functionality
let tokenExpiryTimer = null;

function initializeAuth() {
    const token = localStorage.getItem('authToken');
    const tokenExpiry = localStorage.getItem('tokenExpiry');
    
    if (token && tokenExpiry && Date.now() < parseInt(tokenExpiry)) {
        authToken = token;
        setupTokenExpiryTimer(parseInt(tokenExpiry) - Date.now());
        fetchUserInfo();
    } else {
        handleTokenExpiry();
    }
    
    // Check for password reset token in URL
    checkPasswordResetToken();
}

function checkPasswordResetToken() {
    const urlParams = new URLSearchParams(window.location.search);
    const resetToken = urlParams.get('token');
    
    // Check if we're on reset-password page or have token parameter
    if (resetToken || window.location.pathname === '/reset-password') {
        const token = resetToken || urlParams.get('token');
        if (token) {
            // Clear URL parameters
            window.history.replaceState({}, document.title, '/');
            // Show reset password modal
            showResetPasswordModal(token);
        }
    }
}

function setupTokenExpiryTimer(timeUntilExpiry) {
    if (tokenExpiryTimer) clearTimeout(tokenExpiryTimer);
    
    const refreshTime = timeUntilExpiry - (5 * 60 * 1000); // 5 minutes before expiry
    if (refreshTime > 0) {
        tokenExpiryTimer = setTimeout(refreshToken, refreshTime);
    } else {
        refreshToken();
    }
}

async function refreshToken() {
    try {
        const response = await makeAuthenticatedRequest(`${API_BASE_URL}/auth/refresh`, { method: 'POST' });
        if (response.ok) {
            const data = await response.json();
            authToken = data.access_token;
            const expiryTime = Date.now() + (data.expires_in * 1000);
            
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('tokenExpiry', expiryTime.toString());
            setupTokenExpiryTimer(data.expires_in * 1000);
        } else {
            throw new Error('Token refresh failed');
        }
    } catch (error) {
        console.error('Token refresh error:', error);
        handleTokenExpiry();
    }
}

function handleTokenExpiry() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('tokenExpiry');
    
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
    if (!authToken) throw new Error('No authentication token');
    
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
    const forms = { login: 'loginForm', register: 'registerForm' };
    const tabs = { login: 'loginTab', register: 'registerTab' };
    
    Object.values(forms).forEach(form => {
        document.getElementById(form).style.display = 'none';
    });
    Object.values(tabs).forEach(tab => {
        document.getElementById(tab).classList.remove('active');
    });
    
    document.getElementById(forms[type]).style.display = 'block';
    document.getElementById(tabs[type]).classList.add('active');
}

async function logout() {
    try {
        if (authToken) {
            await makeAuthenticatedRequest(`${API_BASE_URL}/auth/logout`, { method: 'POST' });
        }
    } catch (error) {
        console.error('Logout API error:', error);
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

// Forgot Password Functions
function showForgotPasswordModal() {
    document.getElementById('forgotPasswordModal').style.display = 'block';
    // Focus on email input after animation
    setTimeout(() => {
        document.getElementById('forgotEmail').focus();
    }, 300);
}

function showResetPasswordModal(token) {
    document.getElementById('resetPasswordModal').style.display = 'block';
    document.getElementById('resetToken').value = token;
    // Focus on password input after animation
    setTimeout(() => {
        document.getElementById('newPassword').focus();
    }, 300);
}

async function requestPasswordReset(email) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/forgot-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });

        const data = await response.json();
        
        if (response.ok) {
            showToast(
                'If an account with that email exists, we\'ve sent reset instructions. Check your email!',
                'success',
                'Reset Email Sent'
            );
            closeModal('forgotPasswordModal');
        } else {
            showToast(data.detail || 'Unable to process request. Please try again.', 'error');
        }
    } catch (error) {
        console.error('Password reset request error:', error);
        showToast('Connection error. Please check your internet and try again.', 'error', 'Connection Problem');
    }
}

async function resetPassword(token, newPassword) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token, new_password: newPassword })
        });

        const data = await response.json();
        
        if (response.ok) {
            showToast(
                'Password reset successful! You can now log in with your new password.',
                'success',
                'Password Updated'
            );
            closeModal('resetPasswordModal');
            // Switch to login form
            switchAuth('login');
            scrollToSection('authSection');
        } else {
            showToast(data.detail || 'Unable to reset password. Please try again.', 'error');
        }
    } catch (error) {
        console.error('Password reset error:', error);
        showToast('Connection error. Please check your internet and try again.', 'error', 'Connection Problem');
    }
}

// Validation utilities
function validateEmail(email) {
    return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email);
}

function validatePassword(password) {
    return password.length >= 12 && 
           /[A-Z]/.test(password) && 
           /[a-z]/.test(password) && 
           /\d/.test(password) && 
           /[!@#$%^&*(),.?":{}|<>]/.test(password);
}

function escapeHtml(unsafe) {
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

// Form handlers
async function handleAuthForm(endpoint, formData, successMessage, onSuccess) {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(formData)
        });

        const data = await response.json();
        
        if (response.ok) {
            showToast(successMessage, 'success');
            onSuccess(data);
        } else {
            const errorMessages = {
                401: 'Invalid email or password. Please check your credentials and try again.',
                404: 'Account not found. Please check your email or create a new account.',
                409: 'An account with this email already exists. Try logging in instead.',
                429: 'Too many attempts. Please wait a moment before trying again.',
                500: 'Server error. Please try again in a moment.'
            };
            showToast(errorMessages[response.status] || data.detail || 'Unable to process request. Please try again.', 'error');
        }
    } catch (error) {
        console.error(`${endpoint} error:`, error);
        showToast('Connection error. Please check your internet and try again.', 'error', 'Connection Problem');
    }
}

// Login form handler
document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    
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
    
    await handleAuthForm('login', { email, password }, 
        `Welcome back, ${email}! Great to see you again.`,
        (data) => {
            authToken = data.access_token;
            currentUser = data.user;
            const expiryTime = Date.now() + (data.expires_in * 1000);
            
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('tokenExpiry', expiryTime.toString());
            setupTokenExpiryTimer(data.expires_in * 1000);
            
            showUserSection();
            this.reset();
        }
    );
    
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
});

// Registration form handler
document.getElementById('registerForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const email = document.getElementById('registerEmail').value.trim();
    const password = document.getElementById('registerPassword').value;
    const displayName = document.getElementById('displayName').value.trim();
    const ageVerified = document.getElementById('ageVerification').checked;
    const termsAgreed = document.getElementById('termsAgreement').checked;
    
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
    
    await handleAuthForm('register', {
        email,
        password,
        display_name: displayName || null,
        age_verified: ageVerified,
        agrees_to_terms: termsAgreed
    }, 'Welcome to our community! Your account has been created successfully. Please login with your new credentials.', 
    () => {
        switchAuth('login');
        this.reset();
    });
    
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
});

// Forgot password form handler
document.getElementById('forgotPasswordForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const email = document.getElementById('forgotEmail').value.trim();
    
    if (!validateEmail(email)) {
        showToast('Please enter a valid email address.', 'error', 'Invalid Email');
        return;
    }
    
    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Sending...';
    submitBtn.disabled = true;
    
    await requestPasswordReset(email);
    
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
    this.reset();
});

// Reset password form handler
document.getElementById('resetPasswordForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const token = document.getElementById('resetToken').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    if (!newPassword || newPassword !== confirmPassword) {
        showToast('Passwords do not match. Please try again.', 'error', 'Password Mismatch');
        return;
    }
    
    if (!validatePassword(newPassword)) {
        showToast('Password must be at least 12 characters and include uppercase, lowercase, numbers, and special characters.', 'error', 'Password Too Weak');
        return;
    }
    
    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Resetting...';
    submitBtn.disabled = true;
    
    await resetPassword(token, newPassword);
    
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
    this.reset();
});