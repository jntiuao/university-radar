import type { InputHTMLAttributes, SelectHTMLAttributes } from "react";

const baseInputClass =
  "w-full px-4 py-2.5 rounded-xl border border-border bg-input-background text-[13px] focus:outline-none focus:ring-2 transition-all";

interface FormInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  accent?: "purple" | "blue";
}

export function FormInput({ label, accent = "purple", className, ...props }: FormInputProps) {
  const ringColor = accent === "blue" ? "#0984e3" : "#6c5ce7";
  return (
    <div className={className}>
      <label className="text-[12px] text-muted-foreground mb-1.5 block">{label}</label>
      <input
        className={baseInputClass}
        style={{
          // @ts-ignore
          "--tw-ring-color": `color-mix(in srgb, ${ringColor} 20%, transparent)`,
        }}
        onFocus={(e) => {
          e.target.style.borderColor = ringColor;
        }}
        onBlur={(e) => {
          e.target.style.borderColor = "";
        }}
        {...props}
      />
    </div>
  );
}

interface FormSelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  options: { value: string; label: string }[];
  placeholderOption?: string;
  accent?: "purple" | "blue";
}

export function FormSelect({
  label,
  options,
  placeholderOption,
  accent = "purple",
  className,
  ...props
}: FormSelectProps) {
  const ringColor = accent === "purple" ? "#6c5ce7" : "#0984e3";
  return (
    <div className={className}>
      <label className="text-[12px] text-muted-foreground mb-1.5 block">{label}</label>
      <select
        className={`${baseInputClass} ${props.disabled ? "text-muted-foreground opacity-50" : ""}`}
        onFocus={(e) => {
          if (!props.disabled) e.target.style.borderColor = ringColor;
        }}
        onBlur={(e) => {
          e.target.style.borderColor = "";
        }}
        {...props}
      >
        {placeholderOption && <option value="">{placeholderOption}</option>}
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
