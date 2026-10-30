import { useState } from "react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import NumberField from "./NumberField";

function Harness({ initial = "" }) {
  const [value, setValue] = useState(initial);
  return <NumberField ariaLabel="Budget" value={value} onChange={setValue} maxLength={8} />;
}

describe("NumberField (manual budget / distance entry)", () => {
  it("is a text input with a numeric keypad hint, so no spinner arrows exist", () => {
    render(<Harness />);
    const input = screen.getByLabelText("Budget");
    expect(input).toHaveAttribute("type", "text");
    expect(input).toHaveAttribute("inputmode", "numeric");
  });

  it("can be cleared and stays empty (not turned into 0) while typing", async () => {
    const user = userEvent.setup();
    render(<Harness initial="20000" />);
    const input = screen.getByLabelText("Budget");
    await user.clear(input);
    expect(input).toHaveValue("");
    await user.type(input, "5");
    expect(input).toHaveValue("5");
  });

  it("drops non-digits, accepts pasted formatted amounts and caps the length", async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const input = screen.getByLabelText("Budget");
    await user.type(input, "ab-12e");
    expect(input).toHaveValue("12");
    await user.clear(input);
    await user.click(input);
    await user.paste("₹ 20,000");
    expect(input).toHaveValue("20000");
    await user.clear(input);
    await user.type(input, "123456789012");
    expect(input).toHaveValue("12345678");
  });
});
