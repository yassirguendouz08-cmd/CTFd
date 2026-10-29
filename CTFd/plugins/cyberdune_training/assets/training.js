(() => {
  const dialog = document.querySelector('[data-training-dialog]');
  const dialogBody = dialog?.querySelector('[data-training-dialog-body]');

  const updateProgress = summary => {
    document.querySelectorAll('[data-training-solved]').forEach(node => {
      node.replaceChildren(document.createTextNode(summary.solved));
      const total = document.createElement('small');
      total.textContent = ` / ${summary.total}`;
      node.append(total);
    });
    document.querySelectorAll('[data-training-xp]').forEach(node => { node.textContent = summary.xp; });
    document.querySelectorAll('[data-training-rank]').forEach(node => { node.textContent = summary.rank ? `#${summary.rank}` : '—'; });
    document.querySelectorAll('[data-training-percent]').forEach(node => { node.textContent = `${summary.percent}%`; });
    document.querySelectorAll('.tr-progress progress').forEach(node => { node.value = summary.percent; });
  };

  const bindDetail = root => {
    root.querySelectorAll('[data-training-submit]').forEach(form => {
      if (form.dataset.bound) return;
      form.dataset.bound = '1';
      form.addEventListener('submit', async event => {
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
            root.querySelectorAll('.tr-complete,.tr-solved-message').forEach(node => { node.hidden = false; });
            updateProgress(data.summary);
            document.querySelectorAll('.tr-card[data-training-slug]').forEach(card => {
              if (card.dataset.trainingSlug === form.dataset.trainingSlug) card.classList.add('tr-card-solved');
            });
          }
        } catch (error) {
          message.textContent = error instanceof SyntaxError ? form.dataset.error : (error.message || form.dataset.error);
          message.className = 'tr-feedback-error';
        } finally {
          button.disabled = completed; button.textContent = label;
        }
      });
    });

    root.querySelectorAll('[data-training-reset]').forEach(button => {
      if (button.dataset.bound) return;
      button.dataset.bound = '1';
      button.addEventListener('click', () => {
        const frame = root.querySelector('#training-lab-frame');
        if (frame) frame.src = frame.src;
      });
    });

    root.querySelectorAll('[data-training-sql]').forEach(form => {
      if (form.dataset.bound) return;
      form.dataset.bound = '1';
      form.addEventListener('submit', async event => {
        event.preventDefault();
        const output = form.querySelector('[data-sql-result]'), values = new FormData(form);
        const button = form.querySelector('button'); button.disabled = true;
        try {
          const response = await fetch(form.action, {method: 'POST', credentials: 'same-origin', headers: {'Content-Type':'application/json', 'CSRF-Token':values.get('nonce')}, body:JSON.stringify({username:values.get('username'), password:values.get('password')})});
          const result = await response.json(); output.textContent = result.message || 'Request failed.';
        } catch (_) { output.textContent = 'Could not reach the lab. Please try again.'; }
        finally { button.disabled = false; }
      });
    });
  };

  bindDetail(document);

  if (!dialog || !dialogBody) return;
  const openChallenge = async href => {
    dialogBody.innerHTML = '<p class="tr-dialog-status" role="status">Loading challenge…</p>';
    if (!dialog.open) dialog.showModal();
    try {
      const url = new URL(href, window.location.href);
      url.searchParams.set('modal', '1');
      const response = await fetch(url, {credentials: 'same-origin', headers: {'X-Requested-With': 'XMLHttpRequest'}});
      if (response.redirected) {
        window.location.assign(response.url);
        return;
      }
      if (!response.ok) throw new Error('Could not load this challenge.');
      const documentView = new DOMParser().parseFromString(await response.text(), 'text/html');
      const fragment = documentView.querySelector('[data-training-detail-fragment]');
      if (!fragment) throw new Error('Challenge content is unavailable.');
      dialogBody.replaceChildren(fragment.cloneNode(true));
      const heading = dialogBody.querySelector('h1');
      if (heading) {
        heading.id = 'training-modal-title';
        dialog.setAttribute('aria-labelledby', heading.id);
      }
      bindDetail(dialogBody);
    } catch (error) {
      const message = document.createElement('p');
      message.className = 'tr-dialog-status tr-feedback-error';
      message.setAttribute('role', 'alert');
      message.textContent = error.message || 'Could not load this challenge.';
      const fallback = document.createElement('a');
      fallback.href = href; fallback.textContent = 'Open challenge page';
      fallback.className = 'btn btn-secondary';
      dialogBody.replaceChildren(message, fallback);
    }
  };

  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-training-open]');
    if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.target || link.hasAttribute('download')) return;
    event.preventDefault();
    openChallenge(link.href);
  });
  dialog.querySelector('[data-training-close]')?.addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  dialog.addEventListener('close', () => dialogBody.replaceChildren());
})();
