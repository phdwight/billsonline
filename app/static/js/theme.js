/**
 * Theme Management
 * Handles theme loading and saving to localStorage
 */
(function() {
  // Load saved theme on page load
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme && savedTheme !== 'default') {
    document.body.classList.add('theme-' + savedTheme);
  }
  
  // Compact mode from URL params
  const params = new URLSearchParams(location.search);
  if (params.get('compact') === '1') {
    document.body.classList.add('compact');
  }
})();

/**
 * Apply theme class to body
 * @param {string} theme - Theme name (e.g., 'default', 'vibrant')
 */
function applyTheme(theme) {
  // Remove any existing theme classes
  document.body.className = document.body.className.replace(/theme-\w+/g, '').trim();
  // Add new theme class if not default
  if (theme && theme !== 'default') {
    document.body.classList.add('theme-' + theme);
  }
  // Save to localStorage
  localStorage.setItem('theme', theme);
}

/**
 * Get current theme
 * @returns {string} Current theme name
 */
function getCurrentTheme() {
  return localStorage.getItem('theme') || 'default';
}
