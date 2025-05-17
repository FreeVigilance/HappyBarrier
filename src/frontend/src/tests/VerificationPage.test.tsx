import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import VerificationPage from "../pages/VerificationPage";
import fetchMock from "jest-fetch-mock";

// Enable fetch mocks
fetchMock.enableMocks();

// Mock useNavigate
jest.mock("react-router-dom", () => {
  const original = jest.requireActual("react-router-dom");
  return {
    ...original,
    useNavigate: () => jest.fn(),
  };
});

describe("VerificationPage", () => {
  beforeEach(() => {
    fetchMock.resetMocks();
  });

  const renderWithRouter = (state = {}) => {
    return render(
      <MemoryRouter initialEntries={[{ pathname: "/verifyuser", state }]}>
        <Routes>
          <Route path="/verifyuser" element={<VerificationPage />} />
        </Routes>
      </MemoryRouter>,
    );
  };

  it("renders input and submit button", () => {
    renderWithRouter({ phone: "+79991234567", verification_token: "token123" });
    expect(screen.getByLabelText(/код/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /подтвердить/i }),
    ).toBeInTheDocument();
  });

  it("shows error for invalid code format", async () => {
    renderWithRouter({ phone: "+79991234567", verification_token: "token123" });

    fireEvent.change(screen.getByLabelText(/код/i), {
      target: { value: "123" },
    });
    fireEvent.click(screen.getByRole("button", { name: /подтвердить/i }));

    expect(
      await screen.findByText(/код должен содержать 6 цифр/i),
    ).toBeInTheDocument();
  });

  it("handles successful verification and login", async () => {
    fetchMock.mockResponses(
      [
        JSON.stringify({ message: "Code verified successfully." }),
        { status: 200 },
      ],
      [
        JSON.stringify({ access_token: "access", refresh_token: "refresh" }),
        { status: 200 },
      ],
    );

    renderWithRouter({ phone: "+79991234567", verification_token: "token123" });

    fireEvent.change(screen.getByLabelText(/код/i), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByRole("button", { name: /подтвердить/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });
  });
});
