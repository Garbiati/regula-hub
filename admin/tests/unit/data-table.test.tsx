import { describe, expect, it, vi } from "vitest";

import { render, screen, fireEvent, within } from "../test-utils";
import { DataTable } from "@/components/shared/data-table";
import type { ColumnDef } from "@tanstack/react-table";

interface TestRow {
  id: string;
  name: string;
  value: number;
}

const columns: ColumnDef<TestRow, unknown>[] = [
  { accessorKey: "id", header: "ID" },
  { accessorKey: "name", header: "Name" },
  { accessorKey: "value", header: "Value" },
];

function makeRows(count: number): TestRow[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `ID-${String(i + 1).padStart(3, "0")}`,
    name: `Item ${i + 1}`,
    value: (i + 1) * 10,
  }));
}

describe("DataTable", () => {
  it("renders all rows when data fits in one page", () => {
    const data = makeRows(5);
    render(<DataTable columns={columns} data={data} pageSize={50} />);

    expect(screen.getByText("ID-001")).toBeInTheDocument();
    expect(screen.getByText("ID-005")).toBeInTheDocument();
    expect(screen.getByText("Item 3")).toBeInTheDocument();
  });

  it("paginates when data exceeds page size", () => {
    const data = makeRows(100);
    render(<DataTable columns={columns} data={data} pageSize={25} />);

    // First page: items 1-25 visible
    expect(screen.getByText("ID-001")).toBeInTheDocument();
    expect(screen.getByText("ID-025")).toBeInTheDocument();
    // Item 26 should NOT be on the first page
    expect(screen.queryByText("ID-026")).not.toBeInTheDocument();

    // Navigate to next page
    const nextBtn = screen.getByText(">");
    fireEvent.click(nextBtn);

    // Second page: items 26-50 visible
    expect(screen.getByText("ID-026")).toBeInTheDocument();
    expect(screen.getByText("ID-050")).toBeInTheDocument();
    expect(screen.queryByText("ID-001")).not.toBeInTheDocument();
  });

  it("shows 'All' button that disables pagination", () => {
    const data = makeRows(60);
    render(<DataTable columns={columns} data={data} pageSize={25} />);

    // Initially paginated — item 26 not visible
    expect(screen.queryByText("ID-060")).not.toBeInTheDocument();

    // Click 'All'
    fireEvent.click(screen.getByText("All"));

    // All items visible
    expect(screen.getByText("ID-001")).toBeInTheDocument();
    expect(screen.getByText("ID-060")).toBeInTheDocument();
  });

  it("sorts by column when header is clicked", () => {
    const data: TestRow[] = [
      { id: "ID-003", name: "Charlie", value: 30 },
      { id: "ID-001", name: "Alice", value: 10 },
      { id: "ID-002", name: "Bob", value: 20 },
    ];
    render(<DataTable columns={columns} data={data} pageSize={50} />);

    // Click "Name" header to sort ascending
    fireEvent.click(screen.getByText("Name"));

    const rows = screen.getAllByRole("row");
    // rows[0] is header, data rows start at index 1
    expect(within(rows[1]).getByText("Alice")).toBeInTheDocument();
    expect(within(rows[2]).getByText("Bob")).toBeInTheDocument();
    expect(within(rows[3]).getByText("Charlie")).toBeInTheDocument();
  });

  it("filters by column text input", () => {
    const data: TestRow[] = [
      { id: "ID-001", name: "Alice", value: 10 },
      { id: "ID-002", name: "Bob", value: 20 },
      { id: "ID-003", name: "Charlie", value: 30 },
    ];
    render(<DataTable columns={columns} data={data} pageSize={50} />);

    // Find filter inputs (one per column)
    const filterInputs = screen.getAllByPlaceholderText("Filter...");
    // Type in the Name column filter (second input)
    fireEvent.change(filterInputs[1], { target: { value: "Ali" } });

    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.queryByText("Bob")).not.toBeInTheDocument();
    expect(screen.queryByText("Charlie")).not.toBeInTheDocument();
  });

  it("shows no results message when filter matches nothing", () => {
    const data = makeRows(3);
    render(<DataTable columns={columns} data={data} pageSize={50} />);

    const filterInputs = screen.getAllByPlaceholderText("Filter...");
    fireEvent.change(filterInputs[0], { target: { value: "NONEXISTENT" } });

    expect(screen.getByText("No records found")).toBeInTheDocument();
  });

  it("calls onRowClick when a row is clicked", () => {
    const data = makeRows(3);
    const onClick = vi.fn();
    render(<DataTable columns={columns} data={data} pageSize={50} onRowClick={onClick} />);

    fireEvent.click(screen.getByText("Item 2"));
    expect(onClick).toHaveBeenCalledWith(data[1]);
  });

  it("changes page size when a size button is clicked", () => {
    const data = makeRows(100);
    render(<DataTable columns={columns} data={data} pageSize={50} />);

    // Click page size 25
    fireEvent.click(screen.getByText("25"));

    // Should show 25 items — item 26 not visible
    expect(screen.getByText("ID-025")).toBeInTheDocument();
    expect(screen.queryByText("ID-026")).not.toBeInTheDocument();
  });
});
