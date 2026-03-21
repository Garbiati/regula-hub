import { describe, expect, it } from "vitest";

import { MetadataField } from "@/components/shared/metadata-field";

import { render, screen } from "../test-utils";

describe("MetadataField", () => {
  it("renders label and value", () => {
    render(<MetadataField label="Profile" value="videofonista" />);
    expect(screen.getByText("Profile")).toBeTruthy();
    expect(screen.getByText("videofonista")).toBeTruthy();
  });
});
