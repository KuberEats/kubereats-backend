import { expect } from 'vitest'

export const apiBaseUrl =
  process.env.BACKEND_API_BASE_URL ?? 'http://localhost:8000'

type JsonRequestOptions = RequestInit & {
  expectedStatus?: number
}

export async function getJson<T>(
  path: string,
  options: JsonRequestOptions = {},
): Promise<T> {
  return requestJson<T>(path, { ...options, method: 'GET' })
}

export async function postJson<T>(
  path: string,
  body: unknown,
  options: JsonRequestOptions = {},
): Promise<T> {
  return requestJson<T>(path, {
    ...options,
    method: 'POST',
    body: JSON.stringify(body),
    headers: {
      'content-type': 'application/json',
      ...options.headers,
    },
  })
}

export async function requestJson<T>(
  path: string,
  options: JsonRequestOptions = {},
): Promise<T> {
  const expectedStatus = options.expectedStatus ?? 200
  const response = await fetch(`${apiBaseUrl}${path}`, options)
  const text = await response.text()
  const body = text ? JSON.parse(text) : null

  expect(response.status, JSON.stringify(body, null, 2)).toBe(expectedStatus)
  return body as T
}

export async function waitForBackendHealth(): Promise<void> {
  const deadline = Date.now() + 30_000
  let lastError: unknown

  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${apiBaseUrl}/health`)

      if (response.ok) {
        return
      }

      lastError = new Error(`health returned ${response.status}`)
    } catch (error) {
      lastError = error
    }

    await new Promise((resolve) => setTimeout(resolve, 1_000))
  }

  throw new Error(
    `Backend health check failed at ${apiBaseUrl}/health: ${String(lastError)}`,
  )
}
