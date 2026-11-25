import { expect, test } from '@playwright/test'

test('landing page loads', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByText('Turn raw business data')).toBeVisible()
})

test('workspace page loads', async ({ page }) => {
  await page.goto('/workspace')
  await expect(page.getByText('Upload Business Dataset')).toBeVisible()
})

test('model management page loads', async ({ page }) => {
  await page.goto('/models')
  await expect(page.getByText('LLM & Model Management')).toBeVisible()
})
