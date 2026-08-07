const form = document.querySelector('#training-form');
const status = document.querySelector('#status');

form.addEventListener('submit', (event) => {
  event.preventDefault();
  form.reset();
  status.textContent = 'Simulation only: no information was submitted, stored, or transmitted.';
});
