import { describe, expect, it } from 'vitest'

const apiKey = process.env.OPENROUTER_API_KEY
const apiUrl =
  process.env.OPENROUTER_API_URL ??
  'https://openrouter.ai/api/v1/chat/completions'
const model =
  process.env.OPENROUTER_MODEL ?? 'google/gemini-3.1-flash-lite'

describe.runIf(apiKey)('OpenRouter live integration', () => {
  it('accepts the configured chat completions model and returns JSON content', async () => {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        authorization: `Bearer ${apiKey}`,
        'content-type': 'application/json',
        'http-referer': process.env.OPENROUTER_SITE_URL ?? 'http://localhost',
        'x-title': process.env.OPENROUTER_APP_NAME ?? 'Kubereats CI',
      },
      body: JSON.stringify({
        model,
        messages: [
          {
            role: 'system',
            content: 'Return only JSON that matches the schema.',
          },
          {
            role: 'user',
            content:
              'Parse this food prompt: 我想吃竹科 150 元以內的健康餐盒',
          },
        ],
        temperature: 0,
        max_tokens: 120,
        response_format: {
          type: 'json_schema',
          json_schema: {
            name: 'ci_openrouter_smoke',
            strict: true,
            schema: {
              type: 'object',
              additionalProperties: false,
              properties: {
                ok: { type: 'boolean' },
                terms: {
                  type: 'array',
                  items: { type: 'string' },
                },
              },
              required: ['ok', 'terms'],
            },
          },
        },
      }),
    })

    const text = await response.text()
    expect(response.status, text).toBeGreaterThanOrEqual(200)
    expect(response.status, text).toBeLessThan(300)

    const payload = JSON.parse(text)
    const content = payload.choices?.[0]?.message?.content
    const parsed = typeof content === 'string' ? JSON.parse(content) : content

    expect(parsed).toMatchObject({
      ok: expect.any(Boolean),
      terms: expect.any(Array),
    })
  })
})
