import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'Optara — Intelligence, Optimized.', description: 'An evidence-driven AI execution control plane. Spend intelligence where it matters.' };
export default function RootLayout({children}:{children:React.ReactNode}) {return <html lang="en"><body>{children}</body></html>;}
