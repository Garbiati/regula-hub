import { describe, expect, it, vi } from "vitest";

import { ErrorBoundary } from "@/components/shared/error-boundary";

import { fireEvent, render, screen } from "../test-utils";

const TEST_TRANSLATIONS = {
  title: "Something went wrong",
  guidance: "Try again later.",
  retry: "Try again",
};

function ThrowingChild({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error("Test error message");
  }
  return <div>Child content</div>;
}

describe("ErrorBoundary", () => {
  // Suppress React error boundary console.error noise during tests
  const originalError = console.error;
  beforeEach(() => {
    console.error = vi.fn();
  });
  afterEach(() => {
    console.error = originalError;
  });

  it("renders children normally when no error", () => {
    render(
      <ErrorBoundary translations={TEST_TRANSLATIONS}>
        <div>Normal content</div>
      </ErrorBoundary>,
    );
    expect(screen.getByText("Normal content")).toBeTruthy();
  });

  it("catches thrown error and shows error UI", () => {
    render(
      <ErrorBoundary translations={TEST_TRANSLATIONS}>
        <ThrowingChild shouldThrow />
      </ErrorBoundary>,
    );
    expect(screen.getByText("Something went wrong")).toBeTruthy();
    expect(screen.getByText("Test error message")).toBeTruthy();
    expect(screen.getByText("Try again")).toBeTruthy();
  });

  it("Try again button resets and re-renders children", () => {
    // We use a ref-like approach: first render throws, after reset it won't
    let shouldThrow = true;

    function ConditionalChild() {
      if (shouldThrow) {
        throw new Error("Boom");
      }
      return <div>Recovered content</div>;
    }

    render(
      <ErrorBoundary translations={TEST_TRANSLATIONS}>
        <ConditionalChild />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Something went wrong")).toBeTruthy();

    // Fix the "error"
    shouldThrow = false;
    fireEvent.click(screen.getByText("Try again"));

    expect(screen.getByText("Recovered content")).toBeTruthy();
  });
});
