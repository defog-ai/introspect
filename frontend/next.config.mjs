/** @type {import('next').NextConfig} */

export default {
  reactStrictMode: false,
  assetPrefix: "./",
  // need this for docker build
  output: "export",
  webpack: (config) => {
    config.resolve.fallback = { fs: false };
    return config;
  },
  // experimental: {
  // If you’re on Next 12 or 13, this often helps
  // esmExternals: false,
  // },
  images: {
    unoptimized: true,
  },
};
