// AI contribution: 50% or more AI-generated
import { ApiError } from "./client";

export const object = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

export const invalidResponse = (message: string) => (): never => {
  throw new ApiError(message, "invalid-response");
};
