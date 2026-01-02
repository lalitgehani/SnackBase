import * as React from "react"
import { X } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

export interface TagInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    value?: string[]
    onValueChange?: (value: string[]) => void
}

const TagInput = React.forwardRef<HTMLInputElement, TagInputProps>(
    ({ className, value = [], onValueChange, ...props }, ref) => {
        const [inputValue, setInputValue] = React.useState("")

        const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
            if (e.key === "Enter") {
                e.preventDefault()
                const trimmedValue = inputValue.trim()
                if (trimmedValue && !value.includes(trimmedValue)) {
                    const newValue = [...value, trimmedValue]
                    onValueChange?.(newValue)
                    setInputValue("")
                }
            } else if (e.key === "Backspace" && !inputValue && value.length > 0) {
                const newValue = value.slice(0, -1)
                onValueChange?.(newValue)
            }
        }

        const removeTag = (tagToRemove: string) => {
            const newValue = value.filter((tag) => tag !== tagToRemove)
            onValueChange?.(newValue)
        }

        return (
            <div
                className={cn(
                    "flex min-h-10 w-full flex-wrap gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background disabled:cursor-not-allowed disabled:opacity-50",
                    className
                )}
            >
                {value.map((tag) => (
                    <Badge key={tag} variant="secondary" className="gap-1 pr-1">
                        {tag}
                        <button
                            type="button"
                            onClick={() => removeTag(tag)}
                            className="rounded-full outline-none ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-2"
                        >
                            <X className="h-3 w-3" />
                            <span className="sr-only">Remove {tag}</span>
                        </button>
                    </Badge>
                ))}
                <input
                    {...props}
                    ref={ref}
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className="flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
                />
            </div>
        )
    }
)
TagInput.displayName = "TagInput"

export { TagInput }
