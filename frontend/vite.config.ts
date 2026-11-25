import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
  build: {
    chunkSizeWarningLimit: 3000,
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom', 'react-router-dom'],
          'vendor-charts': ['plotly.js-dist-min', 'react-plotly.js'],
          'vendor-three': ['three', '@react-three/fiber', '@react-three/drei'],
          'vendor-icons': ['lucide-react'],
        },
      },
    },
  },
})
