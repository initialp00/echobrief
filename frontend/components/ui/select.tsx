import * as React from "react";
import { cn } from "@/lib/utils";

// Lightweight native <select> styled to match the shadcn/ui look.
const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => {
  return (
    <select
      ref={ref}
      className={cn(
        "flex h-10 w-full rounded-md border-2 border-black bg-white px-3 py-2 text-sm font-medium shadow-brutal-sm transition-shadow focus-visible:shadow-brutal focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    >
      {children}
    </select>
  );
});
Select.displayName = "Select";

export { Select };
