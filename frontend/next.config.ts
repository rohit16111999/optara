import type { NextConfig } from 'next';
const config: NextConfig = {
  reactStrictMode: true,
  devIndicators: false,
  async rewrites() { return [{source:'/api/:path*',destination:`${process.env.OPTARA_API_URL??'http://127.0.0.1:8000'}/api/:path*`}]; },
};
export default config;
