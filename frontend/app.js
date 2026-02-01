// frontend/app.js

// Configuration
const API_URL = '/api/v1';

// State
let currentUser = null;
let accessToken = null;
let currentEditPost = null;
let currentEditComment = null;
let postsSortOrder = 'desc';        // порядок постов
let commentsSortOrder = {};         // порядок комментариев по postId

function handleAuthError(response) {
    if (response.status === 401) {
        // токен истёк или стал невалидным
        localStorage.removeItem('accessToken');
        localStorage.removeItem('username');
        accessToken = null;
        currentUser = null;

        showError('Сессия истекла. Пожалуйста, войдите снова.');
        showAuthSection();
        return true;  // сигнал, что уже всё обработали
    }
    return false;
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    setupEventListeners();
});

// ---------- Auth ----------

function checkAuth() {
    accessToken = localStorage.getItem('accessToken');
    const username = localStorage.getItem('username');

    if (accessToken && username) {
        currentUser = { username };
        showPostsSection();
        loadPosts(postsSortOrder);
    } else {
        showAuthSection();
    }
}

function setupEventListeners() {
    // Вкладки авторизации
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

    // Логин
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        await login(email, password);
    });

    // Регистрация
    document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('registerUsername').value;
        const email = document.getElementById('registerEmail').value;
        const password = document.getElementById('registerPassword').value;
        await register(username, email, password);
    });

    // Logout
    document.getElementById('logoutBtn').addEventListener('click', logout);

    // Создать пост
    document.getElementById('createPostBtn').addEventListener('click', () => {
        currentEditPost = null;
        document.getElementById('postModalTitle').textContent = 'Создать публикацию';
        document.getElementById('postTitle').value = '';
        document.getElementById('postContent').value = '';
        openModal('postModal');
    });

    // Сохранение поста
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

    // Сохранение отредактированного комментария
    document.getElementById('commentForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const content = document.getElementById('commentContent').value;
        await updateComment(currentEditComment.postId, currentEditComment.id, content);
    });

    // Закрытие модалок
    document.querySelectorAll('.close-modal').forEach(btn => {
        btn.addEventListener('click', closeAllModals);
    });

    // Закрытие модалки по клику вне
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeAllModals();
        });
    });

    // Делегирование для кнопок комментариев (редакт/удалить)
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('edit-comment-btn')) {
            const postId = e.target.dataset.postId;
            const commentId = e.target.dataset.commentId;
            const content = e.target.dataset.content || '';

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
}

async function register(username, email, password) {
    try {
        const response = await fetch(`${API_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Ошибка регистрации');

        // запомним ник для этого email
        localStorage.setItem('lastRegisteredEmail', email);
        localStorage.setItem('lastRegisteredUsername', username);

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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Ошибка входа');

        accessToken = data.access_token;
        localStorage.setItem('accessToken', accessToken);

        const lastEmail = localStorage.getItem('lastRegisteredEmail');
        const lastUsername = localStorage.getItem('lastRegisteredUsername');

        // базовый ник — часть email до @
        let nickname = email.includes('@') ? email.split('@')[0] : email;

        // если при регистрации для этого email сохранён username — используем его
        if (lastEmail && lastEmail === email && lastUsername) {
            nickname = lastUsername;
        }

        localStorage.setItem('username', nickname);
        currentUser = { username: nickname };

        showSuccess('Вход выполнен успешно!');
        showPostsSection();
        loadPosts(postsSortOrder);
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

// ---------- Posts & Comments API ----------

async function loadPosts(sort = postsSortOrder) {
    try {
        const response = await fetch(`${API_URL}/posts?sort=${sort}`, {
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
            body: JSON.stringify({ title, content, is_published: true })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Ошибка создания публикации');
        }

        showSuccess('Публикация создана!');
        closeAllModals();
        loadPosts(postsSortOrder);
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

        if (!response.ok) throw new Error('Ошибка обновления публикации');

        showSuccess('Публикация обновлена!');
        closeAllModals();
        loadPosts(postsSortOrder);
    } catch (error) {
        showError(error.message);
    }
}

async function deletePost(postId) {
    if (!confirm('Вы уверены, что хотите удалить эту публикацию?')) return;

    try {
        const response = await fetch(`${API_URL}/posts/${postId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });

        if (!response.ok) throw new Error('Ошибка удаления публикации');

        showSuccess('Публикация удалена!');

        // убрать карточку поста из DOM
        const postCard = document.querySelector(`.post-card [data-id="${postId}"]`)?.closest('.post-card');
        if (postCard) postCard.remove();
    } catch (error) {
        showError(error.message);
    }
}


async function loadComments(postId, sort = commentsSortOrder[postId] || 'desc') {
    try {
        const response = await fetch(
            `${API_URL}/posts/${postId}/comments?sort=${sort}`,
            { headers: { 'Authorization': `Bearer ${accessToken}` } }
        );

        if (!response.ok) throw new Error('Ошибка загрузки комментариев');

        return await response.json(); // уже отсортированы на сервере
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

        if (!response.ok) throw new Error('Ошибка создания комментария');

        showSuccess('Комментарий добавлен!');
        await refreshCommentsForPost(postId);
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

        if (!response.ok) throw new Error('Ошибка обновления комментария');

        showSuccess('Комментарий обновлён!');
        closeAllModals();
        await refreshCommentsForPost(postId);
    } catch (error) {
        showError(error.message);
    }
}


async function deleteComment(postId, commentId) {
    if (!confirm('Вы уверены, что хотите удалить этот комментарий?')) return;

    try {
        const response = await fetch(`${API_URL}/posts/${postId}/comments/${commentId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${accessToken}` }
        });

        if (!response.ok) throw new Error('Ошибка удаления комментария');

        showSuccess('Комментарий удалён!');
        await refreshCommentsForPost(postId);
    } catch (error) {
        showError(error.message);
    }
}


async function refreshCommentsForPost(postId) {
    const comments = await loadComments(postId, commentsSortOrder[postId] || 'desc');
    const commentsContainer = document.getElementById(`comments-${postId}`);
    if (commentsContainer) {
        commentsContainer.innerHTML = comments
            .map(c => createCommentHTML(postId, c))
            .join('');
    }
}


// ---------- Rendering ----------

async function displayPosts(posts) {
    const container = document.getElementById('postsContainer');

    if (!posts || posts.length === 0) {
        container.innerHTML = '<p class="loading">Пока нет публикаций. Создайте первую!</p>';
        return;
    }

    container.innerHTML = '';

    // Кнопка сортировки постов
    const sortControlDiv = document.createElement('div');
    sortControlDiv.style.marginBottom = '1rem';
    sortControlDiv.style.display = 'flex';
    sortControlDiv.style.justifyContent = 'flex-end';
    sortControlDiv.innerHTML = `
        <button class="btn btn-secondary btn-small" id="togglePostsSort">
            ${postsSortOrder === 'desc' ? '⬇ Сначала новые' : '⬆ Сначала старые'}
        </button>
    `;
    container.appendChild(sortControlDiv);

    document.getElementById('togglePostsSort').addEventListener('click', () => {
        postsSortOrder = postsSortOrder === 'desc' ? 'asc' : 'desc';
        loadPosts(postsSortOrder);
    });

    for (const post of posts) {
        if (!commentsSortOrder[post.id]) commentsSortOrder[post.id] = 'desc';
        const comments = await loadComments(post.id, commentsSortOrder[post.id]);
        const postEl = createPostElement(post, comments);
        container.appendChild(postEl);
    }
}

// автор поста по схемам PostWithAuthor
function getPostAuthor(post) {
    if (post.author && post.author.username) return post.author.username;
    if (post.author && post.author.email) return post.author.email;
    return 'anon';
}

// автор комментария по схемам CommentWithAuthor
function getCommentAuthor(comment) {
    if (comment.author && comment.author.username) return comment.author.username;
    if (comment.author && comment.author.email) return comment.author.email;
    return 'anon';
}

function createPostElement(post, comments) {
    const postDiv = document.createElement('div');
    postDiv.className = 'post-card';

    const author = getPostAuthor(post);
    const isOwner = currentUser && author === currentUser.username;

    const sortOrder = commentsSortOrder[post.id] || 'desc';

    postDiv.innerHTML = `
        <div class="post-header">
            <div>
                <h3 class="post-title">${escapeHtml(post.title)}</h3>
                <div class="post-meta">
                    Автор: ${escapeHtml(author)} • ${formatDate(post.created_at)}
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
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;">
                <div class="comments-header">Комментарии (${comments.length})</div>
                ${comments.length > 0 ? `
                    <button class="btn btn-secondary btn-small toggle-comments-sort" data-post-id="${post.id}">
                        ${sortOrder === 'desc' ? '⬇ Сначала новые' : '⬆ Сначала старые'}
                    </button>
                ` : ''}
            </div>
            <div class="comments-list" id="comments-${post.id}">
                ${comments.map(c => createCommentHTML(post.id, c)).join('')}
            </div>
            <div class="comment-form">
                <textarea class="comment-input" id="comment-input-${post.id}" placeholder="Добавить комментарий..." rows="2"></textarea>
                <button class="btn btn-primary btn-small add-comment-btn" style="margin-top:0.5rem;" data-post-id="${post.id}">Добавить комментарий</button>
            </div>
        </div>
    `;

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

    postDiv.querySelector('.add-comment-btn').addEventListener('click', () => {
        const input = document.getElementById(`comment-input-${post.id}`);
        const content = input.value.trim();
        if (content) {
            createComment(post.id, content);
            input.value = '';
        }
    });

    const toggleBtn = postDiv.querySelector('.toggle-comments-sort');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', async () => {
            commentsSortOrder[post.id] =
                commentsSortOrder[post.id] === 'desc' ? 'asc' : 'desc';

            const updatedComments = await loadComments(post.id, commentsSortOrder[post.id]);
            const commentsContainer = document.getElementById(`comments-${post.id}`);

            commentsContainer.innerHTML = updatedComments
                .map(c => createCommentHTML(post.id, c))
                .join('');

            toggleBtn.textContent =
                commentsSortOrder[post.id] === 'desc'
                    ? '⬇ Сначала новые'
                    : '⬆ Сначала старые';
        });
    }

    return postDiv;
}

function createCommentHTML(postId, comment) {
    const author = getCommentAuthor(comment);
    const isOwner = currentUser && author === currentUser.username;

    return `
        <div class="comment">
            <div class="comment-header">
                <span class="comment-author">${escapeHtml(author)}</span>
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

// ---------- UI helpers ----------

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
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}
