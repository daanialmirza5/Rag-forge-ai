import { Button } from "@/components/ui/button";

const PRESETS = [
  { label: "7 days", days: 7 },
  { label: "30 days", days: 30 },
  { label: "90 days", days: 90 },
];

/** One filter row above everything it scopes — every chart/stat/table on the
 * page re-renders against the same slice, so the numbers always agree. */
export function DateRangeFilter({
  value,
  onChange,
}: {
  value: number;
  onChange: (days: number) => void;
}) {
  return (
    <div className="flex gap-1.5">
      {PRESETS.map((preset) => (
        <Button
          key={preset.days}
          type="button"
          size="sm"
          variant={value === preset.days ? "default" : "outline"}
          onClick={() => onChange(preset.days)}
        >
          {preset.label}
        </Button>
      ))}
    </div>
  );
}
