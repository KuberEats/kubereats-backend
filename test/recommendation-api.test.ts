import { beforeAll, describe, expect, it } from 'vitest'

import { getJson, postJson, waitForBackendHealth } from './api-client'

type MerchantRecommendation = {
  id: number
  name: string
  campus: string
  category: string
  rating: number
  orderCount: number
  deliveryTime: string
  tags: string[]
  score: number
  reason: string
  signals: Record<string, unknown>
}

type MenuRecommendation = {
  id: number
  merchantId: number
  merchantName: string
  itemName: string
  price: number
  maxDailyQuantity: number
  score: number
  reason: string
  signals: Record<string, unknown>
}

type GrafanaCheck = {
  service: string
  status: string
  api: {
    totalRequests: number
    successfulRequests: number
    failedRequests: number
    successRate: number | null
    errorRate: number | null
    averageLatencyMs: number | null
    byEndpoint: Record<
      string,
      {
        totalRequests: number
        successfulRequests: number
        failedRequests: number
        averageLatencyMs: number | null
      }
    >
  }
  openRouter: {
    totalCalls: number
    successfulCalls: number
    failedCalls: number
    fallbackCount: number
  }
  openRouterUsage: {
    promptTokens: number
    completionTokens: number
    totalTokens: number
    rerankSearchUnits: number
    lastUsage: unknown
  }
}

describe('recommendation backend API', () => {
  beforeAll(async () => {
    await waitForBackendHealth()
  })

  it('returns health status', async () => {
    const body = await getJson<{ status: string }>('/health')

    expect(body).toEqual({ status: 'ok' })
  })

  it('recommends merchants from the requested campus with response reasons', async () => {
    const merchants = await postJson<MerchantRecommendation[]>(
      '/recommendations/merchants',
      {
        userId: 2,
        campus: '竹科',
        prompt: '想吃清爽健康一點，預算 150 元以內，最近沒吃過的店',
        limit: 3,
      },
    )

    expect(merchants).toHaveLength(3)
    expect(merchants.every((merchant) => merchant.campus === '竹科')).toBe(true)
    expect(merchants[0]).toMatchObject({
      id: expect.any(Number),
      name: expect.any(String),
      category: expect.any(String),
      rating: expect.any(Number),
      orderCount: expect.any(Number),
      deliveryTime: expect.any(String),
      tags: expect.any(Array),
      score: expect.any(Number),
      reason: expect.any(String),
    })
    expect(merchants[0].reason.length).toBeGreaterThan(0)
    expect(merchants[0].signals).toHaveProperty('rerankSource')
  })

  it('recommends menus and keeps merchant filters', async () => {
    const menus = await postJson<MenuRecommendation[]>('/recommendations/menus', {
      userId: 2,
      campus: '竹科',
      merchantId: 3,
      prompt: '想吃健康低卡的餐盒',
      limit: 5,
    })

    expect(menus.length).toBeGreaterThan(0)
    expect(menus.every((menu) => menu.merchantId === 3)).toBe(true)
    expect(menus[0]).toMatchObject({
      id: expect.any(Number),
      merchantId: 3,
      merchantName: expect.any(String),
      itemName: expect.any(String),
      price: expect.any(Number),
      maxDailyQuantity: expect.any(Number),
      score: expect.any(Number),
      reason: expect.any(String),
    })
  })

  it('supports query-style merchant recommendations', async () => {
    const merchants = await getJson<MerchantRecommendation[]>(
      '/recommendations/merchants?userId=2&campus=%E7%AB%B9%E7%A7%91&limit=2',
    )

    expect(merchants).toHaveLength(2)
    expect(merchants.every((merchant) => merchant.campus === '竹科')).toBe(true)
  })

  it('returns 404 for unknown users', async () => {
    const body = await getJson<{ detail: string }>(
      '/recommendations/merchants?userId=999999&limit=1',
      { expectedStatus: 404 },
    )

    expect(body.detail).toBe('User not found')
  })

  it('rejects invalid recommendation limits', async () => {
    const body = await getJson<{ detail: unknown }>(
      '/recommendations/merchants?userId=2&limit=0',
      { expectedStatus: 422 },
    )

    expect(body.detail).toBeDefined()
  })

  it('returns in-memory metrics for Grafana checks', async () => {
    const metrics = await getJson<GrafanaCheck>('/recommendations/grafana-check')

    expect(metrics).toMatchObject({
      service: 'recommendation',
      status: 'ok',
      api: {
        totalRequests: expect.any(Number),
        successfulRequests: expect.any(Number),
        failedRequests: expect.any(Number),
        byEndpoint: expect.any(Object),
      },
      openRouter: {
        totalCalls: expect.any(Number),
        successfulCalls: expect.any(Number),
        failedCalls: expect.any(Number),
        fallbackCount: expect.any(Number),
      },
      openRouterUsage: {
        promptTokens: expect.any(Number),
        completionTokens: expect.any(Number),
        totalTokens: expect.any(Number),
        rerankSearchUnits: expect.any(Number),
      },
    })
    expect(metrics.api.totalRequests).toBeGreaterThanOrEqual(4)
    expect(metrics.api.successfulRequests).toBeGreaterThanOrEqual(3)
    expect(metrics.api.failedRequests).toBeGreaterThanOrEqual(1)
    expect(metrics.api.averageLatencyMs).toEqual(expect.any(Number))
    expect(metrics.api.byEndpoint['POST /recommendations/merchants']).toBeDefined()
  })
})
