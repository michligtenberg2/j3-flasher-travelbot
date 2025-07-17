document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.step').forEach(step => {
    const header = step.querySelector('.toggle');
    header.addEventListener('click', () => {
      step.classList.toggle('collapsed');
    });
  });
});
