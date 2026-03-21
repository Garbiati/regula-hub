import { describe, expect, it } from "vitest";

import { ValidationResult } from "@/components/shared/validation-result";

import { render, screen } from "../test-utils";

describe("ValidationResult", () => {
  it("renders valid state", () => {
    render(<ValidationResult valid validLabel="Login valid" invalidLabel="Login invalid" />);
    expect(screen.getByText("Login valid")).toBeTruthy();
    expect(screen.queryByText("Login invalid")).toBeNull();
  });

  it("renders invalid state", () => {
    render(<ValidationResult valid={false} validLabel="Login valid" invalidLabel="Login invalid" />);
    expect(screen.getByText("Login invalid")).toBeTruthy();
    expect(screen.queryByText("Login valid")).toBeNull();
  });
});
