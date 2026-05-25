import { expect } from 'vitest'

export const API_BASE_URL = process.env.KUBEREATS_API_BASE_URL ?? 'http://localhost:8000'

interface ApiResponse<T> {
  status: number
  body: T
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<ApiResponse<T>> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  const text = await response.text()
  const body = text ? JSON.parse(text) as T : null as T

  return {
    status: response.status,
    body,
  }
}

export function expectError(response: ApiResponse<{ detail?: unknown }>, status: number, detail: string) {
  expect(response.status).toBe(status)
  expect(response.body.detail).toBe(detail)
}
