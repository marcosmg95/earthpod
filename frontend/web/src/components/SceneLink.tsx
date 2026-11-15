import type { MouseEvent, ReactNode } from "react";
import { useLocation } from "wouter";
import { withTransition } from "../a11y/transition";

interface Props {
  href: string;
  className?: string;
  current?: boolean;
  children: ReactNode;
}

export function SceneLink({ href, className, current, children }: Props) {
  const [, navigate] = useLocation();
  const go = (e: MouseEvent<HTMLAnchorElement>) => {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey)
      return;
    e.preventDefault();
    withTransition(() => navigate(href));
  };
  return (
    <a
      href={`#${href}`}
      className={className}
      aria-current={current ? "page" : undefined}
      onClick={go}
    >
      {children}
    </a>
  );
}
