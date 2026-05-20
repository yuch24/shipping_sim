import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'LinerDT - 班轮航运数字孪生仿真平台',
  description: '面向班轮航运的离散事件仿真与AI交互平台',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN" className="dark">
      <head>
        <link
          rel="stylesheet"
          href="/cesium/Widgets/widgets.css"
        />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-[#0a1929] text-white font-sans antialiased">
        {children}
      </body>
    </html>
  )
}
