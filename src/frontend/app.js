document.querySelector('#health').addEventListener('click', async () => {
  const status = document.querySelector('#status');
  status.textContent = 'Checking…';
  try {
    const response = await fetch('http://127.0.0.1:8000/health');
    const body = await response.json();
    status.textContent = response.ok ? `Connected: ${body.observation_count} observations.` : 'Database is not ready.';
  } catch (_) { status.textContent = 'Start the local backend to check PostgreSQL.'; }
});
