import { describe, expect, it } from "vitest";

import { StatusBadge } from "@/components/shared/status-badge";

import { render, screen } from "../test-utils";

const labels = {
  notVerified: "Not verified",
  verifying: "Verifying...",
  valid: "Credential valid",
  invalid: "Credential invalid",
  error: "Connection error",
};

describe("StatusBadge", () => {
  it("renders idle state", () => {
    render(<StatusBadge status="idle" labels={labels} />);
    expect(screen.getByText("Not verified")).toBeTruthy();
  });

  it("renders checking state", () => {
    render(<StatusBadge status="checking" labels={labels} />);
    expect(screen.getByText("Verifying...")).toBeTruthy();
  });

  it("renders valid state", () => {
    render(<StatusBadge status="valid" labels={labels} />);
    expect(screen.getByText("Credential valid")).toBeTruthy();
  });

  it("renders invalid state", () => {
    render(<StatusBadge status="invalid" labels={labels} />);
    expect(screen.getByText("Credential invalid")).toBeTruthy();
  });

  it("renders error state", () => {
    render(<StatusBadge status="error" labels={labels} />);
    expect(screen.getByText("Connection error")).toBeTruthy();
  });
});
