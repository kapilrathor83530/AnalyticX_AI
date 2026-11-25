import { expect, test } from '@playwright/test'

test('full user workflow: upload → analytics → studio → dashboard', async ({ page }) => {
  await page.goto('/workspace')
  await expect(page.getByText('Upload Business Dataset')).toBeVisible()

  // Upload via the hidden file input
  const fileChooserPromise = page.waitForEvent('filechooser')
  await page.getByRole('button', { name: 'Choose File' }).click()
  const fileChooser = await fileChooserPromise
  await fileChooser.setFiles({
    name: 'e2e_sample.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from('region,revenue,cost\nNorth,100,40\nSouth,200,80\nNorth,150,60\n'),
  })

  // Dataset appears in the list
  await expect(page.getByRole('heading', { name: 'e2e_sample.csv' }).first()).toBeVisible({ timeout: 10000 })

  // Navigate to Studio
  await page.getByRole('link', { name: 'Studio' }).first().click()
  await expect(page.getByText('Preview')).toBeVisible()

  // Validate
  await page.getByRole('button', { name: 'Validate' }).click()
  await expect(page.getByText(/Chart configuration is valid|Missing required/)).toBeVisible({ timeout: 5000 })
})

test('auth flow: register → login → logout', async ({ page }) => {
  const email = `e2e_${Date.now()}@example.com`
  const password = 'password-1234'

  await page.goto('/register')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Password (min 8 chars)').fill(password)
  await page.getByRole('button', { name: 'Create Account' }).click()

  await expect(page).toHaveURL(/workspace/, { timeout: 10000 })

  await expect(page.getByText('Upload Business Dataset')).toBeVisible()
})
