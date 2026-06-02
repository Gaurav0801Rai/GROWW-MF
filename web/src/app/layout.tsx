import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mutual Fund FAQ Assistant | Facts-Only Mutual Fund Q&A",
  description: "A secure, compliance-focused RAG application designed to provide factual information about HDFC Mutual Fund schemes without advisory bias.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
