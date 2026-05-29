import { describe, expect, it } from 'vitest'

import { apiRequest } from './client'

describe('health API', () => {
  it('returns ok when the backend is running', async () => {
    const response = await apiRequest<{ status: string }>('/health')

    expect(response.status).toBe(200)
    expect(response.body).toEqual({ status: 'ok' })
  })

  it('returns ok from the health-check endpoint', async () => {
    const response = await apiRequest<{ status: string }>('/health-check')

    expect(response.status).toBe(200)
    expect(response.body).toEqual({ status: 'ok' })
  })
})
