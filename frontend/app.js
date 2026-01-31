// frontend/app.js

// Configuration
const API_URL = '/api/v1';

// State
let currentUser = null;
let accessToken = null;
let currentEditPost = null;
let currentEditComment = null;
let postsSortOrder = 'desc'; // По умолчанию сначала новые
let commentsSortOrder = {}; // Порядок сортировки для каждого поста

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

// Check if user is logged in
function checkAuth() {
    accessToken = localStorage.getItem('accessToken');
    const username = localStorage.getItem('username');

    if (accessToken && username) {
        currentUser = { username };
        showPostsSection();
        loadPosts();
    } else {
        showAuthSection();
    }
}

// Setup Event Listeners
function setupEventListeners() {
    // Auth tabs
    document.querySelectorAll('.auth-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const tabName = tab.dataset.tab;
            if (tabName === 'login') {
                document.getElementById('loginForm').classList.remove('hidden');
                document.getElementById('registerForm').classList.add('hidden');
            } else {
                document.getElementById('loginForm').classList.add('hidden');
                document.getElementById('registerForm').classList.remove('hidden');
            }
        });
    });

    // Login form
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        await login(email, password);
    });

    // Register form
    document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('registerUsername').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        await register(username, email, password);
    });

    // Logout
    document.getElementById('logoutBtn').addEventListener('click', logout);

    // Create post button
    document.getElementById('createPostBtn').addEventListener('click', () => {
        currentEditPost = null;
        document.getElementById('postModalTitle').textContent = 'Создать публикацию';
        document.getElementById('postTitle').value = '';
        document.getElementById('postContent').value = '';
        openModal('postModal');
    });

    // Post form
    document.getElementById('postForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const title = document.getElementById('postTitle').value;
        const content = document.getElementById('postContent').value;

        if (currentEditPost) {
            await updatePost(currentEditPost.id, title, content);
        } else {
            await createPost(title, content);
        }
    });

    // Comment form
    document.getElementById('commentForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const content = document.getElementById('commentContent').value;
        await updateComment(currentEditComment.postId, currentEditComment.id, content);
    });

    // Close modals
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', () => {
            closeAllModals();
        });
    });

    // Close modal on outside click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeAllModals();
            }
        });
    });
}

// API Functions
async function register(username, email, password) {
    try {
        const response = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Ошибка регистрации');
        }

        showSuccess('Регистрация успешна! Теперь войдите в систему.');
        document.querySelector('[data-tab="login"]').click();
    } catch (error) {
        showError(error.message);
    }
}

async function login(email, password) {
    try {
        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Ошибка входа');
        }

        accessToken = data.access_token;
        localStorage.setItem('accessToken', accessToken);
        localStorage.setItem('username', email);

        currentUser = { username: email };
        showSuccess('Вход выполнен успешно!');
        showPostsSection();
        loadPosts();
    } catch (error) {
        showError(error.message);
    }
}

function logout() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('username');
    accessToken = null;
    currentUser = null;
    showAuthSection();
    showSuccess('Вы вышли из системы');
}

async function loadPosts() {
    try {
        const response = await fetch(`${API_URL}/posts`, {
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка загрузки публикаций');
        }

        const posts = await response.json();
        displayPosts(posts);
    } catch (error) {
        showError(error.message);
    }
}


async function createPost(title, content) {
    try {
        const response = await fetch(`${API_URL}/posts`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ title, content, is_published: true })  // ✅ ДОБАВЛЕНО
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка создания публикации');
        }

        showSuccess('Публикация создана!');
        closeAllModals();
        loadPosts();
    } catch (error) {
        showError(error.message);
    }
}


async function updatePost(postId, title, content) {
    try {
        const response = await fetch(`${API_URL}/posts/${postId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ title, content })
        });

        if (!response.ok) {
            throw new Error('Ошибка обновления публикации');
        }

        showSuccess('Публикация обновлена!');
        closeAllModals();
        loadPosts();
    } catch (error) {
        showError(error.message);
    }
}

async function deletePost(postId) {
    if (!confirm('Вы уверены, что хотите удалить эту публикацию?')) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/posts/${postId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });

        if (!response.ok) {
            throw new Error('Ошибка удаления публикации');
        }

        showSuccess('Публикация удалена!');
        loadPosts();
    } catch (error) {
        showError(error.message);
    }
}

async function loadComments(postId) {
    try {
        const response = await fetch(`${API_URL}/posts/${postId}/comments`, {
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });

        if (!response.ok) {
            throw new Error('Ошибка загрузки комментариев');
        }

        const comments = await response.json();
        return comments;
    } catch (error) {
        showError(error.message);
        return [];
    }
}

async function createComment(postId, content) {
    try {
        const response = await fetch(`${API_URL}/posts/${postId}/comments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ content })
        });

        if (!response.ok) {
            throw new Error('Ошибка создания комментария');
        }

        showSuccess('Комментарий добавлен!');
        loadPosts();
    } catch (error) {
        showError(error.message);
    }
}

async function updateComment(postId, commentId, content) {
    try {
        const response = await fetch(`${API_URL}/posts/${postId}/comments/${commentId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${accessToken}`
            },
            body: JSON.stringify({ content })
        });

        if (!response.ok) {
            throw new Error('Ошибка обновления комментария');
        }

        showSuccess('Комментарий обновлён!');
        closeAllModals();
        loadPosts();
    } catch (error) {
        showError(error.message);
    }
}

async function deleteComment(postId, commentId) {
    if (!confirm('Вы уверены, что хотите удалить этот комментарий?')) {
        return;
    }

    try {
        const response = await fetch(`${API_URL}/posts/${postId}/comments/${commentId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });

        if (!response.ok) {
            throw new Error('Ошибка удаления комментария');
        }

        showSuccess('Комментарий удалён!');
        loadPosts();
    } catch (error) {
        showError(error.message);
    }
}

// Display Functions
async function displayPosts(posts) {
    const container = document.getElementById('postsContainer');

    if (posts.length === 0) {
        container.innerHTML = '<p class="loading">Пока нет публикаций. Создайте первую!</p>';
        return;
    }

    container.innerHTML = '';

    for (const post of posts) {
        const comments = await loadComments(post.id);
        const postEl = createPostElement(post, comments);
        container.appendChild(postEl);
    }
}

function createPostElement(post, comments) {
    const postDiv = document.createElement('div');
    postDiv.className = 'post-card';

    const isOwner = post.author_email === currentUser.username;

    postDiv.innerHTML = `
        <div class="post-header">
            <div>
                <h3 class="post-title">${escapeHtml(post.title)}</h3>
                <div class="post-meta">
                    Автор: ${escapeHtml(post.author_email)} • ${formatDate(post.created_at)}
                </div>
            </div>
            ${isOwner ? `
                <div class="post-actions">
                    <button class="btn btn-secondary btn-small edit-post-btn" data-id="${post.id}">Редактировать</button>
                    <button class="btn btn-danger btn-small delete-post-btn" data-id="${post.id}">Удалить</button>
                </div>
            ` : ''}
        </div>
        <div class="post-content">${escapeHtml(post.content)}</div>
        
        <div class="comments-section">
            <div class="comments-header">Комментарии (${comments.length})</div>
            <div class="comments-list" id="comments-${post.id}">
                ${comments.map(c => createCommentHTML(post.id, c)).join('')}
            </div>
            <div class="comment-form">
                <textarea class="comment-input" id="comment-input-${post.id}" placeholder="Добавить комментарий..." rows="2"></textarea>
                <button class="btn btn-primary btn-small add-comment-btn" style="margin-top: 0.5rem;" data-post-id="${post.id}">Добавить комментарий</button>
            </div>
        </div>
    `;

    // Event listeners for post actions
    if (isOwner) {
        postDiv.querySelector('.edit-post-btn').addEventListener('click', () => {
            currentEditPost = post;
            document.getElementById('postModalTitle').textContent = 'Редактировать публикацию';
            document.getElementById('postTitle').value = post.title;
            document.getElementById('postContent').value = post.content;
            openModal('postModal');
        });

        postDiv.querySelector('.delete-post-btn').addEventListener('click', () => {
            deletePost(post.id);
        });
    }

    // Event listener for add comment
    postDiv.querySelector('.add-comment-btn').addEventListener('click', () => {
        const input = document.getElementById(`comment-input-${post.id}`);
        const content = input.value.trim();
        if (content) {
            createComment(post.id, content);
            input.value = '';
        }
    });

    return postDiv;
}

function createCommentHTML(postId, comment) {
    const isOwner = comment.author_email === currentUser.username;

    return `
        <div class="comment">
            <div class="comment-header">
                <span class="comment-author">${escapeHtml(comment.author_email)}</span>
                <span class="post-meta">${formatDate(comment.created_at)}</span>
            </div>
            <div class="comment-content">${escapeHtml(comment.content)}</div>
            ${isOwner ? `
                <div class="comment-actions">
                    <button class="btn btn-secondary btn-small edit-comment-btn" 
                            data-post-id="${postId}" 
                            data-comment-id="${comment.id}" 
                            data-content="${escapeHtml(comment.content)}">
                        Редактировать
                    </button>
                    <button class="btn btn-danger btn-small delete-comment-btn" 
                            data-post-id="${postId}" 
                            data-comment-id="${comment.id}">
                        Удалить
                    </button>
                </div>
            ` : ''}
        </div>
    `;
}

// Utility Functions
function showAuthSection() {
    document.getElementById('authSection').classList.remove('hidden');
    document.getElementById('postsSection').classList.add('hidden');
    document.getElementById('userName').classList.add('hidden');
    document.getElementById('logoutBtn').classList.add('hidden');
}

function showPostsSection() {
    document.getElementById('authSection').classList.add('hidden');
    document.getElementById('postsSection').classList.remove('hidden');
    document.getElementById('userName').classList.remove('hidden');
    document.getElementById('userName').textContent = currentUser.username;
    document.getElementById('logoutBtn').classList.remove('hidden');
}

function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeAllModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.classList.remove('active');
    });
}

function showError(message) {
    const alert = document.getElementById('alertError');
    alert.textContent = message;
    alert.classList.add('show');
    setTimeout(() => alert.classList.remove('show'), 5000);
}

function showSuccess(message) {
    const alert = document.getElementById('alertSuccess');
    alert.textContent = message;
    alert.classList.add('show');
    setTimeout(() => alert.classList.remove('show'), 5000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Event delegation for dynamically created elements
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('edit-comment-btn')) {
        const postId = e.target.dataset.postId;
        const commentId = e.target.dataset.commentId;
        const content = e.target.dataset.content;

        currentEditComment = { postId, id: commentId };
        document.getElementById('commentContent').value = content;
        openModal('commentModal');
    }

    if (e.target.classList.contains('delete-comment-btn')) {
        const postId = e.target.dataset.postId;
        const commentId = e.target.dataset.commentId;
        deleteComment(postId, commentId);
    }
});

function sortItems(items, order) {
    return items.sort((a, b) => {
        const dateA = new Date(a.created_at);
        const dateB = new Date(b.created_at);
        return order === 'desc' ? dateB - dateA : dateA - dateB;
    });
}
