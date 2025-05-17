import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import VerifyAdminPage from "../pages/VerifyAdminPage";
import fetchMock from "jest-fetch-mock";

jest.mock("react-router-dom", () => {
  const original = jest.requireActual("react-router-dom");
  return {
    ...original,
    useNavigate: () => jest.fn(),
  };
});

describe("VerifyAdminPage", () => {
  beforeEach(() => {
    fetchMock.resetMocks();
  });

  const renderWithRouter = (state = {}) => {
    render(
      <MemoryRouter initialEntries={[{ pathname: "/verifyadmin", state }]}>
        <Routes>
          <Route path="/verifyadmin" element={<VerifyAdminPage />} />
        </Routes>
      </MemoryRouter>,
    );
  };

  it("рендерит поле ввода пароля и кнопки", () => {
    renderWithRouter({ phone: "+79991234567", verification_token: "abc123" });
    expect(screen.getByPlaceholderText(/введите пароль/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /далее/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /восстановить пароль/i }),
    ).toBeInTheDocument();
  });

  it("показывает ошибку, если пароль пустой", async () => {
    renderWithRouter({ phone: "+79991234567", verification_token: "abc123" });
    fireEvent.click(screen.getByRole("button", { name: /далее/i }));
    expect(
      await screen.findByText(/пароль не должен быть пустым/i),
    ).toBeInTheDocument();
  });

  it("выполняет успешную верификацию пароля", async () => {
    fetchMock.mockResponseOnce(
      JSON.stringify({ message: "Password verified successfully." }),
      { status: 200 },
    );

    renderWithRouter({ phone: "+79991234567", verification_token: "abc123" });

    fireEvent.change(screen.getByPlaceholderText(/введите пароль/i), {
      target: { value: "adminpass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /далее/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/auth/admin/password_verification/",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({
            phone: "+79991234567",
            password: "adminpass",
          }),
        }),
      );
    });
  });

  it("показывает сообщение об ошибке, если пароль неверный", async () => {
    fetchMock.mockResponseOnce(JSON.stringify({ detail: "Неверный пароль" }), {
      status: 401,
    });

    renderWithRouter({ phone: "+79991234567", verification_token: "abc123" });

    fireEvent.change(screen.getByPlaceholderText(/введите пароль/i), {
      target: { value: "wrongpass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /далее/i }));

    expect(await screen.findByText(/неверный пароль/i)).toBeInTheDocument();
  });

  it("отображает ошибку сети при сбое запроса", async () => {
    fetchMock.mockRejectOnce(new Error("Network error"));

    renderWithRouter({ phone: "+79991234567", verification_token: "abc123" });

    fireEvent.change(screen.getByPlaceholderText(/введите пароль/i), {
      target: { value: "anypass" },
    });
    fireEvent.click(screen.getByRole("button", { name: /далее/i }));

    expect(
      await screen.findByText(/не удалось связаться с сервером/i),
    ).toBeInTheDocument();
  });
});
