/** @type {import('next').NextConfig} */
const withPWA = require("next-pwa")({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development",
  runtimeCaching: [
    {
      urlPattern: /\/api\/v1\/attendance/,
      handler: "StaleWhileRevalidate",
      options: { cacheName: "attendance-cache", expiration: { maxEntries: 50, maxAgeSeconds: 3600 } },
    },
    {
      urlPattern: /\/api\/v1\/students/,
      handler: "NetworkFirst",
      options: { cacheName: "students-cache", expiration: { maxEntries: 200, maxAgeSeconds: 86400 } },
    },
  ],
  fallbacks: { document: "/offline" },
});

const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  images: { domains: ["lh3.googleusercontent.com"] },
  experimental: { serverActions: { allowedOrigins: ["localhost:3000"] } },
};

module.exports = withPWA(nextConfig);
