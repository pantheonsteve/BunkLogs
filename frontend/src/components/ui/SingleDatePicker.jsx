import * as React from "react"
import { format } from "date-fns"
import { cn } from "../../lib/utils"
import { Calendar } from "./calendar"
import { Popover, PopoverContent, PopoverTrigger } from "./popover"

export default function SingleDatePicker({ className, date, setDate }) {
  // Ensure the date is set to noon
  const normalizedDate = React.useMemo(() => {
    if (!date) return null;
    const d = new Date(date);
    d.setHours(12, 0, 0, 0);
    return d;
  }, [date]);

  return (
    <div className={cn("grid gap-2", className)}>
      <Popover>
        <PopoverTrigger asChild>
          <button
            id="date"
            className={cn(
              "btn px-2.5 min-w-[15.5rem] bg-white border-gray-200 hover:border-gray-300 dark:border-gray-700/60 dark:hover:border-gray-600 dark:bg-gray-800 text-gray-600 hover:text-gray-800 dark:text-gray-300 dark:hover:text-gray-100 font-medium text-left justify-start",
              !normalizedDate && "text-muted-foreground"
            )}
          >
            <svg className="fill-current text-gray-400 dark:text-gray-500 ml-1 mr-2" width="16" height="16" viewBox="0 0 16 16">
              <path d="M5 4a1 1 0 0 0 0 2h6a1 1 0 1 0 0-2H5Z"></path>
              <path d="M4 0a4 4 0 0 0-4 4v8a4 4 0 0 0 4 4h8a4 4 0 0 0 4-4V4a4 4 0 0 0-4-4H4ZM2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V4Z"></path>
            </svg>
            {normalizedDate ? format(normalizedDate, "LLL dd, y") : "Pick a date"}
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar
            mode="single"
            selected={normalizedDate}
            onSelect={(selectedDate) => {
              if (selectedDate) {
                // Ensure new selections are also set to noon
                const newDate = new Date(selectedDate);
                console.log('New Date', JSON.stringify(newDate));
                newDate.setHours(12, 0, 0, 0);
                // Save in local storage first
                localStorage.setItem('selectedDate', JSON.stringify(newDate));
                // Then set the date
                setDate(newDate);
              } else {
                localStorage.setItem('selectedDate', JSON.stringify(selectedDate));
                setDate(selectedDate);
              }
            }}
            defaultMonth={normalizedDate}
          />
        </PopoverContent>
      </Popover>
    </div>
  );
}