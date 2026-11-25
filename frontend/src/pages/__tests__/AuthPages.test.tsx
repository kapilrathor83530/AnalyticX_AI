import { fireEvent, render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AuthProvider } from '../../contexts/AuthContext'
import LoginPage from '../LoginPage'
import RegisterPage from '../RegisterPage'

function renderWithAuth(ui: React.ReactElement) {
  return render(
    <BrowserRouter>
      <AuthProvider>{ui}</AuthProvider>
    </BrowserRouter>
  )
}

describe('Authentication Pages', () => {
  it('renders LoginPage with form inputs and demo button', () => {
    renderWithAuth(<LoginPage />)
    expect(screen.getByText('Welcome Back')).toBeDefined()
    // Defaults to Email OTP mode
    expect(screen.getByPlaceholderText('Enter your email address')).toBeDefined()
    expect(screen.getByText('Send Verification Code')).toBeDefined()
    expect(screen.getByText('Fill Demo')).toBeDefined()

    // Clicking Fill Demo switches to password mode and fills in credentials
    const fillBtn = screen.getByText('Fill Demo')
    fireEvent.click(fillBtn)
    const emailInput = screen.getByPlaceholderText('analyst@example.com') as HTMLInputElement
    expect(emailInput.value).toBe('demo@analyticx.ai')
    expect(screen.getByPlaceholderText('••••••••')).toBeDefined()
  })

  it('allows toggling between Password and Email OTP mode on LoginPage', () => {
    renderWithAuth(<LoginPage />)
    expect(screen.getByText('Continue with Google')).toBeDefined()

    // Switch to Password
    const pwdTab = screen.getByText('Email & Password')
    fireEvent.click(pwdTab)
    expect(screen.getByPlaceholderText('analyst@example.com')).toBeDefined()

    // Switch back to Email OTP
    const otpTab = screen.getByText('Email Code (OTP)')
    fireEvent.click(otpTab)
    expect(screen.getByPlaceholderText('Enter your email address')).toBeDefined()
    expect(screen.getByText('Send Verification Code')).toBeDefined()
  })

  it('renders RegisterPage with full name, email, and password confirmation', () => {
    renderWithAuth(<RegisterPage />)
    expect(screen.getByRole('heading', { name: 'Create Account' })).toBeDefined()
    expect(screen.getByPlaceholderText('Full Name')).toBeDefined()
    expect(screen.getByPlaceholderText('analyst@example.com')).toBeDefined()
    expect(screen.getByPlaceholderText('Minimum 8 characters')).toBeDefined()
    expect(screen.getByPlaceholderText('Repeat your password')).toBeDefined()
    expect(screen.getByText('At least 8 characters')).toBeDefined()
  })
})
