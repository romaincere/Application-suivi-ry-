// ===== Menu mobile =====
const navToggle = document.getElementById('navToggle');
const nav = document.getElementById('nav');

navToggle?.addEventListener('click', () => {
  const open = nav.classList.toggle('open');
  navToggle.classList.toggle('open', open);
  navToggle.setAttribute('aria-expanded', String(open));
});

// Ferme le menu après un clic sur un lien
nav?.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => {
    nav.classList.remove('open');
    navToggle.classList.remove('open');
    navToggle.setAttribute('aria-expanded', 'false');
  });
});

// ===== Apparition au scroll =====
const reveals = document.querySelectorAll('.reveal');
if ('IntersectionObserver' in window) {
  const io = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('in');
        io.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  reveals.forEach((el) => io.observe(el));
} else {
  reveals.forEach((el) => el.classList.add('in'));
}

// ===== Année du footer =====
const yearEl = document.getElementById('year');
if (yearEl) yearEl.textContent = new Date().getFullYear();

// ===== Formulaire de contact =====
const form = document.getElementById('contactForm');
const note = document.getElementById('formNote');

form?.addEventListener('submit', async (e) => {
  // Si le endpoint Formspree n'est pas configuré, on bloque l'envoi réel
  const action = form.getAttribute('action') || '';
  const configured = action && !action.includes('your_form_id');

  if (!configured) {
    e.preventDefault();
    if (!form.checkValidity()) { form.reportValidity(); return; }
    note.textContent = "Merci ! Le formulaire n'est pas encore relié à une boîte mail — écrivez-nous directement à contact@berdea-paysage.fr.";
    note.className = 'form-note ok';
    return;
  }

  // Envoi AJAX vers Formspree pour rester sur la page
  e.preventDefault();
  if (!form.checkValidity()) { form.reportValidity(); return; }

  note.textContent = 'Envoi en cours…';
  note.className = 'form-note';

  try {
    const res = await fetch(action, {
      method: 'POST',
      body: new FormData(form),
      headers: { Accept: 'application/json' },
    });
    if (res.ok) {
      form.reset();
      note.textContent = 'Merci ! Votre demande a bien été envoyée. Nous vous recontactons rapidement.';
      note.className = 'form-note ok';
    } else {
      throw new Error('send failed');
    }
  } catch (err) {
    note.textContent = "Oups, l'envoi a échoué. Écrivez-nous directement à contact@berdea-paysage.fr.";
    note.className = 'form-note err';
  }
});
