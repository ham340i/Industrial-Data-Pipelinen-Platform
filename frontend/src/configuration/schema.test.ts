// AI contribution: 50% or more AI-generated
import { describe, expect, it } from "vitest";
import type { Configuration } from "./schema";
import {
  assertPublic,
  defaultsFor,
  fieldsFromSchema,
  validateConfiguration,
} from "./schema";
const schema = {
  type: "object",
  additionalProperties: false,
  required: ["amount", "resource_ref"],
  properties: {
    amount: { type: "integer", default: 1, minimum: -10, maximum: 10 },
    resource_ref: { type: "string", minLength: 1 },
    enabled: { type: "boolean", default: false },
    choice: { type: "string", enum: ["fill", "drop"] },
    optional: { anyOf: [{ type: "string" }, { type: "null" }], default: null },
    columns: { type: "array", items: { type: "string" }, uniqueItems: true },
  },
};
describe("bounded public configuration schema", () => {
  it.each([
    { rule: { type: "integer", minimum: -2, maximum: 2 }, good: -2, bad: -3 },
    {
      rule: { type: "number", exclusiveMinimum: 0, exclusiveMaximum: 2 },
      good: 1.5,
      bad: 2,
    },
    {
      rule: { type: "string", minLength: 1, maxLength: 2 },
      good: "😀",
      bad: "abc",
    },
    {
      rule: {
        type: "array",
        items: { type: "integer" },
        minItems: 1,
        maxItems: 2,
      },
      good: [1, 2],
      bad: [],
    },
    {
      rule: { type: "array", items: { type: "string" }, uniqueItems: true },
      good: ["a", "b"],
      bad: ["a", "a"],
    },
    { rule: { type: "boolean" }, good: false, bad: "false" },
    {
      rule: { type: "string", enum: ["one", "two"] },
      good: "two",
      bad: "three",
    },
  ])(
    "checks independently chosen scalar/list boundaries: $rule",
    ({ rule, good, bad }) => {
      const fields = fieldsFromSchema({
        type: "object",
        additionalProperties: false,
        required: ["value"],
        properties: { value: rule },
      });
      expect(validateConfiguration(fields, { value: good })).toEqual([]);
      expect(validateConfiguration(fields, { value: bad })).toHaveLength(1);
    },
  );
  it("applies typed defaults and distinguishes missing required fields", () => {
    const fields = fieldsFromSchema(schema);
    expect(defaultsFor(fields)).toEqual({
      amount: 1,
      enabled: false,
      optional: null,
    });
    expect(
      validateConfiguration(fields, { resource_ref: "logical-dataset" }),
    ).toEqual([]);
    expect(validateConfiguration(fields, {})).toEqual([
      { field: "resource_ref", message: "This field is required." },
    ]);
  });
  it("checks integer, range, length, enum, nullable and typed list constraints", () => {
    const fields = fieldsFromSchema(schema);
    expect(
      validateConfiguration(fields, { amount: 1.5, resource_ref: "" }),
    ).toHaveLength(2);
    expect(
      validateConfiguration(fields, {
        amount: 11,
        resource_ref: "r",
        choice: "unknown",
        columns: ["a", "a"],
      }),
    ).toHaveLength(3);
    expect(
      validateConfiguration(fields, { resource_ref: "r", optional: null }),
    ).toEqual([]);
    expect(
      validateConfiguration(fields, { resource_ref: "r", columns: [1] }),
    ).toHaveLength(1);
    expect(
      validateConfiguration(fields, { resource_ref: "r", undeclared: true }),
    ).toHaveLength(1);
  });
  it("rejects unsupported rules instead of claiming valid configuration", () => {
    for (const property of [
      { type: "object" },
      { type: "string", pattern: "a" },
      { $ref: "#/$defs/Secret" },
      { anyOf: [{ type: "integer" }, { type: "string" }] },
      { type: "string", anyOf: "invalid" },
      { type: "array", items: { type: "string" }, minItems: -1 },
      { type: "string", enum: [{ nested: "unsupported" }] },
      { type: "string", const: { nested: "unsupported" } },
    ]) {
      expect(() =>
        fieldsFromSchema({
          type: "object",
          additionalProperties: false,
          properties: { value: property },
        }),
      ).toThrow();
    }
    expect(() =>
      fieldsFromSchema({ ...schema, additionalProperties: true }),
    ).toThrow();
  });
  it("blocks credential keys, prototype pollution, nested secrets and non-finite numbers", () => {
    for (const value of [
      { api_key: "fake" },
      { nested: { password: "fake" } },
      { x: Infinity },
      { x: new Date() },
      { resource_ref: "C:\\private\\input.csv" },
      { resource_ref: "/private/input.csv" },
      { local_path: "relative.csv" },
      JSON.parse('{"__proto__": {"x": 1}}'),
    ])
      expect(() => assertPublic(value)).toThrow();
    expect(() =>
      assertPublic({
        resource_ref: "logical-resource",
        values: [1, false, null],
      }),
    ).not.toThrow();
  });
});

// Regression: the actual quality/aggregate registry uses referenced objects.
const nestedSchema = {
  type: "object",
  additionalProperties: false,
  required: ["columns"],
  $defs: {
    Column: {
      type: "object",
      additionalProperties: false,
      required: ["name", "dtype"],
      properties: {
        name: { type: "string", minLength: 1 },
        dtype: { type: "string", enum: ["integer", "string"] },
        nullable: { type: "boolean", default: false },
      },
    },
  },
  properties: {
    columns: { type: "array", minItems: 1, items: { $ref: "#/$defs/Column" } },
  },
};
it("accepts public referenced object lists and applies nested validation/defaults", () => {
  const fields = fieldsFromSchema(nestedSchema);
  expect(
    validateConfiguration(fields, {
      columns: [{ name: "reading", dtype: "integer" }],
    }),
  ).toEqual([]);
  for (const column of [
    { name: "x" },
    { name: "", dtype: "integer" },
    { name: "x", dtype: "unknown" },
    { name: "x", dtype: "integer", nullable: "false" },
    { name: "x", dtype: "integer", extra: 1 },
  ] as Configuration[])
    expect(validateConfiguration(fields, { columns: [column] })).toHaveLength(
      1,
    );
});
it("rejects recursive, missing and external schema definitions", () => {
  for (const ref of [
    "https://example.invalid/schema",
    "#/$defs/Missing",
    "#/$defs/Loop",
  ])
    expect(() =>
      fieldsFromSchema({
        ...nestedSchema,
        $defs: { Loop: { type: "array", items: { $ref: "#/$defs/Loop" } } },
        properties: { value: { $ref: ref } },
        required: ["value"],
      }),
    ).toThrow();
});
