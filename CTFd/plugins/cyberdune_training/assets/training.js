(() => {
  const form = document.querySelector('[data-training-submit]');
  if (form) form.addEventListener('submit', async event => {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]'), flag = form.querySelector('[name="flag"]');
    const message = form.querySelector('[data-training-message]'), label = button.textContent;
    if (button.disabled) return;
    button.disabled = true; button.textContent = form.dataset.checking;
    message.textContent = ''; message.className = '';
    let completed = false;
    try {
      const response = await fetch(form.action, {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'CSRF-Token': form.querySelector('[name="nonce"]').value}, body: JSON.stringify({flag: flag.value})});
      const data = await response.json();
      if (!response.ok || !data.success) throw new Error(data.message || form.dataset.error);
      message.textContent = data.message;
      completed = data.status === 'correct' || data.status === 'already_solved';
      message.className = completed ? 'tr-feedback-success' : 'tr-feedback-error';
      if (completed) {
        flag.disabled = true;
        document.querySelectorAll('.tr-complete,.tr-solved-message').forEach(node => { node.hidden = false; });
        const summary = data.summary;
        document.querySelector('[data-training-solved]').textContent = `${summary.solved} / ${summary.total}`;
        document.querySelector('[data-training-xp]').textContent = summary.xp;
        document.querySelector('[data-training-rank]').textContent = summary.rank ? `#${summary.rank}` : '—';
        document.querySelector('[data-training-percent]').textContent = `${summary.percent}%`;
        document.querySelector('#training-progress').value = summary.percent;
      }
    } catch (error) {
      message.textContent = error instanceof SyntaxError ? form.dataset.error : (error.message || form.dataset.error);
      message.className = 'tr-feedback-error';
    } finally {
      button.disabled = completed; button.textContent = label;
    }
  });
  document.querySelector('[data-training-reset]')?.addEventListener('click', () => {
    const frame = document.getElementById('training-lab-frame');
    frame.src = frame.src;
  });
})();

 document.querySelectorAll('[data-training-sql]').forEach(form => form.addEventListener('submit', async event => {
   event.preventDefault();
   const output = form.querySelector('[data-sql-result]');
   const values = new FormData(form);
   const button = form.querySelector('button'); button.disabled = true;
   try {
     const response = await fetch(form.action, {method: 'POST', credentials: 'same-origin', headers: {'Content-Type':'application/json', 'CSRF-Token':values.get('nonce')}, body:JSON.stringify({username:values.get('username'), password:values.get('password')})});
     const result = await response.json(); output.textContent = result.message || 'Request failed.';
   } catch (_) { output.textContent = 'Could not reach the lab. Please try again.'; }
   finally { button.disabled = false; }
 }));
