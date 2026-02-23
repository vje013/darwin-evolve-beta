import React, { useState } from 'react'
import { Box, TextField, Button, Typography, Paper, Alert } from '@mui/material'
import { login, register, setToken } from '../api/client'

export default function AuthScreen({ onAuth }) {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = isLogin
        ? await login(email, password)
        : await register(email, displayName, password)

      setToken(res.access_token)
      onAuth({ user_id: res.user_id, display_name: res.display_name, email })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box sx={{
      height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'linear-gradient(145deg, #0a0e17 0%, #111827 50%, #0f172a 100%)',
    }}>
      <Paper sx={{
        p: 5, width: 400, bgcolor: 'background.paper',
        border: '1px solid rgba(110, 231, 183, 0.15)',
      }}>
        <Typography variant="h6" sx={{ mb: 0.5, color: 'primary.main', letterSpacing: '-0.02em' }}>
          Darwin Evolve β
        </Typography>
        <Typography variant="body2" sx={{ mb: 3, color: 'text.secondary' }}>
          Enterprise collaboration with graph intelligence
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <form onSubmit={handleSubmit}>
          <TextField
            fullWidth label="Email" type="email" value={email}
            onChange={(e) => setEmail(e.target.value)}
            sx={{ mb: 2 }} size="small" required
          />
          {!isLogin && (
            <TextField
              fullWidth label="Display Name" value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              sx={{ mb: 2 }} size="small" required
            />
          )}
          <TextField
            fullWidth label="Password" type="password" value={password}
            onChange={(e) => setPassword(e.target.value)}
            sx={{ mb: 3 }} size="small" required
          />
          <Button
            type="submit" fullWidth variant="contained" disabled={loading}
            sx={{ mb: 2, py: 1.2, bgcolor: 'primary.main', color: '#0a0e17',
              '&:hover': { bgcolor: '#5ddba8' } }}
          >
            {loading ? '...' : isLogin ? 'Sign In' : 'Create Account'}
          </Button>
        </form>

        <Button
          fullWidth size="small" onClick={() => { setIsLogin(!isLogin); setError('') }}
          sx={{ color: 'text.secondary' }}
        >
          {isLogin ? "Don't have an account? Register" : 'Already have an account? Sign in'}
        </Button>
      </Paper>
    </Box>
  )
}
