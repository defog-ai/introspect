/** @type {import('next').NextConfig} */

const removeImports = require("next-remove-imports")();

const nextConfig = removeImports({
  reactStrictMode: false,
  assetPrefix: "./",
  // need this for docker build
  output: "standalone",
  webpack: (config) => {
    config.resolve.fallback = { fs: false };
    return config;
  },
  experimental: { esmExternals: true },
  compiler: {
    styledComponents: true,
  },
});

module.exports = nextConfig;
