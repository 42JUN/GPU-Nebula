import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['vite.svg'],
      manifest: {
        name: 'GPU Nebula',
        short_name: 'Nebula',
        description: 'Advanced GPU Cluster Management PWA',
        start_url: '.',
        display: 'standalone',
        theme_color: '#0b0f1a',
        background_color: '#0b0f1a',
        icons: [
          {
            src: '/vite.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'any'
          }
        ]
      }
    })
  ],
})
