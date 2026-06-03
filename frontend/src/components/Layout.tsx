import type { ReactNode } from 'react'
import { Toaster } from 'react-hot-toast'
import Sidebar from './Sidebar'

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#F5F5F0' }}>
      <Toaster position="top-right" />
      <Sidebar />
      {/* En mobile, padding-top extra para la top bar fija */}
      <main className="flex-1 overflow-y-auto p-4 pt-20 sm:p-8 sm:pt-20 md:pt-8">
        {children}
      </main>
    </div>
  )
}
