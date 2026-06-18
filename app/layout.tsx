import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Payfin — Bank Smarter. Move Faster.",
  description:
    "India's next-generation digital banking platform with UPI, real-time transfers, and bank-grade security.",
  keywords: ["banking", "UPI", "digital payments", "India", "fintech"],
  authors: [{ name: "Payfin" }],
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@100..900&family=JetBrains+Mono:wght@100..800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-sans antialiased bg-bg-root text-white min-h-screen">
        {children}
      </body>
    </html>
  );
}
