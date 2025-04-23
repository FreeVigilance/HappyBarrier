import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { MemoryRouter } from "react-router-dom";
import LoginUserPage from "../pages/LoginUserPage";

// Добавляем поддержку TextEncoder и TextDecoder
import { TextEncoder, TextDecoder } from "util";
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder as any;

// Mock navigate
const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));

describe("LoginUserPage", () => {
  test("рендерится корректно", () => {
    render(
      <MemoryRouter>
        <LoginUserPage />
      </MemoryRouter>,
    );
    expect(screen.getByText(/вход/i)).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Введите номер телефона/i),
    ).toBeInTheDocument();
  });

  test("разрешает ввод номера телефона", () => {
    render(
      <MemoryRouter>
        <LoginUserPage />
      </MemoryRouter>,
    );
    const input = screen.getByLabelText(/Введите номер телефона/i);
    fireEvent.change(input, { target: { value: "+79991234567" } });
    expect((input as HTMLInputElement).value).toBe("+79991234567");
  });

  test("перенаправляет на /verifyadmin при номере администратора", async () => {
    render(
      <MemoryRouter>
        <LoginUserPage />
      </MemoryRouter>,
    );
    const input = screen.getByLabelText(/Введите номер телефона/i);
    fireEvent.change(input, { target: { value: "+78005553535" } });
    const button = screen.getByText(/далее/i);
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/verifyadmin");
    });
  });

  test("перенаправляет на /verifyuser при любом другом номере", async () => {
    render(
      <MemoryRouter>
        <LoginUserPage />
      </MemoryRouter>,
    );
    const input = screen.getByLabelText(/Введите номер телефона/i);
    fireEvent.change(input, { target: { value: "+79998887766" } });
    const button = screen.getByText(/далее/i);
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/verifyuser");
    });
  });

  test("не позволяет ввести номер не начинающийся с +7", () => {
    render(
      <MemoryRouter>
        <LoginUserPage />
      </MemoryRouter>,
    );
    const input = screen.getByLabelText(/Введите номер телефона/i);
    fireEvent.change(input, { target: { value: "+1234567890" } });
    expect((input as HTMLInputElement).value).toBe("+7"); // Должен остаться +7
  });
});
