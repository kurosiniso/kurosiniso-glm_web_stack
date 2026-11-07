"use client";

import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import Image from "next/image";

export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-background font-sans">
      <main className="flex flex-1 w-full max-w-3xl flex-col items-center justify-between py-32 px-16 sm:items-start">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Image
            className="dark:invert h-5 w-[100px]"
            src="/next.svg"
            alt="Next.js logo"
            width={100}
            height={20}
            priority
          />
        </motion.div>
        <motion.div
          className="flex flex-col items-center gap-6 text-center sm:items-start sm:text-left"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <h1 className="max-w-xs text-3xl font-semibold leading-10 tracking-tight text-foreground">
            Stack configured:{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[0.9em]">
              Next.js 16 + Tailwind 4 + shadcn/ui + framer-motion
            </code>
          </h1>
          <p className="max-w-md text-lg leading-8 text-muted-foreground">
            Your development environment is ready. Start building amazing applications.
          </p>
        </motion.div>
        <motion.div
          className="flex flex-col gap-4 text-base font-medium sm:flex-row"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <Button onClick={() => window.open("https://vercel.com/new", "_blank")}>
            Deploy Now
          </Button>
          <Button variant="outline" onClick={() => window.open("https://nextjs.org/docs", "_blank")}>
            Documentation
          </Button>
        </motion.div>
      </main>
    </div>
  );
}
