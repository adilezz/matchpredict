"use client";

import { useState, useRef, useEffect } from "react";
import { getDaysArray, isSameDay, toDateString } from "@/lib/helpers";

interface DateNavProps {
  selectedDate: Date;
  onSelect: (date: Date) => void;
}

export default function DateNav({ selectedDate, onSelect }: DateNavProps) {
  const [showCalendar, setShowCalendar] = useState(false);
  const [calMonth, setCalMonth] = useState(selectedDate);
  const calRef = useRef<HTMLDivElement>(null);

  const days = getDaysArray(new Date(), 7);
  const today = new Date();

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (calRef.current && !calRef.current.contains(e.target as Node)) {
        setShowCalendar(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const calDays = getCalendarDays(calMonth);

  return (
    <div className="flex items-center gap-2">
      {/* Quick day buttons */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 flex-1">
        {days.map((day) => {
          const isSelected = isSameDay(day, selectedDate);
          const isToday = isSameDay(day, today);
          const dayName = isToday
            ? "Today"
            : day.toLocaleDateString("en-GB", { weekday: "short" });
          const dayNum = day.getDate();
          const month = day.toLocaleDateString("en-GB", { month: "short" });

          return (
            <button
              key={day.toISOString()}
              onClick={() => onSelect(day)}
              className={`flex flex-col items-center min-w-[52px] px-2 py-1.5 rounded transition-colors ${
                isSelected
                  ? "bg-accent text-white"
                  : "bg-surface-3 text-gray-400 hover:bg-surface-5 hover:text-gray-200"
              }`}
            >
              <span className="text-[10px] font-medium">{dayName}</span>
              <span className="text-sm font-bold">{dayNum}</span>
              <span className="text-[10px]">{month}</span>
            </button>
          );
        })}
      </div>

      {/* Calendar toggle */}
      <div className="relative" ref={calRef}>
        <button
          onClick={() => {
            setCalMonth(selectedDate);
            setShowCalendar(!showCalendar);
          }}
          className="flex items-center gap-1.5 px-3 py-2 bg-surface-3 hover:bg-surface-5 text-gray-400 hover:text-white rounded transition-colors text-xs"
          title="Open calendar"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
          </svg>
          <span className="hidden sm:inline">
            {selectedDate.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })}
          </span>
        </button>

        {showCalendar && (
          <div className="absolute right-0 top-full mt-1 z-50 bg-surface-1 border border-surface-4 rounded-lg shadow-xl p-3 w-72">
            {/* Month nav */}
            <div className="flex items-center justify-between mb-2">
              <button
                onClick={() =>
                  setCalMonth(new Date(calMonth.getFullYear(), calMonth.getMonth() - 1, 1))
                }
                className="p-1 hover:bg-surface-3 rounded transition-colors text-gray-400 hover:text-white"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <span className="text-xs font-semibold text-gray-200">
                {calMonth.toLocaleDateString("en-GB", { month: "long", year: "numeric" })}
              </span>
              <button
                onClick={() =>
                  setCalMonth(new Date(calMonth.getFullYear(), calMonth.getMonth() + 1, 1))
                }
                className="p-1 hover:bg-surface-3 rounded transition-colors text-gray-400 hover:text-white"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
              </button>
            </div>

            {/* Day names */}
            <div className="grid grid-cols-7 gap-0.5 mb-1">
              {["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"].map((d) => (
                <div key={d} className="text-center text-[10px] text-gray-600 font-medium py-1">
                  {d}
                </div>
              ))}
            </div>

            {/* Days grid */}
            <div className="grid grid-cols-7 gap-0.5">
              {calDays.map((day, i) => {
                const isCurrentMonth = day.getMonth() === calMonth.getMonth();
                const isSel = isSameDay(day, selectedDate);
                const isTod = isSameDay(day, today);
                return (
                  <button
                    key={i}
                    onClick={() => {
                      onSelect(day);
                      setShowCalendar(false);
                    }}
                    className={`h-8 text-xs rounded transition-colors ${
                      isSel
                        ? "bg-accent text-white font-bold"
                        : isTod
                          ? "bg-accent/20 text-accent font-semibold"
                          : isCurrentMonth
                            ? "text-gray-300 hover:bg-surface-3"
                            : "text-gray-600 hover:bg-surface-3"
                    }`}
                  >
                    {day.getDate()}
                  </button>
                );
              })}
            </div>

            {/* Quick actions */}
            <div className="flex gap-1.5 mt-2 pt-2 border-t border-surface-4">
              <button
                onClick={() => {
                  onSelect(new Date());
                  setShowCalendar(false);
                }}
                className="flex-1 text-[10px] py-1.5 bg-surface-3 hover:bg-surface-5 text-gray-400 hover:text-white rounded transition-colors font-medium"
              >
                Today
              </button>
              <button
                onClick={() => {
                  const sat = getNextSaturday();
                  onSelect(sat);
                  setShowCalendar(false);
                }}
                className="flex-1 text-[10px] py-1.5 bg-surface-3 hover:bg-surface-5 text-gray-400 hover:text-white rounded transition-colors font-medium"
              >
                This Weekend
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function getCalendarDays(month: Date): Date[] {
  const year = month.getFullYear();
  const m = month.getMonth();
  const firstDay = new Date(year, m, 1);
  const lastDay = new Date(year, m + 1, 0);

  let startDay = firstDay.getDay() - 1;
  if (startDay < 0) startDay = 6;

  const days: Date[] = [];
  for (let i = startDay - 1; i >= 0; i--) {
    days.push(new Date(year, m, -i));
  }
  for (let d = 1; d <= lastDay.getDate(); d++) {
    days.push(new Date(year, m, d));
  }
  while (days.length < 42) {
    const next = days.length - startDay - lastDay.getDate() + 1;
    days.push(new Date(year, m + 1, next));
  }
  return days;
}

function getNextSaturday(): Date {
  const d = new Date();
  const day = d.getDay();
  const diff = (6 - day + 7) % 7 || 7;
  d.setDate(d.getDate() + diff);
  return d;
}
