import { describe, expect, it } from 'vitest'

import { apiRequest, expectError } from './client'

interface OrderResponse {
  id: number
  userId: number
  totalAmount: number
  orderStatus: number
  items: Array<{
    menuId: number
    itemName: string
    quantity: number
    unitPrice: number
    subtotal: number
  }>
  financeRecords: Array<{
    merchantId: number
    merchantName: string
    settlementAmount: number
  }>
}

describe('order APIs', () => {
  it('creates an order, merges repeated menu items, and creates finance records', async () => {
    const response = await apiRequest<OrderResponse>('/orders', {
      method: 'POST',
      body: JSON.stringify({
        userId: 1,
        items: [
          { menuId: 1, quantity: 1 },
          { menuId: 1, quantity: 2 },
        ],
      }),
    })

    expect(response.status).toBe(201)
    expect(response.body).toMatchObject({
      userId: 1,
      totalAmount: 360,
      orderStatus: 0,
    })
    expect(response.body.items).toEqual([
      expect.objectContaining({
        menuId: 1,
        itemName: 'Chicken Bento',
        quantity: 3,
        unitPrice: 120,
        subtotal: 360,
      }),
    ])
    expect(response.body.financeRecords).toEqual([
      expect.objectContaining({
        merchantId: 1,
        merchantName: '阿明便當',
        settlementAmount: 324,
      }),
    ])
  })

  it('rejects orders with a missing menu item', async () => {
    const response = await apiRequest<{ detail: string }>('/orders', {
      method: 'POST',
      body: JSON.stringify({
        userId: 1,
        items: [{ menuId: 999, quantity: 1 }],
      }),
    })

    expectError(response, 404, 'Menu item 999 not found')
  })

  it('rejects orders that exceed daily menu quantity', async () => {
    const response = await apiRequest<{ detail: string }>('/orders', {
      method: 'POST',
      body: JSON.stringify({
        userId: 1,
        items: [{ menuId: 1, quantity: 51 }],
      }),
    })

    expectError(response, 400, 'Chicken Bento exceeds daily available quantity')
  })

  it('rejects invalid order payloads', async () => {
    const response = await apiRequest<{ detail: unknown }>('/orders', {
      method: 'POST',
      body: JSON.stringify({
        userId: 1,
        items: [],
      }),
    })

    expect(response.status).toBe(422)
    expect(response.body.detail).toEqual(expect.any(Array))
  })

  it('lists orders for a user with camelCase response fields', async () => {
    const response = await apiRequest<OrderResponse[]>('/orders?userId=1&sortBy=time')

    expect(response.status).toBe(200)
    expect(response.body.length).toBeGreaterThanOrEqual(1)
    expect(response.body[0]).toEqual(expect.objectContaining({
      userId: expect.any(Number),
      totalAmount: expect.any(Number),
      orderStatus: expect.any(Number),
      financeRecords: expect.any(Array),
    }))
  })

  it('updates an in-progress order status to completed', async () => {
    const createResponse = await apiRequest<OrderResponse>('/orders', {
      method: 'POST',
      body: JSON.stringify({
        userId: 1,
        items: [{ menuId: 3, quantity: 1 }],
      }),
    })

    expect(createResponse.status).toBe(201)

    const updateResponse = await apiRequest<OrderResponse>(`/orders/${createResponse.body.id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ orderStatus: 1 }),
    })

    expect(updateResponse.status).toBe(200)
    expect(updateResponse.body.orderStatus).toBe(1)
  })

  it('does not allow completed orders to be cancelled', async () => {
    const response = await apiRequest<{ detail: string }>('/orders/1/status', {
      method: 'PATCH',
      body: JSON.stringify({ orderStatus: 2 }),
    })

    expectError(response, 400, 'Completed or cancelled orders cannot change status')
  })
})
