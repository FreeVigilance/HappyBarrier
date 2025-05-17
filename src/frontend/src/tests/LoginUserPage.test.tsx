import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { MemoryRouter } from "react-router-dom";
import fetchMock from "jest-fetch-mock";
import LoginUserPage from "../pages/LoginUserPage";

// Поддержка TextEncoder / TextDecoder в Node.js
import { TextEncoder, TextDecoder } from "util";
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder as any;

// Mock useNavigate
const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));

beforeEach(() => {
  fetchMock.resetMocks();
  mockNavigate.mockReset();
});

describe("LoginUserPage", () => {
  test("рендерится корректно", () => {
    render(
      <MemoryRouter>
        <LoginUserPage />
      </MemoryRouter>,
    );
    expect(
      screen.getByLabelText(/Введите номер телефона/i),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Далее/i })).toBeInTheDocument();
  });

  test("не отправляет запрос при неправильном номере", () => {
    render(
      <MemoryRouter>
        <LoginUserPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Введите номер телефона/i), {
      target: { value: "+7" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Далее/i }));

    expect(fetchMock).not.toHaveBeenCalled();
  });

  test("навигация к админ-проверке, если пользователь — админ", async () => {
    fetchMock.mockResponseOnce(JSON.stringify({ is_admin: true }));

    render(
      <MemoryRouter>
        <LoginUserPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Введите номер телефона/i), {
      target: { value: "+79991234567" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Далее/i }));

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith("/verifyadmin", {
        state: { phone: "+79991234567" },
      }),
    );
  });

  test("отправка кода и переход к verifyuser для обычного пользователя", async () => {
    fetchMock.mockResponses(
      [JSON.stringify({ is_admin: false }), { status: 200 }],
      [
        JSON.stringify({ verification_token: "abc123", code: "1234" }),
        { status: 200 },
      ],
    );

    render(
      <MemoryRouter>
        <LoginUserPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Введите номер телефона/i), {
      target: { value: "+79991234567" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Далее/i }));

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith("/verifyuser", {
        state: { phone: "+79991234567", verification_token: "abc123" },
      }),
    );
  });

  test("ошибка при отправке кода — переход с ошибкой", async () => {
    fetchMock.mockResponses(
      [JSON.stringify({ is_admin: false }), { status: 200 }],
      [
        JSON.stringify({ error: "Too many attempts", retry: 60 }),
        { status: 429 },
      ],
    );

    render(
      <MemoryRouter>
        <LoginUserPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Введите номер телефона/i), {
      target: { value: "+79991234567" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Далее/i }));

    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith("/verifyuser", {
        state: {
          phone: "+79991234567",
          verification_token: null,
          error: "Ошибка при отправке кода. Попробуйте позже.",
        },
      }),
    );
  });

  test("ошибка сети при проверке", async () => {
    fetchMock.mockRejectOnce(new Error("Network error"));

    render(
      <MemoryRouter>
        <LoginUserPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText(/Введите номер телефона/i), {
      target: { value: "+79991234567" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Далее/i }));

    await waitFor(() =>
      expect(
        screen.getByText(/Ошибка сети. Попробуйте ещё раз./i),
      ).toBeInTheDocument(),
    );
  });
});
