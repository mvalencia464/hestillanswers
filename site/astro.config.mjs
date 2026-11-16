import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

// Set SITE_URL to the real domain once you have one (used for canonical links and the sitemap).
export default defineConfig({
  site: process.env.SITE_URL || 'https://hestillanswers.pages.dev',
  integrations: [sitemap({ filter: (page) => !page.includes('/thanks') })],
});
