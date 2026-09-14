import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'Optara — Constraint-Aware LLM Execution & Evaluation', description: 'Evaluate execution strategies against quality, cost and latency constraints, validate responses and inspect complete execution evidence.' };
export default function RootLayout({children}:{children:React.ReactNode}) {return <html lang="en"><body>{children}</body></html>;}
