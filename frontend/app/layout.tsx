import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DayOutPlanner | AI Travel Itinerary & Route Generator",
  description: "Plan your perfect day out in Singapore with intelligent spatial routing and automated scheduling.",
  keywords: ["Singapore travel", "itinerary planner", "AI travel guide", "DayOutPlanner"],
  openGraph: {
    title: "DayOutPlanner - AI Travel Itinerary Generator",
    description: "Generate optimized day trips and spatial transit routes in seconds.",
    url: "https://dayout.sherlock-yh.top",
    siteName: "DayOutPlanner",
    locale: "en_US",
    type: "website",
  },
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon-16x16.png",
    apple: "/apple-touch-icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
