import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Novel-to-Drama",
  description: "把参差不齐的小说原料自动改编成符合标准格式的对白短剧脚本",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-Hans" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
