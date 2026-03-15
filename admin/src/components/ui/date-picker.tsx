"use client";

import { CalendarIcon } from "lucide-react";
import { format, parse, isValid } from "date-fns";
import { ptBR } from "date-fns/locale";
import { useState } from "react";

import { buttonVariants } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface DatePickerProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

function parseDate(str: string): Date | null {
  if (!str) return null;
  const parsed = parse(str, "dd/MM/yyyy", new Date());
  return isValid(parsed) ? parsed : null;
}

export function DatePicker({ value, onChange, placeholder = "dd/MM/yyyy", className }: DatePickerProps) {
  const [open, setOpen] = useState(false);
  const selectedDate = parseDate(value);

  const handleSelect = (date: Date | undefined) => {
    if (date) {
      onChange(format(date, "dd/MM/yyyy"));
    }
    setOpen(false);
  };

  return (
    <div className={cn("flex gap-1", className)}>
      <Input
        type="text"
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-28"
      />
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger
          className={cn(buttonVariants({ variant: "outline", size: "icon" }), "shrink-0")}
        >
          <CalendarIcon className="h-4 w-4 text-muted-foreground" />
        </PopoverTrigger>
        <PopoverContent align="start" className="w-auto p-0">
          <Calendar
            mode="single"
            selected={selectedDate ?? undefined}
            onSelect={handleSelect}
            locale={ptBR}
            captionLayout="dropdown"
            defaultMonth={selectedDate ?? new Date()}
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}
