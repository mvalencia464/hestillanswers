// Cloudflare Pages Function: POST /api/subscribe
// Forwards the signup to a HighLevel "Inbound Webhook" workflow trigger, then sends the reader to /thanks/.
// Set SIGNUP_WEBHOOK_URL in the Pages project settings (Settings > Variables and secrets).
export async function onRequestPost({ request, env }) {
  const form = await request.formData();
  const back = (path) => Response.redirect(new URL(path, request.url).toString(), 303);
  if (form.get('company')) return back('/thanks/');                    // honeypot: bots fill hidden fields
  const email = String(form.get('email') || '').trim().toLowerCase();
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return new Response('Please go back and enter a valid email address.', { status: 400 });
  if (!env.SIGNUP_WEBHOOK_URL) return new Response('Signup is not configured yet.', { status: 503 });
  const payload = {
    email,
    first_name: String(form.get('first_name') || '').trim().slice(0, 60),
    source: 'He Still Answers website',
    page: String(form.get('page') || ''),
    tags: ['he-still-answers', 'ebook-30-stories'],
  };
  const res = await fetch(env.SIGNUP_WEBHOOK_URL, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(payload) });
  if (!res.ok) return new Response('Sorry, something went wrong. Please try again in a minute.', { status: 502 });
  return back('/thanks/');
}
