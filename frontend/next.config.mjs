/** @type {import('next').NextConfig} */

// import removeImports from "next-remove-imports";

export default {
  reactStrictMode: false,
  assetPrefix: "./",
  // need this for docker build
  output: "export",
  webpack: (config) => {
    config.resolve.fallback = { fs: false };
    return config;
  },
  experimental: { esmExternals: true },
  compiler: {
    styledComponents: true,
  },
  images: {
    unoptimized: true,
  },
};
