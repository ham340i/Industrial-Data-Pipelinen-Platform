import { useEffect, useId, useRef, useState } from "react";
import {
  Alert,
  Button,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import {
  assertPublic,
  defaultsFor,
  fieldsFromSchema,
  validateConfiguration,
} from "./schema";
import type { Configuration, ConfigField, JsonValue } from "./schema";

export interface SelectedBlock {
  nodeId: string;
  blockId: string;
  version: string;
}
export interface RegistryBlock {
  block_id: string;
  version: string;
  name: string;
  config_schema: unknown;
}
export type RegistryState =
  | { status: "loading" }
  | { status: "error" }
  | { status: "ready"; blocks: RegistryBlock[] };
export interface BlockConfigPanelProps {
  selected: SelectedBlock | null;
  registry: RegistryState;
  value: Configuration;
  onChange: (nodeId: string, value: Configuration) => void;
  disabled?: boolean;
  serverErrors?: Record<string, string[]>;
  focusRequest?: { nodeId: string; field: string | null } | null;
  onRetry?: () => void;
}

function ArrayField({
  field,
  value,
  onChange,
  issue,
  disabled,
}: {
  field: ConfigField;
  value: JsonValue | undefined;
  onChange: (value: JsonValue | undefined) => void;
  issue?: string;
  disabled?: boolean;
}) {
  const text =
    value === undefined
      ? ""
      : typeof value === "string"
        ? value
        : JSON.stringify(value);
  const parseError =
    value !== undefined && value !== null && !Array.isArray(value);
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
          ? "Enter a valid JSON list."
          : (issue ??
            field.description ??
            'Enter a JSON list, such as ["column_a"].')
      }
      onChange={(event) => {
        const next = event.target.value;
        if (!next.trim()) {
          onChange(next);
          return;
        }
        try {
          const parsed: unknown = JSON.parse(next);
          if (!Array.isArray(parsed)) throw new Error();
          onChange(parsed as JsonValue[]);
        } catch {
          onChange(next);
        }
      }}
    />
  );
}

function ConfigForm({
  selected,
  block,
  value,
  onChange,
  disabled = false,
  serverErrors = {},
  focusRequest,
}: {
  selected: SelectedBlock;
  block: RegistryBlock;
  value: Configuration;
  onChange: BlockConfigPanelProps["onChange"];
  disabled?: boolean;
  serverErrors?: Record<string, string[]>;
  focusRequest?: BlockConfigPanelProps["focusRequest"];
}) {
  const headingId = useId();
  const formRef = useRef<HTMLElement>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);
  useEffect(() => {
    if (!focusRequest || disabled) return;
    const controls = Array.from(
      formRef.current?.querySelectorAll<HTMLElement>(
        "input, textarea, select",
      ) ?? [],
    );
    const field = focusRequest.field?.split(/[.[]/, 1)[0];
    (
      controls.find(
        (input) => input.dataset.configField === focusRequest.field,
      ) ??
      controls.find((input) => input.dataset.configField === field) ??
      controls.find((input) => input.getAttribute("aria-invalid") === "true") ??
      controls[0] ??
      formRef.current
    )?.focus();
  }, [focusRequest, disabled]);
  let fields: ConfigField[];
  try {
    fields = fieldsFromSchema(block.config_schema);
  } catch {
    return (
      <Alert severity="error">
        This block has an unsupported or unsafe configuration schema. Existing
        values have been preserved. Ask the block owner to provide a supported
        public schema.
      </Alert>
    );
  }
  const effective = { ...defaultsFor(fields), ...value };
  const issues = validateConfiguration(fields, effective);
  const update = (name: string, next: JsonValue | undefined) => {
    const config = { ...effective };
    if (next === undefined) delete config[name];
    else config[name] = next;
    try {
      assertPublic(config);
      onChange(selected.nodeId, config);
      setUpdateError(null);
    } catch {
      setUpdateError(
        "Use logical resource references instead of runtime bindings or credential fields. This edit was not stored.",
      );
    }
  };
  return (
    <Paper
      component="section"
      ref={formRef}
      tabIndex={-1}
      aria-labelledby={headingId}
      variant="outlined"
      sx={{ p: 3 }}
    >
      <Stack spacing={2.5}>
        <div>
          <Typography id={headingId} component="h2" variant="h6">
            Configure {block.name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Block {selected.nodeId} · {block.version}
          </Typography>
        </div>
        {issues.length > 0 && (
          <Alert severity="warning" role="status">
            {issues.length} configuration{" "}
            {issues.length === 1 ? "issue needs" : "issues need"} attention for
            block {selected.nodeId}.
          </Alert>
        )}
        {updateError && <Alert severity="error">{updateError}</Alert>}
        {issues
          .filter((issue) => !issue.field)
          .map((issue) => (
            <Alert severity="warning" key={issue.message}>
              {issue.message}
            </Alert>
          ))}
        {fields.map((field) => {
          const current = effective[field.name];
          const localIssue = issues.find(
            (item) => item.field === field.name,
          )?.message;
          const remote = Object.entries(serverErrors)
            .filter(
              ([key]) =>
                key === field.name ||
                key.startsWith(`${field.name}.`) ||
                key.startsWith(`${field.name}[`),
            )
            .flatMap(([, messages]) => messages);
          const issue =
            [...new Set([localIssue, ...remote].filter(Boolean))].join(" ") ||
            undefined;
          const helper =
            issue ??
            field.description ??
            (field.required ? "Required" : "Optional");
          const options = Array.isArray(field.schema.enum)
            ? field.schema.enum
            : field.type === "boolean"
              ? [true, false]
              : undefined;
          return (
            <Stack key={field.name} spacing={1}>
              {field.type === "array" ? (
                <ArrayField
                  key={`${selected.nodeId}:${field.name}:${JSON.stringify(field.schema)}`}
                  field={field}
                  value={current}
                  issue={issue}
                  disabled={disabled}
                  onChange={(next) => update(field.name, next)}
                />
              ) : options ? (
                <TextField
                  select
                  disabled={disabled}
                  slotProps={{
                    select: { native: true },
                    htmlInput: { "data-config-field": field.name },
                  }}
                  label={field.label}
                  value={current === undefined ? "" : JSON.stringify(current)}
                  required={field.required}
                  error={Boolean(issue)}
                  helperText={helper}
                  onChange={(event) =>
                    update(
                      field.name,
                      event.target.value === ""
                        ? undefined
                        : (JSON.parse(event.target.value) as JsonValue),
                    )
                  }
                >
                  <option value="">Not set</option>
                  {options.map((option) => (
                    <option
                      key={JSON.stringify(option)}
                      value={JSON.stringify(option)}
                    >
                      {String(option)}
                    </option>
                  ))}
                  {field.nullable && !options.includes(null) && (
                    <option value="null">Null</option>
                  )}
                </TextField>
              ) : (
                <TextField
                  label={field.label}
                  disabled={disabled}
                  value={
                    current === undefined || current === null
                      ? ""
                      : String(current)
                  }
                  required={field.required}
                  error={Boolean(issue)}
                  helperText={current === null ? "Explicit null value" : helper}
                  type={
                    field.type === "number" || field.type === "integer"
                      ? "number"
                      : "text"
                  }
                  slotProps={{
                    htmlInput: {
                      "data-config-field": field.name,
                      step: field.type === "integer" ? 1 : "any",
                    },
                  }}
                  onChange={(event) => {
                    const raw = event.target.value;
                    update(
                      field.name,
                      field.type === "string"
                        ? raw
                        : raw === ""
                          ? ""
                          : Number(raw),
                    );
                  }}
                />
              )}
              {field.nullable && !options && (
                <Button
                  size="small"
                  disabled={disabled}
                  onClick={() => update(field.name, null)}
                  sx={{ alignSelf: "flex-start" }}
                >
                  Set {field.label} to null
                </Button>
              )}
            </Stack>
          );
        })}
        {fields.length === 0 && (
          <Typography>This block needs no configuration.</Typography>
        )}
        <Typography variant="caption" color="text.secondary">
          Values stay with this block when selection changes. Use resource
          references for protected data. The server validates configuration
          before execution.
        </Typography>
      </Stack>
    </Paper>
  );
}

export function BlockConfigPanel(props: BlockConfigPanelProps) {
  if (!props.selected)
    return (
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography component="h2" variant="h6">
          Block configuration
        </Typography>
        <Typography sx={{ mt: 1 }}>Select a block to configure it.</Typography>
      </Paper>
    );
  if (props.registry.status === "loading")
    return (
      <Alert severity="info" role="status">
        Loading block definitions. Your configuration is preserved.
      </Alert>
    );
  if (props.registry.status === "error")
    return (
      <Alert severity="error">
        Block definitions could not be loaded. Your configuration is preserved.
        {props.onRetry && (
          <Button onClick={props.onRetry}>Retry definitions</Button>
        )}
      </Alert>
    );
  const matches = props.registry.blocks.filter(
    (item) =>
      item.block_id === props.selected?.blockId &&
      item.version === props.selected.version,
  );
  if (matches.length !== 1)
    return (
      <Alert severity="error">
        The exact block version is unavailable or duplicated. Your configuration
        is preserved.
      </Alert>
    );
  return (
    <ConfigForm
      key={`${props.selected.nodeId}:${props.selected.blockId}:${props.selected.version}`}
      selected={props.selected}
      block={matches[0]}
      value={props.value}
      onChange={props.onChange}
      disabled={props.disabled}
      serverErrors={props.serverErrors}
      focusRequest={props.focusRequest}
    />
  );
}
