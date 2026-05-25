import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    fileParallelism: false,
    globalSetup: './test/global-setup.ts',
    include: ['test/**/*.test.ts'],
    testTimeout: 20_000,
  },
})
