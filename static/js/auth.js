document.addEventListener('click', event => {
    const button = event.target.closest('.toggle-password');
    if (!button) return;

    const input = button.closest('.input-wrap')?.querySelector('input');
    const icon = button.querySelector('i');
    if (!input || !icon) return;

    const showPassword = input.type === 'password';
    input.type = showPassword ? 'text' : 'password';
    button.setAttribute('aria-label', showPassword ? 'Hide password' : 'Show password');
    icon.classList.toggle('fa-eye', !showPassword);
    icon.classList.toggle('fa-eye-slash', showPassword);
});