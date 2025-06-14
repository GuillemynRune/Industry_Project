// Authentication functionality
let tokenExpiryTimer = null;

// Initialization
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

    checkPasswordResetToken();
}

function checkPasswordResetToken() {
    const urlParams = new URLSearchParams(window.location.search);
    const resetToken = urlParams.get('token');

    if (resetToken) {
        window.history.replaceState({}, document.title, '/');
        showResetPasswordModal(resetToken);
    }
}

// Token Management
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

// User Info Management
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

// UI State Management
function showAuthSection() {
    openModal('authModal');
    updateUserSection();
}

function showUserSection() {
    closeModal('authModal');
    updateUserSection();
    checkAdminAccess();
}

function updateUserSection() {
    const userSection = document.getElementById('userSection');

    if (currentUser) {
        userSection.innerHTML = `
            <div class="user-dropdown">
                <button class="user-menu-btn" onclick="toggleUserMenu()">
                    <span class="user-avatar">${currentUser.display_name.charAt(0).toUpperCase()}</span>
                    <span>${escapeHtml(currentUser.display_name)}</span>
                    <span>▼</span>
                </button>
                <div class="user-menu" id="userMenu">
                    <button class="user-menu-item" onclick="toggleTheme(); closeUserMenu()">
                        <span id="themeIcon">${document.documentElement.getAttribute('data-theme') === 'dark' ? '☀️' : '🌙'}</span>
                        <span id="themeText">${document.documentElement.getAttribute('data-theme') === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
                    </button>
                    <hr style="margin: 0.5rem 0; border: none; border-top: 1px solid rgba(168, 216, 234, 0.3);">
                    <button class="user-menu-item" onclick="logout(); closeUserMenu()">Logout</button>
                    <button class="user-menu-item danger" onclick="showDeleteAccountModal(); closeUserMenu()">Delete Account</button>
                </div>
            </div>
        `;
    } else {
        userSection.innerHTML = `
            <button class="auth-prompt-btn" onclick="openModal('authModal')">Login / Sign Up</button>
        `;
    }
}

function toggleTheme() {
    if (typeof themeManager !== 'undefined') {
        themeManager.toggleTheme();
        // Update dropdown text
        const themeIcon = document.getElementById('themeIcon');
        const themeText = document.getElementById('themeText');
        if (themeIcon && themeText) {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            themeIcon.textContent = isDark ? '☀️' : '🌙';
            themeText.textContent = isDark ? 'Light Mode' : 'Dark Mode';
        }
    }
}

function toggleUserMenu() {
    const dropdown = document.querySelector('.user-dropdown');
    dropdown.classList.toggle('open');
}

function closeUserMenu() {
    const dropdown = document.querySelector('.user-dropdown');
    dropdown.classList.remove('open');
}

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
    const dropdown = document.querySelector('.user-dropdown');
    if (dropdown && !dropdown.contains(e.target)) {
        closeUserMenu();
    }
});

function addTourLinkIfNeeded() {
    if (!document.getElementById('tourLink')) {
        const navLinks = document.querySelector('.nav-links');
        const tourLi = document.createElement('li');
        tourLi.innerHTML = '<a href="javascript:void(0)" id="tourLink" onclick="startTour()">Take Tour</a>';
        navLinks.appendChild(tourLi);
    }
}

function removeTourLink() {
    const existingTourLink = document.getElementById('tourLink');
    if (existingTourLink) {
        existingTourLink.parentElement.remove();
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

// Password Reset Functions
function showForgotPasswordModal() {
    openModal('forgotPasswordModal');
    setTimeout(() => document.getElementById('forgotEmail').focus(), 300);
}

function showResetPasswordModal(token) {
    document.getElementById('resetToken').value = token;
    openModal('resetPasswordModal');
    setTimeout(() => document.getElementById('newPassword').focus(), 300);
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

// Validation Utilities
function validateEmail(email) {
    return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(email);
}

function validatePassword(password) {
    return password.length >= 8 &&
        /[A-Za-z]/.test(password) &&
        /\d/.test(password);
}

function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Form Handler Utilities
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

function setButtonLoading(button, isLoading, originalText) {
    if (isLoading) {
        button.textContent = button.dataset.loadingText || 'Loading...';
        button.disabled = true;
    } else {
        button.textContent = originalText;
        button.disabled = false;
    }
}

// Form Event Handlers
document.getElementById('loginForm').addEventListener('submit', async function (e) {
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
    setButtonLoading(submitBtn, true, originalText);

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

    setButtonLoading(submitBtn, false, originalText);
});

document.getElementById('registerForm').addEventListener('submit', async function (e) {
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
        showToast('Password must be at least 8 characters and include letters and numbers.', 'error', 'Password Too Weak');
        return;
    }

    if (!ageVerified || !termsAgreed) {
        showToast('Please confirm your age and agree to our terms to continue.', 'warning', 'Agreement Required');
        return;
    }

    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    setButtonLoading(submitBtn, true, originalText);

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

    setButtonLoading(submitBtn, false, originalText);
});

document.getElementById('forgotPasswordForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const email = document.getElementById('forgotEmail').value.trim();

    if (!validateEmail(email)) {
        showToast('Please enter a valid email address.', 'error', 'Invalid Email');
        return;
    }

    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    setButtonLoading(submitBtn, true, originalText);

    await requestPasswordReset(email);

    setButtonLoading(submitBtn, false, originalText);
    this.reset();
});

document.getElementById('resetPasswordForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const token = document.getElementById('resetToken').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    if (!newPassword || newPassword !== confirmPassword) {
        showToast('Passwords do not match. Please try again.', 'error', 'Password Mismatch');
        return;
    }

    if (!validatePassword(newPassword)) {
        showToast('Password must be at least 8 characters and include letters and numbers.', 'error', 'Password Too Weak');
        return;
    }

    const submitBtn = this.querySelector('button[type="submit"]');
    const originalText = submitBtn.textContent;
    setButtonLoading(submitBtn, true, originalText);

    await resetPassword(token, newPassword);

    setButtonLoading(submitBtn, false, originalText);
    this.reset();
});

function showDeleteAccountModal() {
    document.getElementById('deleteEmail').value = currentUser.email || '';
    openModal('deleteAccountModal');
}

document.getElementById('deleteAccountForm').addEventListener('submit', async function (e) {
    e.preventDefault();

    const email = document.getElementById('deleteEmail').value.trim();
    const password = document.getElementById('deletePassword').value;
    const button = this.querySelector('button[type="submit"]');
    const originalText = button.textContent;

    if (!validateEmail(email) || !password) {
        showToast('Please provide valid credentials.', 'error');
        return;
    }

    setButtonLoading(button, true, originalText);

    try {
        const response = await fetch(`${API_BASE_URL}/auth/delete-account`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (response.ok) {
            localStorage.removeItem('authToken');
            localStorage.removeItem('tokenExpiry');
            authToken = null;
            currentUser = null;
            showAuthSection();
            showToast(data.message || 'Account deleted.', 'success');
            closeModal('deleteAccountModal');
        } else {
            showToast(data.detail || 'Unable to delete account.', 'error');
        }
    } catch (err) {
        console.error('Account deletion error:', err);
        showToast('Server error. Please try again later.', 'error');
    }

    setButtonLoading(button, false, originalText);
});
