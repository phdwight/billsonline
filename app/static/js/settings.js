/**
 * Settings Page JavaScript
 * Handles theme selection and database upload
 */
(function() {
  document.addEventListener('DOMContentLoaded', function() {
    initThemeSelector();
    initDatabaseUpload();
  });

  /**
   * Initialize theme selector radio buttons
   */
  function initThemeSelector() {
    const savedTheme = getCurrentTheme();
    
    // Set the radio button to match saved theme
    const radio = document.querySelector(`input[name="theme"][value="${savedTheme}"]`);
    if (radio) radio.checked = true;
    
    // Handle theme changes
    document.querySelectorAll('input[name="theme"]').forEach(radio => {
      radio.addEventListener('change', function() {
        applyTheme(this.value);
        console.log('Theme changed to:', this.value, 'Body classes:', document.body.className);
      });
    });
  }

  /**
   * Initialize database upload handling
   */
  function initDatabaseUpload() {
    const fileInput = document.getElementById('db-file-input');
    if (!fileInput) return;

    fileInput.addEventListener('change', function(e) {
      if (this.files.length > 0) {
        const fileName = this.files[0].name;
        if (confirm('Are you sure you want to replace the database with "' + fileName + '"? This action cannot be undone.')) {
          document.getElementById('file-label').classList.add('hidden');
          document.getElementById('upload-indicator').classList.remove('hidden');
          document.getElementById('upload-form').submit();
        } else {
          this.value = '';
        }
      }
    });
  }
})();
