'use client';
export default function ErrorPage({reset}:{reset:()=>void}){return <main className="error-boundary"><h1>Mission Control needs to reconnect.</h1><p>Your run history is persisted in the local control plane.</p><button onClick={reset}>Reconnect</button></main>;}
