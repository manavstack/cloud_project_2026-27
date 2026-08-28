const demand = document.querySelector('#demand');
const button = document.querySelector('#refresh');
button.addEventListener('click', () => {
  const value = 820 + Math.floor(Math.random() * 55);
  demand.textContent = `${value} kW`;
  button.textContent = 'Forecast updated';
  setTimeout(() => { button.textContent = 'Refresh forecast'; }, 1600);
});
