import { defineConfig } from 'vitest/config';

// Vite serves the app from index.html; USF packages are workspace links into vendor/usf and are
// consumed as TypeScript source (Blueprint OD-15). Vitest runs only this project's tests.
export default defineConfig({
  test: {
    include: ['src/**/*.test.ts'],
  },
});
