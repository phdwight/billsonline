/**
 * Settings Page JavaScript
 * Handles database upload confirmation and flash visibility.
 */
(function() {
  document.addEventListener('DOMContentLoaded', function() {
    initDatabaseUpload();
    showFlashAlert();
  });

  /**
   * Show an alert if there's a success message (for visibility)
   */
  function showFlashAlert() {
    const successMsg = document.querySelector('.status-success');
    if (successMsg) {
      // Scroll to top to ensure message is visible
      window.scrollTo(0, 0);
      // Also show an alert for clear feedback
      alert(successMsg.textContent.trim());
    }
  }

  /**
   * Initialize database upload handling
   */
  function initDatabaseUpload() {
    const fileInput = document.getElementById('db-file-input');
    const uploadForm = document.getElementById('upload-form');
    const uploadIndicator = document.getElementById('upload-indicator');

    if (!fileInput || !uploadForm) return;

    fileInput.addEventListener('change', function(e) {
      if (this.files.length > 0) {
        const fileName = this.files[0].name;
        if (confirm('Are you sure you want to replace the database with "' + fileName + '"? This action cannot be undone.')) {
          // Show upload indicator
          if (uploadIndicator) {
            uploadIndicator.classList.remove('hidden');
          }
          uploadForm.submit();
        } else {
          this.value = '';
        }
      }
    });
  }
})();
