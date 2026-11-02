import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import App from './App'

const summary = {
  balance: 2150,
  income: 2500,
  expenses: 350,
  savings_rate: 86,
  monthly: [],
  categories: [{ category: 'Food', amount: 350 }],
}
const transactions = [
  { id: 1, title: 'Groceries', amount: 350, type: 'expense', category: 'Food', date: '2026-11-02' },
]
const budgets = [{ id: 1, category: 'Food', limit: 500, spent: 350 }]
const goals = [{ id: 1, name: 'Emergency fund', target_amount: 1000, saved_amount: 250 }]

function mockApi({ online = true } = {}) {
  const requests = []
  vi.stubGlobal('fetch', vi.fn(async (url, options = {}) => {
    requests.push({ url, options })
    if (!online) throw new Error('Network unavailable')
    const data = {
      '/api/summary': summary,
      '/api/transactions': transactions,
      '/api/budgets': budgets,
      '/api/goals': goals,
    }
    return { ok: true, json: async () => data[url] ?? {} }
  }))
  return requests
}

async function renderAuthenticatedApp() {
  render(<App />)
  fireEvent.change(screen.getByLabelText('Email address'), { target: { value: 'tester@example.com' } })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: 'securepass123' } })
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
  expect(await screen.findByText('Good to see you.')).toBeInTheDocument()
}

describe('FinTrack application', () => {
  beforeEach(() => mockApi())
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('loads dashboard metrics and recent transactions', async () => {
    await renderAuthenticatedApp()
    expect(await screen.findByText('Groceries')).toBeInTheDocument()
    expect(screen.getByText('$2,150')).toBeInTheDocument()
    expect(screen.getByText('$2,500')).toBeInTheDocument()
    expect(screen.getByText('86%')).toBeInTheDocument()
  })

  it('filters transactions using the accessible search field', async () => {
    render(<App />)
    await screen.findByText('Groceries')
    fireEvent.change(screen.getByRole('textbox', { name: 'Search transactions' }), {
      target: { value: 'not found' },
    })
    fireEvent.click(screen.getByText('View all →'))
    expect(screen.getByText('No matching transactions found.')).toBeInTheDocument()
  })

  it('opens the transaction form from the primary action', async () => {
    render(<App />)
    await screen.findByText('Groceries')
    fireEvent.click(screen.getByRole('button', { name: 'Add transaction' }))
    expect(screen.getByText('New transaction')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('e.g. Grocery shopping')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Close transaction dialog' })).toBeInTheDocument()
  })

  it('shows budget usage with an accessible progress indicator', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Budgets' }))
    expect(await screen.findByRole('heading', { name: 'Food' })).toBeInTheDocument()
    expect(screen.getAllByRole('progressbar', { name: 'Food budget usage' })).toHaveLength(2)
    expect(screen.getAllByRole('progressbar', { name: 'Food budget usage' })[0]).toHaveAttribute('aria-valuenow', '70')
    fireEvent.click(screen.getByRole('button', { name: 'Create budget' }))
    expect(screen.getByText('Create monthly budget')).toBeInTheDocument()
  })

  it('opens savings goals and the contribution dialog', async () => {
    render(<App />)
    fireEvent.click(screen.getByRole('button', { name: 'Savings goals' }))
    expect(await screen.findByText('Emergency fund')).toBeInTheDocument()
    expect(screen.getByRole('progressbar', { name: 'Emergency fund savings progress' })).toHaveAttribute('aria-valuenow', '25')
    fireEvent.click(screen.getByRole('button', { name: 'Add funds to Emergency fund' }))
    expect(screen.getByText('Add to Emergency fund')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Close contribution dialog' })).toBeInTheDocument()
  })

  it('shows a clear offline message when the API cannot be reached', async () => {
    mockApi({ online: false })
    render(<App />)
    expect(await screen.findByText(/Backend is offline/)).toBeInTheDocument()
    expect(screen.getByText('Waiting for API')).toBeInTheDocument()
  })
})
