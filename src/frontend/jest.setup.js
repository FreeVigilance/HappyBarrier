/* eslint-disable no-undef */

// Импорт расширений expect
require("@testing-library/jest-dom");

// Поддержка TextEncoder/TextDecoder в среде Node.js
const { TextEncoder, TextDecoder } = require("util");
global.TextEncoder = TextEncoder;
global.TextDecoder = TextDecoder;

// Активация jest-fetch-mock
const fetchMock = require("jest-fetch-mock");
fetchMock.enableMocks();
