// AI contribution: 50% or more AI-generated
import { Button, Stack, TextField } from "@mui/material";
import type { ConfigField, ConfigIssue, JsonValue } from "./schema";

interface FieldControlProps {
  field: ConfigField;
  value: JsonValue | undefined;
  onChange: (value: JsonValue | undefined) => void;
  issue?: string;
  previousIssue?: string;
  disabled: boolean;
}

function isStructuredValue(field: ConfigField, value: unknown) {
  return field.type === "array"
    ? Array.isArray(value)
    : value !== null && typeof value === "object" && !Array.isArray(value);
}

function parseStructuredEdit(field: ConfigField, text: string): JsonValue {
  if (!text.trim()) return text;
  try {
    const parsed: unknown = JSON.parse(text);
    return isStructuredValue(field, parsed) ? (parsed as JsonValue) : text;
  } catch {
    return text;
  }
}

function StructuredField({
  field,
  value,
  onChange,
  issue,
  previousIssue,
  disabled,
}: FieldControlProps) {
  const text =
    value === undefined
      ? ""
      : typeof value === "string"
        ? value
        : JSON.stringify(value);
  const parseError =
    value !== undefined && value !== null && !isStructuredValue(field, value);
  const kind = field.type === "array" ? "list" : "object";
  const hint =
    kind === "object"
      ? "Enter a JSON object."
      : 'Enter a JSON list, such as ["column_a"].';
  return (
    <TextField
      label={field.label}
      disabled={disabled}
      slotProps={{ htmlInput: { "data-config-field": field.name } }}
      fullWidth
      multiline
      minRows={2}
      value={text}
      required={field.required}
      error={parseError || Boolean(issue)}
      helperText={
        parseError
          ? `Enter a valid JSON ${kind}.`
          : (issue ?? previousIssue ?? field.description ?? hint)
      }
      onChange={(event) =>
        onChange(parseStructuredEdit(field, event.target.value))
      }
    />
  );
}

function fieldHint(field: ConfigField) {
  return field.description ?? (field.required ? "Required" : "Optional");
}

function SelectField({
  field,
  value,
  onChange,
  issue,
  previousIssue,
  disabled,
  options,
}: FieldControlProps & { options: JsonValue[] }) {
  return (
    <TextField
      select
      disabled={disabled}
      slotProps={{
        select: { native: true },
        htmlInput: { "data-config-field": field.name },
      }}
      label={field.label}
      value={value === undefined ? "" : JSON.stringify(value)}
      required={field.required}
      error={Boolean(issue)}
      helperText={issue ?? previousIssue ?? fieldHint(field)}
      onChange={(event) =>
        onChange(
          event.target.value === ""
            ? undefined
            : (JSON.parse(event.target.value) as JsonValue),
        )
      }
    >
      <option value="">Not set</option>
      {options.map((option) => (
        <option key={JSON.stringify(option)} value={JSON.stringify(option)}>
          {String(option)}
        </option>
      ))}
      {field.nullable && !options.includes(null) && (
        <option value="null">Null</option>
      )}
    </TextField>
  );
}

function ScalarField({
  field,
  value,
  onChange,
  issue,
  previousIssue,
  disabled,
}: FieldControlProps) {
  const numeric = field.type === "number" || field.type === "integer";
  return (
    <TextField
      label={field.label}
      disabled={disabled}
      value={value === undefined || value === null ? "" : String(value)}
      required={field.required}
      error={Boolean(issue)}
      helperText={
        issue ??
        previousIssue ??
        (value === null ? "Explicit null value" : fieldHint(field))
      }
      type={numeric ? "number" : "text"}
      slotProps={{
        htmlInput: {
          "data-config-field": field.name,
          step: field.type === "integer" ? 1 : "any",
        },
      }}
      onChange={(event) => {
        const raw = event.target.value;
        onChange(field.type === "string" || raw === "" ? raw : Number(raw));
      }}
    />
  );
}

function fieldDiagnostics(
  name: string,
  issues: ConfigIssue[],
  serverErrors: Record<string, string[]>,
  stale: boolean,
) {
  const local = issues.find((item) => item.field === name)?.message;
  const remote = Object.entries(serverErrors)
    .filter(
      ([key]) =>
        key === name ||
        key.startsWith(`${name}.`) ||
        key.startsWith(`${name}[`),
    )
    .flatMap(([, messages]) => messages);
  const current = [local, ...(stale ? [] : remote)].filter(Boolean);
  return {
    issue: [...new Set(current)].join(" ") || undefined,
    previousIssue:
      stale && remote.length > 0
        ? `Previous check: ${[...new Set(remote)].join(" ")}`
        : undefined,
  };
}

export function ConfigFormField({
  nodeId,
  issues,
  serverErrors,
  staleDiagnostics,
  ...control
}: Omit<FieldControlProps, "issue" | "previousIssue"> & {
  nodeId: string;
  issues: ConfigIssue[];
  serverErrors: Record<string, string[]>;
  staleDiagnostics: boolean;
}) {
  const { field, disabled, onChange } = control;
  const options = Array.isArray(field.schema.enum)
    ? (field.schema.enum as JsonValue[])
    : field.type === "boolean"
      ? [true, false]
      : undefined;
  const props = {
    ...control,
    ...fieldDiagnostics(field.name, issues, serverErrors, staleDiagnostics),
  };
  return (
    <Stack spacing={1}>
      {field.type === "array" || field.type === "object" ? (
        <StructuredField
          key={`${nodeId}:${field.name}:${JSON.stringify(field.schema)}`}
          {...props}
        />
      ) : options ? (
        <SelectField {...props} options={options} />
      ) : (
        <ScalarField {...props} />
      )}
      {field.nullable && !options && (
        <Button
          size="small"
          disabled={disabled}
          onClick={() => onChange(null)}
          sx={{ alignSelf: "flex-start" }}
        >
          Set {field.label} to null
        </Button>
      )}
    </Stack>
  );
}
