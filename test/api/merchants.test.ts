import { describe, expect, it } from 'vitest'

import { apiRequest } from './client'

interface MerchantListItem {
  id: number
  name: string
  campus: string
  rating: number
  orderCount: number
}

interface MenuItem {
  id: number
  merchantId: number
  itemName: string
  maxDailyQuantity: number
  price: number
}

describe('merchant APIs', () => {
  it('lists approved merchants for a campus', async () => {
    const response = await apiRequest<MerchantListItem[]>('/merchants?campus=竹科&sort_by=recommend')

    expect(response.status).toBe(200)
    expect(response.body).toHaveLength(3)
    expect(response.body.every(merchant => merchant.campus === '竹科')).toBe(true)
  })

  it('sorts merchants by order count when sort_by is people', async () => {
    const response = await apiRequest<MerchantListItem[]>('/merchants?campus=竹科&sort_by=people')

    expect(response.status).toBe(200)
    expect(response.body.map(merchant => merchant.name)).toEqual([
      '阿明便當',
      '小森咖哩',
      '清爽蔬食盒',
    ])
  })

  it('sorts merchants by rating when sort_by is popular', async () => {
    const response = await apiRequest<MerchantListItem[]>('/merchants?campus=竹科&sort_by=popular')

    expect(response.status).toBe(200)
    expect(response.body.map(merchant => merchant.name)).toEqual([
      '阿明便當',
      '清爽蔬食盒',
      '小森咖哩',
    ])
  })

  it('returns menu items with frontend-facing camelCase fields', async () => {
    const response = await apiRequest<MenuItem[]>('/merchants/1/menus')

    expect(response.status).toBe(200)
    expect(response.body[0]).toMatchObject({
      merchantId: 1,
      itemName: 'Chicken Bento',
      maxDailyQuantity: 50,
      price: 120,
    })
  })

  it('returns 404 for a missing merchant menu', async () => {
    const response = await apiRequest<{ detail: string }>('/merchants/999/menus')

    expect(response.status).toBe(404)
    expect(response.body.detail).toBe('Merchant not found')
  })
})
