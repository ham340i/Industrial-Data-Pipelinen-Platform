export type JsonValue =
  null | boolean | number | string | JsonValue[] | { [key: string]: JsonValue };
export type Configuration = Record<string, JsonValue>;
type Schema = Record<string, unknown>;
export interface ConfigField {
  name: string;
  label: string;
  description?: string;
  type: "string" | "integer" | "number" | "boolean" | "array";
  nullable: boolean;
  required: boolean;
  schema: Schema;
}
export interface ConfigIssue {
  field?: string;
  message: string;
}
const forbidden = new Set([
  "password",
  "passwd",
  "secret",
  "secrets",
  "credential",
  "credentials",
  "token",
  "accesstoken",
  "refreshtoken",
  "apikey",
  "connectionstring",
  "dsn",
  "username",
  "path",
  "localpath",
  "absolutepath",
  "workspacepath",
  "filepath",
  "outputpath",
  "secretref",
  "secretreference",
  "prototype",
  "constructor",
  "proto",
]);
const normalized = (key: string) => key.toLowerCase().replace(/[^a-z0-9]/g, "");
const object = (value: unknown): value is Schema =>
  value !== null && typeof value === "object" && !Array.isArray(value);

export function assertPublic(
  value: unknown,
  depth = 0,
): asserts value is JsonValue {
  if (depth > 20) throw new Error("Configuration is too deeply nested.");
  if (typeof value === "string" && /^(?:[/\\]|[A-Za-z]:|file:)/i.test(value))
    throw new Error(
      "Use logical resource references instead of absolute paths.",
    );
  if (value === null || typeof value === "boolean" || typeof value === "string")
    return;
  if (typeof value === "number" && Number.isFinite(value)) return;
  if (Array.isArray(value)) {
    value.forEach((item) => assertPublic(item, depth + 1));
    return;
  }
  if (object(value)) {
    const prototype = Object.getPrototypeOf(value);
    if (prototype !== Object.prototype && prototype !== null)
      throw new Error("Configuration must contain plain JSON objects.");
    for (const [key, item] of Object.entries(value)) {
      if (forbidden.has(normalized(key)))
        throw new Error(
          "Use resource references instead of credential fields.",
        );
      assertPublic(item, depth + 1);
    }
    return;
  }
  throw new Error("Configuration must contain finite JSON values.");
}

const allowed = new Set([
  "type",
  "title",
  "description",
  "default",
  "enum",
  "const",
  "minimum",
  "maximum",
  "exclusiveMinimum",
  "exclusiveMaximum",
  "minLength",
  "maxLength",
  "minItems",
  "maxItems",
  "uniqueItems",
  "items",
  "anyOf",
]);

function fieldSchema(input: unknown): { schema: Schema; nullable: boolean } {
  if (!object(input)) throw new Error("A field schema is invalid.");
  let schema = input;
  let nullable = false;
  if (input.anyOf !== undefined && !Array.isArray(input.anyOf))
    throw new Error("This union schema is invalid.");
  if (Array.isArray(input.anyOf)) {
    const choices = input.anyOf;
    const nonNull = choices.filter(
      (choice) => !object(choice) || choice.type !== "null",
    );
    if (choices.length !== 2 || nonNull.length !== 1 || !object(nonNull[0]))
      throw new Error("This union schema is not supported.");
    const nullChoice = choices.find(
      (choice) => object(choice) && choice.type === "null",
    ) as Schema;
    if (
      input.type !== undefined ||
      nonNull[0].anyOf !== undefined ||
      Object.keys(nullChoice).some(
        (key) => !["type", "title", "description"].includes(key),
      ) ||
      (input.enum !== undefined && nonNull[0].enum !== undefined) ||
      (input.const !== undefined && nonNull[0].const !== undefined)
    )
      throw new Error("This composed union is not supported.");
    nullable =
      (!Array.isArray(input.enum) || input.enum.includes(null)) &&
      (input.const === undefined || input.const === null);
    schema = { ...input, ...nonNull[0] };
    delete schema.anyOf;
  }
  if (Object.keys(schema).some((key) => !allowed.has(key)))
    throw new Error("This field uses an unsupported schema rule.");
  if (
    !["string", "integer", "number", "boolean", "array"].includes(
      String(schema.type),
    )
  )
    throw new Error("This field type is not supported.");
  if (schema.type === "array") {
    const item = fieldSchema(schema.items);
    if (item.schema.type === "array")
      throw new Error("Nested arrays are not supported.");
  }
  if (
    schema.enum !== undefined &&
    (!Array.isArray(schema.enum) || schema.enum.length === 0)
  )
    throw new Error("The enum schema is invalid.");
  if (
    Array.isArray(schema.enum) &&
    schema.enum.some(
      (option) =>
        option !== null &&
        !["string", "number", "boolean"].includes(typeof option),
    )
  )
    throw new Error("Only scalar enum choices are supported.");
  if (
    schema.const !== undefined &&
    schema.const !== null &&
    !["string", "number", "boolean"].includes(typeof schema.const)
  )
    throw new Error("Only scalar fixed values are supported.");
  for (const key of [
    "minimum",
    "maximum",
    "exclusiveMinimum",
    "exclusiveMaximum",
    "minLength",
    "maxLength",
    "minItems",
    "maxItems",
  ]) {
    if (
      schema[key] !== undefined &&
      (typeof schema[key] !== "number" || !Number.isFinite(schema[key]))
    )
      throw new Error("A schema constraint is invalid.");
  }
  for (const key of ["minLength", "maxLength", "minItems", "maxItems"])
    if (
      schema[key] !== undefined &&
      (!Number.isInteger(schema[key]) || (schema[key] as number) < 0)
    )
      throw new Error("A schema size constraint is invalid.");
  if (
    schema.uniqueItems !== undefined &&
    typeof schema.uniqueItems !== "boolean"
  )
    throw new Error("A uniqueness constraint is invalid.");
  return { schema, nullable };
}

export function fieldsFromSchema(input: unknown): ConfigField[] {
  assertPublic(input);
  if (!object(input) || input.type !== "object" || !object(input.properties))
    throw new Error("A configuration object schema is required.");
  const topAllowed = new Set([
    "type",
    "title",
    "description",
    "properties",
    "required",
    "additionalProperties",
  ]);
  if (
    Object.keys(input).some((key) => !topAllowed.has(key)) ||
    input.additionalProperties !== false
  )
    throw new Error("Only closed configuration object schemas are supported.");
  if (
    input.required !== undefined &&
    (!Array.isArray(input.required) ||
      input.required.some(
        (name) =>
          typeof name !== "string" ||
          !Object.hasOwn(input.properties as Schema, name),
      ))
  )
    throw new Error("Required fields are invalid.");
  return Object.entries(input.properties).map(([name, definition]) => {
    if (forbidden.has(normalized(name)))
      throw new Error(
        "Credential fields must be replaced by resource references.",
      );
    const { schema, nullable } = fieldSchema(definition);
    return {
      name,
      label: typeof schema.title === "string" ? schema.title : name,
      description:
        typeof schema.description === "string" ? schema.description : undefined,
      type: schema.type as ConfigField["type"],
      nullable,
      required: Array.isArray(input.required) && input.required.includes(name),
      schema,
    };
  });
}

function validValue(
  value: JsonValue,
  schema: Schema,
  nullable: boolean,
): string | undefined {
  if (value === null)
    return nullable ? undefined : "A value is required; null is not allowed.";
  const matches =
    schema.type === "integer"
      ? typeof value === "number" && Number.isInteger(value)
      : schema.type === "number"
        ? typeof value === "number" && Number.isFinite(value)
        : schema.type === "array"
          ? Array.isArray(value)
          : typeof value === schema.type;
  if (!matches) return `Enter a valid ${String(schema.type)}.`;
  if (
    Array.isArray(schema.enum) &&
    !schema.enum.some(
      (option) => JSON.stringify(option) === JSON.stringify(value),
    )
  )
    return "Choose one of the supported values.";
  if (
    schema.const !== undefined &&
    JSON.stringify(schema.const) !== JSON.stringify(value)
  )
    return "This value must match the fixed schema value.";
  if (typeof value === "number") {
    if (typeof schema.minimum === "number" && value < schema.minimum)
      return `Use a value of at least ${schema.minimum}.`;
    if (typeof schema.maximum === "number" && value > schema.maximum)
      return `Use a value of at most ${schema.maximum}.`;
    if (
      typeof schema.exclusiveMinimum === "number" &&
      value <= schema.exclusiveMinimum
    )
      return `Use a value greater than ${schema.exclusiveMinimum}.`;
    if (
      typeof schema.exclusiveMaximum === "number" &&
      value >= schema.exclusiveMaximum
    )
      return `Use a value below ${schema.exclusiveMaximum}.`;
  }
  if (typeof value === "string") {
    const length = Array.from(value).length;
    if (typeof schema.minLength === "number" && length < schema.minLength)
      return `Use at least ${schema.minLength} characters.`;
    if (typeof schema.maxLength === "number" && length > schema.maxLength)
      return `Use at most ${schema.maxLength} characters.`;
  }
  if (Array.isArray(value)) {
    if (typeof schema.minItems === "number" && value.length < schema.minItems)
      return `Use at least ${schema.minItems} items.`;
    if (typeof schema.maxItems === "number" && value.length > schema.maxItems)
      return `Use at most ${schema.maxItems} items.`;
    if (
      schema.uniqueItems === true &&
      new Set(value.map((item) => JSON.stringify(item))).size !== value.length
    )
      return "Items must be unique.";
    const item = fieldSchema(schema.items);
    for (const entry of value) {
      const error = validValue(entry, item.schema, item.nullable);
      if (error) return `List item: ${error}`;
    }
  }
}

export function defaultsFor(fields: ConfigField[]): Configuration {
  return Object.fromEntries(
    fields
      .filter((field) => field.schema.default !== undefined)
      .map((field) => [
        field.name,
        structuredClone(field.schema.default) as JsonValue,
      ]),
  );
}

export function validateConfiguration(
  fields: ConfigField[],
  value: Configuration,
): ConfigIssue[] {
  try {
    assertPublic(value);
  } catch {
    return [
      {
        message: "Configuration must use finite, credential-free JSON values.",
      },
    ];
  }
  const issues: ConfigIssue[] = [];
  for (const key of Object.keys(value))
    if (!fields.some((field) => field.name === key))
      issues.push({ message: "Configuration contains an undeclared field." });
  for (const field of fields) {
    const entry = Object.hasOwn(value, field.name)
      ? value[field.name]
      : (field.schema.default as JsonValue | undefined);
    const message =
      entry === undefined
        ? field.required
          ? "This field is required."
          : undefined
        : validValue(entry, field.schema, field.nullable);
    if (message) issues.push({ field: field.name, message });
  }
  return issues;
}
