/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Environment variables exposed to the browser
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL,
    NEXT_PUBLIC_SOLANA_RPC_URL: process.env.NEXT_PUBLIC_SOLANA_RPC_URL,
    NEXT_PUBLIC_COPPER_TOKEN_MINT: process.env.NEXT_PUBLIC_COPPER_TOKEN_MINT,
  },

  // Static export for Cloudflare Pages
  output: 'export',

  // Image optimization - unoptimized for static export
  images: {
    unoptimized: true,
  },

  // Webpack configuration for Solana wallet adapter
  webpack: (config) => {
    config.resolve.fallback = {
      ...config.resolve.fallback,
      fs: false,
      net: false,
      tls: false,
    };
    return config;
  },
};

module.exports = nextConfig;
