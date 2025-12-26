/**
 * Rule Editor component
 * Provides a textarea for rule expression input with real-time syntax validation
 */

import { useState, useEffect, useCallback } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp, Check, AlertCircle, Code } from 'lucide-react';
import { validateRule } from '@/services/roles.service';

interface RuleEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  label?: string;
}

interface SyntaxHelp {
  category: string;
  items: {
    name: string;
    description: string;
    example: string;
  }[];
}

const SYNTAX_HELP: SyntaxHelp[] = [
  {
    category: 'Variables',
    items: [
      { name: 'user.id', description: 'Current user ID', example: 'user.id == "user_123"' },
      { name: 'user.email', description: 'Current user email', example: 'user.email == "admin@example.com"' },
      { name: 'user.role', description: "Current user's role name", example: 'user.role == "admin"' },
      { name: 'account.id', description: 'Current account ID', example: 'account.id == "AB1234"' },
      { name: 'record.field', description: 'Any field on the record', example: 'record.status == "published"' },
    ],
  },
  {
    category: 'Operators',
    items: [
      { name: '== !=', description: 'Equal, not equal', example: 'status == "active"' },
      { name: '< > <= >=', description: 'Comparison', example: 'age >= 18' },
      { name: 'and or not', description: 'Logical operators', example: 'active and verified' },
      { name: 'in', description: 'Membership', example: 'status in ["draft", "published"]' },
    ],
  },
  {
    category: 'Functions',
    items: [
      { name: 'contains()', description: 'String contains', example: 'contains(title, "important")' },
      { name: 'starts_with()', description: 'String starts with', example: 'starts_with(email, "admin@")' },
      { name: 'ends_with()', description: 'String ends with', example: 'ends_with(email, "@company.com")' },
    ],
  },
  {
    category: 'Macros',
    items: [
      { name: '@has_role()', description: 'User has specific role', example: '@has_role("editor")' },
      { name: '@has_group()', description: 'User belongs to group', example: '@has_group("moderators")' },
      { name: '@owns_record()', description: 'User is record creator', example: '@owns_record()' },
      { name: '@has_permission()', description: 'Check specific permission', example: '@has_permission("update", "posts")' },
      { name: '@in_time_range()', description: 'Time-based access', example: '@in_time_range(9, 17)' },
    ],
  },
];

export default function RuleEditor({
  value,
  onChange,
  placeholder = 'e.g., @has_role("admin") or user.id == record.created_by',
  disabled = false,
  label = 'Rule Expression',
}: RuleEditorProps) {
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<{ valid: boolean; error: string | null } | null>(null);
  const [showSyntaxHelp, setShowSyntaxHelp] = useState(false);

  // Debounced validation
  const validateCurrentRule = useCallback(async (rule: string) => {
    if (!rule.trim()) {
      setValidationResult(null);
      return;
    }

    setIsValidating(true);
    try {
      const result = await validateRule(rule);
      setValidationResult(result);
    } catch {
      // If validation API fails, show as unknown but don't block
      setValidationResult(null);
    } finally {
      setIsValidating(false);
    }
  }, []);

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      validateCurrentRule(value);
    }, 500); // 500ms debounce

    return () => clearTimeout(timeoutId);
  }, [value, validateCurrentRule]);

  const insertExample = (example: string) => {
    onChange(example);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label>{label}</Label>
        <div className="flex items-center gap-2">
          {isValidating && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <AlertCircle className="h-3 w-3 animate-spin" />
              Validating...
            </span>
          )}
          {validationResult && !isValidating && (
            <span
              className={`text-xs flex items-center gap-1 ${
                validationResult.valid ? 'text-green-600' : 'text-destructive'
              }`}
            >
              {validationResult.valid ? (
                <>
                  <Check className="h-3 w-3" />
                  Valid rule
                </>
              ) : (
                <>
                  <AlertCircle className="h-3 w-3" />
                  {validationResult.error || 'Invalid syntax'}
                </>
              )}
            </span>
          )}
        </div>
      </div>

      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        rows={4}
        className={`font-mono text-sm ${
          validationResult && !isValidating && !validationResult.valid
            ? 'border-destructive focus-visible:ring-destructive'
            : ''
        }`}
      />

      {/* Syntax Help Toggle */}
      <div className="space-y-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={() => setShowSyntaxHelp(!showSyntaxHelp)}
        >
          <Code className="h-3 w-3 mr-1" />
          Syntax Reference
          {showSyntaxHelp ? (
            <ChevronUp className="h-3 w-3 ml-1" />
          ) : (
            <ChevronDown className="h-3 w-3 ml-1" />
          )}
        </Button>

        {showSyntaxHelp && (
          <div className="border rounded-md p-4 space-y-4 bg-muted/30 max-h-96 overflow-y-auto">
            {SYNTAX_HELP.map((category) => (
              <div key={category.category}>
                <h4 className="text-sm font-semibold mb-2">{category.category}</h4>
                <div className="space-y-2">
                  {category.items.map((item) => (
                    <div
                      key={item.name}
                      className="flex items-start justify-between group p-2 rounded hover:bg-background cursor-pointer"
                      onClick={() => insertExample(item.example)}
                    >
                      <div className="flex-1">
                        <span className="font-mono text-sm font-medium">{item.name}</span>
                        <p className="text-xs text-muted-foreground">{item.description}</p>
                      </div>
                      <code className="text-xs bg-background px-2 py-1 rounded border font-mono opacity-60 group-hover:opacity-100">
                        {item.example}
                      </code>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            <div className="text-xs text-muted-foreground pt-2 border-t">
              Click any example to insert it into the rule editor
            </div>
          </div>
        )}
      </div>

      {/* Example Rules */}
      <div className="text-xs text-muted-foreground">
        <p className="font-medium mb-1">Examples:</p>
        <ul className="space-y-1 ml-4">
          <li
            className="cursor-pointer hover:text-foreground underline"
            onClick={() => insertExample('@has_role("admin")')}
          >
            Admin role only
          </li>
          <li
            className="cursor-pointer hover:text-foreground underline"
            onClick={() => insertExample('@has_role("editor") or @owns_record()')}
          >
            Editors or record owners
          </li>
          <li
            className="cursor-pointer hover:text-foreground underline"
            onClick={() => insertExample('user.id == record.created_by')}
          >
            Record creator only
          </li>
          <li
            className="cursor-pointer hover:text-foreground underline"
            onClick={() => insertExample('status in ["draft", "pending"] and @owns_record()')}
          >
            Draft/pending records owned by user
          </li>
        </ul>
      </div>
    </div>
  );
}
