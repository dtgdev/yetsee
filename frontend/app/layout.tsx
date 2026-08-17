import './styles.css'
export const metadata = { title: 'YetSee', description: 'AI Opportunity Intelligence Platform' }
export default function RootLayout({children}:{children:React.ReactNode}) {
  return <html lang="en"><body>{children}</body></html>
}
