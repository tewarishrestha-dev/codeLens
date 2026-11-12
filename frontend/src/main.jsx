import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Lenis from 'lenis'
import 'lenis/dist/lenis.css'
import './index.css'
import App from './App.jsx'

// Initialize Lenis luxury smooth scrolling (RAF-synchronized)
const lenis = new Lenis({
  autoRaf: true,
  lerp: 0.1,
  smoothWheel: true,
})

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
