import type { Metadata } from "next";
import { Inter, Syne } from "next/font/google";
import "@/styles/globals.css";
import { SETTINGS_STORAGE_KEY } from "@/lib/theme";

const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});

const syne = Syne({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-syne",
  display: "swap",
});

export const metadata: Metadata = {
  title: "DigitalSprint AI — Knowledge RAG",
  description: "Your organisation's AI knowledge hub. Upload documents and chat with your collective knowledge.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const themeBootScript = `
    (function() {
      try {
        var theme = "dark";
        var raw = localStorage.getItem("${SETTINGS_STORAGE_KEY}");
        if (raw) {
          var parsed = JSON.parse(raw);
          if (parsed && (parsed.theme === "dark" || parsed.theme === "light")) {
            theme = parsed.theme;
          }
        }
        document.documentElement.dataset.theme = theme;
        document.documentElement.style.colorScheme = theme;
      } catch (error) {
        document.documentElement.dataset.theme = "dark";
        document.documentElement.style.colorScheme = "dark";
      }
    })();
  `;

  return (
    <html
      lang="en"
      data-theme="dark"
      suppressHydrationWarning
      className={`${inter.variable} ${syne.variable}`}
    >
      <body className="h-full font-sans antialiased">
        <script dangerouslySetInnerHTML={{ __html: themeBootScript }} />
        {children}
      </body>
    </html>
  );
}
