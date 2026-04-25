"use client"

import Link from "next/link"

const primaryLinks = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "About", href: "#about" },
  { label: "Features", href: "#services" },
]

const secondaryLinks = [
  { label: "Top", href: "/" },
  { label: "Explore", href: "#about" },
  { label: "Launch", href: "/dashboard" },
]

export function Footer() {
  return (
    <footer className="relative overflow-hidden bg-[#f4f1ea] text-[#111111]">
      <div className="container mx-auto px-6 py-16 md:py-24">
        <div className="grid grid-cols-1 gap-12 md:grid-cols-[1fr_0.9fr]">
          <div className="max-w-sm">
            <p className="text-[clamp(2rem,4vw,3.75rem)] leading-[0.95] tracking-[-0.05em] text-black/90">
              Agentic systems,
              <br />
              ready for liftoff.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-8 text-left sm:grid-cols-2 sm:justify-self-end">
            <div className="space-y-3 text-[1.8rem] leading-none tracking-[-0.04em] text-black/90">
              {primaryLinks.map((link) => (
                <Link key={link.label} href={link.href} className="block transition-opacity hover:opacity-55">
                  {link.label}
                </Link>
              ))}
            </div>

            <div className="space-y-3 text-[1.8rem] leading-none tracking-[-0.04em] text-black/90">
              {secondaryLinks.map((link) => (
                <Link key={link.label} href={link.href} className="block transition-opacity hover:opacity-55">
                  {link.label}
                </Link>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-14">
          <Link
            href="/"
            aria-label="ARCOS home"
            className="font-display block text-[4.8rem] font-semibold leading-[0.82] tracking-[-0.12em] text-[#111111] sm:text-[7rem] md:text-[10rem] lg:text-[14rem]"
          >
            ARCOS
          </Link>
        </div>

        <div className="mt-10 flex flex-col gap-4 border-t border-black/10 pt-5 text-sm text-black/55 sm:flex-row sm:items-center sm:justify-between">
          <p>ARCOS</p>
          <div className="flex flex-wrap gap-6">
            <Link href="/dashboard" className="transition-opacity hover:opacity-55">
              Product
            </Link>
            <Link href="#about" className="transition-opacity hover:opacity-55">
              Systems
            </Link>
            <Link href="#services" className="transition-opacity hover:opacity-55">
              Use Cases
            </Link>
          </div>
        </div>
      </div>
    </footer>
  )
}
