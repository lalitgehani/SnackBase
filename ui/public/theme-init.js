(function () {
  try {
    var key = 'snackbase.theme';
    var theme = localStorage.getItem(key);
    var isDark =
      theme === 'dark' ||
      ((theme === 'system' || theme == null) &&
        window.matchMedia('(prefers-color-scheme: dark)').matches);
    if (isDark) document.documentElement.classList.add('dark');
    else document.documentElement.classList.remove('dark');
  } catch (_) {}
})();
